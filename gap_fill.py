"""0.22.1 (Sergei's backlog item 8; rulings 5 and 6): the optional fields are filled in the background, after approval.

An approval no longer waits for an online lookup. A book is approved on its local identity at once: its missing optional
fields come from answers already in the research cache (public_research._local_lookup), and the ones nothing answered
are recorded in its job manifest (metadata_facts gap_search: 'background', with the title and author to ask about).
This pass asks the sources later, one book at a time, and records what they confirm in the gap_fill table: the original
title and language (ruling 16) and the full author name, each with its fetched receipts. The book itself is not changed
here: renaming a finished book in Audiobooks Sorted is the rename pass (ruling 21, later). Series positions are series
backfill's, which looks every finished book without a series up and renames it in Sorted (ruling 17).

Fair use of the per-site limits: the pass reserves its requests in the 'gap' lane (public_research.LANES), at most
BACKGROUND_SHARE of a site's hourly bound, so it can never take the bound from research or from series backfill. A
closed source defers the book to when that source reopens; nothing is retried in a loop.

0.31.0, R16 (Sergei 2026-11-22: "the look-up for original titles and author names gets the same limit" as the series
look-up, 3 tries per source). Until now a book whose source never answered was deferred again without end, so the look-up
never ended and "All done" could never show while one such book was left. The rule per book, as series backfill's:
  - each source's answer is kept: a source that answered is not asked about that book again;
  - the app's own limits (kind app_limit) and a busy catalog are no try: the book waits and goes on where it stopped;
  - a source that could not be reached is tried SOURCE_TRIES times for that book, at least TRY_SPACING apart, then given
    up: it counts as no answer;
  - when every source has answered or is given up, the book is settled: 'found' with what was confirmed, or 'none' with the
    sources that never answered named (record 'unreached'); it is not asked again;
  - a look-up that fails for another reason is tried FAILURE_TRIES times, TRY_SPACING apart, then settled 'none'.
The numbers are the series look-up's own (R9: 3 per source, 6 hours apart); the page prints what summary()['tries'] sends.
"""
import json
import threading
import time

from scanner import connect
from series_backfill import FAILURE_TRIES, SOURCE_TRIES, TRY_SPACING  # R16: the same limit, one home for the numbers

TABLE = ('CREATE TABLE IF NOT EXISTS gap_fill(job_id TEXT PRIMARY KEY,candidate_id TEXT NOT NULL,state TEXT NOT NULL,'
         'reason TEXT NOT NULL,record TEXT NOT NULL,updated TEXT NOT NULL)')
FINAL = ('found', 'none')
LOOKUP_POLICY = 'gap-fill-22.1-v1'
PASS_WAIT = 600     # seconds between passes when nothing is due sooner
START_DELAY = 180   # after startup: the published check, the queue and series backfill come first
MIN_WAIT = 30
BUDGET = 12         # requests per book, as research had
NO_TRY_KINDS = ('app_limit', 'catalog_busy')  # the app's own bound or its busy catalog: never a try of the source (R16)
UNREACHED = 'No source confirmed the missing fields. Sources that could not be reached are no longer asked: '
FAILED = 'Gap lookup could not finish after %d tries and is no longer tried: '


def _stamp():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def background(manifest):
    """(gaps, ask) a job's approval left for this pass, or ((), None)."""
    facts = manifest.get('metadata_facts') if isinstance(manifest, dict) else None
    search = facts.get('gap_search') if isinstance(facts, dict) else None
    if not isinstance(search, dict):
        return (), None
    gaps = [gap for gap in search.get('background') or [] if gap in ('original_title', 'author_full')]
    ask = search.get('ask')
    if not gaps or not isinstance(ask, dict) or not isinstance(ask.get('title'), str) or not isinstance(ask.get('author'), str) \
            or not ask['title'].strip() or not ask['author'].strip():
        return (), None
    return tuple(gaps), ask


class GapFill:
    def __init__(self, merge, research=None, clock=time.time):
        self.merge = merge
        self.database = merge.inventory.database
        self._research = research
        self.clock = clock
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.thread = None
        self.progress = None
        with connect(self.database) as db:
            db.execute(TABLE)

    @property
    def research(self):
        """The given research, else the automatic pass's own (its client, cache and per-site ledger)."""
        return self._research if self._research is not None else getattr(getattr(self.merge, 'automatic', None), 'research', None)

    # ------------------------------------------------------------------ thread
    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop.clear()
        self.thread = threading.Thread(target=self._run, name='books-gap-fill', daemon=True)
        self.thread.start()

    def close(self):
        self.stop.set()
        self.wake.set()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(30)

    def _run(self):
        if self.wake.wait(START_DELAY):
            self.wake.clear()
        while not self.stop.is_set():
            try:
                self.run_pass()
            except InterruptedError:
                pass
            except Exception:
                pass  # every book records its own outcome; a failed pass is tried again at the next one
            finally:
                self.progress = None
            self.wake.wait(self._next_wait())
            self.wake.clear()

    def _next_wait(self):
        due = [json.loads(row['record']).get('next_attempt') for row in
               self._rows("SELECT record FROM gap_fill WHERE state='deferred'")]
        due = [value for value in due if isinstance(value, (int, float))]
        return max(MIN_WAIT, min(PASS_WAIT, min(due) - self.clock())) if due else PASS_WAIT

    def status(self):
        value = self.progress
        return dict(value) if value else None

    def summary(self):
        """0.31.0 step 4b: plain counts of the whole detail look-up for /api/state (background_work), from the ledger and
        the last pass's count of books not visited yet: 'left' (to_look_up + between_tries; None until a pass has counted),
        'between_tries' and its earliest 'next_at' (epoch seconds), 'done' (found + none) and 'total'. R16: 'tries' is the
        limit of tries, {'per_source', 'spacing_seconds', 'failures'}, for the Waiting item's tooltip, and 'gave_up' counts
        the books settled 'none' with a source that never answered."""
        now = self.clock()
        rows = self._rows("SELECT job_id,state,json_extract(record,'$.next_attempt') AS next,"
                          "json_extract(record,'$.unreached') IS NOT NULL OR json_extract(record,'$.gave_up') IS NOT NULL AS gave_up FROM gap_fill")
        done = sum(1 for row in rows if row['state'] in FINAL)
        later = [row['next'] for row in rows if row['state'] == 'deferred' and isinstance(row['next'], (int, float)) and row['next'] > now]
        due = sum(1 for row in rows if row['state'] == 'deferred') - len(later)
        with connect(self.database) as db:
            jobs = db.execute('SELECT count(*) FROM audio_jobs').fetchone()[0]
        backlog = self.__dict__.get('_backlog')
        unvisited = len(backlog['unvisited'] - {row['job_id'] for row in rows}) if backlog and backlog['jobs'] == jobs else None
        to_look_up = None if unvisited is None else due + unvisited
        left = None if to_look_up is None else to_look_up + len(later)
        return {'known': unvisited is not None, 'left': left, 'to_look_up': to_look_up, 'between_tries': len(later), 'next_at': min(later) if later else None,
                'done': done, 'total': None if left is None else done + left, 'found': sum(1 for row in rows if row['state'] == 'found'),
                'none': sum(1 for row in rows if row['state'] == 'none'), 'gave_up': sum(1 for row in rows if row['state'] == 'none' and row['gave_up']),
                'tries': {'per_source': SOURCE_TRIES, 'spacing_seconds': TRY_SPACING, 'failures': FAILURE_TRIES}}

    # ------------------------------------------------------------------ ledger
    def _rows(self, sql, params=()):
        with connect(self.database) as db:
            return [dict(r) for r in db.execute(sql, params)]

    def entry(self, job_id):
        rows = self._rows('SELECT * FROM gap_fill WHERE job_id=?', (job_id,))
        if not rows:
            return None
        row = rows[0]
        row['record'] = json.loads(row['record'])
        return row

    def _set(self, job_id, candidate, state, reason, record):
        with connect(self.database) as db:
            db.execute('INSERT OR REPLACE INTO gap_fill VALUES(?,?,?,?,?,?)',
                       (job_id, candidate, state, reason, json.dumps(record, ensure_ascii=False), _stamp()))

    # ------------------------------------------------------------------ pass
    def candidates(self):
        """The newest job of each book whose approval left optional fields for this pass, not finished and not deferred."""
        entries = {r['job_id']: r for r in self._rows('SELECT job_id,state,record FROM gap_fill')}
        newest = {}
        for row in self._rows("SELECT job_id,json_extract(manifest,'$.candidate_id') AS candidate FROM audio_jobs ORDER BY created,job_id"):
            newest[row['candidate']] = row['job_id']
        result = []
        for row in self._rows("SELECT job_id,manifest FROM audio_jobs WHERE json_extract(manifest,'$.metadata_facts.gap_search.background') IS NOT NULL ORDER BY created,job_id"):
            manifest = json.loads(row['manifest'])
            if __import__('publication_reuse').task(manifest):continue
            if newest.get(manifest.get('candidate_id')) != row['job_id'] or not background(manifest)[0]:
                continue
            entry = entries.get(row['job_id'])
            if entry and (entry['state'] in FINAL or json.loads(entry['record']).get('next_attempt', 0) > self.clock()):
                continue
            result.append((row['job_id'], manifest))
        # 0.31.0 step 4b: the books with no ledger row yet, for summary() (with the job count it was taken at).
        self.__dict__['_backlog'] = {'unvisited': {job_id for job_id, _ in result if job_id not in entries},
                                     'jobs': self._rows('SELECT count(*) AS n FROM audio_jobs')[0]['n']}
        return result

    def run_pass(self):
        if self.research is None or not hasattr(self.research, 'fill_gaps'):
            return
        books = self.candidates()
        for index, (job_id, manifest) in enumerate(books):
            if self.stop.is_set():
                return
            self.progress = {'title': (manifest.get('metadata') or {}).get('title', ''), 'done': index, 'total': len(books)}
            self.fill(job_id, manifest)

    def fill(self, job_id, manifest):
        if __import__('publication_reuse').task(manifest):return
        """Ask the sources about one book's background gaps and record the outcome: found, none, or deferred."""
        gaps, ask = background(manifest)
        if not gaps:
            return None
        prior = (self.entry(job_id) or {}).get('record') or {}
        budget = {'remaining': BUDGET, 'lane': 'gap'}
        now = self.clock()
        candidate = manifest.get('candidate_id', '')
        # R16: what each source has done for this book so far: {source: {'answered'} | {'tries', 'next', 'reason'} | {'gave_up'}}.
        memory = {name: dict(value) for name, value in (prior.get('sources') or {}).items() if isinstance(value, dict)}
        settled = lambda state: bool(state.get('answered') or state.get('gave_up'))
        skip = sorted(name for name, state in memory.items() if settled(state) or isinstance(state.get('next'), (int, float)) and state['next'] > now)
        try:
            found, result = self.research.fill_gaps(ask, gaps, self.stop, budget, **({'skip': skip} if skip else {}))
        except InterruptedError:
            raise
        except Exception as error:
            # R16: a look-up that cannot finish is tried FAILURE_TRIES times, TRY_SPACING apart, then settled. It was tried
            # again every pass, without end.
            failures = int(prior.get('failures') or 0) + 1
            text = (str(error) or type(error).__name__)[:300]
            record = dict(prior, lookup_policy=LOOKUP_POLICY, gaps=list(gaps), last_attempt=now, failures=failures)
            if failures >= FAILURE_TRIES:
                record.pop('next_attempt', None)
                record['gave_up'] = True
                self._set(job_id, candidate, 'none', FAILED % failures + text, record)
                return 'none'
            record['next_attempt'] = now + TRY_SPACING
            self._set(job_id, candidate, 'deferred', 'Gap lookup could not finish: ' + text, record)
            return 'deferred'
        values = {key: found[key] for key in ('catalog', 'author_full') if found.get(key)}
        record = {'lookup_policy': LOOKUP_POLICY, 'gaps': list(gaps), 'ask': ask, 'found': values, 'unfilled': list(found.get('unfilled') or []),
                  'receipts': [dict(source) for source in result.get('sources', [])[:40]], 'last_attempt': now}
        wait = found.get('wait')
        closed = [name for name in found.get('closed') or [] if isinstance(name, str)]
        closures = [item for item in found.get('closures') or [] if isinstance(item, dict) and item.get('source') in closed]
        if not closures and wait and closed:
            closures = [dict(wait, source=name) for name in closed]  # a research that names no closure: its one wait stands for each
        counted = set()
        for item in closures:
            name = item['source']
            if name in counted:
                continue  # one try per source and pass (an edition's title and its book title ask the same source twice)
            counted.add(name)
            state = memory.setdefault(name, {})
            state.pop('answered', None)
            retry = item['retry_at'] if isinstance(item.get('retry_at'), (int, float)) else now + PASS_WAIT
            if item.get('kind') in NO_TRY_KINDS:
                state['next'] = max(now + MIN_WAIT, retry)  # the app's own bound: no try; it goes on from here
            else:
                state['tries'] = int(state.get('tries') or 0) + 1
                state['reason'] = str(item.get('reason') or '')[:200]
                if state['tries'] >= SOURCE_TRIES:
                    state['gave_up'] = True
                    state.pop('next', None)
                else:
                    state['next'] = max(retry, now + TRY_SPACING)
        for name in found.get('asked') or []:
            if isinstance(name, str) and not any(item.get('source') == name for item in found.get('closures') or [] if isinstance(item, dict)):
                memory[name] = {'answered': True, 'at': now}  # it answered: never asked about this book again
        if memory:
            record['sources'] = memory
        waiting = sorted(name for name, state in memory.items() if not settled(state))
        if record['unfilled'] and waiting:
            due = [memory[name]['next'] for name in waiting if isinstance(memory[name].get('next'), (int, float))]
            record['next_attempt'] = max(now + MIN_WAIT, float(min(due)) if due else now + PASS_WAIT)
            if wait:
                record['wait'] = wait
            if values:
                record['partial'] = True
            self._set(job_id, candidate, 'deferred', str((wait or {}).get('reason') or 'A source is closed'), record)
            return 'deferred'
        # Settled: every source answered or was given up after SOURCE_TRIES tries (named in 'unreached').
        unreached = sorted(name for name, state in memory.items() if state.get('gave_up')) if record['unfilled'] else []
        if unreached:
            record['unreached'] = unreached
        state = 'found' if values else 'none'
        reason = '' if values else UNREACHED + ', '.join(unreached) if unreached else 'No source confirmed the missing fields'
        self._set(job_id, candidate, state, reason, record)
        return state
