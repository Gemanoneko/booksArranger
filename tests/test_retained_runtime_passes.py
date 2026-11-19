"""0.30.0 item A: the background passes run for a catalog in retained-runtime mode.

Since the 14 Nov portable move Sergei's catalog runs in retained-runtime mode, permanently: a portable binding needs its
source detach, and a detach belongs to a retained-runtime registration (NativeContext._activation). v0.28.2 turned every
background pass off in that mode (web_server: the source check, housekeeping, the published-book check, the restart
restore; 0.30.0 copied it to the queued-actions restore), so none of them ran for him. They run again; a retained job
(historical staging the move copied without resume or disposal authority) is left alone by each of them, as its retry,
cleanup and recovery purge already were.

The fixture is the relocation tests' replay of both moves (test_recovery_ancestry_moves.MovesReplay) with the retained
runtime registered on the selected context as NativeContext.catalog_lease records it, so retained_runtime, retained_job
and retained_path are the production ones.
"""
import contextlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import Mock, patch
import uuid

from action_queue import ActionQueue
from audio_jobs import AudioJobs
from encoding_policy import PROFILE
from merge_service import MergeService
import scanner
from series_backfill import SeriesBackfill
from storage_relocation import _key
import storage_relocation_native as native
from storage_retained_runtime import SCHEMA, index_members
from test_recovery_ancestry_moves import SCOPE, MovesReplay
import web_server
from working_lifecycle import WorkingLifecycle


class Passes:
    """A catalog service that records which background pass the server started."""

    def __init__(self, inventory, cache, progress=None):
        self.inventory = inventory
        self.calls = []

    def check_sources(self, **options):
        self.calls.append('source check')
        return {'roots': [], 'removed': [], 'folders': [], 'files': [], 'cleared': []}

    def start_retention(self, admission):
        self.calls.append('housekeeping')

    def start_published_check(self):
        self.calls.append('published check')

    def restore_work_after_restart(self):
        self.calls.append('saved work')

    def status_snapshot(self):
        return {'state': 'Paused', 'queued': 0, 'jobs': [], 'attention_counts': {'retry': 0}}

    state = status_snapshot

    def cached_page(self, limit, offset, search, status, group=None):
        return {'rows': [], 'total': 0}

    def close(self):
        pass


@unittest.skipUnless(os.name == 'nt', 'Windows native identities and junctions')
class RetainedRuntimePassTests(MovesReplay, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.move_explicitly()
        self.admit(*self.move_portably())
        self.catalog = self.data / 'inventory.sqlite3'
        self.held, self.ordinary = str(uuid.uuid4()), str(uuid.uuid4())  # a retained job and an ordinary one
        self.retain(self.held)
        self.assertTrue(native.retained_runtime(self.catalog), 'fixture: the catalog runs in retained-runtime mode')
        self.assertTrue(native.retained_job(self.catalog, self.held))
        self.assertFalse(native.retained_job(self.catalog, self.ordinary))
        self.assertTrue(native.retained_path(self.data / 'merge-cache' / 'audio-staging' / self.held / self.attempt))

    def retain(self, job):
        """The retained runtime of the selected relocation, as NativeContext.catalog_lease records it after admitting the
        registration: one retained closed stage directory of `job` (historical staging the move copied)."""
        context = native.current()
        self.attempt = str(uuid.uuid4())
        relative = SCOPE + '\\merge-cache\\audio-staging\\' + job + '\\' + self.attempt
        member = {'relative': relative, 'category': 'retained-closed-stage-directory', 'job_id': job,
                  'attempt_id': self.attempt, 'resume_authority': False, 'disposal_authority': False}
        members = index_members([member], SCOPE)
        context.database = str(self.catalog)
        context.retained = {'schema': SCHEMA, 'scope': SCOPE, 'members': [member], 'historical_members': [],
                            'target_members': {_key(relative): {'native': {'relative': relative}}}}
        context.retained_members, context.retained_jobs = members, frozenset({job})

        def release():  # catalog_lease's own release
            context.database = context.retained = None
            context.retained_members, context.retained_jobs = {}, frozenset()
        self.addCleanup(release)

    def inventory(self):
        roots = {name: self.area / 'Library' / name for name in ('Audiobooks', 'Podcasts', 'Ebooks')}
        for path in roots.values():
            path.mkdir(parents=True, exist_ok=True)
        return scanner.Inventory(self.catalog, {name: str(path) for name, path in roots.items()})

    def test_loading_starts_every_pass_for_a_retained_catalog(self):
        restored = []
        with patch.object(ActionQueue, 'restore', autospec=True, side_effect=lambda queue: restored.append(queue)):
            server = web_server.BrowserServer(('127.0.0.1', 0), self.inventory(), Passes, defer=True)
            try:
                server.start_loading().join(20)
                self.assertTrue(server.loading.finished, server.loading.error)
                self.assertEqual(server.merge.calls, ['source check', 'housekeeping', 'published check', 'saved work'])
                self.assertEqual(len(restored), 1, 'the queued actions saved before the last close come back')
                # The pass after a finished scan and after Check again (a drive that answers again) is the same call.
                self.assertEqual(server._check_sources(server.merge, roots=['Z:\\Audiobooks'], wait=True)['roots'], [])
            finally:
                server.server_close()

    def service(self):
        """A MergeService's own sweep code over stand-in collaborators (test_backup_rule.service), on the retained catalog."""
        merge = MergeService.__new__(MergeService)
        merge.operation_lock = threading.RLock()
        merge.inventory = SimpleNamespace(worker=None, database=str(self.catalog))
        merge._retention_stop, merge._retention_wake, merge._retention_thread = threading.Event(), threading.Event(), None
        merge._manual_recovery = merge._post_current = merge.storage_cleanup = None
        merge.working = SimpleNamespace(reconcile=lambda **options: None, schedule_published=lambda job_id: None)
        merge.jobs = SimpleNamespace(_thread=SimpleNamespace(is_alive=lambda: True), start_published_check=Mock())
        merge.cleanup = SimpleNamespace(thread=None, current=None, _rows=lambda *args: [])
        return merge

    def test_housekeeping_purges_no_recovery_copies_of_a_retained_job(self):
        merge, purged, done = self.service(), [], threading.Event()
        merge.recovery = SimpleNamespace(due=lambda: [self.held, self.ordinary], _set=Mock(),
                                         purge=lambda job_id, *rest: (purged.append(job_id), done.set()))
        merge.start_retention(contextlib.nullcontext)
        try:
            self.assertTrue(done.wait(10))
        finally:
            merge._retention_stop.set();merge._retention_wake.set();merge._retention_thread.join(10)
        self.assertEqual(purged, [self.ordinary], 'a retained job keeps its recovery copies and its row, as after its cleanup')
        merge.recovery._set.assert_not_called()

    def test_finished_book_cleanup_skips_a_retained_job(self):
        merge, pruned = self.service(), []
        merge.storage_cleanup = SimpleNamespace(status=lambda: [], working_pending=lambda job_id: True, _diagnose=Mock())
        merge.jobs._rows = lambda sql, *args: [{'job_id': self.held}, {'job_id': self.ordinary}]
        merge.cleanup.status = lambda job_id: None
        merge._maintenance_book = lambda job_id, phase: contextlib.nullcontext()
        merge._prune_working = lambda job_id, raise_errors=False: pruned.append(('working', job_id))
        merge._prune_completed = lambda job_id, stop=None: pruned.append(('temporary', job_id))
        merge._finish_temporary_cleanups()
        self.assertEqual(pruned, [('working', self.ordinary), ('temporary', self.ordinary)])

    def test_working_reconcile_is_not_stopped_by_a_retained_attempt(self):
        life = WorkingLifecycle(self.catalog, self.data / 'merge-cache' / 'audio-staging')
        with scanner.connect(self.catalog) as db:
            for job, updated in ((self.held, '2026-11-01T00:00:00'), (self.ordinary, '2026-11-02T00:00:00')):
                db.execute("INSERT INTO working_attempts VALUES(?,?,'{}','',?,'closed','',?)", (job, str(uuid.uuid4()), 'closed', updated))
        visited = []
        life.terminal = lambda job_id, attempt_id: visited.append(job_id)
        life.reconcile(limit=1)
        self.assertEqual(visited, [self.ordinary], 'the oldest attempt is retained: the next one is reconciled, not none')

    def finished(self, jobs, state='completed'):
        seed = AudioJobs(self.catalog, None, lambda manifest: True, lambda record: True)
        self.addCleanup(seed.close)
        for job in jobs:
            seed.enqueue({'job_id': job, 'candidate_id': str(uuid.uuid4()), 'candidate_revision': 1,
                          'sources': [{'sha256': 'a' * 64, 'fingerprint': {}}], 'destination': 'fixture', 'profile': PROFILE,
                          'evidence': {}, 'cover': {}, 'metadata': {'title': 'Book', 'canonical_author': 'Author'}})
            output = json.dumps({'job_id': job, 'final_path': str(self.area / 'Library' / (job + '.m4b')), 'sha256': 'b' * 64,
                                 'size': 1, 'validation': {'passed': True}}) if state == 'completed' else None
            seed._update(job, state=state, stage=state, output=output)

    def test_series_backfill_never_changes_a_retained_job(self):
        self.finished([self.held, self.ordinary])
        merge = SimpleNamespace(inventory=SimpleNamespace(database=str(self.catalog)), stage_root=self.data / 'merge-cache' / 'audio-staging')
        backfill = SeriesBackfill(merge, stage=self.area / 'series-stage')
        self.assertEqual([row['job_id'] for row in backfill.candidates()], [self.ordinary])

    def test_the_regroup_pass_never_sets_a_retained_job_aside(self):
        self.finished([self.held, self.ordinary], state='needs attention')
        merge = MergeService.__new__(MergeService)
        merge.inventory = SimpleNamespace(database=str(self.catalog))
        looked = []
        merge._partial_folder_job = lambda db, manifest: looked.append(manifest['job_id']) and False
        self.assertEqual(merge.regroup_partial_jobs(), [])
        self.assertEqual(looked, [self.ordinary])


if __name__ == '__main__':
    unittest.main()
