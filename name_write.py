"""0.31.0 ruling R27 (Sergei 2026-11-23): when the rules give a finished audiobook an English title or put its author's
name in order, the new name is written inside the file's tags and into the app's list, not only into the file's name and
folder (milestone B's F10).

What changes a file is not new. It is the series write of 0.16.12 (series_backfill), on other tags:

  1. the new tags in a new file next to the published one (quicktime_chapters.retag): only the title, album, sort-title,
     artist and album-artist items change; every other atom, the media included, is copied byte for byte;
  2. the same proofs (media and sample tables byte-identical, the compressed audio and its decoder configuration the
     same, chapters, cover streams and every other tag read back as they were, the new tags read back as a newly converted
     book under those names would carry them);
  3. a no-replace rename to the file name the rules give, in the book's own folder;
  4. one catalog transaction: the job's manifest (title, author) and output, its verified identity, the owned output,
     the stored review the list shows, the facts the details panel reads, and this ledger's state;
  5. the old file removed, only after the new one is proven, renamed and recorded;

then, when the rules file the book in another folder, the app's usual verified move (book_move) takes it there.

Two ways in, both only through the rules' pass (rule_filing), which reads the one list (sorting_moves.plan: every refusal
of that list still decides):

  - a book that also needs its series written gets both in ONE rewrite: the series write carries the names
    (SeriesBackfill.approve(names=...)); tags(), wanted() and catalog_names() below are what it adds;
  - a book with no series to write runs through NameWrite, a second kind of entry beside the series look-up's ledger: its
    own table (name_writes), its own approval binding, its own pass and recovery. The steps after the write (rename,
    catalog, removal, every restart point) are SeriesBackfill's own code, inherited unchanged.

Nothing here decides a name. The names come from the list (sorting_moves.canonical: the one title rule, the author rules);
a title or author Sergei typed never reaches it (the list leaves them), a doubtful or missing English title is no name
(R3, R18), and a folder he chose is his (R26: the list refuses that book).

Not written (said in the Brief): a book the app has already moved once keeps its later renames in the file's name and
folder only (its location is a chain on top of the receipt, book_move; a rewrite there would break the chain), and a
series' new name is still only the folder's. An author's folder name alone (the credit in the tags unchanged) is no write
either: it is the move's.

The publication record. A rewrite changes the book's receipt (its path, bytes and validation). The series write keeps the
original publication intent and is explained by its own ledger row (publication_locations' series lineage). A write of
names instead makes the new receipt the book's publication intent, in the same transaction, and keeps the one it replaced
in the journal ('publication_intent_before_names', the first one only). So the book resolves as an ordinary publication
for every reader of the catalog, 0.30.1 included (a rollback reads it as published at its new name and path), and no
reader has to learn the name write's ledger (journal_named()).

THE SWITCH. WRITE_NAMES = 'on': the names are written as above. 'off': the 0.31.0 milestone B behaviour, exactly: an
English title or an author's name changes the file's name and folder through the move, and no file is rewritten for it.
One setting, read where the list is made (changed(), needed())."""
import copy
import json
import os
import sqlite3
import threading
import time
from pathlib import Path

import series_backfill
from native_io import AncestorUnavailable, BoundaryError, DirectoryBoundary, VerifiedFile, ordinary
from scanner import connect
from series_backfill import ACTIVE, Blocked, Held, Later, SeriesBackfill, encoded, published_root

WRITE_NAMES = 'on'
TABLE = ('CREATE TABLE IF NOT EXISTS name_writes(job_id TEXT PRIMARY KEY,state TEXT NOT NULL,reason TEXT NOT NULL,'
         'record TEXT NOT NULL,updated TEXT NOT NULL)')
FIELDS = ('title', 'author', 'canonical_author')
TEMP_PREFIX = '.books-arranger-names-'
TITLE, ARTIST, ALBUM_ARTIST, SORT_NAME = b'\xa9nam', b'\xa9ART', b'aART', b'sonm'
BY = 'rules'  # the only approver there is
START_DELAY = 125  # after startup: the published check, the queue and the series look-up's own start come first
PASS_WAIT = 600
FINAL = ('done', 'held', 'skipped')
WAITING = ('pending', 'deferred', 'blocked')
# Reasons, as sentences the could-not list's keys are read from (sorting_moves.NOT_MOVED_KEYS).
NOT_BY_RULES = 'A write of names is approved by the rules only; nothing was changed'
BOOK_CHANGED = 'The book changed since its new names were approved; nothing was changed'
PLACE_CHANGED = 'The planned place changed since its new names were approved. Nothing was changed'
SAME_NAME = 'The new names do not change the file name; left as it is'
BEING_WRITTEN = 'This audiobook is being renamed now'
SERIES_IN_HAND = 'This audiobook is being renamed now (its series is being written)'
DRIVE_AWAY = 'The library drive is not answering'
RETAINED = 'Kept as published while the data folder move is unfinished; left as it is'
NEWER = 'Has a newer version; left as it is'
# The hold of a write of names that failed before its rename (the series write's APPLY_HOLD; 0.31.3 reads it to find a
# leftover temporary file whose removal was refused, SeriesBackfill._clear_leftover_temporaries).
NAMES_FAILED = 'The names could not be written; the audiobook is unchanged: '
# Judy's late-write clean-up spec, section 6: what a write of names whose leftover temporary file was handled says (the
# key tags_not_written still finds "The names could not be written"). With the file kept: TEMP_LEFT + its path.
NAMES_UNCHANGED = 'The names could not be written; the audiobook is unchanged.'
FRESH_NAMES_FAILED = 'Couldn’t update the names. The audiobook is unchanged.'
TEMP_LEFT = ' A temporary file is still there: '
# The marks of the leftover handling and of Sergei's ruling 4 (one more try) that a new write of the same book keeps.
RETRY_KEYS = ('temp_retry', 'temp_removed', 'temp_kept', 'names_retry')


def have(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='name_writes'").fetchone() is not None


def changed(metadata, review):
    """{field: new value} for the names (FIELDS) the rules file a finished book under that its manifest does not hold.
    Empty while the switch is off."""
    if WRITE_NAMES != 'on':
        return {}
    found = {}
    for field in FIELDS:
        new, old = str((review or {}).get(field) or ''), str((metadata or {}).get(field) or '')
        if new.strip() and new != old:
            found[field] = new
    return found


def needed(metadata, review):
    """changed(), only when it changes the file: the title, or the author credit the tags carry (canonical_author). An
    author's folder name alone ('author') changes the path only and is the move's. {} when nothing is to be written."""
    found = changed(metadata, review)
    return found if 'title' in found or 'canonical_author' in found else {}


def journal_named(text, receipt):
    """The job's journal (stored text) with the rewritten receipt as its publication intent (module text, the publication
    record); the intent it replaces is kept once as 'publication_intent_before_names'. Returns the new stored text."""
    journal = json.loads(text) if isinstance(text, str) and text else {}
    if not isinstance(journal, dict):
        raise Held('The job journal cannot be read; nothing was changed')
    if 'publication_intent' not in journal:
        return text  # no intent to follow (never one invented)
    if 'publication_intent_before_names' not in journal:
        journal['publication_intent_before_names'] = journal['publication_intent']
    journal['publication_intent'] = copy.deepcopy(receipt)
    return json.dumps(journal, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def renamed(metadata, names):
    """The review with the new names."""
    return dict(metadata or {}, **{field: str(names[field]) for field in FIELDS if field in (names or {})})


def _album(review):
    return series_backfill.album(review) if review.get('series') else review['title']


def _sort_title(review):
    from metadata import audiobook_sort_title
    value = audiobook_sort_title(review)
    return value if value != review['title'] else None


def tags(was, now):
    """The Apple metadata items a book converted under `now` carries where `was` reads otherwise (audio_pipeline's
    approved_tags and its sort title): {item: bytes}. An empty value takes the item out (retag keeps every item it is not
    given and appends the ones it is: an empty one appends nothing), for a sort title the new title no longer has."""
    from quicktime_chapters import text_tag
    found = {}
    if now.get('title') != was.get('title'):
        found[TITLE] = text_tag(TITLE, now['title'])
        found[series_backfill.ALBUM] = text_tag(series_backfill.ALBUM, _album(now))
        if now.get('series'):
            found[series_backfill.SORT_ALBUM] = text_tag(series_backfill.SORT_ALBUM, _album(now))
        sort = _sort_title(now)
        found[SORT_NAME] = text_tag(SORT_NAME, sort) if sort else b''
    if now.get('canonical_author') != was.get('canonical_author'):
        found[ARTIST] = text_tag(ARTIST, now['canonical_author'])
        found[ALBUM_ARTIST] = text_tag(ALBUM_ARTIST, now['canonical_author'])
    return found


def wanted(was, now):
    """What must read back after the write, by ffprobe's tag names: {name: value}; None for an item that must be gone."""
    found = {}
    if now.get('title') != was.get('title'):
        found.update(title=now['title'], album=_album(now), sort_name=_sort_title(now))
        if now.get('series'):
            found['sort_album'] = _album(now)
    if now.get('canonical_author') != was.get('canonical_author'):
        found.update(artist=now['canonical_author'], album_artist=now['canonical_author'])
    return found


def check(before, after, expected):
    """The new file carries the new names as a converted book would; every other tag, the chapters and the streams (the
    cover among them) read back as they were."""
    def read(raw):
        return {k.lower(): str(v) for k, v in raw.get('format', {}).get('tags', {}).items()}
    old, new = read(before), read(after)
    for key, value in expected.items():
        if new.get(key) != value:
            raise Held('The new names did not read back: ' + key)
    if {k: v for k, v in old.items() if k not in expected} != {k: v for k, v in new.items() if k not in expected}:
        raise Held('Other metadata changed while retagging; left as it is')
    if before.get('chapters') != after.get('chapters'):
        raise Held('Chapters changed while retagging; left as it is')
    streams = lambda raw: [{k: s.get(k) for k in ('codec_type', 'codec_name', 'disposition', 'duration_ts')} for s in raw.get('streams', [])]
    if streams(before) != streams(after):
        raise Held('Streams changed while retagging; left as it is')


def _source(reasons):
    """(provider, url) of the title's reason (sorting_moves.REASON_KINDS), ('', '') when there is none."""
    for reason in reasons or []:
        if isinstance(reason, dict) and reason.get('kind') == 'title':
            return str(reason.get('provider') or ''), str(reason.get('source_url') or '')
    return '', ''


def facts_named(facts, was, now, reasons=None):
    """The book's facts under its new names: the author credit follows the author (the stored review must still read as
    its facts say, standing_metadata.validate_policy), and a title a source gave says so (the details panel's English
    title fact, the row's Title line, merge_service.title_origin). Returns a new dict."""
    facts = dict(facts)
    if now.get('canonical_author') != was.get('canonical_author') and facts.get('authors') == [was.get('canonical_author')]:
        facts['authors'] = [now['canonical_author']]
    if now.get('title') != was.get('title'):
        provider, url = _source(reasons)
        facts['title_source'] = {'rule': 'english', 'provider': provider, 'url': url, 'split': False}
        facts['original_title_lookup'] = {'state': 'found', 'title': now['title'], 'provider': provider, 'url': url}
        if facts.get('title_basis') == 'source_russian':
            facts['title_basis'] = 'published_english'  # it is no longer the Russian source's own title
    return facts


def fits(facts, now):
    """'' when the new names read as the book's facts say, else why not (a review that its own facts contradict would stop
    the book's row from being shown: standing_metadata.validate_policy)."""
    if not isinstance(facts, dict) or not isinstance(facts.get('authors'), list):
        return ''
    credit = '; '.join(str(value) for value in facts['authors'])
    if now.get('canonical_author') != credit or facts.get('author_folder_basis') == 'verified_full_name' and now.get('author') != credit:
        return "The new author name does not fit the book's recorded author credit; left as it is"
    return ''


def catalog_names(manifest, validation, names, reasons=None):
    """In place, for one catalog transaction: the manifest's metadata and facts under the new names, and the receipt's
    read-back tags as a book converted under them records them. Returns (was, now): the reviews before and after."""
    was = dict(manifest['metadata'])
    now = renamed(was, names)
    manifest['metadata'] = now
    if isinstance(manifest.get('metadata_facts'), dict):
        manifest['metadata_facts'] = facts_named(manifest['metadata_facts'], was, now, reasons)
    held = dict(validation.get('tags') or {})
    for key, value in wanted(was, now).items():
        if value is None:
            held.pop(key, None)
        else:
            held[key] = value
    validation['tags'] = held
    return was, now


def catalog_list(db, manifest, was, now, reasons=None):
    """In the same transaction: the stored review the list shows, and the candidate's facts and evidence (only while the
    candidate is the revision the book was made from, as the series write records its own)."""
    names = {field: now[field] for field in FIELDS if now.get(field) != was.get(field)}
    group = db.execute('SELECT review FROM book_groups WHERE id=?', (manifest['candidate_id'],)).fetchone()
    if group and group[0]:
        stored = dict(json.loads(group[0]), **names)
        db.execute('UPDATE book_groups SET review=? WHERE id=?', (json.dumps(stored, ensure_ascii=False), manifest['candidate_id']))
    context = db.execute('SELECT revision,data FROM candidate_context WHERE id=?', (manifest['candidate_id'],)).fetchone()
    if context and context[0] == manifest.get('candidate_revision'):
        data = json.loads(context[1])
        if isinstance(data.get('metadata_facts'), dict):
            data['metadata_facts'] = facts_named(data['metadata_facts'], was, now, reasons)
        provider, url = _source(reasons)
        why = "Written into the finished audiobook's tags by the app's rules (Sergei 2026-11-23, ruling R27)."
        for field, value in names.items():
            if field == 'author':
                continue  # the folder's name; the credit is canonical_author
            data.setdefault('metadata_evidence', []).append({
                'field': 'title' if field == 'title' else 'authors', 'cited_value': value, 'source_url': url if field == 'title' else '',
                'retrieved_utc': series_backfill._stamp(), 'reviewer_actor': 'assistant', 'reviewer_identity': 'Books Arranger name write', 'basis': why})
        db.execute('UPDATE candidate_context SET data=? WHERE id=? AND revision=?', (json.dumps(data, ensure_ascii=False), manifest['candidate_id'], context[0]))


class NameWrite(SeriesBackfill):
    """The second kind of entry (module text): a finished book's new title and author written into its file, with no series
    to write. Inherited unchanged from the series write: the proofs of the new file (_write), the rename, the catalog
    hand-over and the old file's removal with every restart point (resume, _resume_protected, _boundary, _protected,
    _proven), the move that follows (_follow_up), the waits (_idle, settled, unsafe, _defer) and the owned temporary file.
    Its own: the ledger (name_writes), the approval, the pass, what is written (_tags, _read_back) and what is recorded
    (catalog)."""
    LEDGER = 'name_writes'
    TEMP_PREFIX = TEMP_PREFIX
    APPLY_HOLD = NAMES_FAILED

    def __init__(self, merge, stage=None, clock=time.time):
        self.merge = merge
        self.database = merge.inventory.database
        self.research = None  # nothing is ever looked up here
        self.clock = clock
        self.stage = Path(stage) if stage else Path(merge.stage_root).parent / 'name-write'
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.thread = None
        self.progress = None
        with connect(self.database) as db:
            db.execute(TABLE)

    # ------------------------------------------------------------------ thread
    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop.clear()
        self.thread = threading.Thread(target=self._run, name='books-name-write', daemon=True)  # close() stops it; a hard exit is what the resumable states are for
        self.thread.start()

    def _run(self):
        if self.wake.wait(START_DELAY):
            self.wake.clear()
        while not self.stop.is_set():
            try:
                self.run_pass()
            except InterruptedError:
                pass
            except Exception:
                pass  # every book records its own reason
            finally:
                self.progress = None
            self.wake.wait(self._next_wait())
            self.wake.clear()

    def status(self):
        """The running row: {'title', 'step': 'updating'} while a book's names are being written, else None."""
        value = self.progress
        return dict(value) if value else None

    # ------------------------------------------------------------------ ledger
    def entry(self, job_id):
        rows = self._rows('SELECT * FROM name_writes WHERE job_id=?', (job_id,))
        if not rows:
            return None
        row = rows[0]
        row['record'] = json.loads(row['record'])
        return row

    def _set(self, job_id, state, reason='', record=None):
        with connect(self.database) as db:
            prior = db.execute('SELECT record,state FROM name_writes WHERE job_id=?', (job_id,)).fetchone()
            value = record if record is not None else (json.loads(prior[0]) if prior else {})
            # A hold before the catalog names the rewritten file ends that fresh names try. This also
            # covers rename collisions and interrupted writes finished through the inherited resume().
            fresh_failure = (state == 'held' and prior and prior[1] not in ('held', 'cataloged', 'done')
                             and value.get('names_retry') == series_backfill.REMOVAL_RETRY
                             and reason != series_backfill.FOLDER_UNREACHABLE)
            if fresh_failure:
                cause = reason.removeprefix(NAMES_FAILED)
                if cause == series_backfill.FOLDER_CHANGED:
                    cause = 'The book’s folder changed since the app checked it.'
                reason = FRESH_NAMES_FAILED + (' ' + cause if cause else '')
            db.execute('INSERT OR REPLACE INTO name_writes VALUES(?,?,?,?,?)',
                       (job_id, state, reason, json.dumps(value, ensure_ascii=False), series_backfill._stamp()))
        if fresh_failure:
            title = (value.get('review') or {}).get('title') or (value.get('approved_names') or {}).get('title') or Path(value.get('old_path') or job_id).stem
            series_backfill._log('Fresh names try failed: ' + str(title) + ' (' + job_id + '): ' + reason)
        self._changed()
        notify = getattr(self.merge.__dict__.get('rule_filing'), 'notify', None)
        if state in FINAL and callable(notify):
            notify()  # the rules' pass closes this book's entry and puts the next one in hand

    def fresh_failures(self):
        """Current failed fresh writes, for an existing entry in the could-not list."""
        return {row['job_id']: row['reason'] for row in self._rows(
            "SELECT job_id,reason FROM name_writes WHERE state='held' AND reason LIKE ? AND json_valid(record) "
            "AND json_extract(record,'$.names_retry')=?", (FRESH_NAMES_FAILED + '%', series_backfill.REMOVAL_RETRY))}

    def summary(self):
        """Plain counts for the page (background_work), a catalog read: {'waiting': approved writes that wait for a job, a
        cleanup or a scan; 'writes': their job ids; 'writing': being written or renamed now; 'done', 'held'}."""
        counts = dict.fromkeys(('waiting', 'writing', 'done', 'held'), 0)
        writes = []
        for row in self._rows('SELECT job_id,state FROM name_writes'):
            if row['state'] in WAITING:
                counts['waiting'] += 1
                writes.append(row['job_id'])
            elif row['state'] in ACTIVE:
                counts['writing'] += 1
            elif row['state'] == 'done':
                counts['done'] += 1
            else:
                counts['held'] += 1
        return dict(counts, writes=writes[:100])

    def unsettled(self):
        return set()  # no look-up: nothing waits for this ledger

    def candidates(self):
        raise NotImplementedError('A write of names has no look-up')

    def lookup(self, manifest, memory=None):
        raise NotImplementedError('A write of names has no look-up')

    # ------------------------------------------------------------------ the approval
    def approve(self, job_id, names, target, by=None, reasons=None):
        """The rules filed this finished book under new names (the list's item: sorting_moves 'names') and at `target`.
        Bound to the book's manifest as it is now and to that exact path; written by the next pass. by: 'rules', always:
        nothing else may open this door (ValueError). reasons: the list's reasons for the names, kept with the record."""
        if by != BY:
            raise ValueError(NOT_BY_RULES)
        names = {field: str(names[field]) for field in FIELDS if field in (names or {}) and str(names[field]).strip()}
        rows = self._rows('SELECT manifest FROM audio_jobs WHERE job_id=?', (job_id,))
        if not rows or not names:
            raise ValueError('This book has no new name to write; nothing was changed.')
        entry = self.entry(job_id)
        if entry and entry['state'] in ACTIVE:
            raise ValueError(BEING_WRITTEN)
        if self._series_in_hand(job_id):
            raise ValueError(SERIES_IN_HAND)
        record = {'kind': 'names', 'move_approved': True, 'approved_names': names, 'approved_target': str(target),
                  'approved_binding': encoded(json.loads(rows[0]['manifest']))[1], 'approved_utc': series_backfill._stamp(), 'approved_by': BY,
                  'reasons': [dict(reason) for reason in reasons or [] if isinstance(reason, dict) and reason.get('kind') in ('title', 'author')]}
        self._set(job_id, 'pending', '', record)
        self.wake.set()

    def _other_writer(self, job_id):
        return self._series_in_hand(job_id)

    def _waits_for_other(self, job_id):
        """Senua's 0.31.3 review, m2: a begun write of names waits while the same book's series write is in its last step
        (the series write goes first and never waits; SeriesBackfill._waits_for_other)."""
        other = self._ledger_entry('series_backfill', job_id)
        return bool(other and other['state'] in ACTIVE)

    def _retry_blocked(self, job_id):
        """m2: not sent back for the clean-up while the same book's series write is in its last step, or while a series hold
        of it is one the series retry will take first (it goes first)."""
        other = self._ledger_entry('series_backfill', job_id)
        if not other:
            return False
        return other['state'] in ACTIVE or (SeriesBackfill._removal_retained(other) and other['record'].get('removal_retry') != series_backfill.REMOVAL_RETRY)

    def _leftover_outcome(self, entry, record, temp):
        """Judy 6 with Sergei's ruling 4 (2026-11-25): its three tries were used up by the NAS bug, not by the names. Once its
        leftover temporary file is removed, the write gets one fresh try ('pending' with its approval as it was, record
        'names_retry'; the usual pass runs it with every proof of a write of names). If the file was kept, the book stays
        held with section 6's sentence and the file's path."""
        if record.get('temp_removed') and record.get('names_retry') != series_backfill.REMOVAL_RETRY:
            record['names_retry'] = series_backfill.REMOVAL_RETRY
            record.pop('next_attempt', None)
            return 'pending', ''
        if record.get('temp_kept'):
            if record['temp_kept']['reason'] in (series_backfill.TEMP_FOLDER_UNKNOWN, series_backfill.FOLDER_UNREACHABLE):
                return super()._leftover_outcome(entry, record, temp)
            return 'held', NAMES_UNCHANGED + TEMP_LEFT + str(temp)
        return 'held', NAMES_UNCHANGED

    def _series_in_hand(self, job_id):
        """The series look-up is writing this book, or has an approved write of it waiting: one writer per file."""
        with connect(self.database) as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='series_backfill'").fetchone():
                return False
            row = db.execute("SELECT state,json_extract(record,'$.move_approved') FROM series_backfill WHERE job_id=?", (job_id,)).fetchone()
        return bool(row and (row[0] in ACTIVE or row[0] == 'pending' or row[0] in ('deferred', 'blocked') and row[1]))

    # ------------------------------------------------------------------ pass
    def _pass(self):
        from storage_relocation_native import retained_job
        self._retry_retained_removals()  # 0.31.3: the holds 0.31.2 left on the NAS (series_backfill.REMOVAL_RETRY)
        self._clear_leftover_temporaries()  # 0.31.3, Sergei 2026-11-25: the temporary files 0.31.2 left there
        for row in self._rows('SELECT job_id FROM name_writes WHERE state IN (%s)' % ','.join('?' * len(ACTIVE)), ACTIVE):
            if self.stop.is_set():
                return  # Senua's 0.31.3 review, M1: Quit and "Restart to update" stop the clean-up between two books
            entry = self.entry(row['job_id'])
            if entry['record'].get('next_attempt', 0) > self.clock():
                continue
            self._finish_active(row['job_id'], entry)  # SeriesBackfill's: R35, and the clean-up's book in hand
        # A book whose names were written before a restart still gets its move to the folder the rules file it in.
        for row in self._rows("SELECT job_id FROM name_writes WHERE state='done' AND json_extract(record,'$.move_approved') "
                              "AND json_extract(record,'$.follow_up') IS NULL"):
            try:
                self._idle()
                self._follow_up(row['job_id'])
            except Later:
                break
        waiting = self._rows('SELECT job_id FROM name_writes WHERE state IN (%s) ORDER BY updated,job_id' % ','.join('?' * len(WAITING)), WAITING)
        jobs = self.merge.jobs.status()['jobs'] if waiting and getattr(self.merge, 'publications', None) is not None else None
        for row in waiting:
            if self.stop.is_set():
                return
            job_id = row['job_id']
            entry = self.entry(job_id)
            if not entry or entry['state'] not in WAITING or entry['record'].get('next_attempt', 0) > self.clock():
                continue
            if entry['state'] == 'blocked' and self._cleanup(job_id) == 'held':
                continue  # still blocked by a cleanup on hold; a cheap catalog read, never a try
            try:
                self._idle()  # a Pause, a conversion, a cleanup or a scan holds the job before anything is read (Later)
                book = self._rows("SELECT * FROM audio_jobs WHERE job_id=? AND state='completed' AND output IS NOT NULL", (job_id,))
                if not book:
                    raise Held('The audiobook is not in the catalog as a finished book; nothing was changed')
                manifest = json.loads(book[0]['manifest'])
                newest = self._rows("SELECT job_id FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id')=? ORDER BY created DESC,job_id DESC LIMIT 1",
                                    (manifest.get('candidate_id'),))
                if retained_job(self.database, job_id):
                    raise Held(RETAINED)
                if not newest or newest[0]['job_id'] != job_id:
                    raise Held(NEWER)
                reason = self.unsafe(book[0], jobs)  # a replacement, files kept at his choice, a cleanup still to run (Later, Blocked)
                if reason:
                    raise Held(reason)
                if not self._answers(published_root(manifest, json.loads(book[0]['output']))):
                    raise Later(DRIVE_AWAY, self.clock() + 60)  # no try: nothing is read from a drive that is away
                if entry['record'].get('names_retry') == series_backfill.REMOVAL_RETRY:
                    wait = self._library_wait(entry['record'])
                    if wait:
                        raise Later(wait, self.clock() + 60)
                self.progress = {'title': str(manifest['metadata'].get('title') or ''), 'step': 'updating'}  # the title the list shows until the write lands
                self.apply(job_id)
            except Blocked as blocked:
                self._set(job_id, 'blocked', str(blocked), dict(entry['record']))
            except Later as wait:
                self._defer(job_id, wait)
            except InterruptedError:
                return
            except Held as held:
                self._set(job_id, 'held', str(held), entry['record'])
            except Exception as error:
                self._set(job_id, 'held', NAMES_FAILED + (str(error) or type(error).__name__)[:300], entry['record'])
            finally:
                self.progress = None

    @staticmethod
    def _answers(root):
        try:
            return os.path.isdir(root)
        except OSError:
            return False

    # ------------------------------------------------------------------ the write
    def apply(self, job_id, found=None):
        """Steps 1-5 for one approved book (module text); any doubt leaves the published file and records why. The names
        are the approved ones and nothing else: there is no other way to say what to write."""
        from metadata import propose
        self._idle()
        entry = self.entry(job_id)
        prior = dict(entry['record']) if entry else {}
        rows = self._rows('SELECT * FROM audio_jobs WHERE job_id=?', (job_id,))
        manifest = json.loads(rows[0]['manifest'])
        output = json.loads(rows[0]['output'])
        names = {field: str(value) for field, value in (prior.get('approved_names') or {}).items() if field in FIELDS}
        was = dict(manifest['metadata'])
        review = renamed(was, names)
        facts = copy.deepcopy(manifest.get('metadata_facts'))
        old = ordinary(output['final_path'])
        root = published_root(manifest, output)
        record = {'kind': 'names', 'names': names, 'was': {field: was.get(field) for field in names}, 'reasons': prior.get('reasons') or [],
                  'old_path': str(old), 'old_sha256': output['sha256'], 'old_size': output['size']}
        record.update({key: prior[key] for key in series_backfill.APPROVAL_KEYS if key in prior})
        record.update({key: prior[key] for key in RETRY_KEYS if key in prior})  # ruling 4's one try is known as such
        try:
            if not prior.get('move_approved') or prior.get('approved_by') != BY or not names:
                raise Held(NOT_BY_RULES)
            if prior.get('approved_binding') != encoded(manifest)[1]:
                raise Held(BOOK_CHANGED)
            if not any(review.get(field) != was.get(field) for field in FIELDS):
                raise Held('The book already has these names; nothing was changed')
            import book_move
            with connect(self.database) as db:
                moved = book_move.have(db) and db.execute("SELECT 1 FROM book_moves WHERE job_id=? AND state NOT IN ('failed','cancelled') LIMIT 1", (job_id,)).fetchone()
            if moved:
                raise Held('The audiobook was moved already; its names stay in the file name and folder')
            if self._series_in_hand(job_id):
                raise Later(SERIES_IN_HAND, self.clock() + 60)
            if hasattr(self.merge, '_require_sorted'):
                try:
                    self.merge._require_sorted(old)
                except ValueError:
                    raise Held('The audiobook is not in the sorted output folder; left as it is') from None
            current = propose('', str(root), 'audiobook', {}, was, automatic_facts=copy.deepcopy(facts))
            if not current.get('path') or os.path.normcase(current['path']) != os.path.normcase(str(old)):
                raise Held("The audiobook's name does not follow the app's naming; left as it is")
            contradiction = fits(facts_named(facts, was, review, record['reasons']) if isinstance(facts, dict) else None, review)
            if contradiction:
                raise Held(contradiction)
            planned = getattr(self.merge, 'sorting_target', None)
            expected = str(planned(job_id) or '') if callable(planned) else ''
            if not expected or os.path.normcase(expected) != os.path.normcase(str(prior.get('approved_target') or '')):
                raise Held(PLACE_CHANGED)
            new = old.parent / os.path.basename(expected)
            if not ordinary(expected).is_relative_to(root) or new.suffix.lower() != '.m4b':
                raise Held('The new name is not a valid audiobook name')
            if new == old:
                raise Held(SAME_NAME)
            if os.path.normcase(os.path.dirname(expected)) != os.path.normcase(str(old.parent)):
                record['series_folder'] = os.path.dirname(expected)  # the key the inherited follow-up reads: the folder it then moves to
            temp = old.parent / (TEMP_PREFIX + job_id + '.m4b')
            record.update(new_path=str(new), temp=str(temp), review=review, root=str(root), parent_identity=output['parent_identity'])
            self._give_way(job_id, record, 'The audiobook was moved already; its names stay in the file name and folder')
            with self._boundary(record), VerifiedFile(old) as original:
                if original.facts()['size'] != output['size'] or original.sha256() != output['sha256']:
                    raise Held('The published audiobook changed since it was verified; left as it is')
                record['old_identity'] = original.facts()['identity']
                self._set(job_id, 'writing', '', record)
                self._own_temporary(job_id, temp)
                self._write(job_id, manifest, output, old, temp, review, record)
        except Held as held:
            self._discard_temp(job_id, record)
            self._set(job_id, 'held', str(held), record)
            return
        except (Later, InterruptedError):
            self._discard_temp(job_id, record)
            self._set(job_id, 'pending', '', record)
            raise
        except Exception as error:
            self._discard_temp(job_id, record)
            record.setdefault('root', str(root))
            wait = ''
            if record.get('names_retry') == series_backfill.REMOVAL_RETRY:
                if 'folder_network_errors' in prior:
                    record['folder_network_errors'] = prior['folder_network_errors']
                wait = self._network_wait(record, error)
            elif self._drive_away(record, error):
                wait = DRIVE_AWAY
            if wait:
                # Senua's 0.31.3 review, M2: the drive went away during the write. No try is used (ruling 4's one fresh try
                # included): the write waits, as it waits when the drive is away before it starts (_pass, DRIVE_AWAY).
                self._set(job_id, 'pending', '', record)
                raise Later(wait, self.clock() + 60) from None
            if isinstance(error, AncestorUnavailable):
                # Senua's re-review at 520ee66, M5: the drive answers and the book's folder is gone: N4, stored as a Held
                # reason is (the series write's step holds it the same way); nothing was written.
                self._set(job_id, 'held', series_backfill.FOLDER_CHANGED, record)
                return
            self._set(job_id, 'held', NAMES_FAILED + (str(error) or type(error).__name__), record)
            return
        finally:
            self._clear_stage(job_id)
        self.resume(job_id)

    def _tags(self, was, review, record):
        return tags(was, review)

    def _read_back(self, before, after, was, review, record):
        check(before, after, wanted(was, review))

    # ------------------------------------------------------------------ the record
    def catalog(self, job_id, record):
        """Step 4, one transaction: the book reads as verified at once, at its new path and under its new names."""
        merge = self.merge
        new = ordinary(record['new_path'])
        with connect(self.database) as db:
            row = db.execute('SELECT * FROM audio_jobs WHERE job_id=?', (job_id,)).fetchone()
            manifest = json.loads(row['manifest'])
            output = json.loads(row['output'])
            if output['final_path'] == str(new) and output['sha256'] == record['new_sha256']:
                db.execute("UPDATE name_writes SET state='cataloged',updated=? WHERE job_id=?", (series_backfill._stamp(), job_id))
                return  # recorded before a restart
            if output['final_path'] != record['old_path'] or output['sha256'] != record['old_sha256']:
                raise Held('The book changed meanwhile')
            root = published_root(manifest, output)
            with DirectoryBoundary(root, new.parent) as boundary:
                ancestry = [list(item) for item in boundary.identities]
            validation = dict(output['validation'], sha256=record['new_sha256'], size=record['new_size'])
            was, now = catalog_names(manifest, validation, record['names'], record.get('reasons'))
            manifest['destination'] = str(new)
            text, digest = encoded(manifest)
            updated = dict(output, final_path=str(new), sha256=record['new_sha256'], size=record['new_size'], parent_identity=ancestry, validation=validation)
            journal = journal_named(row['journal'], updated)
            db.execute('BEGIN IMMEDIATE')
            # A move of this book began meanwhile (Choose folder… during the write): its chain starts from the receipt as it
            # is, so the receipt is not changed under it. Both copies are kept; the catalog still names the old file. One
            # check for both writes (Senua's 0.31.0 review, M1: a queued move the Mover runs has begun).
            self._no_move_begun(db, job_id)
            count = db.execute('UPDATE audio_jobs SET manifest=?,manifest_hash=?,output=?,journal=?,updated=? WHERE job_id=? AND output=?',
                               (text, digest, json.dumps(updated), journal, series_backfill._stamp(), job_id, row['output'])).rowcount
            if count != 1:
                raise Held('The book changed meanwhile')
            identity = merge._identity_key(new, record['new_sha256'])
            stat = os.stat(new)
            db.execute('DELETE FROM verified_outputs WHERE job_id=?', (job_id,))
            db.execute('INSERT OR REPLACE INTO verified_outputs VALUES(?,?,?,?,?)',
                       (*identity, job_id, json.dumps([stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns]), series_backfill._stamp()))
            db.execute("UPDATE owned_artifacts SET path=?,sha256=?,size=? WHERE job_id=? AND kind='output'",
                       (str(new), record['new_sha256'], record['new_size'], job_id))
            catalog_list(db, manifest, was, now, record.get('reasons'))
            db.execute("UPDATE name_writes SET state='cataloged',updated=? WHERE job_id=?", (series_backfill._stamp(), job_id))
        self._verified(job_id, stat)  # 0.31.0 B1: the book stays converted (SeriesBackfill._verified)
        if hasattr(merge, 'invalidate_status'):
            merge.invalidate_status()

    # ------------------------------------------------------------------ owned temporary file
    @staticmethod
    def _dispose_temporary(temp):
        """The app's own temporary file goes through a held handle of that exact single-link file, with its folder held,
        never by a pathname delete (as the series write's)."""
        temp = ordinary(temp)
        if not temp.name.startswith(TEMP_PREFIX) or temp.suffix.lower() != '.m4b':
            raise BoundaryError('Not a name-write temporary file; kept')
        with DirectoryBoundary(temp.parent, temp.parent), VerifiedFile(temp, delete=True) as handle:
            series_backfill.remove_owned(handle)  # 0.31.3: on the NAS too (series_backfill.RECOVERY_HOLD's note)
        if series_backfill.present(temp):  # Senua M3's pattern: a network error raises; it is never read as removed
            raise BoundaryError(series_backfill.TEMP_STILL_THERE)  # N8


def placed(db):
    """{job_id: (the path the names were written at, the kinds of change that were written)}: a book whose names are in its
    file under its new name in its own folder and that still waits for, or lost, its move to the folder the rules file it
    in (sorting_moves.plan plans it from there, as it does a written series)."""
    if not have(db):
        return {}
    found = {}
    for job_id, record in db.execute("SELECT job_id,record FROM name_writes WHERE state='done'"):
        try:
            record = json.loads(record)
        except (TypeError, ValueError):
            continue
        if isinstance(record, dict) and record.get('move_approved') and record.get('new_path'):
            names = record.get('names') or {}
            found[job_id] = (record['new_path'], [kind for kind in ('title', 'author') if kind in names or kind == 'author' and 'canonical_author' in names])
    return found
