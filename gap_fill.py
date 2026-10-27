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
"""
import json
import threading
import time

from scanner import connect

TABLE = ('CREATE TABLE IF NOT EXISTS gap_fill(job_id TEXT PRIMARY KEY,candidate_id TEXT NOT NULL,state TEXT NOT NULL,'
         'reason TEXT NOT NULL,record TEXT NOT NULL,updated TEXT NOT NULL)')
FINAL = ('found', 'none')
LOOKUP_POLICY = 'gap-fill-22.1-v1'
PASS_WAIT = 600     # seconds between passes when nothing is due sooner
START_DELAY = 180   # after startup: the published check, the queue and series backfill come first
MIN_WAIT = 30
BUDGET = 12         # requests per book, as research had


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
            if newest.get(manifest.get('candidate_id')) != row['job_id'] or not background(manifest)[0]:
                continue
            entry = entries.get(row['job_id'])
            if entry and (entry['state'] in FINAL or json.loads(entry['record']).get('next_attempt', 0) > self.clock()):
                continue
            result.append((row['job_id'], manifest))
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
        """Ask the sources about one book's background gaps and record the outcome: found, none, or deferred."""
        gaps, ask = background(manifest)
        if not gaps:
            return None
        prior = (self.entry(job_id) or {}).get('record') or {}
        budget = {'remaining': BUDGET, 'lane': 'gap'}
        now = self.clock()
        try:
            found, result = self.research.fill_gaps(ask, gaps, self.stop, budget)
        except InterruptedError:
            raise
        except Exception as error:
            record = dict(prior, lookup_policy=LOOKUP_POLICY, gaps=list(gaps), last_attempt=now, next_attempt=now + PASS_WAIT,
                          failures=prior.get('failures', 0) + 1)
            self._set(job_id, manifest.get('candidate_id', ''), 'deferred', 'Gap lookup could not finish: ' + (str(error) or type(error).__name__)[:300], record)
            return 'deferred'
        values = {key: found[key] for key in ('catalog', 'author_full') if found.get(key)}
        record = {'lookup_policy': LOOKUP_POLICY, 'gaps': list(gaps), 'ask': ask, 'found': values, 'unfilled': list(found.get('unfilled') or []),
                  'receipts': [dict(source) for source in result.get('sources', [])[:40]], 'last_attempt': now}
        wait = found.get('wait')
        if wait and record['unfilled']:
            record['next_attempt'] = max(now + MIN_WAIT, float(wait.get('retry_at') or now + PASS_WAIT))
            record['wait'] = wait
            if values:
                record['partial'] = True
            self._set(job_id, manifest.get('candidate_id', ''), 'deferred', str(wait.get('reason') or 'A source is closed'), record)
            return 'deferred'
        state = 'found' if values else 'none'
        reason = '' if values else 'No source confirmed the missing fields'
        self._set(job_id, manifest.get('candidate_id', ''), state, reason, record)
        return state
