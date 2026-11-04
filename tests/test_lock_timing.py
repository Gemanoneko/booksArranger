"""0.22.1, backlog items 6-8 (Ender's diagnosis, 2026-10-25): presses must never wait behind background work.

On the live catalog the status computation held Inventory.group_lock for about 500 publication lookups (15 s), on every
research step and every poll; the list, Scan again, Remove from list, Delete and approvals queued behind it (54-100 s),
and an approval ran Start's re-check of every finished book under the operation lock (4-5 min). Real private audio
fixtures; the slow lookup is a stub that sleeps. No network, no library access."""
import contextlib, threading, time, unittest
from pathlib import Path
from unittest.mock import patch

from merge_service import MergeService, operation
from scanner import connect
from scan_wait import finish_scan, finish_thread as finish


def finish_thread(thread):
    finish(thread, 'A test thread')
from test_approve_as_is import ApproveFixture, tone


class SourceFolderDispatchTests(unittest.TestCase):
    """A catalog-only navigation press must not wait for unrelated grouping work."""
    def setUp(self):
        from test_merge_service import MergeTests
        MergeTests.setUp(self)
    def tearDown(self):
        from test_merge_service import MergeTests
        MergeTests.tearDown(self)
    def test_source_folder_dispatches_while_unrelated_worker_holds_group_lock(self):
        row=self.service.reviews._row('Audiobooks',self.inv.candidates('Audiobooks')['rows'][0]['id'])
        with connect(self.inv.database) as db:db.execute('UPDATE book_catalog_revision SET revision=revision+1 WHERE id=1')
        entered=threading.Event();release=threading.Event();dispatched=threading.Event();errors=[];marks={}
        def worker():
            with self.inv.group_lock:entered.set();release.wait(5)
        def open_folder():
            marks['request']=time.monotonic()
            try:self.service.open_folder('Audiobooks','candidates',row['id'])
            except Exception as error:errors.append(error)
            finally:marks['response']=time.monotonic()
        def dispatch(path):
            self.assertEqual(path,str(self.sources[0].parent));marks['dispatch']=time.monotonic();dispatched.set()
        holder=threading.Thread(target=worker);opener=threading.Thread(target=open_folder)
        with patch.object(self.service,'dispatch_folder',side_effect=dispatch):
            holder.start();self.assertTrue(entered.wait(2));opener.start()
            prompt=dispatched.wait(.5)
            marks['worker_release']=time.monotonic();release.set();holder.join(5);opener.join(5)
        self.assertFalse(holder.is_alive());self.assertFalse(opener.is_alive());self.assertEqual(errors,[])
        print('FOLDER_DISPATCH_TIMING '+str({key:round(value-marks['request'],6) for key,value in marks.items()}))
        self.assertTrue(prompt,'Folder navigation waited for unrelated source grouping; dispatch happened only after the worker released group_lock')

    def test_normal_http_source_folder_route_does_not_wait_for_book_work(self):
        from test_merge_http import MergeHTTPTests
        route=MergeHTTPTests();route.setUp();self.addCleanup(route.tearDown)
        route.server.inventory=self.inv;route.server.merge=self.service
        row=self.inv.candidates('Audiobooks')['rows'][0]
        with connect(self.inv.database) as db:db.execute('UPDATE book_catalog_revision SET revision=revision+1 WHERE id=1')
        entered=threading.Event();release=threading.Event();dispatched=threading.Event();responses=[]
        def worker():
            with self.inv.group_lock,self.service.reviews.lock,self.service.operation_lock:entered.set();release.wait(5)
        def request():responses.append(route.call('/api/open-folder',{'library':'Audiobooks','view':'candidates','id':row['id'],'folder_kind':'source'}))
        holder=threading.Thread(target=worker);caller=threading.Thread(target=request)
        with patch.object(self.service,'dispatch_folder',side_effect=lambda folder:dispatched.set()):
            holder.start();self.assertTrue(entered.wait(2));caller.start();prompt=dispatched.wait(.5)
            release.set();holder.join(5);caller.join(5)
        self.assertFalse(holder.is_alive());self.assertFalse(caller.is_alive());self.assertTrue(prompt)
        self.assertEqual(responses[0][:2],(200,{'opened':True}));self.assertEqual(route.server.merge_admissions,0)
        with patch.object(self.service,'dispatch_folder',side_effect=PermissionError(13,'Private permission denial')):
            response=route.call('/api/open-folder',{'library':'Audiobooks','view':'candidates','id':row['id']})
        self.assertEqual(response[0],400);self.assertEqual(response[1]['code'],'folder_access_denied')
        self.assertEqual(response[1]['folder'],str(self.sources[0].parent));self.assertNotIn('drive',response[1]['error'])

    def test_edit_names_http_read_does_not_wait_for_unrelated_grouping(self):
        from test_merge_http import MergeHTTPTests
        route=MergeHTTPTests();route.setUp();self.addCleanup(route.tearDown);route.server.inventory=self.inv;route.server.merge=self.service
        row=self.inv.candidates('Audiobooks')['rows'][0]
        with connect(self.inv.database) as db:db.execute('UPDATE book_catalog_revision SET revision=revision+1 WHERE id=1')
        entered=threading.Event();release=threading.Event();answered=threading.Event();responses=[];marks={};scope=[]
        approval_before=dict(self.service.__dict__.get('_approval_results',{}));peers_before=dict(self.service.__dict__.get('_shared_peers',{}))
        def worker():
            with self.inv.group_lock,self.service.reviews.lock,self.service.operation_lock:entered.set();release.wait(5)
        def request():
            marks['request']=time.monotonic();responses.append(route.call('/api/candidate/names',{'library':'Audiobooks','id':row['id'],'revision':row['revision']}));marks['response']=time.monotonic();scope.append(getattr(self.service.reviews.page_local,'catalog_only',False));answered.set()
        holder=threading.Thread(target=worker);caller=threading.Thread(target=request)
        holder.start();self.assertTrue(entered.wait(2));caller.start();prompt=answered.wait(.5);marks['worker_release']=time.monotonic();release.set();holder.join(5);caller.join(5)
        self.assertFalse(holder.is_alive());self.assertFalse(caller.is_alive())
        print('NAMES_READ_TIMING '+str({key:round(value-marks['request'],6) for key,value in marks.items()}))
        self.assertEqual(responses[0][0],200,responses);self.assertIn('series',responses[0][1]['editor']['fields']);self.assertIn('universe',responses[0][1]['editor']['fields'])
        self.assertTrue(prompt,'Edit names waited for an unrelated grouping/source worker')
        self.assertEqual(scope,[False]);self.assertEqual(self.service.__dict__.get('_approval_results',{}),approval_before);self.assertEqual(self.service.__dict__.get('_shared_peers',{}),peers_before)

    def test_output_folder_and_gone_source_fallback_do_not_wait_for_grouping(self):
        row=self.inv.candidates('Audiobooks')['rows'][0];source_folder=self.sources[0].parent
        source_folder.rename(self.audio/'Kept private source');output=self.audio/'Sorted';output.mkdir();final=output/'book.m4b';final.write_bytes(b'private recorded output')
        with connect(self.inv.database) as db:db.execute('UPDATE book_catalog_revision SET revision=revision+1 WHERE id=1')
        entered=threading.Event();release=threading.Event();done=threading.Event();answers=[];opened=[]
        def worker():
            with self.inv.group_lock,self.service.reviews.lock:entered.set();release.wait(5)
        def navigate():
            for kind in ('output','source'):answers.append(self.service.open_folder('Audiobooks','candidates',row['id'],kind))
            done.set()
        state={'state':'verified','path':str(final),'identity':'private-key'}
        with patch.object(self.service.publications,'describe',return_value=state),patch.object(self.service.publications,'publication',return_value={}),patch.object(self.service.publications,'protected',side_effect=lambda value:contextlib.nullcontext((None,'private-key'))),patch.object(self.service,'dispatch_folder',side_effect=opened.append):
            holder=threading.Thread(target=worker);caller=threading.Thread(target=navigate);holder.start();self.assertTrue(entered.wait(2));caller.start();prompt=done.wait(.5);release.set();holder.join(5);caller.join(5)
        self.assertFalse(holder.is_alive());self.assertFalse(caller.is_alive());self.assertTrue(prompt)
        self.assertEqual(opened,[str(output),str(output)]);self.assertTrue(answers[0]['opened']);self.assertEqual(answers[1]['fallback'],'output')

    def test_edit_names_save_has_finite_busy_reply_then_preserves_fresh_cas(self):
        from test_merge_http import MergeHTTPTests
        route=MergeHTTPTests();route.setUp();self.addCleanup(route.tearDown);route.server.inventory=self.inv;route.server.merge=self.service
        row=self.inv.candidates('Audiobooks')['rows'][0]
        with connect(self.inv.database) as db:db.execute('UPDATE book_catalog_revision SET revision=revision+1 WHERE id=1')
        entered=threading.Event();release=threading.Event();answered=threading.Event();responses=[]
        values={'title':'B','author':'A','series':'S','number':'1','universe':'W','collection':False}
        payload={'library':'Audiobooks','id':row['id'],'revision':row['revision'],'names':values}
        def worker():
            with self.inv.group_lock,self.service.reviews.lock,self.service.operation_lock:entered.set();release.wait(5)
        def save():responses.append(route.call('/api/candidate/names-save',payload));answered.set()
        holder=threading.Thread(target=worker);caller=threading.Thread(target=save);holder.start();self.assertTrue(entered.wait(2));caller.start();prompt=answered.wait(.5)
        release.set();holder.join(5);caller.join(5);self.assertFalse(holder.is_alive());self.assertFalse(caller.is_alive())
        self.assertTrue(prompt,'Save must answer explicitly while unrelated book work holds its admission locks')
        self.assertEqual(responses[0][0],409,responses);self.assertEqual(responses[0][1]['code'],'busy');self.assertIsNone(responses[0][1]['row'])
        response=route.call('/api/candidate/names-save',payload);self.assertEqual(response[0],200,response)
        import entered_names
        current=self.service.reviews._row('Audiobooks',row['id']);saved=entered_names.book_values(self.inv.database,current)
        self.assertEqual(saved['series'],'S');self.assertEqual(saved['universe'],'W');self.assertEqual(saved['title'],'B')
        with connect(self.inv.database) as db:db.execute('UPDATE book_groups SET revision=revision+1 WHERE id=?',(row['id'],))
        self.assertEqual(route.call('/api/candidate/names-save',payload)[0],409)


class SlowLookup:
    """Every publication lookup sleeps `seconds` first (the live catalog's 433 relocations took 19 s in all)."""
    def __init__(self, service, seconds):
        self.service, self.seconds, self.started = service, seconds, threading.Event()
        self.real = service.publication_bindings.lookup

    def __call__(self, db, record, *args, **kwargs):
        self.started.set(); time.sleep(self.seconds)
        return self.real(db, record, *args, **kwargs)

    def __enter__(self):
        self.service.__dict__.pop('_lookups', None)  # no answer kept from before
        self.patch = patch.object(self.service.publication_bindings, 'lookup', self)
        self.patch.start(); return self

    def __exit__(self, *exc):
        self.patch.stop()


class LockTimingTests(ApproveFixture):
    def converted(self, title='Ясно'):
        tone(self.audio / 'Unsorted' / title / (title + '.mp3'), self.cover, album=title, artist='Иван Петров')

    def approve_all(self, folder='Ясно'):
        for row in self.service.reviews.page()['rows']:
            if all(Path(m['path']).parent.name == folder for m in row['members']):
                self.service.approve_book(row['id'], row['revision'])
        self.start_and_wait()
        jobs = self.service.jobs.status()['jobs']
        self.assertTrue(jobs and all(job['state'] == 'completed' for job in jobs), jobs)
        return jobs

    def timed(self, call):
        started = time.monotonic(); value = call(); return value, time.monotonic() - started

    def in_thread(self, call):
        thread = threading.Thread(target=call, daemon=True); thread.start()
        self.addCleanup(finish_thread, thread)
        return thread

    def test_another_thread_gets_the_group_lock_within_100_ms_during_a_slow_publication_lookup(self):
        self.converted(); self.start(); self.approve_all()
        with SlowLookup(self.service, 2.0) as slow:
            status = self.in_thread(self.service.progress_books)
            self.assertTrue(slow.started.wait(15), 'positive control: the status computation looks the book up')
            got, waited = self.timed(lambda: self.inv.group_lock.acquire(timeout=1.5))
            if got: self.inv.group_lock.release()
            self.assertTrue(got, 'the lookup held group_lock')
            self.assertLess(waited, 0.1)
            finish_thread(status)
        # Positive control: stale groups (the catalog changed) are still rebuilt under the lock, before the read.
        with connect(self.inv.database) as db: db.execute('UPDATE book_catalog_revision SET revision=revision+1 WHERE id=1')
        held, release = threading.Event(), threading.Event()
        def approval():
            with self.inv.group_lock: held.set(); release.wait(30)
        self.in_thread(approval); self.assertTrue(held.wait(5)); self.addCleanup(release.set)
        rebuild = self.in_thread(self.service.progress_books); rebuild.join(1)
        self.assertTrue(rebuild.is_alive(), 'a rebuild waits for the lock')
        release.set(); finish_thread(rebuild)

    def test_the_second_status_reuses_each_lookup_and_a_relocation_change_looks_again(self):
        self.converted(); self.start(); self.approve_all()
        calls = []
        real = self.service.publication_bindings.lookup
        self.service.__dict__.pop('_lookups', None)  # the status polls of wait() kept their answer
        with patch.object(self.service.publication_bindings, 'lookup', lambda db, record, *a, **k: calls.append(1) or real(db, record, *a, **k)):
            first = self.service.progress_books()
            self.assertEqual(len(calls), 1, 'positive control: one finished book, one lookup')
            self.assertEqual(self.service.progress_books(), first); self.assertEqual(len(calls), 1, 'reused: nothing it depends on changed')
            with connect(self.inv.database) as db:
                db.execute('CREATE TABLE IF NOT EXISTS series_backfill(job_id TEXT PRIMARY KEY,state TEXT NOT NULL,reason TEXT NOT NULL,record TEXT NOT NULL,updated TEXT NOT NULL)')
                db.execute("INSERT OR REPLACE INTO series_backfill VALUES('other','done','','{}','2026-10-25T00:00:00Z')")
            self.assertEqual(self.service.progress_books(), first); self.assertEqual(len(calls), 2, 'a completed series backfill looks again')

    def test_remove_from_list_and_the_delete_check_answer_within_1_s_during_a_status_calculation(self):
        self.converted()
        gone = [tone(self.audio / 'Unsorted' / 'Засор' / ('%02d.mp3' % n), self.cover, album='Засор', artist='Михаил Павлов', track='%d/2' % n) for n in (1, 2)]
        self.start(); self.approve_all()
        for path in gone: path.unlink()
        self.inv.launch('Audiobooks'); finish_scan(self.inv)
        missing = [entry for entry in self.service.needs_you().items() if entry[1]['group'] == 'files_missing']
        self.assertEqual(len(missing), 1, 'positive control: the All files missing row')
        identity = missing[0][0]; revision = self.inv.candidate('Audiobooks', identity)['revision']
        with SlowLookup(self.service, 4.0) as slow:
            status = self.in_thread(self.service.state)
            self.assertTrue(slow.started.wait(15))
            preview, took = self.timed(lambda: self.service.delete_preview(identity, revision))
            self.assertIsNone(preview['refusal'], preview); self.assertEqual(preview['files'], [], 'no file is left to delete')
            self.assertLess(took, 1.0, 'the delete check waited behind the status computation')
            removed, took = self.timed(lambda: self.service.dismiss_attention(identity, revision))
            self.assertEqual(removed, {'removed': True}); self.assertLess(took, 1.0, 'Remove from list waited behind the status computation')
            self.assertTrue(status.is_alive(), 'both answered while the status computation was still running')
            finish_thread(status)
        self.assertNotIn(identity, self.service.needs_you(), 'removed from the list')

    def test_scan_again_reads_without_the_group_lock(self):
        tone(self.audio / 'Unsorted' / 'Засор' / '01.mp3', self.cover, album='Засор', artist='Михаил Павлов', track='1/2')
        tone(self.audio / 'Unsorted' / 'Засор' / '02.mp3', self.cover, album='Засор', artist='Михаил Павлов', track='2/2')
        row = self.start()[0]
        held, release = threading.Event(), threading.Event()
        def approval():
            with self.inv.group_lock: held.set(); release.wait(30)
        self.in_thread(approval); self.assertTrue(held.wait(5)); self.addCleanup(release.set)
        receipt, took = self.timed(lambda: self.inv.refresh_candidate_sources('Audiobooks', row['id'], row['revision'], force=False))
        self.assertEqual(receipt['state'], 'unchanged', receipt); self.assertLess(took, 1.0, 'Scan again waited for group_lock')
        # Positive control: a file that changed on disk is written, and the write takes the lock.
        with open(self.audio / 'Unsorted' / 'Засор' / '02.mp3', 'ab') as stream: stream.write(b'\0' * 16)
        results = []
        writer = self.in_thread(lambda: results.append(self.inv.refresh_candidate_sources('Audiobooks', row['id'], row['revision'], force=False)))
        writer.join(1); self.assertTrue(writer.is_alive(), 'the write waits for the lock')
        release.set(); finish_thread(writer)
        self.assertEqual(results[0]['state'], 'refreshed', results)


class ApprovalStartTests(ApproveFixture):
    def test_an_approval_queues_without_start_or_finished_recheck_then_start_converts(self):
        for title in ('Ясно', 'Тихо'):
            tone(self.audio / 'Unsorted' / title / (title + '.mp3'), self.cover, album=title, artist='Иван Петров')
        rows = self.start()
        self.service.approve_book(rows[0]['id'], rows[0]['revision']); self.start_and_wait()
        self.assertEqual(self.service.jobs.status()['jobs'][0]['state'], 'completed', 'positive control: one finished book')
        checked = []
        real = MergeService._prune_completed
        def recheck(service, job_id, *args, **kwargs):
            checked.append(job_id); return real(service, job_id, *args, **kwargs)
        settled = []
        real_settle = type(self.service.jobs)._settle
        def settle(jobs, row, *args, **kwargs):
            settled.append(row['job_id']); return real_settle(jobs, row, *args, **kwargs)
        fresh = self.service.reviews.page()['rows']
        second = next(row for row in fresh if row['id'] == rows[1]['id'])
        with patch.object(MergeService, '_prune_completed', recheck), patch.object(type(self.service.jobs), '_settle', settle), \
                patch.object(MergeService, 'state', side_effect=AssertionError('no status computation on the approval path')):
            queued=self.service.approve_book(second['id'], second['revision'])
        self.assertEqual(next(j for j in self.service.jobs.status()['jobs'] if j['job_id']==queued['job_id'])['state'],'pending','Approve waits for Start')
        self.assertEqual(checked, [], 'the approval re-checked the finished books')
        self.assertEqual(settled, [], 'the approval re-checked the published outputs')
        self.start_and_wait()
        self.assertEqual([job['state'] for job in self.service.jobs.status()['jobs']], ['completed', 'completed'], 'Start converts the queued book')
        # 0.24.2: requested Start never runs unrelated finished-book cleanup.
        # The public idle owner is exercised separately below.
        self.service.pause()
        with patch.object(MergeService, '_prune_completed', recheck):self.service.resume()
        self.wait(); self.assertEqual(checked, [], 'Resume must not recheck finished books')

    def test_a_press_runs_between_two_books_of_idle_recheck(self):
        for title in ('Ясно', 'Тихо'):
            tone(self.audio / 'Unsorted' / title / (title + '.mp3'), self.cover, album=title, artist='Иван Петров')
        for row in self.start():
            self.service.approve_book(row['id'], row['revision'])
        self.start_and_wait(); self.service.pause(); self.service.resume()
        jobs = [job['job_id'] for job in self.service.jobs.status()['jobs']]
        self.assertEqual(len(jobs), 2)
        inside = [threading.Event(), threading.Event()]
        releases = [threading.Event(), threading.Event()]
        finished = threading.Event(); pressed = []; seen = []
        real = self.service.storage_cleanup.sweep_folders
        def slow(job_id):
            index = len(seen); inside[index].set()
            if not releases[index].wait(10): raise AssertionError('private idle check did not release')
            answer = real(job_id); seen.append(job_id)
            if len(seen) == 2: finished.set()
            return answer
        @operation
        def press(service): pressed.append(time.monotonic())
        waiting = None
        with patch.object(self.service.storage_cleanup, 'old_folder_jobs', side_effect=lambda: [job for job in jobs if job not in seen]), \
                patch.object(self.service.storage_cleanup, 'sweep_folders', side_effect=slow):
            try:
                # Same public scheduling owner as production; only which two
                # private finished jobs need a check and its delay are injected.
                self.service.start_retention(contextlib.nullcontext)
                self.assertTrue(inside[0].wait(10))
                waiting = threading.Thread(target=press, args=(self.service,), daemon=True); waiting.start()
                time.sleep(.3); self.assertEqual(pressed, [], 'positive control: not during one book')
                began = time.monotonic(); releases[0].set(); waiting.join(2)
                self.assertTrue(pressed, 'the foreground press waited for the whole idle pass')
                self.assertLess(pressed[0] - began, 1.0)
                self.service._retention_wake.set()
                self.assertTrue(inside[1].wait(10), 'idle work resumes on its own owner after the press')
                releases[1].set(); self.assertTrue(finished.wait(10))
            finally:
                for release in releases: release.set()
                self.service._retention_stop.set(); self.service._retention_wake.set()
                if waiting is not None: finish_thread(waiting)
                finish_thread(self.service._retention_thread)
        self.assertEqual(set(seen), set(jobs), 'both finished books were checked by idle maintenance')


class ApprovalPreviewTests(ApproveFixture):
    def test_the_goes_to_line_is_reused_until_the_book_or_the_rules_change_and_taken_stays_live(self):
        # The to-do list computes this for every held row it shows (0.3 s each on the live catalog: 11-30 s a page during
        # research). Reused while the book, the rules and the catalog facts it reads are unchanged.
        import author_rules
        tone(self.audio / 'Unsorted' / 'Утро снайпера' / '01.mp3', self.cover, album='Утро снайпера', title='Глава 1', track='1/1')
        row = self.start()[0]
        calls = []
        real = self.service.automatic.research.approved
        with patch.object(self.service.automatic.research, 'approved', lambda *a, **k: calls.append(1) or real(*a, **k)):
            first = self.service.approval_preview(row['id'], row['revision'])
            self.assertEqual(self.service.approval_preview(row['id'], row['revision']), first)
            self.assertEqual(len(calls), 1, 'reused')
            Path(first['absolute']).parent.mkdir(parents=True); Path(first['absolute']).write_bytes(b'x')
            self.assertTrue(self.service.approval_preview(row['id'], row['revision'])['taken'], 'the name on disk is checked live')
            self.assertEqual(len(calls), 1)
            self.service.approval_preview(row['id'], row['revision'], title='Утро снайпера 2')
            self.assertEqual(len(calls), 2, 'typed values are their own answer')
            with connect(self.inv.database) as db: author_rules.setup(db); author_rules.append(db, 'keep', 'Кто-то Новый', source='test')
            self.service.approval_preview(row['id'], row['revision'])
            self.assertEqual(len(calls), 3, 'a new rule computes it again')

    def test_the_goes_to_line_is_reused_while_a_job_only_reports_progress_and_computed_again_when_what_it_reads_changes(self):
        # 2026-10-26: the stamp read max(updated) of every job, which a converting job moves several times a second, so
        # the list computed every held row again while anything converted. Research reads the jobs' manifests (library
        # and confirmed spellings), never their progress. A taken-back rule and an approved book's metadata change it.
        import author_rules, datetime
        tone(self.audio / 'Unsorted' / 'Утро снайпера' / '01.mp3', self.cover, album='Утро снайпера', title='Глава 1', track='1/1')
        row = self.start()[0]
        with connect(self.inv.database) as db:
            author_rules.setup(db); rule = author_rules.append(db, 'keep', 'Кто-то Новый', source='test')
            db.execute('CREATE TABLE IF NOT EXISTS audio_jobs (job_id TEXT PRIMARY KEY, manifest TEXT NOT NULL, manifest_hash TEXT NOT NULL, state TEXT NOT NULL, stage TEXT NOT NULL, attempt_id TEXT, journal TEXT NOT NULL, output TEXT, reason TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL)')
            db.execute("INSERT INTO audio_jobs VALUES('fixture-job','{\"candidate_id\":\"elsewhere\"}','h1','Running','encode',NULL,'[]',NULL,'','2026-10-26T00:00:00+00:00','2026-10-26T00:00:00+00:00')")
        calls = []
        real = self.service.automatic.research.approved
        def moment():
            return datetime.datetime.now(datetime.timezone.utc).isoformat()
        with patch.object(self.service.automatic.research, 'approved', lambda *a, **k: calls.append(1) or real(*a, **k)):
            first = self.service.approval_preview(row['id'], row['revision'])
            self.assertEqual(len(calls), 1)
            for _ in range(3):
                time.sleep(0.01)
                with connect(self.inv.database) as db: db.execute("UPDATE audio_jobs SET updated=?,stage='encode' WHERE job_id='fixture-job'", (moment(),))
                self.assertEqual(self.service.approval_preview(row['id'], row['revision']), first)
            self.assertEqual(len(calls), 1, 'progress of a job is not something the line reads')
            with connect(self.inv.database) as db: db.execute("UPDATE audio_jobs SET manifest_hash='h2' WHERE job_id='fixture-job'")
            self.service.approval_preview(row['id'], row['revision'])
            self.assertEqual(len(calls), 2, 'a rewritten manifest (series backfill) computes it again')
            with connect(self.inv.database) as db: author_rules.retract(db, rule, source='test')
            self.service.approval_preview(row['id'], row['revision'])
            self.assertEqual(len(calls), 3, 'a taken-back rule computes it again')
            with connect(self.inv.database) as db:
                db.execute('CREATE TABLE IF NOT EXISTS candidate_context(id TEXT PRIMARY KEY,revision INTEGER NOT NULL,data TEXT NOT NULL)') if not db.execute("SELECT 1 FROM sqlite_master WHERE name='candidate_context'").fetchone() else None
                db.execute("INSERT INTO candidate_context(id,revision,data) VALUES('fixture-context',1,'{}')")
            self.service.approval_preview(row['id'], row['revision'])
            self.assertEqual(len(calls), 4, "another book's saved or approved metadata (confirmed spellings) computes it again")


class ListReadLimitTests(ApproveFixture):
    # The limit leaves the gate (seven workers at once) room: one page took 0.2-2.0 s alone on a live-sized catalog (1,572
    # books, 508 finished; see live_sized), and 21 s on 0.22.0 code during a status computation; the live list took 54-100 s.
    PAGE_LIMIT = 8.0
    timed = LockTimingTests.timed

    def test_the_book_list_answers_within_its_limit_on_a_live_sized_catalog_even_during_a_status_computation(self):
        import live_sized
        tone(self.audio / 'Unsorted' / 'Ясно' / 'Ясно.mp3', self.cover, album='Ясно', artist='Иван Петров')
        row = self.start()[0]; self.service.approve_book(row['id'], row['revision']); self.start_and_wait()
        live_sized.grow(self.inv)
        reviews = self.service.reviews
        self.assertEqual(reviews.page(100, 0, '', 'all')['total'], live_sized.LIVE['books'] + 1, 'positive control: a live-sized catalog')
        with SlowLookup(self.service, 0.02) as slow:  # about 10 s for 509 books (the live catalog's 433 relocations took 19 s)
            self.service.state()  # the first status computation after startup: every lookup once
            self.assertEqual(len(self.service.jobs.status()['jobs']), live_sized.LIVE['finished'] + 1)
            for status in ('converted', 'output_attention', 'all'):
                page, took = self.timed(lambda: reviews.page(100, 0, '', status))
                self.assertLess(took, self.PAGE_LIMIT, status)
            # A status computation that takes longer than the list's 30 s reuse window, as on the live catalog under load.
            self.service._converted_cache = (time.monotonic() - 31, self.service._converted_cache[1], None)
            self.service.__dict__.pop('_lookups', None); slow.started.clear()
            status = threading.Thread(target=self.service.state, daemon=True); status.start(); self.addCleanup(finish_thread, status)
            self.assertTrue(slow.started.wait(30))
            page, took = self.timed(lambda: reviews.page(100, 0, '', 'converted'))
            self.assertEqual(page['total'], 1, 'the converted fixture book')
            self.assertLess(took, self.PAGE_LIMIT, 'the list waited for the status computation')
            self.assertTrue(status.is_alive(), 'answered while the status computation was still running')
            finish_thread(status)


if __name__ == '__main__':
    unittest.main()
