"""0.31.0 milestone B (Sergei 2026-11-22, rulings R18, R19, R20, R24 and R26; Judy's BooksArranger_0.31.0_UX.md, section 3):
finished audiobooks are renamed and moved by the rules, with no approval step, and with a record.

What moves a book is unchanged: the series write of series_backfill (retag in the book's own folder, its proofs, a
no-replace rename, the catalog, then the old file removed) and the app's verified move (book_move: the exact held file
hashed, a no-replace rename or a verified copy, journaled and recovered). What is new is who applies the list. Until
0.31.0 Sergei approved sorting_moves.plan()'s list; now this pass applies it, one book at a time:

  - every book goes through sorting_moves.plan(), so each of its refusals still decides (not in Audiobooks Sorted, a folder
    he chose, files kept at his choice, a replacement, a name the app did not give, a file that is not where the catalog
    says, a file already at the new name, two books for one name, retained while the data folder move is unfinished);
  - the plan computes one final name and folder from all rules together (a series found, the author's folder, the series'
    name, the English title), so a book moves once; a book whose series or detail look-up has not ended waits for it, so
    an answer that comes later never moves it a second time (R19);
  - a doubtful result never reaches the plan (series_certainty; sorting_moves.certain): nothing happens and nothing says so;
  - a book something else still works on (its cleanup, its recovery copies, its working files) is skipped until that has
    ended (series_backfill.settled), and one that converts or is queued is held by the move's own blocker (action_queue);
  - a folder Sergei chose with Choose folder… is his: the plan refuses that book for good (R26).

Pacing. At most FEED books are in hand at a time (a series write approved, or a move queued as the app's own action), so a
press Sergei makes waits behind one or two moves, never behind several hundred. A Pause of the audiobook jobs holds the
pass, the series writes and the app's own queued moves (his Pause, or one saved before this launch: nothing here ends a
Pause). Nothing is kept in a queue of its own: after a Quit the remaining work is derived again from the rules at the
next pass, and a book in hand is taken up where it stopped (its open entry below), so each book is queued once.

The record (table rule_filings). One entry is one time the rules were applied to one book: where it was, where it ended,
when, the kinds of change and the reason for each with its source, the title and author it is filed under now. A series
write and the move after it are one entry. 'open' while in hand, 'done' when the change finished (only these are listed),
'failed' when it started and did not finish: such a book is tried again at most TRIES times, SPACING seconds apart, and is
listed among the books that could not be renamed or moved until it has moved.

Every number the page shows comes from summary(): books left, the three waiting groups, the books that could not be
renamed or moved, the record's count and last time. The page words everything; there is no copy here.

Author names (R23; milestone A's canonical_names.latin_order). A Latin author name whose order the app cannot tell stays as
it is filed: nothing asks, nothing moves. It is put in order only on evidence, and the pass uses the evidence the catalog
already holds (author_orders(): the detail look-up's own records, never a new request): a rule research learned by the old
guess ("Cixin Liu") is replaced by a newer learned rule, and an unruled name gets one. The finished books then follow by
the list like any other author-folder change. A name Sergei ruled or kept is never touched."""
import datetime
import json
import sqlite3
import threading
import time
import uuid

import sorting_moves
from scanner import connect

TABLE = ('CREATE TABLE IF NOT EXISTS rule_filings(filing_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, candidate_id TEXT NOT NULL, state TEXT NOT NULL,'
         ' step TEXT NOT NULL, from_path TEXT NOT NULL, to_path TEXT NOT NULL, placed_path TEXT, final_path TEXT, kinds TEXT NOT NULL,'
         ' reasons TEXT NOT NULL, title TEXT NOT NULL, author TEXT NOT NULL, move_id TEXT, cause TEXT, detail TEXT,'
         ' created_utc TEXT NOT NULL, updated_utc TEXT NOT NULL, done_utc TEXT, written TEXT)')
# 0.31.0 R27: 'written', what the change put inside the file's tags (WRITTEN_KINDS, a JSON list; NULL: nothing, as for a move,
# and for every entry made before the column). Added to a table made by an earlier 0.31.0 build (setup()).
WRITTEN_KINDS = ('series', 'title', 'author')
INDEXES = ("CREATE UNIQUE INDEX IF NOT EXISTS rule_filings_open ON rule_filings(job_id) WHERE state='open'",  # one book, one entry in hand
           'CREATE INDEX IF NOT EXISTS rule_filings_by_state ON rule_filings(state,done_utc)')
OPEN, DONE, FAILED = 'open', 'done', 'failed'
ORIGIN = 'rules'           # book_move.ORIGINS: the mark of a move the app queued by its rules
START_DELAY = 130          # seconds after the engine has loaded: move recovery, the queue and the series look-up's count come first
PASS_WAIT = 600            # between passes when nothing is left
BUSY_WAIT = 60             # between passes while books are left (a finished move wakes the pass at once)
FEED = 2                   # books in hand at a time
TRIES = 3                  # a rename or move that did not finish is tried this often in all,
SPACING = 3600             # this many seconds apart; then the book stays listed until its planned place changes
REFUSALS = 3               # a book the engine would not even queue this often in one run is recorded as failed
# Refusals to queue a move that pass by themselves (the app is closing, the book has another queued action, a move of it
# runs): no try and no record; the next pass asks again.
PASSING = ('Move was not accepted. Nothing was moved.', 'Books Arranger is closing. Nothing was moved.', 'This audiobook is being moved now',
           'Close and reopen Books Arranger to finish the move', 'This audiobook is being renamed now')
RECORD_LIMIT = 200         # entries the record's route returns at a time (Judy 3.4)
DID_NOT_FINISH = 'did_not_finish'  # the could-not-move key of a change that started and did not finish
COULD_NOT_KEYS = sorting_moves.LASTING_KEYS + (DID_NOT_FINISH,)


def _stamp(epoch):
    return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).isoformat()


def _epoch(value):
    try:
        return datetime.datetime.fromisoformat(str(value)).timestamp()
    except ValueError:
        return 0.0


def setup(db):
    db.execute(TABLE)
    if 'written' not in {row[1] for row in db.execute('PRAGMA table_info(rule_filings)')}:
        db.execute('ALTER TABLE rule_filings ADD COLUMN written TEXT')
    for statement in INDEXES:
        db.execute(statement)


def have(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='rule_filings'").fetchone() is not None


def _row(record):
    value = dict(record)
    for name in ('kinds', 'reasons', 'written'):
        try:
            value[name] = json.loads(value[name]) if name in value else []
        except (TypeError, ValueError):
            value[name] = []
        if not isinstance(value[name], list):
            value[name] = []
    return value


def totals(db):
    """(how many finished audiobooks' changes the record holds, the time of the last one or None)."""
    if not have(db):
        return 0, None
    count, last = db.execute("SELECT count(*),max(done_utc) FROM rule_filings WHERE state='done'").fetchone()
    return count or 0, last


def record(db, output_root=None, search='', limit=RECORD_LIMIT):
    """The record for the page (Judy 3.4): {'count': every entry, 'matching': the entries the text matches, 'last_at',
    'entries': the newest `limit` of them}. search: a text looked for in every entry's title, author and both paths, case
    aside; '' matches all. An entry: {'id', 'book_id', 'job_id', 'title', 'author' (as filed now), 'at', 'from', 'to',
    'from_shown', 'to_shown' (under Audiobooks Sorted), 'kinds', 'reasons' (sorting_moves.REASON_KINDS, as fields),
    'in_app': the book is still in the app's list, 'written' (0.31.0 R27): what went inside the file's tags (WRITTEN_KINDS;
    [] for a change of path only)}."""
    limit = max(1, min(int(limit or RECORD_LIMIT), RECORD_LIMIT))
    count, last = totals(db)
    if not count:
        return {'count': 0, 'matching': 0, 'last_at': None, 'limit': limit, 'entries': []}
    rows = [_row(row) for row in db.execute("SELECT * FROM rule_filings WHERE state='done' ORDER BY done_utc DESC, rowid DESC")]
    wanted = str(search or '').strip().casefold()
    if wanted:
        rows = [row for row in rows if any(wanted in str(row.get(name) or '').casefold() for name in ('title', 'author', 'from_path', 'final_path'))]
    shown = rows[:limit]
    listed = set()
    if shown and db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='book_groups'").fetchone():
        listed = {row[0] for row in db.execute('SELECT id FROM book_groups WHERE superseded=0 AND id IN (SELECT value FROM json_each(?))',
                                               (json.dumps([row['candidate_id'] for row in shown]),))}
    entries = [{'id': row['filing_id'], 'book_id': row['candidate_id'], 'job_id': row['job_id'], 'title': row['title'], 'author': row['author'],
                'at': row['done_utc'], 'from': row['from_path'], 'to': row['final_path'], 'from_shown': sorting_moves._shown(row['from_path'], output_root),
                'to_shown': sorting_moves._shown(row['final_path'], output_root), 'kinds': row['kinds'], 'reasons': row['reasons'],
                'in_app': row['candidate_id'] in listed, 'written': row['written']} for row in shown]
    return {'count': count, 'matching': len(rows), 'last_at': last, 'limit': limit, 'entries': entries}


def author_orders(database):
    """B8: the Latin author names whose order the app cannot tell by itself and that the catalog's own records put in
    order: [{'name': as filed now, 'ordered', 'why', 'source_url', 'credit': the learned rule's credit or None}]. A name is
    listed only when every record that speaks of it gives the same order and that order is another than the one it is
    filed under. Candidates: the target of a rule research learned (never one of Sergei's), and the author of a finished
    book that no rule decides. Evidence: canonical_names.latin_order on the detail look-up's record of a work by that
    author (the source's family-name field, the work's language, the credit in the files). Reads only."""
    import author_rules
    import canonical_names
    import local_identity
    from public_research import _order_evidence
    rules = author_rules.load(database)
    if rules is None:
        return []

    def unknown(name):
        return bool(name) and local_identity.script(name) == 'latin' and len(name.split()) >= 2 and canonical_names.latin_order(name)[1] == canonical_names.ORDER_UNKNOWN
    learned = {local_identity.text(row['target']): row for row in rules.rules
               if row['kind'] == 'same_as' and row.get('actor') == 'assistant' and unknown(local_identity.text(row['target'])) and not rules.taken_back(row['credit_as_seen'], row['scope'])}
    his = {local_identity.text(row['target']).casefold() for row in rules.rules if row['kind'] == 'same_as' and row.get('actor') != 'assistant'}
    with connect(database) as db:
        records = []
        have = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='gap_fill'").fetchone()
        for (text,) in db.execute("SELECT record FROM gap_fill WHERE state='found'") if have else ():
            try:
                value = json.loads(text)
                catalog = (value.get('found') or {}).get('catalog')
            except (TypeError, ValueError, AttributeError):
                continue
            if isinstance(catalog, dict) and local_identity.text(catalog.get('author_latin')):
                records.append((catalog, str((value.get('ask') or {}).get('author') or '') if isinstance(value.get('ask'), dict) else ''))
        authors = [local_identity.text(row[0]) for row in db.execute(
            "SELECT DISTINCT json_extract(manifest,'$.metadata.author') FROM audio_jobs WHERE state='completed' AND output IS NOT NULL")] if records else []
    if not records and not learned:
        return []
    # A name the rules already file under another spelling (a learned rule corrected before) needs nothing more.
    plain = {name for name in authors if name not in learned and unknown(name) and rules.rule(name) is None and not rules.taken_back(name)
             and canonical_names.author(name, rules)[0] == name}
    found = []
    for name in sorted(set(learned) | plain):
        if name.casefold() in his:
            continue  # the spelling of one of his own rules: his
        wanted, orders = canonical_names._order_key(name), {}
        if name in learned:
            # The rule's own credit is evidence too (latin_order's fourth: the credit in the files shows which word is the
            # surname): «Лю Цысинь» for "Cixin Liu". The old guess turned the name around whichever way the credit read.
            ordered, why = canonical_names.latin_order(name, learned[name]['credit_as_seen'], {})
            if why != canonical_names.ORDER_UNKNOWN and canonical_names._order_key(ordered) == wanted:
                orders[ordered] = (why, str(learned[name].get('source') or ''))
        for catalog, credit in records:
            latin = local_identity.text(catalog.get('author_latin'))
            if canonical_names._order_key(latin) != wanted:
                continue
            row = learned.get(name)
            ordered, why = canonical_names.latin_order(latin, row['credit_as_seen'] if row else credit, _order_evidence(catalog))
            if why != canonical_names.ORDER_UNKNOWN and canonical_names._order_key(ordered) == wanted:
                orders.setdefault(ordered, (why, str(catalog.get('source_url') or '')))
        if len(orders) == 1:
            ordered, (why, url) = next(iter(orders.items()))
            if ordered != name:
                found.append({'name': name, 'ordered': ordered, 'why': why, 'source_url': url, 'credit': learned[name]['credit_as_seen'] if name in learned else None,
                              'scope': learned[name]['scope'] if name in learned else ''})
    return found


def order_authors(database):
    """Write what author_orders() found as learned author rules (actor 'assistant', the newest rule for a credit wins):
    the corrected target for a learned rule's credit, or the name in order for a name no rule decided. Returns the list."""
    import author_rules
    found = author_orders(database)
    if found:
        with connect(database) as db:
            author_rules.setup(db)
            for entry in found:
                author_rules.append(db, 'same_as', entry['credit'] or entry['name'], target=entry['ordered'], scope=entry['scope'], actor='assistant',
                                    source=entry['source_url'] or 'detail look-up', question='Name order: ' + entry['why'][:200])
    return found


def kinds_of(item):
    """The kinds of change of a planned book as the record names them (sorting_moves.REASON_KINDS)."""
    names = {'series_language': 'series_name'}
    return [names.get(name, name) for name in item.get('items') or []]


def route(item, names_writer=True):
    """How a planned book is put in hand (0.31.0 R27, one pass per book): 'write', its series written into the file (with the
    names the list files it under, in the same rewrite); 'names', its new title or author credit written into the file
    (name_write) when it has no series to write; 'move', the app's verified move alone (the new name and folder only). A
    book whose write is done (placed) is moved. names_writer: the engine runs the write of names."""
    if 'series' in (item.get('items') or []) and not item.get('placed'):
        return 'write'
    if item.get('names') and not item.get('placed') and names_writer:
        return 'names'
    return 'move'


def written_kinds(record):
    """WRITTEN_KINDS a finished write's ledger record says went into the file: the series (series_backfill), the title
    and the author credit (record 'names')."""
    names = record.get('names') if isinstance(record.get('names'), dict) else {}
    found = ['series'] if record.get('series') else []
    if 'title' in names:
        found.append('title')
    if 'canonical_author' in names:
        found.append('author')
    return found


class RuleFiling:
    """The pass (module text). merge: the MergeService; clock: epoch seconds (a test's own)."""

    def __init__(self, merge, clock=time.time):
        self.merge = merge
        self.database = merge.inventory.database
        self.clock = clock
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.thread = None
        self.lock = threading.Lock()
        self.error = None
        self._value = None
        self._could_not = []
        self._refusals = {}
        self._orders_read = None
        with connect(self.database) as db:
            setup(db)

    # ------------------------------------------------------------------ thread
    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop.clear()
        self.thread = threading.Thread(target=self._run, name='books-rule-filing', daemon=True)  # close() stops it; a hard exit leaves journals only
        self.thread.start()

    def close(self):
        self.stop.set()
        self.wake.set()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(30)

    def notify(self):
        """A move or a series write ended: the pass looks again now, not at its next wait."""
        self.wake.set()

    def _run(self):
        if self.wake.wait(START_DELAY):
            self.wake.clear()
        while not self.stop.is_set():
            wait = PASS_WAIT
            try:
                value = self.tick()
                self.error = None
                if value and value.get('left'):
                    wait = BUSY_WAIT
            except Exception as error:  # never ends the thread; the next pass derives everything again
                self.error = (str(error) or type(error).__name__)[:300]
                wait = BUSY_WAIT
            self.wake.wait(wait)
            self.wake.clear()

    # ------------------------------------------------------------------ the catalog
    def _rows(self, sql, params=()):
        with connect(self.database) as db:
            return [_row(row) for row in db.execute(sql, params)]

    def _open(self):
        """{job id: its entry in hand}."""
        return {row['job_id']: row for row in self._rows("SELECT * FROM rule_filings WHERE state='open' ORDER BY created_utc, rowid")}

    def _stamp(self):
        """Now, by the pass's own clock (the spacing of tries reads the same clock)."""
        return _stamp(self.clock())

    def _update(self, filing_id, **fields):
        fields['updated_utc'] = self._stamp()
        with connect(self.database) as db:
            db.execute('UPDATE rule_filings SET ' + ','.join(name + '=?' for name in fields) + ' WHERE filing_id=?', (*fields.values(), filing_id))

    def _begin(self, item):
        """A new entry in hand for a planned book. A book whose last try wrote its series and then could not move keeps the
        place it was in before that write, so the entry never starts at the in-between name."""
        now = self._stamp()
        filing_id = str(uuid.uuid4())
        filed = item.get('filed') or {}
        start = item['from']
        with connect(self.database) as db:
            prior = db.execute("SELECT from_path,placed_path FROM rule_filings WHERE job_id=? AND state='failed' ORDER BY updated_utc DESC, rowid DESC LIMIT 1",
                               (item['job_id'],)).fetchone()
            if prior and prior[1] and sorting_moves.key(prior[1]) == sorting_moves.key(start):
                start = prior[0]
            db.execute('INSERT INTO rule_filings(filing_id,job_id,candidate_id,state,step,from_path,to_path,placed_path,final_path,kinds,reasons,title,author,'
                       'move_id,cause,detail,created_utc,updated_utc,done_utc) VALUES(?,?,?,?,?,?,?,NULL,NULL,?,?,?,?,NULL,NULL,NULL,?,?,NULL)',
                       (filing_id, item['job_id'], str(item.get('book_id') or ''), OPEN, '', start, item['to'], json.dumps(kinds_of(item)),
                        json.dumps(item.get('reasons') or [], ensure_ascii=False), str(filed.get('title') or item.get('title') or ''),
                        str(filed.get('author') or item.get('author') or ''), now, now))
        return {'filing_id': filing_id, 'job_id': item['job_id'], 'step': '', 'from_path': start, 'to_path': item['to'], 'placed_path': None, 'move_id': None}

    def _finish(self, filing, final, detail=None):
        self._update(filing['filing_id'], state=DONE, final_path=str(final), done_utc=self._stamp(), detail=detail)

    def _fail(self, filing, cause, detail):
        self._update(filing['filing_id'], state=FAILED, cause=str(cause or '')[:60], detail=str(detail or '')[:500])

    def _drop(self, filing):
        """An entry for which nothing was changed (the engine would not queue it): it never was."""
        with connect(self.database) as db:
            db.execute("DELETE FROM rule_filings WHERE filing_id=? AND state='open' AND placed_path IS NULL", (filing['filing_id'],))

    def _failed(self):
        """{(job id, planned path): (tries that did not finish, epoch of the last one, the last one's cause key)}."""
        found = {}
        for row in self._rows("SELECT job_id,to_path,updated_utc,cause,kinds,reasons FROM rule_filings WHERE state='failed' ORDER BY updated_utc,rowid"):
            name = (row['job_id'], sorting_moves.key(row['to_path']))
            count, last, _ = found.get(name, (0, 0.0, None))
            found[name] = (count + 1, max(last, _epoch(row['updated_utc'])), row['cause'] or None)
        return found

    # ------------------------------------------------------------------ entries in hand
    def reconcile(self):
        """Close every entry in hand whose work has ended, from the series look-up's ledger and the move journal; an entry
        whose queued move was taken back before it ran (the app closed) goes back to be queued again."""
        import book_move
        ledgers = {'write': self.merge.__dict__.get('series_backfill'), 'names': self.merge.__dict__.get('name_write')}
        for filing in self._open().values():
            if filing['step'] in ledgers:
                ledger = ledgers[filing['step']]
                entry = ledger.entry(filing['job_id']) if ledger is not None else None
                if entry is None:
                    self._fail(filing, 'changed', 'The series update is not on record' if filing['step'] == 'write' else 'The new names are not on record')
                    continue
                state, written = entry['state'], entry['record']
                if state == 'done':
                    follow = written.get('follow_up')
                    if not isinstance(follow, dict):
                        continue  # its move into the series folder is still to be asked for
                    placed = written.get('new_path')
                    move_id = (follow.get('move') or {}).get('move_id') if isinstance(follow.get('move'), dict) else None
                    tags = json.dumps(written_kinds(written))
                    if follow.get('state') == 'none':
                        self._update(filing['filing_id'], written=tags)
                        self._finish(filing, placed)
                        continue
                    if move_id:
                        filing = dict(filing, step='move', move_id=move_id, placed_path=placed)
                        self._update(filing['filing_id'], step='move', move_id=move_id, placed_path=placed, written=tags)
                    else:
                        # Written and renamed in its own folder; the move was not queued. The plan lists the book again from
                        # there (sorting_moves: placed) and this entry goes on with it.
                        self._update(filing['filing_id'], step='', placed_path=placed, written=tags, detail=str(follow.get('reason') or follow.get('state') or '')[:500])
                        continue
                elif state in ('held', 'none', 'skipped'):
                    self._fail(filing, sorting_moves.reason_key(entry['reason'], sorting_moves.NOT_MOVED_KEYS), entry['reason'])
                    continue
                else:
                    continue  # approved and next, waiting for the queue, or being written
            if filing['step'] == 'move':
                with connect(self.database) as db:
                    move = book_move.load(db, filing['move_id']) if filing.get('move_id') else None
                if move is None:
                    self._update(filing['filing_id'], step='', move_id=None)
                elif move['state'] in ('complete', 'partial'):
                    final = (move.get('final') or {}).get('final_path') or move['target_path']
                    # 'partial': the book is at its new place and the old file could not be removed; the move line says so.
                    self._finish(filing, final, 'The old file was kept' if move['state'] == 'partial' else None)
                elif move['state'] == 'failed':
                    reason = move.get('detail').get('reason') if isinstance(move.get('detail'), dict) else ''
                    self._fail(filing, move.get('cause') or 'failed', reason or move.get('cause') or '')
                elif move['state'] == 'cancelled':
                    self._update(filing['filing_id'], step='', move_id=None)  # it never ran: queued again by the rules

    def _route(self, item):
        return route(item, self.merge.__dict__.get('name_write') is not None)

    def _dispatch(self, item, filing=None):
        """Put one planned book in hand: its series write approved (series_backfill.approve, exactly as an approval of the
        list did, with the names the list files it under: one rewrite), its names approved for a write of their own
        (name_write.approve, 0.31.0 R27), or its move queued as the app's own. True when it is in hand."""
        merge = self.merge
        job = item['job_id']
        created = filing is None
        try:
            if created:
                filing = self._begin(item)
            kind = self._route(item)
            if kind == 'write':
                extra = {'names': item['names'], 'reasons': item.get('reasons')} if item.get('names') else {}
                merge.series_backfill.approve(job, item['series'], item['to'], by=ORIGIN, **extra)
                self._update(filing['filing_id'], step='write', to_path=item['to'])
            elif kind == 'names':
                merge.name_write.approve(job, item['names'], item['to'], by=ORIGIN, reasons=item.get('reasons'))
                self._update(filing['filing_id'], step='names', to_path=item['to'])
            else:
                answer = merge._sorting_move(job, item['to'], origin=ORIGIN)
                move = answer.get('move') if isinstance(answer.get('move'), dict) else {}
                if not move.get('move_id'):
                    raise ValueError('The move was not queued (%s)' % (answer.get('state') or 'no answer'))
                try:
                    self._update(filing['filing_id'], step='move', move_id=move['move_id'], to_path=item['to'])
                except sqlite3.Error:
                    merge.cancel_move(move['move_id'])  # never a move of the app's own that the record does not hold
                    raise
            self._refusals.pop(job, None)
            return True
        except Exception as error:
            text = str(error) or type(error).__name__
            if any(text.startswith(mark) for mark in PASSING):
                if filing is not None and created:
                    self._drop(filing)
                return False
            count = self._refusals[job] = self._refusals.get(job, 0) + 1
            if filing is not None:
                if count >= REFUSALS:
                    self._fail(filing, 'refused', str(error) or type(error).__name__)
                    self._refusals.pop(job, None)
                elif created:
                    self._drop(filing)
            return False

    # ------------------------------------------------------------------ the pass
    def _look_ups_open(self):
        """Job ids of the finished books whose series or detail look-up has not ended (they wait for it: a book moves once)."""
        found = set()
        for name in ('series_backfill', 'gap_fill'):
            worker = self.merge.__dict__.get(name)
            if worker is not None and callable(getattr(worker, 'unsettled', None)):
                found |= set(worker.unsettled())
        return found

    def _held_back(self, job_id):
        """'' when nothing else still works on the book's files; 'hold' while one of its cleanups is on hold (it waits for
        Sergei), 'later' while one has still to run."""
        import series_backfill
        backfill = self.merge.__dict__.get('series_backfill')
        if backfill is None or not callable(getattr(backfill, 'settled', None)):
            return ''
        try:
            backfill.settled(job_id)
        except series_backfill.Blocked:
            return 'hold'
        except series_backfill.Later:
            return 'later'
        return ''

    def _order_authors(self):
        """B8, once per change of the detail look-up's records: author names put in order on the evidence the catalog holds.
        Never fails a pass."""
        try:
            with connect(self.database) as db:
                tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('gap_fill','author_rules')")}
                seen = (tuple(db.execute("SELECT count(*),max(updated) FROM gap_fill WHERE state='found'").fetchone()) if 'gap_fill' in tables else None,
                        tuple(db.execute('SELECT count(*),max(saved_utc) FROM author_rules').fetchone()) if 'author_rules' in tables else None)
            if seen == self._orders_read:
                return
            if order_authors(self.database):
                seen = None  # rules were written: read once more at the next pass (it then finds nothing to write)
            self._orders_read = seen
        except Exception as error:
            self.error = (str(error) or type(error).__name__)[:300]

    def tick(self, dispatch=True):
        """One pass: close what ended, read the list, put up to FEED books in hand, and keep the numbers for the page.
        Returns summary()'s value, or None when the engine is closing."""
        merge = self.merge
        hold = merge.__dict__.get('_update_hold')
        if self.stop.is_set() or merge.draining or merge.__dict__.get('_closing') or hold is not None and hold.is_set():
            return None
        now = self.clock()
        # The library drive does not answer (asleep, disconnected): every file would read as "not where the catalog says".
        # Nothing is planned on a drive that is away; the numbers of the last pass stand, and the page has its own line for
        # a drive that does not answer (R14).
        root = getattr(merge.inventory, 'output_root', None)
        if root and not self._answers(root):
            return self._away()
        if dispatch:
            self._order_authors()
        self.reconcile()
        answer = merge.sorting_moves()
        if root and not self._answers(root):
            return self._away()  # it went away while the list was read: that list is not to be trusted
        output_root = answer.get('output_root') or ''
        waits = self._look_ups_open()
        opened = self._open()
        failed = self._failed()
        paused = bool(merge.filing_paused()) if callable(getattr(merge, 'filing_paused', None)) else False
        ready, could, counts = [], [], {'waiting_for_lookup': 0, 'on_hold': 0, 'settling': 0}
        listed = set()
        for item in answer['items']:
            job = item['job_id']
            listed.add(job)
            if job in opened and opened[job]['step']:
                continue  # in hand: being written, or its move queued or running
            if job in waits and job not in opened:
                counts['waiting_for_lookup'] += 1
                continue
            held = self._held_back(job)
            if held:
                counts['on_hold' if held == 'hold' else 'settling'] += 1
                continue
            tries = failed.get((job, sorting_moves.key(item['to'])))
            if tries and job not in opened and (tries[0] >= TRIES or now - tries[1] < SPACING):
                could.append(self._could(item, DID_NOT_FINISH, output_root, tries=tries[0], cause=tries[2]))
                continue
            ready.append(item)
        for item in answer['refused']:
            if item.get('refused_key') in sorting_moves.LASTING_KEYS and item['job_id'] not in waits and not (item['job_id'] in opened and opened[item['job_id']]['step']):
                could.append(self._could(item, item['refused_key'], output_root))
        # An entry in hand with nothing queued whose book the list no longer moves (he chose its folder meanwhile, or the
        # list now refuses it): closed. Its series was written and the file renamed in its own folder: that is the change.
        for job, filing in opened.items():
            if not filing['step'] and job not in listed:
                if filing.get('placed_path'):
                    self._finish(filing, filing['placed_path'])
                else:
                    self._drop(filing)
        # A move that waits for a restart (its retries ran out: the drive dropped under it) is in hand, and holds no place:
        # the other books go on.
        running = getattr(merge, '_move_running', None)
        stalled = {job for job, filing in opened.items() if filing['step'] == 'move' and callable(running) and self._stalled(filing, running)}
        in_hand = sum(1 for job, filing in opened.items() if filing['step'] and job not in stalled)
        if dispatch and not paused:
            for item in ready:
                if in_hand >= FEED or self.stop.is_set():
                    break
                if self._dispatch(item, opened.get(item['job_id'])):
                    in_hand += 1
        value = self._count(answer, ready, could, counts, paused, now)
        with self.lock:
            self._value = value
            self._could_not = sorted(could, key=lambda entry: (str(entry['from_shown']).split('\\')[0].casefold(), str(entry['title']).casefold(), entry['job_id']))
        return dict(value)

    @staticmethod
    def _answers(root):
        import os
        try:
            return os.path.isdir(root)
        except OSError:
            return False

    def _away(self):
        with self.lock:
            if self._value is not None:
                self._value = dict(self._value, drive_away=True)
            return dict(self._value) if self._value is not None else None

    def _stalled(self, filing, running):
        import book_move
        try:
            with connect(self.database) as db:
                move = book_move.load(db, filing['move_id']) if filing.get('move_id') else None
            return bool(move and move['state'] in book_move.ACTIVE and not running(move['move_id']))
        except Exception:
            return False

    def _could(self, item, name, output_root, tries=None, cause=None):
        filed = item.get('filed') or {}
        value = {'job_id': item['job_id'], 'book_id': item.get('book_id'), 'title': str(filed.get('title') or item.get('title') or ''),
                 'author': str(filed.get('author') or item.get('author') or ''), 'from': item.get('from') or '', 'to': item.get('to') or None,
                 'from_shown': item.get('from_shown') if item.get('from_shown') is not None else sorting_moves._shown(item.get('from'), output_root),
                 'to_shown': item.get('to_shown'), 'key': name, 'kinds': kinds_of(item), 'reasons': item.get('reasons') or []}
        if tries is not None:
            # 'cause' (0.31.0 R27): the last try's own key (sorting_moves.NOT_MOVED_KEYS, a move's cause, 'refused', or
            # 'other'), e.g. 'tags_not_written' when the new names did not read back from the rewritten file.
            value.update(tries=tries, tries_limit=TRIES, retries=tries < TRIES, cause=cause)
        return value

    def _count(self, answer, ready, could, counts, paused, now):
        """The numbers for the page, read after this pass's dispatch (summary())."""
        import book_move
        import series_backfill
        opened = self._open()
        backfill = self.merge.__dict__.get('series_backfill')
        names = self.merge.__dict__.get('name_write')
        groups = {'writes_waiting': [], 'writes_running': [], 'renames_waiting': [], 'renames_running': [], 'moves_waiting': [], 'moves_running': []}
        by_job = {item['job_id']: item for item in answer['items']}
        for job, filing in opened.items():
            if filing['step'] == 'write':
                entry = backfill.entry(job) if backfill is not None else None
                groups['writes_running' if entry and entry['state'] in series_backfill.ACTIVE else 'writes_waiting'].append(self._book(filing, by_job.get(job)))
            elif filing['step'] == 'names':
                entry = names.entry(job) if names is not None else None
                groups['renames_running' if entry and entry['state'] in series_backfill.ACTIVE else 'renames_waiting'].append(self._book(filing, by_job.get(job)))
            elif filing['step'] == 'move':
                with connect(self.database) as db:
                    move = book_move.load(db, filing['move_id'])
                groups['moves_running' if move and move['state'] in book_move.ACTIVE else 'moves_waiting'].append(self._book(filing, by_job.get(job)))
        for item in ready:
            if item['job_id'] in opened and opened[item['job_id']]['step']:
                continue
            group = {'write': 'writes_waiting', 'names': 'renames_waiting'}.get(self._route(item), 'moves_waiting')
            groups[group].append({'job_id': item['job_id'], 'book_id': item.get('book_id'), 'title': item.get('title') or '', 'move_id': None})
        with connect(self.database) as db:
            total, last = totals(db)
        return {'known': True, 'at': now, 'paused': paused, 'drive_away': False, 'left': sum(len(group) for group in groups.values()),
                'writes_waiting': len(groups['writes_waiting']), 'writes_running': len(groups['writes_running']),
                'moves_waiting': len(groups['moves_waiting']), 'moves_running': len(groups['moves_running']),
                # 0.31.0 R27: an English title or an author's name written into the file of a book with no series to write
                # (name_write) is a job of its own: its row and items (Judy 3.3). One written with a series is the series write's.
                'renames_waiting': len(groups['renames_waiting']), 'renames_running': len(groups['renames_running']),
                'next_write': (groups['writes_waiting'] or [None])[0], 'next_move': (groups['moves_waiting'] or [None])[0],
                'next_rename': (groups['renames_waiting'] or [None])[0],
                'could_not': len(could), 'record': {'count': total, 'last_at': last},
                'waiting_for_lookup': counts['waiting_for_lookup'], 'on_hold': counts['on_hold'], 'settling': counts['settling'],
                'tries': {'limit': TRIES, 'spacing_seconds': SPACING}, 'feed': FEED}

    @staticmethod
    def _book(filing, item):
        return {'job_id': filing['job_id'], 'book_id': filing.get('candidate_id') or (item or {}).get('book_id'), 'title': (item or {}).get('title') or filing.get('title') or '',
                'move_id': filing.get('move_id')}

    # ------------------------------------------------------------------ for the page
    def summary(self):
        """/api/state work['filing'] (background_work), kept from the last pass; never computed at a poll.
          known           False until the first pass of this run has read the list (the state is then 'unknown', never 'all done')
          left            finished audiobooks the rules are renaming or moving now or are about to: books, each once (a book
                          with a series write and then a move counts once until both are done). The notice's number (3.3a)
          writes_waiting, writes_running   books whose series is still to be written into the file / is being written
          moves_waiting, moves_running     books whose one move (new name and folder) waits / runs
          renames_waiting, renames_running (0.31.0 R27) books whose new title or author credit is still to be written into
                          the file / is being written, with no series to write (name_write); a book whose names are written
                          with its series counts as a series write
          next_write, next_move, next_rename   the first waiting book of each group: {'job_id', 'book_id', 'title', 'move_id'}
                          or None
          could_not       finished audiobooks with a certain new name or folder that could not be given it, for a lasting
                          reason (the quiet line's number, 3.2; the list is could_not())
          record          {'count', 'last_at'}: the record's summary (3.4)
          waiting_for_lookup, on_hold, settling   books with a listed change that wait for their look-up to end, for a cleanup
                          on hold, or for a cleanup still to run. They are in no number above: nothing happens to them yet
          paused          a Pause of the audiobook jobs holds the pass
          drive_away      the output folder did not answer at the last pass: nothing was planned, the numbers are the last known"""
        with self.lock:
            value = self._value
        if value is not None:
            return dict(value)
        try:
            with connect(self.database) as db:
                total, last = totals(db)
        except sqlite3.Error:
            total, last = 0, None
        started = bool(self.thread and self.thread.is_alive())
        return {'known': not started, 'at': None, 'paused': False, 'drive_away': False, 'left': None if started else 0, 'writes_waiting': 0, 'writes_running': 0,
                'moves_waiting': 0, 'moves_running': 0, 'renames_waiting': 0, 'renames_running': 0, 'next_write': None, 'next_move': None, 'next_rename': None,
                'could_not': None if started else 0,
                'record': {'count': total, 'last_at': last}, 'waiting_for_lookup': 0, 'on_hold': 0, 'settling': 0,
                'tries': {'limit': TRIES, 'spacing_seconds': SPACING}, 'feed': FEED}

    def could_not(self):
        """The books summary()['could_not'] counts, by author folder and title (Judy 3.4a): [{'job_id', 'book_id', 'title',
        'author', 'from', 'to', 'from_shown', 'to_shown', 'key' (one of COULD_NOT_KEYS), 'kinds', 'reasons'}]; a book whose
        change started and did not finish also carries 'tries', 'tries_limit', 'retries' (it is tried again by itself) and
        'cause' (the last try's key: why it did not finish)."""
        with self.lock:
            return {'count': len(self._could_not), 'known': self._value is not None, 'keys': list(COULD_NOT_KEYS), 'entries': [dict(entry) for entry in self._could_not]}

    def record(self, search='', limit=RECORD_LIMIT):
        with connect(self.database) as db:
            return record(db, getattr(self.merge.inventory, 'output_root', None), search, limit)
