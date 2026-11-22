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


def settled(state):
    """True for a source that has answered about a book, or was given up after its tries: never asked about it again."""
    return bool(state.get('answered') or state.get('gave_up'))


def remember(memory, found, now, wait=None, floor=None, ceiling=None, tries=None, candidate_wait=None):
    """The bounded-tries rule (R16), in one place for this pass and for the look-up before review
    (public_research._bounded_lookup, 0.31.0 step 2): write into memory what each source did in one look-up.
      memory  {source: {'answered'} | {'tries', 'next', 'reason'} | {'gave_up'}}, kept with the book between its visits
      found   the look-up's answer (public_research._gap_fill): 'asked', 'closed', 'closures'
      wait    the look-up's one wait, for a research that names no closure
    A source that answered is settled. The app's own bound and a busy catalog (NO_TRY_KINDS) are no try: the source is due
    again when the bound reopens. Any other closure is a try: after `tries` of them the source is given up; before that it
    is due when it says it reopens, never sooner than `floor` seconds from now (default TRY_SPACING) and, with `ceiling`,
    never later than that. candidate_wait: seconds until the next visit when only this visit's own request budget ran out
    (default: the closure's own time)."""
    floor = TRY_SPACING if floor is None else floor
    tries = SOURCE_TRIES if tries is None else tries  # read at the call: the module's number, never a copy of it
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
            # the app's own bound: no try; it goes on from here
            state['next'] = now + candidate_wait if candidate_wait is not None and item.get('scope') == 'candidate' else max(now + MIN_WAIT, retry)
        else:
            state['tries'] = int(state.get('tries') or 0) + 1
            state['reason'] = str(item.get('reason') or '')[:200]
            if state['tries'] >= tries:
                state['gave_up'] = True
                state.pop('next', None)
            else:
                state['next'] = max(retry, now + floor) if ceiling is None else min(max(retry, now + floor), now + ceiling)
    for name in found.get('asked') or []:
        if isinstance(name, str) and not any(item.get('source') == name for item in found.get('closures') or [] if isinstance(item, dict)):
            memory[name] = {'answered': True, 'at': now}  # it answered: never asked about this book again
    return memory


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
        try:
            held = self._held_counts(force=True).get('next_at')
        except Exception:
            held = None
        if isinstance(held, (int, float)):
            due.append(held)  # a review-list row's next try (0.31.0 step 2)
        return max(MIN_WAIT, min(PASS_WAIT, min(due) - self.clock())) if due else PASS_WAIT

    def status(self):
        value = self.progress
        return dict(value) if value else None

    # ------------------------------------------------------------------ review-list rows (0.31.0 step 2, rulings R2 and R5)
    # A book held for Sergei is looked up before he reviews it: research asks the sources once when it holds the book
    # (public_research._held_lookup), and this pass goes on with it, in the same 'gap' lane and under the same bounded
    # tries, until every source has answered or is given up: the rows that were already held when 0.31.0 first starts,
    # and any row whose source was closed. The record is kept with the book's own research result (automatic_candidates
    # 'lookup'); the row's preview and Approve read the answers from it and from the research cache. Nothing is filed or
    # changed here, and a row research has taken up again meanwhile is left to it (the write is compare-and-swap).
    HELD_SQL = ("SELECT c.id AS id,c.revision AS revision,c.fingerprint AS fingerprint,json_extract(c.result,'$.lookup.policy') AS policy,"
                "json_extract(c.result,'$.lookup.waiting') AS waiting,json_extract(c.result,'$.lookup.next_at') AS next_at,"
                "json_extract(c.result,'$.lookup.nothing') AS none_to_ask FROM automatic_candidates c JOIN book_groups g "
                "ON g.id=c.id AND g.revision=c.revision AND g.fingerprint=c.fingerprint WHERE c.state='Held' AND g.superseded=0 ORDER BY c.attempted,c.id")
    HELD_RECOUNT = 30  # seconds: the counts for the page are read again at most this often while research results change

    def _held_rows(self):
        from public_research import LOOKUP_POLICY
        with connect(self.database) as db:
            have = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('automatic_candidates','book_groups')")}
            if len(have) != 2:
                return []
            rows = [dict(row) for row in db.execute(self.HELD_SQL)]
        for row in rows:
            row['current'] = row.pop('policy') == LOOKUP_POLICY
            row['nothing'] = row.pop('none_to_ask')
        return rows

    def _held_counts(self, force=False):
        """{'left', 'to_look_up', 'between_tries', 'next_at', 'done', 'total'} of the review-list rows' look-up. Counted from
        the catalog when a research result changed (at most every HELD_RECOUNT seconds for a poll), else kept."""
        now = self.clock()
        kept = self.__dict__.get('_held')
        with connect(self.database) as db:
            have = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='automatic_result_revision'").fetchone()
            revision = (db.execute('SELECT revision FROM automatic_result_revision WHERE id=1').fetchone() or (None,))[0] if have else None
        if kept and kept['revision'] == revision and (kept['counts']['next_at'] is None or kept['counts']['next_at'] > now):
            return dict(kept['counts'])
        if kept and not force and time.monotonic() - kept['at'] < self.HELD_RECOUNT:
            return dict(kept['counts'])
        rows = self._held_rows()
        later = [row['next_at'] for row in rows if row['current'] and row['waiting'] and isinstance(row['next_at'], (int, float)) and row['next_at'] > now]
        due = sum(1 for row in rows if not row['current'] or row['waiting']) - len(later)
        done = sum(1 for row in rows if row['current'] and not row['waiting'] and not row['nothing'])
        counts = {'left': due + len(later), 'to_look_up': due, 'between_tries': len(later), 'next_at': min(later) if later else None,
                  'done': done, 'total': done + due + len(later), 'nothing_to_ask': sum(1 for row in rows if row['current'] and row['nothing'])}
        self.__dict__['_held'] = {'revision': revision, 'at': time.monotonic(), 'counts': counts}
        return dict(counts)

    def _held_title(self, book_id):
        try:
            with connect(self.database) as db:
                row = db.execute("SELECT json_extract(evidence,'$.title_clue') FROM book_groups WHERE id=?", (book_id,)).fetchone()
            return (row[0] if row else '') or ''
        except Exception:
            return ''

    def held_candidates(self):
        """The review-list rows whose look-up is due: not looked up under this policy yet, or waiting and at its next try."""
        now = self.clock()
        return [row for row in self._held_rows() if not row['current'] or row['waiting'] and not (isinstance(row['next_at'], (int, float)) and row['next_at'] > now)]

    def look_up_held(self, entry):
        """One review-list row: ask the sources (research.held_lookup) and keep the record with the row's research result,
        only while that result is still the one read here. Returns 'saved', 'changed' (research took the row up
        meanwhile, or it is no longer held: nothing written) or 'gone'."""
        automatic = getattr(self.merge, 'automatic', None)
        reviews = getattr(self.merge, 'reviews', None)
        if automatic is None or reviews is None or not hasattr(self.research, 'held_lookup'):
            return 'gone'
        with connect(self.database) as db:
            saved = db.execute("SELECT result FROM automatic_candidates WHERE id=? AND revision=? AND fingerprint=? AND state='Held'",
                               (entry['id'], entry['revision'], entry['fingerprint'])).fetchone()
        if not saved:
            return 'changed'
        try:
            result = json.loads(saved[0] or '{}')
            row = reviews._row('Audiobooks', entry['id'])
        except ValueError:
            return 'gone'
        if row.get('revision') != entry['revision'] or row.get('fingerprint') != entry['fingerprint'] or row.get('manual_conversion'):
            return 'changed'
        from public_research import LOOKUP_POLICY
        prior = result.get('lookup') if isinstance(result.get('lookup'), dict) and result['lookup'].get('policy') == LOOKUP_POLICY else None
        try:
            record = self.research.held_lookup(row, automatic._candidate_root(row), prior, self.stop)
        except InterruptedError:
            raise
        except Exception as error:
            # A row that cannot be looked up is not tried again at every pass: recorded as nothing to ask, with why.
            record = {'policy': LOOKUP_POLICY, 'nothing': True, 'fields': {}, 'waiting': False, 'next_at': None, 'sources': {}, 'tries': 0,
                      'doubtful': [], 'found': {}, 'error': (str(error) or type(error).__name__)[:200]}
        result['lookup'] = record
        with connect(self.database) as db:
            changed = db.execute("UPDATE automatic_candidates SET result=? WHERE id=? AND revision=? AND fingerprint=? AND state='Held' AND result=?",
                                 (json.dumps(result, ensure_ascii=False), entry['id'], entry['revision'], entry['fingerprint'], saved[0])).rowcount
        self.__dict__['_held'] = None
        return 'saved' if changed else 'changed'

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
        # 0.31.0 step 2: the review-list rows this pass also looks up (books held for Sergei, before he reviews them). Their
        # numbers are in 'review', and inside the totals too, so the finished state never says "all done" while one of
        # them is still to be asked about; 'approved' keeps the numbers of the books already approved alone.
        try:
            review = self._held_counts()
        except Exception:
            review = None
        approved = {'left': left, 'to_look_up': to_look_up, 'between_tries': len(later), 'next_at': min(later) if later else None,
                    'done': done, 'total': None if left is None else done + left}
        nexts = later + ([review['next_at']] if review and isinstance(review.get('next_at'), (int, float)) else [])
        extra = review or {'left': 0, 'to_look_up': 0, 'between_tries': 0, 'done': 0, 'total': 0}
        from public_research import LOOKUP_MAX_WAIT, LOOKUP_RETRY_MIN, LOOKUP_SOURCES
        return {'known': unvisited is not None, 'left': None if left is None else left + extra['left'],
                'to_look_up': None if to_look_up is None else to_look_up + extra['to_look_up'], 'between_tries': len(later) + extra['between_tries'],
                'next_at': min(nexts) if nexts else None, 'done': done + extra['done'], 'total': None if left is None else done + left + extra['total'],
                'found': sum(1 for row in rows if row['state'] == 'found'),
                'none': sum(1 for row in rows if row['state'] == 'none'), 'gave_up': sum(1 for row in rows if row['state'] == 'none' and row['gave_up']),
                'tries': {'per_source': SOURCE_TRIES, 'spacing_seconds': TRY_SPACING, 'failures': FAILURE_TRIES},
                'approved': approved, 'review': review,
                'review_tries': {'per_source': SOURCE_TRIES, 'min_spacing_seconds': LOOKUP_RETRY_MIN, 'max_spacing_seconds': TRY_SPACING,
                                 'max_wait_seconds': LOOKUP_MAX_WAIT, 'sources': list(LOOKUP_SOURCES)}}

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
        # 0.31.0 step 2: the review-list rows first (they wait for Sergei's eyes), then the books already approved. Both
        # use the 'gap' lane's share of each site's hourly bound, so a row that finds the share used waits for it: no try.
        held = self.held_candidates() if hasattr(self.research, 'held_lookup') else []
        for index, entry in enumerate(held):
            if self.stop.is_set():
                return
            self.progress = {'title': self._held_title(entry['id']), 'done': index, 'total': len(held) + len(books), 'about': 'review'}
            self.look_up_held(entry)
        for index, (job_id, manifest) in enumerate(books):
            if self.stop.is_set():
                return
            self.progress = {'title': (manifest.get('metadata') or {}).get('title', ''), 'done': len(held) + index, 'total': len(held) + len(books), 'about': 'approved'}
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
        remember(memory, found, now, wait)
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
