"""Every kind of background work, for the jobs panel (0.30.0).

Sergei (2026-11-18): "If there is a conversion (or any other job) running, I need to see all the running jobs with clear
explanation of what they are and status bars." 0.29.0 showed one row per kind, four at most, from a status computation
that could be minutes old, and about twenty kinds of work had no row at all (Ender's diagnosis in the 0.22.1 backlog doc;
Judy's spec BooksArranger_0.30.0_UX.md).

view() builds /api/state 'work' at each poll from the engine's live state: the jobs fields MergeService.live_state() read
at this poll, the action queue, automatic processing, the scan, and the workers' own memory. It never computes the full
status. The page words everything (label_key, step, blocker cause); there is no copy here.

Contract (field names are stable; a field the engine cannot know is None, never guessed):

work = {
  'schema': 'books-work-v1',
  'rows':    [row],      every job that runs, is pausing or is paused, in a fixed kind order (KINDS), oldest first inside one
  'waiting': [item],     everything that waits to run, in a fixed kind order (WAITING_KINDS), queue order inside one
  'counts':  {tasks_running, queued_conversions, cleanups_waiting, cleanups_paused, actions_waiting, retry_checks_waiting},
  'snapshot_age_ms': int or None,  how old the counts behind audiobook_jobs are (attention, converted, candidates); the rows
                                   and waiting items are read at this poll
  'refreshing': bool,              a newer status computation runs now
  'unread': [kind],                sources that could not be read this poll (their rows are missing, never invented)
}
row = {id, kind, label_key, subject, book_id, job_id, step, step_text, state, done, total, unit, fraction, started, count, task_kind}
  id: unique per job ('<kind>:<job, book or move id>' or the kind alone for a one-off worker); state: 'running', 'pausing'
  or 'paused'; done/total/unit: an amount the engine counts (unit 'files', 'books', 'seconds', 'percent', 'moves'), else
  None and the bar slides; fraction: 0..1 where the engine knows a finer one; started: epoch ms, the engine's own start or
  the first poll that saw the row; count: how many things a row stands for when it has no amount (a paused queue's books);
  task_kind: the job's own task kind where it has one (duplicate_source_cleanup: an extra source's check and removal).
item = {id, kind, label_key, subject, book_id, job_id, blocker, ahead, at, count}
  blocker: {kind, cause, title, book_id, count} for a queued action (ActionQueue blocker kinds, the cause split out; see
  explain()), else None; ahead: actions ahead of it in the queue; at: epoch ms of a timed retry; count: books it stands for.
"""
import copy
import threading
import time

SCHEMA = 'books-work-v1'
# Row kinds, top to bottom (Judy 1.5).
KINDS = ('conversion', 'chapter_check', 'cleanup', 'queue', 'source_folders', 'move', 'move_recovery', 'action', 'bulk',
         'start_check', 'retry_check', 'maintenance', 'finished_check', 'series', 'gap_fill', 'lookup', 'decisions',
         'repair_check', 'recovery_delete', 'regroup', 'scan', 'research', 'discovery', 'source_check', 'drive_check')
WAITING_KINDS = ('action', 'conversions', 'cleanup', 'retry_checks', 'cleanup_retry', 'recovery_delete', 'decisions',
                 'metadata_sources', 'drive', 'resume', 'automatic_start', 'automatic')
ROW_KEYS = ('id', 'kind', 'label_key', 'subject', 'book_id', 'job_id', 'step', 'step_text', 'state', 'done', 'total', 'unit',
            'fraction', 'started', 'count', 'task_kind')
ITEM_KEYS = ('id', 'kind', 'label_key', 'subject', 'book_id', 'job_id', 'blocker', 'ahead', 'at', 'count')
CLEANUP_STEPS = {'recovery copies', 'originals', 'temporary', 'folders', 'former outputs', 'verifying replacement', 'retiring former outputs'}
LIST_LIMIT = 100  # waiting cleanups listed one by one; the counts carry the rest (a NAS backlog can hold hundreds)


def _row(**values):
    row = dict.fromkeys(ROW_KEYS)
    row.update(values)
    row['label_key'] = row['label_key'] or row['kind']
    row['state'] = row['state'] or 'running'
    return row


def _item(**values):
    item = dict.fromkeys(ITEM_KEYS)
    item.update(values)
    item['label_key'] = item['label_key'] or item['kind']
    return item


def _amount(done, total, unit):
    """done/total/unit when they form a real measurement, else all None (the bar slides)."""
    if type(done) not in (int, float) or type(total) not in (int, float) or not total > 0 or not 0 <= done <= total:
        return {'done': None, 'total': None, 'unit': None}
    return {'done': done, 'total': total, 'unit': unit}


def _titles(merge, job_ids):
    """{job id: (title, candidate id)} in one catalog read (no manifest is parsed in Python)."""
    ids = [identity for identity in dict.fromkeys(job_ids) if identity]
    if not ids:
        return {}
    import json
    from scanner import connect
    with connect(merge.inventory.database) as db:
        return {row[0]: (row[1] or '', row[2]) for row in db.execute(
            "SELECT job_id,json_extract(manifest,'$.metadata.title'),json_extract(manifest,'$.candidate_id') FROM audio_jobs "
            "WHERE job_id IN (SELECT value FROM json_each(?))", (json.dumps(ids),))}


def _book_titles(merge, book_ids):
    """{candidate id: the list's title} in one catalog read."""
    ids = [identity for identity in dict.fromkeys(book_ids) if identity]
    if not ids:
        return {}
    import json
    from scanner import connect
    with connect(merge.inventory.database) as db:
        return {row[0]: row[1] or '' for row in db.execute(
            "SELECT id,json_extract(evidence,'$.title_clue') FROM book_groups WHERE id IN (SELECT value FROM json_each(?))", (json.dumps(ids),))}


class Reader:
    """One poll's reads. Each source is read once; a source that fails is listed in 'unread' and adds nothing."""

    def __init__(self, server, jobs, automatic, queue, scanning, scan_status, roots=None):
        self.server = server
        self.merge = getattr(server, 'merge', None)
        self.jobs = jobs if isinstance(jobs, dict) else {}
        self.automatic = automatic if isinstance(automatic, dict) else {}
        self.queue = queue if isinstance(queue, dict) else {}
        self.scanning = scanning
        self.scan_status = scan_status if isinstance(scan_status, dict) else None
        self.roots = roots or []
        self.rows, self.waiting, self.unread = [], [], []
        self.job_titles, self.books = {}, {}

    def attempt(self, kind, read):
        try:
            read()
        except Exception:  # never fail a poll over one source; say which one could not be read
            self.unread.append(kind)

    def attr(self, name, default=None):
        """An attribute the engine set on itself (its __dict__), else default."""
        return getattr(self.merge, '__dict__', {}).get(name, default)

    def title(self, job_id):
        if job_id and job_id not in self.job_titles:
            self.job_titles.update(_titles(self.merge, [job_id]))
        return self.job_titles.get(job_id, ('', None))

    # ---------------------------------------------------------------- the jobs (live_state's fields)
    def conversion_and_cleanup(self):
        jobs = self.jobs
        progress = jobs.get('progress') if isinstance(jobs.get('progress'), dict) else None
        state = {'Pausing': 'pausing', 'Paused': 'paused'}.get(jobs.get('state'), 'running')
        job, book, title = jobs.get('current_job_id'), jobs.get('current_book_id'), jobs.get('current_title') or ''
        task = jobs.get('current_task_kind') if isinstance(jobs.get('current_task_kind'), str) else None
        # A stopped job the status still shows (state 'Needs attention') is On hold on the page, never a running row (0.29.0).
        if job and progress and progress.get('phase') and not progress.get('attention') and jobs.get('state') != 'Needs attention':
            phase = progress['phase']
            if progress.get('chapter_check'):
                check = progress['chapter_check'] if isinstance(progress['chapter_check'], dict) else {}
                self.rows.append(_row(id='chapter_check:' + job, kind='chapter_check', subject=title, book_id=book, job_id=job,
                                      step='checking_source_audio', step_text=check.get('file'), state=state, task_kind=task))
            elif phase in CLEANUP_STEPS:
                unit = 'files' if phase in ('originals', 'recovery copies') else None
                self.rows.append(_row(id='cleanup:' + job, kind='cleanup', subject=title, book_id=book, job_id=job, step=phase,
                                      state=state, task_kind=task, **_amount(progress.get('completed'), progress.get('total'), unit)))
            elif jobs.get('state') in ('Running', 'Pausing') or state == 'paused':
                unit = progress.get('unit') or ('seconds' if phase == 'encoding' else None)
                started = progress.get('started') if type(progress.get('started')) is int else None
                fraction = progress.get('fraction') if type(progress.get('fraction')) in (int, float) and 0 <= progress['fraction'] <= 1 else None
                self.rows.append(_row(id='conversion:' + job, kind='conversion', subject=title, book_id=book, job_id=job, step=phase,
                                      state=state, fraction=fraction, started=started, task_kind=task,
                                      **_amount(progress.get('completed'), progress.get('total'), unit)))
        running = next((row['job_id'] for row in self.rows if row['kind'] == 'cleanup'), None)
        pending = [c for c in jobs.get('cleanups_pending') or [] if isinstance(c, dict) and c.get('job_id') != running]
        # Every started one is a row (paused: one row each, Judy 1.5 row 4); the first LIST_LIMIT not started are listed.
        started = [c for c in pending if c['state'] != 'waiting'];waiting = [c for c in pending if c['state'] == 'waiting'][:LIST_LIMIT]
        self.job_titles.update(_titles(self.merge, [c['job_id'] for c in started + waiting]))
        for cleanup in started:
            title, book = self.job_titles.get(cleanup['job_id'], ('', None))
            # Not the one the status calls current, so not progressing: paused (a pausing one says so), whatever it stored.
            self.rows.append(_row(id='cleanup:' + cleanup['job_id'], kind='cleanup', subject=title, book_id=book, job_id=cleanup['job_id'],
                                  step='originals', state='pausing' if cleanup['state'] == 'pausing' else 'paused',
                                  **_amount(cleanup.get('removed'), cleanup.get('total'), 'files')))
        for cleanup in waiting:
            title, book = self.job_titles.get(cleanup['job_id'], ('', None))
            self.waiting.append(_item(id='cleanup:' + cleanup['job_id'], kind='cleanup', subject=title, book_id=book, job_id=cleanup['job_id']))
        conversions = jobs.get('queued_conversions') if type(jobs.get('queued_conversions')) is int else 0
        if conversions > 0:
            nxt = None
            try:
                found = self.merge.jobs._pending_unreserved(None)
                nxt = found[0]['job_id'] if found else None
            except Exception:
                pass
            title, book = self.title(nxt) if nxt else ('', None)
            if jobs.get('state') in ('Paused', 'Pausing'):
                self.rows.append(_row(id='queue', kind='queue', subject=title, book_id=book, job_id=nxt, step='paused',
                                      state='paused' if jobs.get('state') == 'Paused' else 'pausing', count=conversions))
            else:
                self.waiting.append(_item(id='conversions', kind='conversions', subject=title, book_id=book, job_id=nxt, count=conversions))

    def checks(self):
        jobs = self.jobs
        admission = jobs.get('start_admission') if isinstance(jobs.get('start_admission'), dict) else {}
        check = jobs.get('published_check') if isinstance(jobs.get('published_check'), dict) else None
        queue_work = jobs.get('queue_work') if isinstance(jobs.get('queue_work'), dict) else None
        start = check if check and check.get('kind') == 'start' else None
        if admission.get('state') == 'checking' or start or queue_work:
            amount = _amount(start.get('completed'), start.get('total'), 'books') if start else _amount(None, None, None)
            self.rows.append(_row(id='start_check', kind='start_check', step='checking_pending',
                                  started=start.get('started') if start and type(start.get('started')) is int else None, **amount))
        if check and check.get('kind') != 'start':
            self.rows.append(_row(id='finished_check', kind='finished_check', step='identity',
                                  started=check.get('started') if type(check.get('started')) is int else None,
                                  **_amount(check.get('completed'), check.get('total'), 'books')))
        retry = jobs.get('retry_checks') if isinstance(jobs.get('retry_checks'), dict) else {}
        worker = retry.get('worker') if isinstance(retry.get('worker'), dict) else {}
        if worker.get('state') == 'checking' and worker.get('job_id'):
            title, book = self.title(worker['job_id'])
            self.rows.append(_row(id='retry_check:' + worker['job_id'], kind='retry_check', subject=title, book_id=book, job_id=worker['job_id']))
        if type(retry.get('waiting')) is int and retry['waiting'] > 0:
            self.waiting.append(_item(id='retry_checks', kind='retry_checks', count=retry['waiting']))
        maintenance = jobs.get('maintenance') if isinstance(jobs.get('maintenance'), dict) else None
        if maintenance and maintenance.get('state') in ('checking', 'stopping'):
            job = maintenance.get('job_id')
            self.rows.append(_row(id='maintenance:' + str(job), kind='maintenance', subject=maintenance.get('title') or '', job_id=job,
                                  book_id=self.title(job)[1] if job else None, step=maintenance.get('phase'),
                                  state='pausing' if maintenance['state'] == 'stopping' or maintenance.get('cancel_requested') else 'running'))
        series = jobs.get('series_update') if isinstance(jobs.get('series_update'), dict) else None
        if series and series.get('title'):
            self.rows.append(_row(id='series', kind='series', subject=series['title'], step='updating' if series.get('step') == 'updating' else 'looking_up',
                                  **_amount(series.get('done'), series.get('total'), 'books')))
        if jobs.get('start_waiting') or admission.get('state') == 'waiting':
            self.waiting.append(_item(id='resume', kind='resume'))
        run = jobs.get('retry_all') if isinstance(jobs.get('retry_all'), dict) else None
        if run and run.get('state') == 'running':
            self.rows.append(_row(id='bulk:retry', kind='bulk', label_key='retry_' + ('selected' if run.get('mode') == 'selected' else 'all'),
                                  **_amount(run.get('done'), run.get('total'), 'books')))
        for key, deadline in list((self.attr('_cleanup_retry_at') or {}).items()):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                continue
            job = key[1] if isinstance(key, tuple) and len(key) > 1 else key
            title, book = self.title(job) if isinstance(job, str) else ('', None)
            what = key[0] if isinstance(key, tuple) and key and isinstance(key[0], str) else None  # working, temporary, folder
            self.waiting.append(_item(id='cleanup_retry:' + '/'.join(map(str, key if isinstance(key, tuple) else (key,))), kind='cleanup_retry',
                                      label_key='cleanup_retry_' + what if what else None, subject=title, book_id=book,
                                      job_id=job if isinstance(job, str) else None, at=int((time.time() + remaining) * 1000)))

    # ---------------------------------------------------------------- the action queue
    def actions(self):
        running = self.queue.get('queue_running') if isinstance(self.queue.get('queue_running'), dict) else None
        if running:
            if running.get('action') == 'move':
                # One move runs at a time (the action queue); its percent is the only one the mover reports.
                progress = dict(self.attr('_move_progress') or {})
                percent = next(iter(progress.values())) if len(progress) == 1 else None
                self.rows.append(_row(id='move:' + running['id'], kind='move', subject=running.get('title') or '', book_id=running.get('book_id'),
                                      fraction=percent / 100 if type(percent) in (int, float) and 0 <= percent <= 100 else None,
                                      **_amount(percent, 100, 'percent')))
            else:
                self.rows.append(_row(id='action:' + running['id'], kind='action', label_key=running.get('action'), subject=running.get('title') or '',
                                      book_id=running.get('book_id'), count=running.get('n')))
        for item in self.queue.get('queued_actions') or []:
            if isinstance(item, dict):
                self.waiting.append(_item(id='action:' + item['id'], kind='action', label_key=item.get('action'), subject=item.get('title') or '',
                                          book_id=item.get('book_id'), blocker=item.get('blocker'), ahead=max(0, (item.get('position') or 1) - 1)))

    # ---------------------------------------------------------------- workers outside the jobs queue
    def workers(self):
        merge = self.merge
        alive = lambda thread: thread is not None and thread.is_alive()
        gap = self.attr('gap_fill')  # instance attributes only (merge.__dict__): a stand-in engine adds no invented row
        progress = gap.status() if gap is not None and hasattr(gap, 'status') else None
        if progress and alive(getattr(gap, 'thread', None)):
            self.rows.append(_row(id='gap_fill', kind='gap_fill', subject=progress.get('title') or '', **_amount(progress.get('done'), progress.get('total'), 'books')))
        reviews = self.attr('reviews')
        matching = {key: value for key, value in list((getattr(reviews, 'matching', None) or {}).items()) if isinstance(value, dict) and value.get('state') == 'finding'}
        chapters = dict(getattr(reviews, '__dict__', {}).get('_chapter_activity') or {})
        books = _book_titles(merge, list(matching) + list(chapters))
        for book in matching:
            self.rows.append(_row(id='lookup:' + book, kind='lookup', label_key='find_metadata', subject=books.get(book, ''), book_id=book))
        for book, check in chapters.items():
            if any(row['kind'] == 'chapter_check' and row['book_id'] == book for row in self.rows):
                continue
            self.rows.append(_row(id='chapter_check:' + book, kind='chapter_check', subject=books.get(book, ''), book_id=book, step='checking_source_audio',
                                  step_text=check.get('file') if isinstance(check, dict) else None))
        if self.attr('_repair_running'):
            pending = list(self.attr('_repair_pending') or [])
            title, book = self.title(pending[0]) if pending else ('', None)
            self.rows.append(_row(id='repair_check', kind='repair_check', subject=title, book_id=book, job_id=pending[0] if pending else None, count=len(pending) or None))
        manual = self.attr('_manual_recovery')
        if manual:
            job = manual[0] if isinstance(manual, (tuple, list)) else None
            title, book = self.title(job) if job else ('', None)
            self.rows.append(_row(id='recovery_delete:' + str(job), kind='recovery_delete', subject=title, book_id=book, job_id=job))
        for press in list(self.attr('_manual_presses') or []):
            job = press[0] if isinstance(press, (tuple, list)) else None
            title, book = self.title(job) if job else ('', None)
            count = press[1].get('count') if isinstance(press, (tuple, list)) and len(press) > 1 and isinstance(press[1], dict) else None
            self.waiting.append(_item(id='recovery_delete:' + str(job), kind='recovery_delete', subject=title, book_id=book, job_id=job, count=count))
        if alive(self.attr('_regroup_thread')):
            self.rows.append(_row(id='regroup', kind='regroup'))
        if alive(self.attr('_move_recovery')):
            self.rows.append(_row(id='move_recovery', kind='move_recovery'))
        self.decisions()
        source = self.attr('_source_progress')
        if isinstance(source, dict):
            started = source.get('started') if type(source.get('started')) is int else None
            if source.get('phase') == 'folders':
                self.rows.append(_row(id='source_folders', kind='source_folders', started=started))
            else:
                self.rows.append(_row(id='source_check', kind='source_check', started=started, **_amount(source.get('done'), source.get('total'), 'books')))
        # Root probes (a check pass's first step, Check again, the 30 s re-check) run on threads of this name.
        if any(thread.name == 'books-root-probes' and thread.is_alive() for thread in threading.enumerate()):
            self.rows.append(_row(id='drive_check', kind='drive_check'))

    def decisions(self):
        """Saved decisions (names, choices, approvals) the engine applies after accepting them: the one it applies runs, the
        rest wait. A catalog read of the open ones only."""
        runtime = self.attr('decisions')
        store = getattr(runtime, 'store', None)
        if store is None or not hasattr(store, 'database'):
            return
        from scanner import connect
        with connect(store.database) as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='book_decisions'").fetchone():
                return
            rows = [dict(row) for row in db.execute("SELECT request_id,book_id,action,state FROM book_decisions WHERE state IN ('accepted','applying') ORDER BY accepted_utc,seq")]
        books = _book_titles(self.merge, [row['book_id'] for row in rows])
        for row in rows:
            if row['state'] == 'applying':
                self.rows.append(_row(id='decisions:' + row['request_id'], kind='decisions', label_key='decision_' + str(row['action']),
                                      subject=books.get(row['book_id'], ''), book_id=row['book_id']))
            else:
                self.waiting.append(_item(id='decisions:' + row['request_id'], kind='decisions', label_key='decision_' + str(row['action']),
                                          subject=books.get(row['book_id'], ''), book_id=row['book_id']))

    # ---------------------------------------------------------------- scan and automatic processing
    def scan_and_automatic(self):
        automatic = self.automatic
        if self.scan_status is not None:
            checked, pending = self.scan_status.get('checked'), self.scan_status.get('pending')
            amount = _amount(checked, checked + pending, 'files') if type(checked) is int and type(pending) is int else _amount(None, None, None)
            self.rows.append(_row(id='scan', kind='scan', subject=self.server.active_library or '', step='scanning',
                                  step_text=self.scan_status.get('current') or None, **amount))
        state, phase = automatic.get('state'), automatic.get('phase')
        if state in ('Running', 'Stopping'):
            pausing = 'pausing' if state == 'Stopping' else 'running'
            current = automatic.get('current') if isinstance(automatic.get('current'), dict) else {}
            if phase == 'research':
                text = ' / '.join(part for part in (current.get('source'), current.get('stage')) if isinstance(part, str) and part)
                research = automatic.get('research_pass') if isinstance(automatic.get('research_pass'), dict) else {}
                self.rows.append(_row(id='research', kind='research', subject=current.get('title') if isinstance(current.get('title'), str) else '',
                                      step='researching', step_text=text or None, state=pausing,
                                      **_amount(research.get('completed'), research.get('total'), 'books')))
            elif phase == 'discovery' and self.scan_status is None:
                self.rows.append(_row(id='discovery', kind='discovery', state=pausing))
            research = automatic.get('research') if isinstance(automatic.get('research'), dict) else {}
            at = automatic.get('next_retry_at')
            if type(research.get('waiting')) is int and research['waiting'] > 0 or type(at) in (int, float) and at > 0:
                self.waiting.append(_item(id='metadata_sources', kind='metadata_sources', count=research.get('waiting') if type(research.get('waiting')) is int else None,
                                          at=int(at * 1000 if at < 1e12 else at) if type(at) in (int, float) and at > 0 else None))
            if phase in ('conversion', 'waiting') and not any(row['kind'] == 'research' for row in self.rows):
                self.waiting.append(_item(id='automatic', kind='automatic', label_key='automatic_' + str(phase)))
        if automatic.get('start_pending'):
            self.waiting.append(_item(id='automatic_start', kind='automatic_start'))
        for root in self.roots:
            if isinstance(root, dict) and (not root.get('available') or root.get('empty')):
                self.waiting.append(_item(id='drive:' + str(root.get('path')), kind='drive', label_key='drive_empty' if root.get('available') else 'drive', subject=root.get('path')))


def explain(kind, item, jobs, queue_running=None):
    """The blocker object of a queued action (Judy's spec 2.1): {kind, cause, title, book_id, count}. kind is the action
    queue's own (blocker kinds in action_queue); cause splits it into what really holds the action, from the same poll's
    jobs fields, so the sentence can name the row above it:
      jobs:      own_conversion, own_cleanup (this book's own work), conversion (one book converts, none waits), conversion_queue
                 (count: the books converting and waiting), queue_paused (count: books waiting), cleanup_running,
                 cleanup_waiting, cleanup_paused (title, book_id of that cleanup's book), checking (start or retry checks),
                 unknown
      operation: action (title, book_id of the running queued action), source_check (a scan waits for a source check pass)
                 or operation (another press holds the engine)
      retry_run: retry_run (count: books left in Retry all); others: the kind itself (scan, automatic, book, loading,
                 approve_run)."""
    value = {'kind': kind, 'cause': kind, 'title': None, 'book_id': None, 'count': None}
    jobs = jobs if isinstance(jobs, dict) else {}
    book = item.get('book_id') if isinstance(item, dict) else None
    if kind == 'jobs':
        progress = jobs.get('progress') if isinstance(jobs.get('progress'), dict) else {}
        phase = progress.get('phase') if not progress.get('attention') else None
        current_book, title = jobs.get('current_book_id'), jobs.get('current_title') or None
        conversions = jobs.get('queued_conversions') if type(jobs.get('queued_conversions')) is int else 0
        cleanups = [c for c in jobs.get('cleanups_pending') or [] if isinstance(c, dict)]
        cleaning = phase in CLEANUP_STEPS
        if jobs.get('current_job_id') and phase and current_book and current_book == book:
            value['cause'] = 'own_cleanup' if cleaning else 'own_conversion'
        elif jobs.get('current_job_id') and cleaning:
            value.update(cause='cleanup_running', title=title, book_id=current_book)
        elif jobs.get('current_job_id') and phase and jobs.get('state') in ('Running', 'Pausing'):
            if conversions > 0:
                value.update(cause='conversion_queue', count=conversions + 1)
            else:
                value.update(cause='conversion', title=title, book_id=current_book)
        elif conversions > 0 and jobs.get('state') in ('Paused', 'Pausing'):
            value.update(cause='queue_paused', count=conversions)
        elif conversions > 0:
            value.update(cause='conversion_queue', count=conversions)
        elif any(c.get('state') in ('paused', 'pausing') for c in cleanups):
            value['cause'] = 'cleanup_paused'
        elif any(c.get('state') == 'waiting' for c in cleanups):
            value['cause'] = 'cleanup_waiting'
        elif jobs.get('state') in ('Running', 'Pausing'):
            value['cause'] = 'checking'
        else:
            value['cause'] = 'unknown'
    elif kind == 'operation':
        if isinstance(queue_running, dict):
            value.update(cause='action', title=queue_running.get('title') or None, book_id=queue_running.get('book_id'))
    elif kind == 'book' and isinstance(item, dict) and item.get('action') == 'join':
        # 0.30.0 item D (Judy 8.5: 2.2, book/conversion): a queued join waits for the part that converts now; the sentence
        # names its row ("It runs when Converting: Впусти меня 2 finishes.").
        args = item.get('args') if isinstance(item.get('args'), dict) else {}
        parts = item.get('parts') or [entry.get('id') for entry in args.get('items') or [] if isinstance(entry, dict)]
        current = jobs.get('current_book_id')
        if current and current in parts and jobs.get('current_job_id'):
            value.update(cause='conversion', title=jobs.get('current_title') or None, book_id=current)
    elif kind == 'retry_run':
        run = jobs.get('retry_all') if isinstance(jobs.get('retry_all'), dict) else {}
        if type(run.get('total')) is int and type(run.get('done')) is int:
            value['count'] = max(0, run['total'] - run['done'])
    return value


def explain_one(kind, item, jobs, running=None, merge=None, named=None):
    """explain() plus what only the engine can add: a scan that waits for a check pass, the title of the cleanup a cause
    names. named: a {job id: (title, book id)} cache shared by one poll."""
    jobs = jobs if isinstance(jobs, dict) else {}
    named = {} if named is None else named
    value = explain(kind, item, jobs, running)
    if value['cause'] == 'operation' and getattr(merge, '__dict__', {}).get('_source_checking'):
        value['cause'] = 'source_check'  # a scan waits for a check pass (Senua S-m9)
    if value['cause'] in ('cleanup_paused', 'cleanup_waiting') and merge is not None:
        state = ('paused', 'pausing') if value['cause'] == 'cleanup_paused' else ('waiting',)
        first = next((c for c in jobs.get('cleanups_pending') or [] if isinstance(c, dict) and c.get('state') in state), None)
        if first:
            if first['job_id'] not in named:
                try:
                    named.update(_titles(merge, [first['job_id']]))
                except Exception:
                    named[first['job_id']] = (None, None)
            value['title'], value['book_id'] = named.get(first['job_id'], (None, None))
    return value


def explain_queue(queue, jobs, merge=None):
    """Every queued action's blocker gets its cause (explain_one) in place."""
    running = queue.get('queue_running') if isinstance(queue, dict) else None
    named = {}
    for item in (queue.get('queued_actions') or []) if isinstance(queue, dict) else []:
        blocker = item.get('blocker') if isinstance(item.get('blocker'), dict) else {}
        item['blocker'] = explain_one(blocker.get('kind'), item, jobs, running, merge, named)


def view(server, jobs, automatic, queue, scanning, scan_status, roots=None, memo=None, now_ms=None):
    """/api/state 'work' (module docstring). roots: /api/state 'library_roots'; memo: {row id: epoch ms} the server keeps
    between polls (when a row was first seen)."""
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    reader = Reader(server, jobs, automatic, queue, scanning, scan_status, roots)
    reader.attempt('jobs', reader.conversion_and_cleanup)
    reader.attempt('checks', reader.checks)
    reader.attempt('actions', reader.actions)
    reader.attempt('workers', reader.workers)
    reader.attempt('automatic', reader.scan_and_automatic)
    memo = memo if memo is not None else {}
    seen = set()
    for row in reader.rows:
        seen.add(row['id'])
        if row['started'] is None:
            row['started'] = memo.setdefault(row['id'], now_ms)
    for key in [key for key in memo if key not in seen]:
        del memo[key]
    order = {kind: n for n, kind in enumerate(KINDS)}
    rows = sorted(reader.rows, key=lambda row: (order.get(row['kind'], len(KINDS)), row['state'] == 'paused', row['started'] or 0))
    worder = {kind: n for n, kind in enumerate(WAITING_KINDS)}
    waiting = sorted(enumerate(reader.waiting), key=lambda pair: (worder.get(pair[1]['kind'], len(WAITING_KINDS)), pair[0]))
    jobs = jobs if isinstance(jobs, dict) else {}
    retry = jobs.get('retry_checks') if isinstance(jobs.get('retry_checks'), dict) else {}
    info = None
    snapshot = getattr(getattr(server, 'merge', None), 'snapshot_info', None)
    if callable(snapshot) and callable(getattr(type(server.merge), 'snapshot_info', None)):
        try:
            info = snapshot()
        except Exception:
            info = None
    count = lambda key: jobs.get(key) if type(jobs.get(key)) is int else 0
    return {'schema': SCHEMA, 'rows': rows, 'waiting': [item for _n, item in waiting],
            'counts': {'tasks_running': sum(row['state'] in ('running', 'pausing') for row in rows), 'queued_conversions': count('queued_conversions'),
                       'cleanups_waiting': count('cleanups_waiting'), 'cleanups_paused': count('cleanups_paused'),
                       'actions_waiting': len((queue or {}).get('queued_actions') or []),
                       'retry_checks_waiting': retry.get('waiting') if type(retry.get('waiting')) is int else 0},
            'snapshot_age_ms': info.get('snapshot_age_ms') if isinstance(info, dict) else None,
            'refreshing': bool(info.get('refreshing')) if isinstance(info, dict) else False,
            'unread': reader.unread}
