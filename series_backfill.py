"""v0.16.12 series backfill (Sergei, 2026-10-18): published audiobooks that were made without a series get one.

One background pass at a time, resumable across restarts (series_backfill table). For each finished book
without a series it asks the series sources (Goodreads first, FantLab fallback: public_research, with
their pacing and cache). When one is found and the book can be changed safely:

  1. writes the new metadata next to the published file (quicktime_chapters.retag): only the album, grouping,
     sort-album and track items change; every other atom, the media included, is copied byte for byte;
  2. proves nothing else changed: media and sample tables byte-identical (quicktime_chapters.media_unchanged),
     the compressed audio and its decoder configuration the same (the preservation proofs), chapters and
     cover the same, and the new tags as a newly converted book with that series would carry;
  3. renames it to the name the app gives a book with that series (metadata.propose), on the same volume,
     never over an existing file;
  4. records the new file in the catalog in one transaction (job output and manifest, verified identity,
     owned output, the book's review), so it reads as verified at once and nothing re-checks or purges it;
  5. removes the old file. No copy is kept (Sergei's rule); the old file goes only after the new one is
     proven, renamed and recorded.

Any doubt leaves the published file as it is and records why. File changes wait while a book converts.
"""
import copy
from contextlib import contextmanager
import critical_sections
from datetime import datetime
import hashlib
import itertools
import sqlite3
import json
import os
import re
import threading
import time
from pathlib import Path

from native_io import AncestorUnavailable, BoundaryError, DirectoryBoundary, VerifiedFile, ordinary, publish_no_replace
from scanner import connect

def published_root(manifest, output):
    """The folder a book was published under: the output's own root, else the job's output root, else (books made
    before 0.13.0 published into their library) the source root."""
    return ordinary(output.get('root') or manifest.get('output_root') or manifest['root'])


TABLE = ('CREATE TABLE IF NOT EXISTS series_backfill(job_id TEXT PRIMARY KEY,state TEXT NOT NULL,reason TEXT NOT NULL,'
         'record TEXT NOT NULL,updated TEXT NOT NULL)')
FINAL = ('none', 'done', 'skipped', 'held')
ACTIVE = ('writing', 'written', 'renamed', 'cataloged')
LOOKUP_POLICY = 'series-fallbacks-20-v1'
ALBUM, GROUPING, SORT_ALBUM, TRACK = b'\xa9alb', b'\xa9grp', b'soal', b'trkn'
PASS_WAIT = 600
START_DELAY = 120  # after startup: the published check and the queue come first
TEMP_PREFIX = '.books-arranger-series-'
# 0.30.0 item 2 (Sergei 2026-11-18): a series whose folder is another folder than the one the book was published in (every
# books-hierarchy-v2 book: Author\Series\) never passed ("The recorded series paths do not share their original parent").
# Moving an existing book in Sorted waits for Sergei's approval of the listed moves (sorting_moves): until then the book is
# held with this reason and left exactly as it is. Approved (approve()), the series is written into the file in its own
# folder as before (retag, proofs, no-replace rename, catalog), then the app's usual verified move (book_move) takes it into
# its series folder (MergeService.sorting_follow_up).
MOVE_WAITS = 'Series found. Moving it into its series folder waits for your approval.'
# THE GUARD (0.31.0, Jane for Sergei 2026-11-22): may the look-up write a series into a finished audiobook and rename it
# WITHOUT his approval? It could, whenever the name with the series stays in the book's own folder (books published
# under the flat naming: 296 of the 798 finished books without a series on a copy of the live catalog, 282 of them still
# to look up; all 87 writes before 0.31.0 were of this kind). Making the look-up end (step 4a) lets it reach those books
# again, and the series it would write is in whatever language the source gives, before ruling R1 is built.
#   'hold'   (the default, until Sergei rules) nothing is written or renamed without approval. The look-up still runs and
#            ends; a series found is kept and the book is held with WRITE_WAITS, counted with the moves that wait for
#            him (summary()['moves_waiting'], and on its own as 'writes_held') and listed for approval (sorting_moves).
#   'allow'  the 0.16.12 behaviour: such a book is written and renamed in its own folder at once.
# One setting, read at each write (SeriesBackfill.apply). A series folder that is another folder always needed approval.
# 0.31.0 milestone B (rulings R18 and R20: finished books are renamed and moved by the rules with no approval step). The
# setting STAYS 'hold': the look-up itself still writes nothing. What changed is who approves. The app's rules do
# (rule_filing.RuleFiling), one book at a time through the same list Sergei used to approve (sorting_moves.plan: every
# refusal of that list still applies) and the same approve() below, with record 'approved_by': 'rules'. So a series is
# written only for a book the list lets through, bound to its manifest and to the exact path the list names.
WRITE_WITHOUT_APPROVAL = 'hold'
APPROVAL_KEYS = ('move_approved', 'approved_found', 'approved_target', 'approved_binding', 'approved_utc', 'approved_by', 'approved_names', 'approved_name_reasons')
WRITE_WAITS = 'Series found. Writing it into the file and renaming it waits for your approval.'
# The reason the 81 books were held by that bug. Such a book is looked up once more (a lookup only: its file is never touched
# without approval), so its series is found again under 0.30.0's rules (item 6: the original-language name) and it then
# waits for approval with MOVE_WAITS.
OLD_FOLDER_REASON = 'The recorded series paths do not share their original parent'
# 0.31.0 step 4a (Sergei 2026-11-22: "the series look-up of finished books must come to an end"). A book was recorded "no
# series" only when every source answered in one pass, and any source that waited sent the whole book round again, every
# source asked anew: on a copy of the live catalog 745 of 907 ledger rows were deferred, 576 of them more than 1,000 times
# (one 3,287), and 98% of the app's requests in the last hour (129 of 131) were these repeats. DuckDuckGo sat behind a
# human check for weeks, so no book it was asked about could ever end. The rule now, per book:
#   - each source's answer is kept: a source that answered "no series" is never asked about that book again;
#   - the app's own hourly limits (kind app_limit) are no try: the book waits for the limit and goes on where it stopped;
#   - a source that could not be reached, or whose answer could not be used, is tried SOURCE_TRIES times for that book,
#     at least TRY_SPACING apart, then given up: it counts as no answer;
#   - when every source has answered or is given up, the book is settled: a series found, or "none" with the sources
#     that never answered named (record 'unreached'); it is not looked up again under this lookup policy;
#   - a look-up that fails for another reason is tried FAILURE_TRIES times, TRY_SPACING apart, then held;
#   - a book whose cleanup is on hold (waiting for Sergei) is 'blocked': not tried, not counted as a look-up, and looked
#     up once its cleanup has finished.
# The numbers are product numbers Sergei may overrule; the page prints them (summary()['tries']).
SOURCE_TRIES = 3
TRY_SPACING = 6 * 3600
FAILURE_TRIES = 3
SOURCES = ('goodreads', 'fantlab', 'wikidata', 'publisher', 'litres')
NO_SERIES = 'No verified narrative series found in the supported sources'
UNREACHED = 'No series found. Sources that could not be reached are no longer asked: '
BLOCKED = 'Its source cleanup is on hold; the series look-up waits for it'
# 0.31.0 (rulings R18, R21 and R22; series_certainty): a series a source names is certain or doubtful by one rule, and a
# doubtful one is treated as not found: the source counts as having answered "none" for that book (with why, record
# 'sources' -> 'doubt') and the look-up goes on to the next source. A source that contradicts itself used to hold the
# book with this reason (six books on a copy of the live catalog, all from a qualifier on a Wikidata author statement);
# such a book is looked up once more under the rule.
REVIEW_REASON = 'Series sources need review'
WAITING_ON = ('blocked',)
# Senua's 0.31.0 review, M1 and M2: a move of the book began during a write (Choose folder… while it was written); the
# write's catalog step leaves the receipt the move started from as it is (SeriesBackfill._no_move_begun), and (R33, the
# delta review's M5) the write's own rewritten copy, which the catalog never named, goes (SeriesBackfill._withdraw).
MOVED_MEANWHILE = 'The audiobook was moved meanwhile; the catalog is unchanged'
# 0.31.3, root cause of the 24-25 Nov holds (measured on Sergei's machine and a copy of his catalog, 2026-11-25): every file
# this module removes in the library (the former file, its own temporary file, a withdrawn rewritten copy) went through the
# hardened local disposition only. Z:\Audiobooks Sorted is an SMB share; for a handle there the hardened guard refuses
# (no volume-GUID path: RemoteProviderRefused) before anything is removed, so the file was kept: all 115 writes since
# 24 Nov 21:23 (82 series, 33 names, name_write) kept both files, and two writes of names kept their temporary file.
# No series write had finished since 20 Oct, before that guard (0.28). Source cleanup had Sergei's 2026-11-16 NAS ruling
# (VerifiedFile.dispose remote_legacy: on a positively remote SMB volume, the pre-0.28 exact-handle method, after the
# caller's own last checks repeat through the same held handle); these removals now have it too (_last_checks).
RECOVERY_HOLD = 'Series recovery could not verify the files; remaining copies kept: '
# A write held at its last step only because its former file's removal was refused (RECOVERY_HOLD + native_io's
# retained_text of that file) goes back to that step once per value of this (record 'removal_retry'): 0.31.3 finishes the
# holds 0.31.2 left (_retry_retained_removals). Everything is proven again first; any doubt holds it again, both kept.
REMOVAL_RETRY = '0.31.3'
RETRY_FIELDS = ('old_path', 'new_path', 'temp', 'root', 'parent_identity', 'old_identity', 'new_identity', 'old_sha256', 'new_sha256',
                'old_size', 'new_size')
# Senua's 0.31.3 review, m5: what 0.31.2 and older STORED for the two kinds of hold this version finishes, frozen here as
# data. The retry finds those holds by these, never by the sentences the app shows now (RECOVERY_HOLD, APPLY_HOLD,
# native_io.retained_text), so rewording the screen can never change which books are sent back. A removal 0.31.3 starts
# itself is marked in its record ('removal_version', m3), and such a hold is never one of 0.31.2's.
LEGACY_REMOVAL_HOLD = 'Series recovery could not verify the files; remaining copies kept: Safe removal of “{}” could not be verified. The file was kept.'
LEGACY_APPLY_HOLDS = {'series_backfill': 'Series update failed; the audiobook is unchanged: ',
                      'name_writes': 'The names could not be written; the audiobook is unchanged: '}
LEGACY_TEMP_REFUSAL = 'Safe removal of “{}” could not be verified. The file was kept.'
# m2: one write of a book at a time (the words apply() already uses when the names write has the book).
ONE_AT_A_TIME = 'This audiobook is being renamed now'
# The hold of a write that failed before its rename (apply); a refused removal of the write's own leftover temporary file
# reads APPLY_HOLD + retained_text(temp). Sergei 2026-11-25: such a leftover is removed by the app, once per REMOVAL_RETRY
# (record 'temp_retry'), after the proofs of _remove_leftover (_clear_leftover_temporaries).
APPLY_HOLD = 'Series update failed; the audiobook is unchanged: '
# Judy's BooksArranger_LateWriteCleanup_UXSpec_2026-11-25.md, section 5 (Sergei's ruling 3): the hold reasons of a write's
# last steps, in "old file" and "new file", one fact plus the outcome. A Held one is stored without RECOVERY_HOLD (resume).
# RECOVERY_HOLD itself, OLD_FOLDER_REASON and APPLY_HOLD stay as they were: they find the holds 0.31.2 and older stored.
CATALOG_MISMATCH = 'The catalog does not match the new file; both files kept.'                     # 5.1 row 1
CHANGED = {'old': 'The old file changed since the app checked it; both files kept.',                  # 5.1 row 2a
           'new': 'The new file changed since the app checked it; both files kept.'}                  # 5.1 row 2b
NEW_CHANGED_OR_MISSING = 'The new file changed or is missing; the old file is kept.'                  # 5.1 row 3
TEMP_CHANGED = 'The temporary file changed since the app made it; it was left in place.'              # 5.1 row 4
OTHER_NAME = {'old': 'The old file is also stored under another name; both files kept.',              # 5.2 N1
              'new': 'The new file is also stored under another name; both files kept.'}  # only inside N9 (_withdraw), never shown alone
TEMP_OTHER_NAME = 'The temporary file is also stored under another name; it was left in place.'       # N2
SAME_FILE = 'The old and new files are the same file; nothing was removed.'                           # N3
FOLDER_CHANGED = "The book's folder changed since the app checked it; nothing was removed."           # N4
NOT_ONE_FOLDER = 'The old and new files are not recorded in the same folder; nothing was removed.'    # N5
OLD_STILL_THERE = 'The old file is still there after removal; both files kept.'                       # N6
OLD_MISSING = 'The old file is missing, and the app did not remove it.'                               # N7
TEMP_STILL_THERE = 'The temporary file is still there after removal; it was left in place.'           # N8
WITHDRAW_KEPT = MOVED_MEANWHILE + '. The new file could not be removed; both files kept.'             # N9
WITHDRAWN = MOVED_MEANWHILE + '; the new file was removed.'                                           # N9's success variant
# Section 6: why a leftover temporary file was kept (record 'temp_kept').
TEMP_NAMED = 'Another record of the app uses this file; it was left in place.'
TEMP_BOOK_UNNAMED = "The catalog does not match the book's file; the temporary file was left in place."
TEMP_BOOK_CHANGED = "The book's file changed since the app checked it; the temporary file was left in place."
TEMP_AUDIO_DIFFERS = "The temporary file's audio differs from the book's; it was left in place."
TEMP_WRITTEN_AFTER = 'The temporary file changed after the app last handled it; it was left in place.'
TEMP_CHANGED_DURING = 'The temporary file changed while the app checked it; it was left in place.'
# Judy's spec, section 6, "A series write's leftover temporary file" (Senua m6): the series hold once its leftover was
# handled. The engine's own opening stays, the false tail ("The file was kept.") goes; with the file kept, where it is.
SERIES_UNCHANGED = 'Series update failed; the audiobook is unchanged.'
TEMP_STILL_LEFT = ' A temporary file is still there: '
SCAN_WAIT = 'A library scan is running'  # _idle's and _may_finish's wait; the clean-up's Waiting item (Judy 3) reads it
# Senua's 0.31.3 review, M2: the library drive does not answer (asleep, offline, a network error). Nothing is tried and no
# one-time mark is used; the book waits as a write of names already waited (name_write.DRIVE_AWAY, the same words).
DRIVE_AWAY = 'The library drive is not answering'
# Judy's spec 4 and 7.3: the clean-up's outcome shows on the status line for this long after its last book settles.
LATE_SHOW_MS = 3600000
_CLEANUP_LOCK = threading.Lock()
_GENERATIONS = itertools.count(1)  # m1: each ledger write's token; a count read across one is not kept
# The hosts a deferral recorded before 0.31.0 named, as the sources that ask them.
HOST_SOURCES = {'www.goodreads.com': ('goodreads',), 'api.fantlab.ru': ('fantlab',), 'fantlab.ru': ('fantlab',), 'www.wikidata.org': ('wikidata',),
                'html.duckduckgo.com': ('publisher', 'litres'), 'en.wikipedia.org': ('publisher',), 'ru.wikipedia.org': ('publisher',),
                'ja.wikipedia.org': ('publisher',), 'www.penguinrandomhouse.com': ('publisher',), 'www.litres.ru': ('litres',)}
# Ruling R32 (Sergei 2026-11-23): the search the publisher and Litres sources go through; its human check counts as
# "nothing found" at once (SeriesBackfill.lookup). A human check from any other host is still a try (R9).
HUMAN_CHECK_HOST = 'html.duckduckgo.com'


class Held(ValueError):
    """The book is left as it is, with this reason."""


class Blocked(Exception):
    """Step 4a: the book's cleanup is on hold (it waits for Sergei); the look-up is not tried until that has finished."""


class Later(Exception):
    """Not now (a conversion, a scan, a source pause or an unfinished cleanup); the next pass tries again."""
    def __init__(self, reason, retry_at=None, waits=None):
        super().__init__(reason)
        self.retry_at = retry_at
        self.waits = waits or []


def judged(found):
    """0.31.0 (Senua's review, M3; ruling R18): a series the look-up kept passed series_certainty, the one rule. Every certain
    verdict says where its number came from (series_certainty.NUMBER_FROM), and the ledger keeps that with the series (the
    record's 'series_proof', an approval's 'approved_found'). A series found before 0.31.0 carries none (0.30.x had no such
    key): its adapters let through shapes the rule calls doubtful (Goodreads kept the first of several series, FantLab had
    no universe check), and the fields stored with it cannot show them. (A hold made by a 0.31.0 build before this check
    kept none either; it is looked up once more too.) Such a series is looked up again through 0.31.0's own adapters
    before the rules may act on it (pre_rule()), and until then it counts as not found
    (sorting_moves.certain). found: a look-up's answer or a ledger record. Returns where the number came from (one of
    NUMBER_FROM), '' when the rule never judged it."""
    import series_certainty
    if not isinstance(found, dict):
        return ''
    return next((place['number_from'] for place in (found, found.get('series_proof'), found.get('approved_found'))
                 if isinstance(place, dict) and place.get('number_from') in series_certainty.NUMBER_FROM), '')


def pre_rule(reason, record):
    """Senua's 0.31.0 review, M3: a book held with a series found before 0.31.0 that waits for the rules (MOVE_WAITS, or
    WRITE_WAITS) and that no one approved: it is looked up once more through 0.31.0's adapters (candidates()), and the rules
    wait for that look-up (unsettled()), as for a book held by the old bug (OLD_FOLDER_REASON)."""
    return reason in (MOVE_WAITS, WRITE_WAITS) and isinstance(record, dict) and not record.get('move_approved') and not judged(record)


def _stamp():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def _log(line):
    """A normal-level line in the engine's own log, with the time (as MergeService._removal_log): never sent to the page."""
    import sys
    try:
        print('Books Arranger ' + time.strftime('%Y-%m-%d %H:%M:%S') + ': ' + line, file=sys.stderr, flush=True)
    except Exception:
        pass


def present(path):
    """Whether this exact name is there: True or False only when that is known. Senua's 0.31.3 review, M3: pathlib's exists()
    answers False on any OSError (the bundled Python 3.14), so a network error read as "the old file is gone". Here only
    "not found" is False; any other error is raised (it cannot be told). Senua's re-review at 520ee66, M6: Python raises
    FileNotFoundError for Windows errors 3, 15, 53 and 67 too, and 53 and 67 are what an SMB server that cannot be reached
    answers. Only error 2 says this name is not there (off Windows: no winerror); every other code is raised."""
    try:
        os.lstat(path)
        return True
    except FileNotFoundError as error:
        if getattr(error, 'winerror', None) in (None, 2):
            return False
        raise


def network_lost(error):
    """Senua's re-review at 520ee66, m7: the error, or one it was raised from, carries the Windows code of a drive or share
    that went away (audio_jobs.UNREACHABLE, the set a conversion's Retry reads): as its winerror, as a native diagnostic
    (ProtectedIdentityUnavailable), or as the "[WinError N]" / "Windows error N" its text quotes (native_io's BoundaryError
    texts). Such a short error is a wait, as a drive that does not answer is (SeriesBackfill._drive_away)."""
    from audio_jobs import UNREACHABLE
    for _ in range(8):  # its cause chain, bounded
        if error is None:
            return False
        diagnostic = getattr(error, 'diagnostic', None)
        codes = [getattr(error, 'winerror', None), diagnostic.get('windows_error') if isinstance(diagnostic, dict) else None]
        codes += [int(code) for code in re.findall(r'(?:\[WinError |Windows error )(\d+)', str(error))]
        if any(code in UNREACHABLE for code in codes):
            return True
        error = error.__cause__ or error.__context__
    return False


def size_text(size):
    """A size as the page's byteText words it: 1024-based, one decimal under 10, none from 10 up."""
    units, index = ('B', 'KB', 'MB', 'GB', 'TB'), 0
    while index < len(units) - 1 and size >= 1024 ** (index + 1):
        index += 1
    scaled = size / 1024 ** index
    return ('%.1f' % scaled).rstrip('0').rstrip('.') + ' ' + units[index] if scaled < 10 and index else '%d %s' % (round(scaled), units[index])


def encoded(manifest):
    """The stored manifest text and its hash, exactly as AudioJobs.enqueue freezes them."""
    text = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return text, hashlib.sha256(text.encode('utf-8')).hexdigest()


def album(review):
    return ' - '.join([review['series'], review.get('number', ''), review['title']])


def series_tags(review):
    """The Apple metadata items a book converted with this series carries (audio_pipeline._encode_inputs)."""
    from quicktime_chapters import text_tag, track_tag
    value = album(review)
    tags = {ALBUM: text_tag(ALBUM, value), GROUPING: text_tag(GROUPING, review['series']), SORT_ALBUM: text_tag(SORT_ALBUM, value)}
    if str(review.get('number', '')).isdigit() and 0 < int(review['number']) < 65536:
        tags[TRACK] = track_tag(int(review['number']))
    return tags


def sha256(path, stop):
    value = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            if stop.is_set():
                raise InterruptedError('Series update stopped; the published audiobook is unchanged')
            value.update(block)
    return value.hexdigest()


def remove_owned(handle):
    """0.31.3: remove the app's own file through its held, single-link handle (the caller checked its name and folder). On
    the NAS, Sergei's 2026-11-16 method removes it after the same check again: the handle still names the file it opened."""
    facts = handle.facts()
    if facts['links'] != 1:
        raise BoundaryError(TEMP_OTHER_NAME)

    def same(held):
        now = held.refresh()
        if now['identity'] != facts['identity'] or now['links'] != 1 or now['attributes'] & (0x400 | 0x10):
            raise BoundaryError(TEMP_CHANGED)
    handle.dispose(remote_legacy=same)


def scanning(merge):
    """A library scan is running now (what _idle and _may_finish wait for: SCAN_WAIT)."""
    worker = getattr(getattr(merge, 'inventory', None), 'worker', None)
    return bool(worker and worker.is_alive())


def cleanup_view(merge):
    """The late-write clean-up across both writes (Judy's BooksArranger_LateWriteCleanup_UXSpec_2026-11-25.md, sections 2-4 and
    7): {'total', 'done', 'removed', 'kept', 'left', 'freed_bytes', 'title' (the book in hand, '' between books), 'in_hand',
    'active' (a book was in hand in this run, or a library scan held one), 'started' (epoch ms, then), 'waiting' (a library
    scan that is running now holds the books and none is in hand)}, or None when the engine runs neither write. Counts come
    from the ledgers (rows sent back with removal_retry, and the ones still to be sent back), summed over the series and the
    name passes. When the last book settles, the outcome for the status line is fixed once, in memory (outcome_view): only a
    run this engine saw with books left has one, so a relaunch shows none."""
    ledgers = [merge.__dict__.get(name) for name in ('series_backfill', 'name_write')] if hasattr(merge, '__dict__') else []
    ledgers = [ledger for ledger in ledgers if ledger is not None and callable(getattr(ledger, '_cleanup_counts', None))]
    if not ledgers:
        return None
    total = removed = kept = freed = 0
    titles, starts, waiting = [], [], False
    for ledger in ledgers:
        counts = ledger._cleanup_counts()
        total, removed, kept, freed = total + counts['total'], removed + counts['removed'], kept + counts['kept'], freed + counts['freed']
        own = ledger.__dict__
        if own.get('_cleanup_hand') is not None:
            titles.append(own['_cleanup_hand'])
        if own.get('_cleanup_started'):
            starts.append(own['_cleanup_started'])
        waiting = waiting or bool(own.get('_cleanup_waiting'))
    left = total - removed - kept
    # Futaba's 0.31.3 QA, m6: the flag stays set until the next book is in hand, up to a minute after the scan ended (the
    # books' next try); the scan itself says whether it still holds them, so the row replaces the item in the same update.
    waiting = waiting and scanning(merge)
    with _CLEANUP_LOCK:
        memo = merge.__dict__.setdefault('_late_cleanup', {'seen': False, 'finished': None, 'outcome': None})
        if left > 0:
            memo.update(seen=True, finished=None, outcome=None)
        elif memo['seen'] and memo['finished'] is None and total:
            memo.update(finished=time.monotonic(), outcome={'removed': removed, 'kept': kept, 'freed_bytes': freed})
    return {'total': total, 'done': removed + kept, 'removed': removed, 'kept': kept, 'left': left, 'freed_bytes': freed,
            'title': next((title for title in titles if title), ''), 'in_hand': bool(titles), 'active': bool(starts),
            'started': min(starts) if starts else None, 'waiting': waiting and not titles}


def outcome_view(merge):
    """/api/state 'late_cleanup' (Judy 7.3): {removed, kept, freed_bytes, last_age_ms}, the clean-up's end for the status line,
    like 'relinked' and 'removed': an age, never a clock time; zeros once LATE_SHOW_MS has passed, and before any end."""
    with _CLEANUP_LOCK:
        memo = dict(merge.__dict__.get('_late_cleanup') or {}) if hasattr(merge, '__dict__') else {}
    if memo.get('finished') is None or not memo.get('outcome'):
        return {'removed': 0, 'kept': 0, 'freed_bytes': 0, 'last_age_ms': None}
    age = max(0, round((time.monotonic() - memo['finished']) * 1000))
    if age >= LATE_SHOW_MS:
        return {'removed': 0, 'kept': 0, 'freed_bytes': 0, 'last_age_ms': age}
    return dict(memo['outcome'], last_age_ms=age)


class SeriesBackfill:
    LEDGER = 'series_backfill'  # this kind of write's ledger table (name_write.NameWrite: 'name_writes')
    TEMP_PREFIX = TEMP_PREFIX  # its own temporary file's name (name_write: '.books-arranger-names-')
    APPLY_HOLD = APPLY_HOLD  # the hold of a write that failed before its rename (name_write: NAMES_FAILED)

    def __init__(self, merge, research=None, stage=None, clock=time.time):
        self.merge = merge
        self.database = merge.inventory.database
        self.research = research
        self.clock = clock
        self.stage = Path(stage) if stage else Path(merge.stage_root).parent / 'series-backfill'
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
        # Futaba's 0.31.3 QA, m2: until START_DELAY has passed, reading the state (summary) never starts the first pass.
        self.__dict__['_delay_until'] = time.monotonic() + START_DELAY
        self.thread = threading.Thread(target=self._run, name='books-series-backfill', daemon=True)  # close() stops it; a hard exit is what the resumable states are for
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
                pass  # display only; every book records its own reason
            finally:
                self.progress = None
            self.wake.wait(self._next_wait())
            self.wake.clear()

    def _next_wait(self):
        """Due deferrals get another pass without a hot loop or renewed provider allowance."""
        due = [json.loads(row['record']).get('next_attempt') for row in
               self._rows("SELECT record FROM series_backfill WHERE state NOT IN (%s)" % ','.join('?' * len(FINAL)), FINAL)]
        due = [value for value in due if isinstance(value, (int, float))]
        return max(30, min(PASS_WAIT, min(due) - self.clock())) if due else PASS_WAIT

    def status(self):
        """The progress row: {'title', 'done', 'total', 'step'} while a pass works on a book, else None. 0.31.0 (Judy's
        spec 2.1): done and total are the whole look-up's (settled books of every book that needed it, summary()), not
        one pass's, which started again every ten minutes and read as no progress; 'pass_done' and 'pass_total' keep the
        pass's own. 'pacing': the pass only waits for a site's pacing now (no running row then, Judy 2.2)."""
        value = self.progress
        if not value:
            return None
        value = dict(value, pass_done=value.get('done'), pass_total=value.get('total'), pacing=bool(self.__dict__.get('_pacing_until', 0) > time.monotonic()))
        try:
            whole = self.summary()
        except sqlite3.Error:
            whole = None
        if whole and whole.get('total'):
            value.update(done=whole['done'], total=whole['total'])
        return value

    def _pacing(self, seconds):
        """PublicClient's note (budget['pacing']): it waits this long for a site's pacing before its request; 0 when done."""
        self.__dict__['_pacing_until'] = time.monotonic() + seconds if seconds and seconds > 1 else 0

    # ------------------------------------------------------------------ ledger
    def _rows(self, sql, params=()):
        with connect(self.database) as db:
            return [dict(r) for r in db.execute(sql, params)]

    def entry(self, job_id):
        rows = self._rows('SELECT * FROM series_backfill WHERE job_id=?', (job_id,))
        if not rows:
            return None
        row = rows[0]
        row['record'] = json.loads(row['record'])
        return row

    def _set(self, job_id, state, reason='', record=None):
        with connect(self.database) as db:
            prior = db.execute('SELECT record FROM series_backfill WHERE job_id=?', (job_id,)).fetchone()
            value = record if record is not None else (json.loads(prior[0]) if prior else {})
            if state == 'held' and isinstance(value, dict) and value.get('move_approved') and reason not in (MOVE_WAITS, WRITE_WAITS) \
                    and not value.get('approved_failed'):
                # Judy's 0.31.0 spec, 3.3: whatever held a book after he approved it (its file or its place changed, a
                # name taken, a failed proof), the list shows it again with why (sorting_moves). One place for every hold.
                value = dict(value, approved_failed={'reason': str(reason)[:300], 'at': _stamp()})
            db.execute('INSERT OR REPLACE INTO series_backfill VALUES(?,?,?,?,?)',
                       (job_id, state, reason, json.dumps(value, ensure_ascii=False), _stamp()))
        self._changed()

    def _changed(self):
        """The ledger was written: the cached summary (and the clean-up's counts) are recounted at their next read."""
        self.__dict__['_summary'] = None
        with _CLEANUP_LOCK:  # m1: a count read across this write is never kept (its generation no longer matches)
            self.__dict__['_cleanup_generation'] = next(_GENERATIONS)
            self.__dict__['_cleanup_cache'] = None

    # ------------------------------------------------------------------ the clean-up's progress (Judy's late-write clean-up spec)
    def _cleanup_counts(self):
        """{'total', 'removed', 'kept', 'freed'} of this ledger's books sent back for the clean-up (REMOVAL_RETRY), from the
        ledger, so a quit or a crash keeps them (Judy 2): total, those and the ones still to be sent back (m8), so it is
        fixed from the start; removed: the old file went
        ('done'); kept: a check kept both files (held again); freed: the removed old files' recorded sizes. Read again only
        after the ledger is written (_changed)."""
        cached = self.__dict__.get('_cleanup_cache')
        if cached is not None:
            return dict(cached)
        generation = self.__dict__.get('_cleanup_generation')
        counts = {'total': 0, 'removed': 0, 'kept': 0, 'freed': 0}
        with connect(self.database) as db:
            for state, number, freed in db.execute(
                    "SELECT state,count(*),sum(json_extract(record,'$.old_size')) FROM " + self.LEDGER + " WHERE record LIKE '%removal_retry%' "
                    "AND json_valid(record) AND json_extract(record,'$.removal_retry')=? GROUP BY state", (REMOVAL_RETRY,)):
                counts['total'] += number
                if state == 'done':
                    counts['removed'] += number
                    counts['freed'] += int(freed or 0)
                elif state not in ACTIVE:
                    counts['kept'] += number
            # Futaba's 0.31.3 QA, m8: the books not sent back yet are in the total from the start. Each pass queues its own
            # ledger's books (the names pass about 5 s after the series pass, and a book whose other write is in hand on a
            # later pass), so a total of the queued books alone grew once during the run (82, then 115) and the bar stepped
            # back. The same test as the selection (_removal_retained, not yet marked), so the total is the run's books.
            for job_id, state, reason, record in db.execute(
                    'SELECT job_id,state,reason,record FROM ' + self.LEDGER + " WHERE state='held' AND record LIKE '%removal_intended%'"):
                try:
                    record = json.loads(record)
                except (TypeError, ValueError):
                    continue
                if isinstance(record, dict) and record.get('removal_retry') != REMOVAL_RETRY and \
                        self._removal_retained({'job_id': job_id, 'state': state, 'reason': reason, 'record': record}):
                    counts['total'] += 1
        with _CLEANUP_LOCK:
            # Senua's 0.31.3 review, m1: the other thread's write (a book settling) may land while this read runs; its _changed()
            # moves the generation, and then this answer is used once but not kept, so the next read counts again.
            if self.__dict__.get('_cleanup_generation') == generation:
                self.__dict__['_cleanup_cache'] = dict(counts)
        return counts

    @staticmethod
    def _answers(root):
        """The library folder answers now (a drive that is asleep or offline does not)."""
        try:
            return os.path.isdir(root)
        except OSError:
            return False

    def _drive_away(self, record, error=None):
        """Senua's 0.31.3 review, M2: the book's library drive does not answer, so the book waits (Later) and nothing it may
        do once is used up. Any error says so when the library folder does not answer right after it. Senua's re-review at
        520ee66, M5: an error of a folder on the way that is not there (AncestorUnavailable) also means "the folder is gone",
        so it is the drive only while the book's folder cannot be told gone (_absent): with the library folder answering
        and the book's folder positively not there, the book settles (held N4) instead of waiting for good. Senua's
        re-review, m7: an error that carries the code of a drive or share that went away (network_lost) waits too, even when
        the library folder answers a moment later; one blip never ends a retried book for good."""
        if isinstance(error, AncestorUnavailable):
            old = record.get('old_path') if isinstance(record, dict) else None
            return not (old and self._absent(record, os.path.dirname(str(old))))
        if network_lost(error):
            return True
        root = record.get('root') if isinstance(record, dict) else None
        return bool(root) and not self._answers(root)

    def _absent(self, record, path):
        """M5: this path is positively not there while the drive answers. The library folder (record 'root') answers, and
        walking down from it, a name on the way is not found (present(): Windows error 2, so the folder it is in answered).
        A folder renamed, moved or deleted is not a drive that is away. Anything that cannot be told (no root, a path
        outside it, a network error on the way) is False: the caller waits, as before."""
        try:
            root, path = ordinary(record['root']), ordinary(path)
            steps = path.relative_to(root).parts
        except (KeyError, TypeError, ValueError):  # BoundaryError is a ValueError
            return False
        if not self._answers(root):
            return False
        current = root
        try:
            for part in steps:
                current = current / part
                if not present(current):
                    return True
        except OSError:
            return False
        return False

    def _finish_active(self, job_id, entry):
        """One begun write finished from its recorded state (both passes' first loop). A book of the clean-up is the row's
        book in hand while it runs (Judy 2); a library scan that holds it is the Waiting item's cause (Judy 3)."""
        retried = entry['record'].get('removal_retry') == REMOVAL_RETRY
        try:
            self._may_finish()  # R35: a begun write finishes without the Pause or conversion gate (_idle)
            if self._drive_away(entry['record']):
                raise Later(DRIVE_AWAY, self.clock() + 60)  # Senua M2: nothing is tried on a drive that does not answer
            if self._waits_for_other(job_id):
                raise Later(ONE_AT_A_TIME, self.clock() + 60)  # Senua m2: the same book's other write is in its last step
            if retried:
                self.__dict__.update(_cleanup_hand=str((entry['record'].get('review') or {}).get('title') or ''), _cleanup_waiting=False)
                self.__dict__.setdefault('_cleanup_started', int(time.time() * 1000))
            self.resume(job_id)
        except Later as wait:
            if retried and str(wait) == SCAN_WAIT:
                self.__dict__['_cleanup_waiting'] = True
                # Futaba's 0.31.3 QA, m6: the run is taken up here too, so when the scan ends the row stands in for the
                # Waiting item at once (cleanup_view 'active'), its elapsed time running from now, before a book is in hand.
                self.__dict__.setdefault('_cleanup_started', int(time.time() * 1000))
            self._defer(job_id, wait, state=entry['state'])
        finally:
            if retried:
                self.__dict__['_cleanup_hand'] = None
                try:
                    cleanup_view(self.merge)  # the outcome's hour starts when the last book settles, whether a page asks or not
                except Exception as error:
                    # Senua's 0.31.3 review, m4: a failed count (a busy catalog) never replaces the step's own outcome or stops
                    # the pass; it is said in the log, and the next count (a poll, the next book) reads again.
                    _log('Clean-up count not read: ' + (str(error) or type(error).__name__))

    def _ledger_entry(self, table, job_id):
        """The same book's entry in another ledger (series_backfill or name_writes), or None."""
        with connect(self.database) as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                return None
            row = db.execute('SELECT * FROM ' + table + ' WHERE job_id=?', (job_id,)).fetchone()
        if not row:
            return None
        entry = dict(row)
        try:
            entry['record'] = json.loads(entry['record'])
        except (TypeError, ValueError):
            entry['record'] = {}
        return entry

    def _waits_for_other(self, job_id):
        """Senua's 0.31.3 review, m2: one write of a book at a time. The series write goes first and never waits here (two
        that waited for each other would both wait for good); the names write waits for it (NameWrite)."""
        return False

    def _retry_blocked(self, job_id):
        """m2: this book is not sent back for the clean-up now: the series write waits while the names write of the same
        book is in its last step (NameWrite also waits for a series hold the series retry will take first)."""
        other = self._ledger_entry('name_writes', job_id)
        return bool(other and other['state'] in ACTIVE)

    # ------------------------------------------------------------------ what is left (0.31.0 step 4b)
    def summary(self):
        """Plain counts of the whole look-up for /api/state (background_work), read from the ledger: no manifest is parsed,
        and the answer is kept until the ledger is written again or a book finishes converting.
          left          finished books that still wait for a series look-up (to_look_up + between_tries)
          to_look_up    due now or not visited yet; None until the first pass has counted the books not visited
          between_tries waiting for a later try (a source's limit or pause); next_at: the earliest, epoch seconds
          write_waiting a series was found and its write waits for the queue, a cleanup or a scan (job ids in 'writes')
          writing       being written or renamed now, or approved and next
          moves_waiting a series was found and is not applied: the guard holds every write (WRITE_WITHOUT_APPROVAL), or its
                        series folder is another folder. Third round (Sergei's R18 and R19, 2026-11-22): he approves none,
                        so it waits for the app's rules, not for him; it is the quiet line's number (Judy 3.2) and holds
                        back no state. For the look-up itself such a book is settled: its series was found.
          applies_by_itself  the app writes a found series into a finished file without anyone's approval (false while the
                        guard is at 'hold'): the one fact the page reads for the series row's tooltip (Judy 2.1)
          blocked       the book's cleanup is on hold; not looked up until that has finished
          settled       with_series + without + gave_up + left_alone (held or skipped for a lasting reason)
          done, total   books the look-up has settled (a series found, applied or not; none found; given up) and every book
                        that needed it, for the row's bar: it only grows and ends at the total
          tries         {'per_source', 'spacing_seconds', 'failures'}: the limits (SOURCE_TRIES, TRY_SPACING, FAILURE_TRIES)"""
        now = self.clock()
        with connect(self.database) as db:
            finished = db.execute("SELECT count(*) FROM audio_jobs WHERE state='completed'").fetchone()[0]
            kept = self.__dict__.get('_summary')
            if kept is not None and kept[0] == finished and (kept[1] is None or kept[1] > now):
                return dict(kept[2])
            # 0.31.0 milestone B: an approved write that waits for the queue was deferred with no 'found' of its own (its
            # series is 'approved_found') and counted as a look-up between tries; it is a write that waits.
            rows = db.execute("SELECT job_id,state,reason,json_extract(record,'$.next_attempt'),json_extract(record,'$.found') IS NOT NULL "
                              "OR json_extract(record,'$.move_approved') IS NOT NULL,"
                              "json_extract(record,'$.unreached') IS NOT NULL,json_extract(record,'$.approved_failed') IS NOT NULL,"
                              "CASE WHEN state='held' AND reason IN (?,?) THEN record END FROM series_backfill"
                              # 0.31.1 (Futaba's QA, minor 1): a finished book removed from the list is in no count
                              " WHERE job_id NOT IN (SELECT job_id FROM audio_jobs WHERE state='removed')", (MOVE_WAITS, WRITE_WAITS)).fetchall()
        counts = dict.fromkeys(('between_tries', 'due', 'write_waiting', 'writing', 'moves_waiting', 'blocked', 'with_series', 'without', 'gave_up', 'left_alone'), 0)
        writes, nexts, writes_held, taken = [], [], 0, None
        for job_id, state, reason, next_attempt, found, unreached, failed, waits in rows:
            later = isinstance(next_attempt, (int, float)) and next_attempt > now
            # Senua's 0.31.0 review, M3: a series found before 0.31.0 is looked up again (pre_rule()): due, not a move waiting.
            again = waits is not None and pre_rule(reason, json.loads(waits))
            if state == 'held' and (reason in (MOVE_WAITS, WRITE_WAITS, OLD_FOLDER_REASON) or failed or str(reason).startswith(REVIEW_REASON)):
                due = reason == OLD_FOLDER_REASON or str(reason).startswith(REVIEW_REASON) and not failed or again
                if due:
                    # R34 (Senua's delta review, m11): only a hold the look-up will take again is "to look up"; one whose job
                    # is not its book's current, eligible job (converted again, replaced, retained) never is, and counts as
                    # it did before 0.31.0.
                    taken = self._look_up_jobs() if taken is None else taken
                    due = job_id in taken
                counts['due' if due else 'moves_waiting'] += 1
                writes_held += reason == WRITE_WAITS and not due
            elif state in ACTIVE or state == 'pending':
                counts['writing'] += 1
            elif state in WAITING_ON:
                counts['blocked'] += 1
            elif state == 'deferred' and found:
                counts['write_waiting'] += 1
                writes.append(job_id)
            elif state == 'deferred':
                counts['between_tries' if later else 'due'] += 1
                if later:
                    nexts.append(next_attempt)
            elif state == 'done':
                counts['with_series'] += 1
            elif state == 'none':
                counts['gave_up' if unreached else 'without'] += 1
            else:
                counts['left_alone'] += 1
        backlog = self.__dict__.get('_backlog')
        # Not visited yet: counted at the last pass's start, less the books that got a ledger row since.
        unvisited = len(backlog['unvisited'] - {row[0] for row in rows}) if backlog and backlog['finished'] == finished else None
        if unvisited is None and self.thread and self.thread.is_alive() and time.monotonic() >= self.__dict__.get('_delay_until', 0):
            # A book finished converting (or nothing was counted yet): the pass counts the books not visited. Futaba's 0.31.3
            # QA, m2: never before the start delay is over. The page reads the state at once, so this woke the first pass
            # (and the clean-up) seconds after launch, ahead of the published check the delay lets finish first; the first
            # pass counts them anyway.
            self.wake.set()
        settled = counts['with_series'] + counts['without'] + counts['gave_up'] + counts['left_alone']
        to_look_up = None if unvisited is None else counts['due'] + unvisited
        left = None if to_look_up is None else to_look_up + counts['between_tries']
        value = {'known': unvisited is not None, 'left': left, 'to_look_up': to_look_up, 'between_tries': counts['between_tries'],
                 'next_at': min(nexts) if nexts else None, 'write_waiting': counts['write_waiting'], 'writes': writes[:100], 'writing': counts['writing'],
                 'moves_waiting': counts['moves_waiting'], 'writes_held': writes_held, 'write_without_approval': WRITE_WITHOUT_APPROVAL,
                 'applies_by_itself': WRITE_WITHOUT_APPROVAL == 'allow',
                 'blocked': counts['blocked'], 'settled': settled, 'with_series': counts['with_series'],
                 'without': counts['without'], 'gave_up': counts['gave_up'], 'left_alone': counts['left_alone'], 'done': settled + counts['moves_waiting'],
                 'total': None if left is None else settled + left + counts['write_waiting'] + counts['writing'] + counts['moves_waiting'],
                 'tries': {'per_source': SOURCE_TRIES, 'spacing_seconds': TRY_SPACING, 'failures': FAILURE_TRIES}}
        self.__dict__['_summary'] = (finished, min(nexts) if nexts else None, value)
        return dict(value)

    def approve(self, job_id, found, target, by=None, names=None, reasons=None):
        """0.30.0 item 2: Sergei approved this book's listed move (sorting_moves). found: the series it is filed under
        ({'name','number','provider','source_url'}, the original-language name, item 6); target: the path he saw. The held
        book is looked at again by the next pass with exactly this series (no new lookup), only while the book's manifest is
        the one he approved. Raises ValueError when the book is not held for this reason.
        by (0.31.0 milestone B): 'rules' when the app's rules approved it (rule_filing), kept as record 'approved_by'.
        names (0.31.0 ruling R27): {'title', 'author', 'canonical_author'} the rules also file the book under (the list's
        item 'names'); they are written into the file in the same rewrite (one rewrite per book). Only the rules approve
        names (ValueError otherwise). reasons: the list's reasons for them, kept with the record (the title's source)."""
        entry = self.entry(job_id)
        rows = self._rows('SELECT manifest FROM audio_jobs WHERE job_id=?', (job_id,))
        if not entry or entry['state'] != 'held' or not rows:
            raise ValueError('This book is not waiting for a series move; nothing was changed.')
        import name_write
        names = {field: str(names[field]) for field in name_write.FIELDS if field in (names or {}) and str(names[field]).strip()}
        if names and by != name_write.BY:
            raise ValueError(name_write.NOT_BY_RULES)
        if names and self._names_in_hand(job_id):
            raise ValueError(name_write.BEING_WRITTEN)
        record = dict(entry['record'])
        record.pop('approved_names', None)
        record.pop('approved_name_reasons', None)
        if names:
            record['approved_names'] = names
            record['approved_name_reasons'] = [dict(reason) for reason in reasons or [] if isinstance(reason, dict) and reason.get('kind') in ('title', 'author')]
        approved = {key: found[key] for key in ('name', 'number', 'provider', 'source_url') if key in found}
        approved['receipts'] = record.get('research_receipts') or []
        approved['deferred_sources'] = record.get('deferred_sources') or []
        approved.update({key: copy.deepcopy(value) for key, value in (record.get('series_proof') or {}).items()})
        record.update(move_approved=True, approved_found=approved, approved_target=str(target), approved_binding=encoded(json.loads(rows[0]['manifest']))[1],
                      approved_utc=_stamp())
        record.pop('approved_by', None)
        if by:
            record['approved_by'] = str(by)
        record.pop('next_attempt', None)
        record.pop('follow_up', None)
        record.pop('approved_failed', None)  # a new approval of a move that could not run before
        self._set(job_id, 'pending', '', record)
        self.wake.set()

    def _follow_up(self, job_id):
        """0.30.0 item 2: after an approved book's series was written into it ('done'), its move into the series folder
        (MergeService.sorting_follow_up: the app's usual verified move, only to the path Sergei approved). Recorded once, when
        the answer lasts. Senua's 0.30.0 review, M2: a refusal that passes ('later': Quit, the queue, a move already running,
        a busy catalog) or an unexpected error was recorded for good, and the pass never came back (it retries only rows
        with no follow_up): the book stayed in its old folder under its new name. Now it is noted (follow_up_wait) and the
        next pass asks again."""
        entry = self.entry(job_id)
        if not entry or entry['state'] != 'done':
            return
        record = entry['record']
        if not record.get('move_approved') or record.get('follow_up'):
            return
        # 0.31.0 ruling R30: a Choose folder… pressed while this book was rewritten wins over the move below, and over a
        # write in its own folder too (MergeService.choice_after_write). None: there is no such choice.
        choice = getattr(self.merge, 'choice_after_write', None)
        if callable(choice):
            try:
                answer = choice(job_id, record)
            except Exception as error:
                answer = {'state': 'later', 'reason': (str(error) or type(error).__name__)[:300]}
            if answer is not None:
                if answer.get('state') == 'later':
                    self._set(job_id, 'done', '', dict(record, follow_up_wait=dict(answer, at=_stamp())))
                    return
                record = {key: value for key, value in record.items() if key != 'follow_up_wait'}
                self._set(job_id, 'done', '', dict(record, follow_up=dict(answer, at=_stamp())))
                return
        if not record.get('series_folder'):
            # An approved write in the book's own folder (the guard): it is where it belongs; there is no move to make.
            self._set(job_id, 'done', '', dict(record, follow_up={'state': 'none', 'reason': 'Written in its own folder', 'at': _stamp()}))
            return
        hook = getattr(self.merge, 'sorting_follow_up', None)
        if not callable(hook):
            return
        try:
            answer = dict(hook(job_id, record['approved_target'], record.get('new_path')) or {})
        except Exception as error:
            answer = {'state': 'later', 'reason': (str(error) or type(error).__name__)[:300]}
        if answer.get('state') == 'later':
            self._set(job_id, 'done', '', dict(record, follow_up_wait=dict(answer, at=_stamp())))
            return
        record = {key: value for key, value in record.items() if key != 'follow_up_wait'}
        self._set(job_id, 'done', '', dict(record, follow_up=dict(answer, at=_stamp())))

    # ------------------------------------------------------------------ pass
    def candidates(self):
        """Finished books (the newest job of each book) without a series and without a final record. Never a retained job
        (0.30.0 item A: the storage move kept its evidence without authority to change it; its book stays as published)."""
        from storage_relocation_native import retained_job
        entries = {r['job_id']: r for r in self._rows('SELECT job_id,state,reason,record FROM series_backfill')}
        for entry in entries.values():
            if entry['state'] == 'held' and (entry['reason'] == OLD_FOLDER_REASON or str(entry['reason']).startswith(REVIEW_REASON)
                                             or entry['reason'] in (MOVE_WAITS, WRITE_WAITS) and pre_rule(entry['reason'], json.loads(entry['record']))):
                # 0.30.0 item 2: held by the old bug; looked up once more (see OLD_FOLDER_REASON). 0.31.0: so is a book held
                # because a source contradicted itself (REVIEW_REASON): that is a doubtful answer now, not a hold; and a
                # series found before 0.31.0 that waits for the rules (pre_rule(), Senua's 0.31.0 review, M3).
                entry['state'] = 'deferred'
        generation = self._local_generation()
        newest = {}
        for row in self._rows("SELECT job_id,json_extract(manifest,'$.candidate_id') AS candidate FROM audio_jobs ORDER BY created,job_id"):
            newest[row['candidate']] = row['job_id']
        result = []
        for row in self._rows("SELECT * FROM audio_jobs WHERE state='completed' AND output IS NOT NULL ORDER BY updated,job_id"):
            manifest = json.loads(row['manifest'])
            if __import__('publication_reuse').task(manifest) or retained_job(self.database, row['job_id']):continue
            review = manifest.get('metadata') or {}
            entry = entries.get(row['job_id'])
            record = json.loads(entry['record']) if entry else {}
            final = entry and entry['state'] in FINAL
            if entry and entry['state'] == 'none':
                final = record.get('lookup_policy') == LOOKUP_POLICY and (generation is None or record.get('local_generation') == generation)
            if entry and (final or entry['state'] in ACTIVE or record.get('next_attempt', 0) > self.clock()) \
                    or newest.get(manifest.get('candidate_id')) != row['job_id']:
                continue
            if review.get('series') or not review.get('title') or not review.get('canonical_author'):
                continue
            if entry and entry['state'] in WAITING_ON and self._cleanup(row['job_id']) == 'held':
                continue  # step 4a: still blocked by a cleanup on hold; a cheap catalog read, never a try
            result.append(row)
        # Step 4b: the books that need a look-up and have no ledger row yet, for summary() (with the count of finished
        # jobs it was taken at: a book that finishes converting makes it unknown until the next pass).
        with connect(self.database) as db:
            finished = db.execute("SELECT count(*) FROM audio_jobs WHERE state='completed'").fetchone()[0]
        self.__dict__['_backlog'] = {'unvisited': {row['job_id'] for row in result if row['job_id'] not in entries}, 'finished': finished}
        self._changed()
        # Unvisited books go first; one slow oldest candidate cannot monopolize a pass.
        return sorted(result, key=lambda row: json.loads(entries[row['job_id']]['record']).get('last_attempt', 0)
                      if row['job_id'] in entries else 0)

    def _local_generation(self):
        function = getattr(self.research, 'local_generation', None)
        return function() if callable(function) else None

    def _defer(self, job_id, wait, found=None, state='deferred', manifest=None, sources=None, failures=None):
        entry = self.entry(job_id)
        record = dict(entry['record']) if entry else {}
        if state == 'deferred' and entry and entry['state'] in ACTIVE:
            state = entry['state']  # Never replace a crash-recovery checkpoint with a lookup state.
        now = self.clock()
        record.update(last_attempt=now, next_attempt=max(now + 60, wait.retry_at or now + PASS_WAIT),
                      waits=wait.waits, deferrals=record.get('deferrals', 0) + 1)
        if sources is not None:
            record['sources'] = sources  # step 4a: what each source answered so far, and its tries
        if failures is not None:
            record['failures'] = failures
        if found:
            binding = encoded(manifest)[1] if manifest is not None else None
            found_at = self._finding_time(found, now)
            if record.get('found') == found and record.get('found_binding') == binding:
                found_at = min(record.get('found_at', 0), found_at)
            record['found'] = found
            record['found_binding'] = binding
            record['found_at'] = found_at  # Waiting for idle does not renew source-evidence age.
        self._set(job_id, state, str(wait), record)

    @staticmethod
    def _finding_time(found, now):
        """The oldest actual receipt, not the time an old cache entry was observed."""
        times = []
        for receipt in found.get('receipts') or []:
            try:
                digest = receipt['sha256']
                if not isinstance(digest, str) or len(digest) != 64 or set(digest) - set('0123456789abcdef'):
                    return 0
                parsed = datetime.fromisoformat(receipt['retrieved_utc'].replace('Z', '+00:00'))
                if parsed.tzinfo is None or parsed.timestamp() > now + 60:
                    return 0
                times.append(parsed.timestamp())
            except (KeyError, TypeError, ValueError, AttributeError):
                return 0
        return min([now, *times]) if times else 0

    def run_pass(self):
        try:
            self._pass()
        finally:
            self.progress = None

    def _pass(self):
        if self.research is None:
            return
        self._retry_retained_removals()
        self._clear_leftover_temporaries()
        for row in self._rows('SELECT job_id FROM series_backfill WHERE state IN (%s)' % ','.join('?' * len(ACTIVE)), ACTIVE):
            if self.stop.is_set():
                return  # Senua M1: Quit and "Restart to update" stop the clean-up between two books
            entry = self.entry(row['job_id'])
            if entry['record'].get('next_attempt', 0) > self.clock():
                continue
            self._finish_active(row['job_id'], entry)
        # 0.30.0 item 2: an approved book whose series was written before a restart still gets its approved move. (R35: a
        # Choose folder… of the book does not wait for this; run_move records the follow-up itself, _follow_up_now.)
        for row in self._rows("SELECT job_id FROM series_backfill WHERE state='done' AND json_extract(record,'$.move_approved') "
                              "AND json_extract(record,'$.follow_up') IS NULL"):
            try:
                self._idle()
                self._follow_up(row['job_id'])
            except Later:
                break
        books = self.candidates()
        jobs = self.merge.jobs.status()['jobs'] if books and getattr(self.merge, 'publications', None) is not None else None
        for index, row in enumerate(books):
            if self.stop.is_set():
                return
            manifest = json.loads(row['manifest'])
            title = manifest['metadata']['title']
            self.progress = {'title': title, 'done': index, 'total': len(books), 'step': 'looking up'}
            found = None
            memory = None
            try:
                reason = self.unsafe(row, jobs)
                if reason:
                    self._set(row['job_id'], 'skipped', reason)
                    continue
                entry = self.entry(row['job_id'])
                prior = entry['record'] if entry else {}
                memory = self._memory(prior)
                lookup_generation = self._local_generation()
                if prior.get('move_approved'):
                    # 0.30.0 item 2: the series Sergei approved with its move, exactly; never a new lookup.
                    if prior.get('approved_binding') != encoded(manifest)[1] or not prior.get('approved_found'):
                        raise Held('The book changed since you approved its move; nothing was changed')
                    self.progress = {'title': title, 'done': index, 'total': len(books), 'step': 'updating'}
                    self.apply(row['job_id'], dict(prior['approved_found']))
                    continue
                # A series kept from an earlier pass is used again only when the one rule judged it (judged(); Senua's 0.31.0
                # review, M3): one found before 0.31.0 is looked up again.
                found = prior.get('found') if prior.get('found_binding') == encoded(manifest)[1] and prior.get('found_at', 0) > 0 \
                    and 0 <= self.clock() - prior.get('found_at', 0) <= 7 * 86400 and judged(prior.get('found')) else None
                found = found or self.lookup(manifest, memory)
                preferred = prior.get('found') or {}
                if found and prior.get('found_binding') == encoded(manifest)[1] and preferred.get('provider') == 'goodreads' \
                        and (found['name'], found['number']) != (preferred.get('name'), preferred.get('number')):
                    raise Held('The new series answer conflicts with the retained Goodreads sequence; copies kept')
                if not found:
                    # Step 4a: settled. Every source answered "no series", or was given up after SOURCE_TRIES tries (named
                    # in 'unreached', so a later job can ask just those again).
                    unreached = [name for name in SOURCES if (memory.get(name) or {}).get('gave_up')]
                    record = dict(prior, lookup_policy=LOOKUP_POLICY, local_generation=lookup_generation, last_attempt=self.clock(), sources=memory)
                    record.pop('next_attempt', None)
                    record.pop('unreached', None)
                    if unreached:
                        record['unreached'] = unreached
                    self._set(row['job_id'], 'none', UNREACHED + ', '.join(unreached) if unreached else NO_SERIES, record)
                    continue
                self.progress = {'title': title, 'done': index, 'total': len(books), 'step': 'updating'}
                self.apply(row['job_id'], found)
            except Blocked as blocked:
                entry = self.entry(row['job_id'])
                self._set(row['job_id'], 'blocked', str(blocked), dict(entry['record']) if entry else {})
                continue
            except Later as wait:
                self._defer(row['job_id'], wait, found, manifest=manifest, sources=memory)
                continue
            except InterruptedError:
                return
            except Held as held:
                entry = self.entry(row['job_id'])
                evidence = dict(entry['record']) if entry else {}
                evidence['last_attempt'] = self.clock()
                if memory is not None:
                    evidence['sources'] = memory
                if evidence.get('move_approved'):
                    # Judy's 0.31.0 spec, 3.3: an approved move that then could not run comes back to the list with why
                    # (sorting_moves reads it); it never fails in silence. A new approval clears it (approve()).
                    evidence['approved_failed'] = {'reason': str(held)[:300], 'at': _stamp()}
                self._set(row['job_id'], 'held', str(held), evidence)
            except Exception as error:
                # Step 4a: a look-up that cannot finish is tried FAILURE_TRIES times, TRY_SPACING apart, then held. It was
                # tried again every ten minutes without end.
                entry = self.entry(row['job_id'])
                failures = int(((entry or {}).get('record') or {}).get('failures') or 0) + 1
                text = 'Series lookup could not finish: ' + (str(error) or type(error).__name__)
                if failures >= FAILURE_TRIES:
                    evidence = dict(entry['record']) if entry else {}
                    evidence.update(last_attempt=self.clock(), failures=failures)
                    evidence.pop('next_attempt', None)
                    self._set(row['job_id'], 'held', text[:400] + ' (tried %d times; left as it is)' % failures, evidence)
                else:
                    self._defer(row['job_id'], Later(text, self.clock() + TRY_SPACING), found, manifest=manifest, sources=memory, failures=failures)

    def _retry_retained_removals(self):
        """0.31.3 (REMOVAL_RETRY): a write held only because its former file's removal was refused goes back to its last
        step ('cataloged'), once per REMOVAL_RETRY, and the resume below takes it from there exactly as after a restart: the
        catalog names the rewritten file (path, size, SHA-256), that file is the one the write proved (identity, size, every
        byte re-hashed), the former file is the one the write started from (identity, size, one link, every byte
        re-hashed), the folder is the same; then the former file goes through its held handle (on the NAS after those
        checks again, _last_checks) and the approved move follows (_follow_up). Any doubt holds it again with why, both
        files kept; it is not tried again by this version."""
        picked = []
        for row in self._rows('SELECT job_id FROM ' + self.LEDGER + " WHERE state='held'"):
            if self.stop.is_set():
                return  # Senua M1
            entry = self.entry(row['job_id'])
            if not self._removal_retained(entry) or entry['record'].get('removal_retry') == REMOVAL_RETRY:
                continue
            if self._drive_away(entry['record']):
                continue  # Senua M2: not sent back while its drive does not answer; the next pass looks again
            if self._retry_blocked(row['job_id']):
                continue  # Senua m2: one write of a book at a time; the next pass looks again
            picked.append(entry)
        if self.stop.is_set():
            return
        # Senua m3: the books are sent back together, so the run's total is fixed once they are queued (Judy 2). Only 0.31.2's
        # holds are found (_removal_retained: never one this version made), so no later hold joins the run.
        for entry in picked:
            # Senua M3: 0.31.2's 'removal_intended' is not carried. It said "the removal began", so a missing old file read as
            # removed by the app; the resume sets it again right before the removal, and a missing old file is N7.
            record = {key: value for key, value in entry['record'].items() if key not in ('approved_failed', 'next_attempt', 'removal_intended')}
            record['removal_retry'] = REMOVAL_RETRY
            self._set(entry['job_id'], 'cataloged', '', record)

    @staticmethod
    def _removal_retained(entry):
        """Whether this ledger entry is a write 0.31.2 (or older) held at its last step only because its former file's removal
        was refused: held with exactly the text 0.31.2 stored for that (LEGACY_REMOVAL_HOLD with that file's path; Senua m5:
        never the screen's sentences), its removal intended, every recorded proof there, and no mark of a removal this
        version started (removal_version; Senua m3: a hold made now never joins the run)."""
        if not entry or entry['state'] != 'held' or not isinstance(entry.get('record'), dict):
            return False
        record = entry['record']
        if record.get('removal_intended') is not True or 'removal_version' in record or any(record.get(field) in (None, '') for field in RETRY_FIELDS):
            return False
        return entry['reason'] == LEGACY_REMOVAL_HOLD.format(record['old_path'])

    def _clear_leftover_temporaries(self):
        """Sergei 2026-11-25 (0.31.3): the write's own temporary file that 0.31.2 could not remove on the NAS (the hold
        APPLY_HOLD + retained_text(temp)) is removed by the app, once per REMOVAL_RETRY (record 'temp_retry'), after every
        proof of _remove_leftover. Removed: what went is recorded ('temp_removed'); any doubt: it stays with why
        ('temp_kept'). The hold itself stays: the write did not happen, and the rules decide whether it is tried again."""
        for row in self._rows('SELECT job_id FROM ' + self.LEDGER + " WHERE state='held'"):
            if self.stop.is_set():
                return  # Senua M1
            entry = self.entry(row['job_id'])
            temp = self._leftover_temporary(entry)
            if temp is None or entry['record'].get('temp_retry') == REMOVAL_RETRY:
                continue
            try:
                self._may_finish()  # a library scan holds every file change: the next pass
            except Later:
                return
            if self._other_writer(row['job_id']):
                continue  # one writer per file: this book's other write goes first
            if self._drive_away(entry['record']):
                continue  # Senua M2: no mark (and no fresh try used) while the drive does not answer
            record = dict(entry['record'], temp_retry=REMOVAL_RETRY)
            try:
                record['temp_removed'] = dict(self._remove_leftover(row['job_id'], entry, temp), at=_stamp())
            except InterruptedError:
                return  # closing: nothing was removed, the next run starts again
            except Exception as error:
                if self._drive_away(entry['record'], error):
                    continue  # Senua M2: the drive went away during the proofs; nothing is marked, the next pass looks again
                record['temp_kept'] = {'reason': (str(error) or type(error).__name__)[:300], 'at': _stamp()}
                _log('Leftover temporary file kept: ' + record['temp_kept']['reason'] + ' (' + str(temp) + ')')
            # Judy 6: the outcome's own sentence is written in this one _set (never earlier: _leftover_temporary finds these
            # books by the old stored text). Sergei's ruling 4: a write of names is tried once more after a removal.
            state, reason = self._leftover_outcome(entry, record, temp)
            self._set(row['job_id'], state, reason, record)

    def _leftover_outcome(self, entry, record, temp):
        """(state, reason) once a leftover temporary file was handled (record 'temp_removed' or 'temp_kept'), written in that
        same _set (Judy's spec 6 and 7.8; Senua m6). A series write stays held (Sergei's ruling 4 gave a fresh try to the two
        writes of names only): its hold keeps the engine's opening and drops the false "The file was kept."; with the file
        kept, it says where. Its could-not line stays the generic one (NameWrite overrides all of this)."""
        if record.get('temp_kept'):
            return 'held', SERIES_UNCHANGED + TEMP_STILL_LEFT + str(temp)
        return 'held', SERIES_UNCHANGED

    def _other_writer(self, job_id):
        """The other kind of write of this book is open or approved (one writer per file)."""
        return self._names_in_hand(job_id)

    def _leftover_temporary(self, entry):
        """The path of this held entry's own temporary file when its hold is that file's refused removal, else None: the
        record names it, it is TEMP_PREFIX + this job id + '.m4b' in the folder of the book's file, and the hold reads
        exactly what 0.31.2 stored for that (LEGACY_APPLY_HOLDS of this ledger + LEGACY_TEMP_REFUSAL; Senua m5: never the
        screen's sentences)."""
        if not entry or entry['state'] != 'held' or not isinstance(entry.get('record'), dict):
            return None
        try:
            temp, old = ordinary(entry['record']['temp']), ordinary(entry['record']['old_path'])
        except (KeyError, TypeError, BoundaryError):
            return None
        legacy = LEGACY_APPLY_HOLDS.get(self.LEDGER, '') + LEGACY_TEMP_REFUSAL.format(temp)
        if temp != old.parent / (self.TEMP_PREFIX + entry['job_id'] + '.m4b') or entry['reason'] != legacy:
            return None
        return temp

    def _remove_leftover(self, job_id, entry, temp):
        """The proofs before a leftover temporary file goes, in order; each failure keeps it (Held):
          1. the catalog: owned_artifacts names it once, as this job's 'temporary'; no job's output, no other ledger
             record (its temp, new or old path) and no move names it; the job's output still names the book's own file;
          2. the book is whole without it: that file's size and SHA-256 are the catalog's (read through a held handle);
          3. it is this book's audio: its media bytes are the book's, byte for byte (quicktime_chapters.media_unchanged),
             so removing it loses nothing;
          4. unchanged since the app recorded keeping it: its last write is not later than the hold's stamp (no hash of it
             was ever recorded), one link, and the same identity, size and time when reopened for removal;
        then it goes through its held handle with its folder held (remove_owned: on the NAS after its own check again).
        Returns what went: {'path', 'size', 'sha256' (read just before), 'modified', 'method'}; or, when it is already
        gone, {'path', 'found_gone': True} with the rest None (Senua's re-review at 520ee66, m8)."""
        import calendar
        from quicktime_chapters import media_unchanged, ChapterFormatError
        record = entry['record']
        old = ordinary(record['old_path'])
        if self._leftover_gone(record, temp):
            # m8: a crash after remove_owned and before the caller's _set (or after the file went by hand) left the file gone
            # under the old hold. Nothing is there to prove or remove: it counts as removed, known as found gone (this pass
            # removed nothing), and its ownership row goes if it is still there. The write of names keeps its one fresh try.
            self._forget_temporary(job_id, temp)
            return {'path': str(temp), 'size': None, 'sha256': None, 'modified': None, 'method': None, 'found_gone': True}
        with connect(self.database) as db:
            owned = [tuple(r) for r in db.execute('SELECT job_id,kind FROM owned_artifacts WHERE path=? COLLATE NOCASE', (str(temp),))]
            row = db.execute('SELECT output FROM audio_jobs WHERE job_id=?', (job_id,)).fetchone()
            named = db.execute("SELECT count(*) FROM audio_jobs WHERE json_valid(output) AND json_extract(output,'$.final_path')=? COLLATE NOCASE",
                               (str(temp),)).fetchone()[0]
            for table in ('series_backfill', 'name_writes'):
                if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                    named += db.execute('SELECT count(*) FROM ' + table + " WHERE NOT (job_id=? AND ?=?) AND json_valid(record) AND ("
                                        "json_extract(record,'$.temp')=? COLLATE NOCASE OR json_extract(record,'$.new_path')=? COLLATE NOCASE OR "
                                        "json_extract(record,'$.old_path')=? COLLATE NOCASE)", (job_id, table, self.LEDGER, *(str(temp),) * 3)).fetchone()[0]
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='book_moves'").fetchone():
                named += db.execute('SELECT count(*) FROM book_moves WHERE target_path=? COLLATE NOCASE OR temp_path=? COLLATE NOCASE',
                                    (str(temp), str(temp))).fetchone()[0]
        if owned != [(job_id, 'temporary')] or named:
            raise Held(TEMP_NAMED)
        try:
            output = json.loads(row[0]) if row and row[0] else {}
        except (TypeError, ValueError):
            output = {}
        if not isinstance(output, dict) or os.path.normcase(str(output.get('final_path') or '')) != os.path.normcase(str(old)) \
                or not output.get('sha256') or not output.get('size') or temp == old:
            raise Held(TEMP_BOOK_UNNAMED)
        with DirectoryBoundary(old.parent, old.parent), VerifiedFile(old) as book:
            if book.facts()['size'] != output['size'] or book.sha256() != output['sha256']:
                raise Held(TEMP_BOOK_CHANGED)
        held_at = calendar.timegm(time.strptime(entry['updated'], '%Y-%m-%dT%H:%M:%SZ'))
        keys = ('identity', 'size', 'modified')
        with DirectoryBoundary(temp.parent, temp.parent), VerifiedFile(temp) as seen:
            before = seen.facts()
            if before['modified'] > (held_at + 1) * 10 ** 9:
                raise Held(TEMP_WRITTEN_AFTER)
            try:
                media_unchanged(old, temp, self.stop)  # read by name; this read-only handle lets nothing write meanwhile
            except ChapterFormatError as error:
                _log(TEMP_AUDIO_DIFFERS + ' ' + str(error) + ' (' + str(temp) + ')')  # the exact error: the log only (Judy 6)
                raise Held(TEMP_AUDIO_DIFFERS) from None
        with DirectoryBoundary(temp.parent, temp.parent), VerifiedFile(temp, delete=True) as handle:
            now = handle.facts()
            if [now[k] for k in keys] != [before[k] for k in keys]:
                raise Held(TEMP_CHANGED_DURING)
            digest = handle.sha256()
            remove_owned(handle)
        if present(temp):  # Senua M3's pattern: an error is not "gone" (raised; the caller keeps it with why)
            raise Held(TEMP_STILL_THERE)
        self._forget_temporary(job_id, temp)
        title = ''
        try:
            title = str(json.loads(self._rows('SELECT manifest FROM audio_jobs WHERE job_id=?', (job_id,))[0]['manifest'])['metadata'].get('title') or '')
        except (IndexError, KeyError, TypeError, ValueError):
            pass
        _log('Removed a leftover temporary file of an unfinished update: ' + title + ' (' + size_text(now['size']) + '): ' + str(temp))  # Judy 6
        return {'path': str(temp), 'size': now['size'], 'sha256': digest, 'modified': now['modified'], 'method': getattr(handle, 'disposition_method', None)}

    def _leftover_gone(self, record, temp):
        """m8: the leftover temporary file is positively not there (present: only "not found", Windows error 2), or (M5) its
        folder is gone while the drive answers (_absent). An error that cannot be told is not "gone": its proofs run as
        before and decide."""
        try:
            return not present(temp)
        except FileNotFoundError:
            return self._absent(record, temp)
        except OSError:
            return False

    # ------------------------------------------------------------------ checks
    def unsafe(self, row, jobs=None):
        """A permanent reason this book is not changed (recorded as skipped), or ''. Raises Later when it is only not yet."""
        merge = self.merge
        job_id = row['job_id']
        manifest = json.loads(row['manifest'])
        output = json.loads(row['output'])
        if __import__('publication_reuse').task(manifest):return 'Extra-source cleanup does not own the finished audiobook'
        if manifest.get('replacement_id') or manifest.get('replacement_parent_job_id'):
            return 'Part of a replacement; left as it is'
        with connect(self.database) as db:
            def table(name):
                return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
            if table('audiobook_replacements') and db.execute(
                    'SELECT 1 FROM audiobook_replacements WHERE parent_job_id=? OR replacement_job_id=?', (job_id, job_id)).fetchone():
                return 'Part of a replacement; left as it is'
            if table('kept_files') and db.execute('SELECT 1 FROM kept_files WHERE job_id=?', (job_id,)).fetchone():
                return 'Files kept at your choice; left as they are'
        self.settled(job_id)
        from encoding_policy import AUTOMATIC_PROFILE, LEGACY_PROFILE, PROFILE
        if output.get('validation', {}).get('profile') not in {PROFILE, LEGACY_PROFILE, AUTOMATIC_PROFILE}:
            return 'Made by an earlier profile; left as it is'
        publications = getattr(merge, 'publications', None)
        if publications is not None:
            current = publications.publication(jobs if jobs is not None else merge.jobs.status()['jobs'], manifest['candidate_id'])
            if not current or current.get('kind') != 'original' or current.get('id') != job_id:
                return 'Has a chapter update or a newer version; left as it is'
        return ''

    def settled(self, job_id):
        """Returns when everything the conversion left for this finished book has ended: its source cleanup, its recovery
        copies, its working files, its source folders, and the step after its conversion. Raises Later while one of them
        is still to run, Blocked while one is on hold (it waits for Sergei). The series write always asked this (unsafe());
        since 0.31.0 milestone B the rules ask it before any move of a finished book too (rule_filing), so a book whose
        files something else still works on is never renamed or moved under it. A catalog read only."""
        merge = self.merge
        with connect(self.database) as db:
            def table(name):
                return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
            cleanup = db.execute('SELECT state FROM source_cleanup WHERE job_id=?', (job_id,)).fetchone() if table('source_cleanup') else None
            recovery = db.execute('SELECT state FROM recovery_retention WHERE job_id=?', (job_id,)).fetchone() if table('recovery_retention') else None
            storage = db.execute('SELECT state FROM storage_cleanup_jobs WHERE job_id=?', (job_id,)).fetchone() if table('storage_cleanup_jobs') else None
            folders = db.execute('SELECT state FROM source_folder_cleanup_jobs WHERE job_id=?', (job_id,)).fetchone() if table('source_folder_cleanup_jobs') else None
        if cleanup and cleanup[0] != 'completed' or recovery and recovery[0] != 'deleted' or not storage or storage[0] != 'completed' \
                or folders and folders[0] not in ('completed', 'unsupported') or job_id in merge.__dict__.get('_post_jobs', set()):
            # Step 4a: a cleanup on hold waits for Sergei, not for time. Such a book was deferred every ten minutes without
            # end (129 ledger rows on the live copy, one 3,287 times); it is blocked until its cleanup has finished.
            if any(state and state[0] == 'needs_attention' for state in (cleanup, storage, folders)):
                raise Blocked(BLOCKED)
            raise Later('Its cleanup is not finished yet')

    def unsettled(self):
        """0.31.0 milestone B: the job ids of the finished books whose series look-up has not come to an end: not visited
        yet, between tries, blocked by a cleanup on hold, or to be looked up once more (candidates()' own tests). The rules
        file a finished book only when its look-up has ended, so a series found later never moves it a second time (ruling
        R19: a book moves once). A catalog read: no manifest is parsed, nothing is asked."""
        entries = {r['job_id']: r for r in self._rows('SELECT job_id,state,reason,record FROM series_backfill')}
        generation = self._local_generation()
        found = set()
        for job_id in self._look_up_jobs():
            entry = entries.get(job_id)
            if not entry:
                found.add(job_id)
                continue
            state, reason, record = entry['state'], str(entry['reason']), json.loads(entry['record'])
            if state == 'held':
                if (reason == OLD_FOLDER_REASON or reason.startswith(REVIEW_REASON)) and not record.get('approved_failed') or pre_rule(reason, record):
                    found.add(job_id)  # pre_rule(): a series found before 0.31.0 is looked up again first (Senua's review, M3)
            elif state == 'none':
                if not (record.get('lookup_policy') == LOOKUP_POLICY and (generation is None or record.get('local_generation') == generation)):
                    found.add(job_id)
            elif state not in FINAL and state not in ACTIVE and state != 'pending' and not record.get('move_approved'):
                found.add(job_id)  # deferred or blocked; an approved write that waits is work, not a look-up
        return found

    def _look_up_jobs(self):
        """The job ids this look-up takes (candidates()' own tests, read from the catalog with no manifest parsed): the
        newest completed, published job of its book, not an extra-source reuse task, not retained, with a title and an
        author and no series. unsettled() and summary() (R34: a 0.30.x hold on a job it never takes is not "to look up")."""
        import publication_reuse
        from storage_relocation_native import retained_job_ids
        retained = retained_job_ids(self.database)
        rows = self._rows("SELECT job_id,state,output IS NOT NULL AS published,json_extract(manifest,'$.candidate_id') AS candidate,"
                          "json_extract(manifest,'$.metadata.series') AS series,json_extract(manifest,'$.metadata.title') AS title,"
                          "json_extract(manifest,'$.metadata.canonical_author') AS author,json_extract(manifest,'$.task_kind') AS task "
                          "FROM audio_jobs ORDER BY created,job_id")
        newest = {row['candidate']: row['job_id'] for row in rows}
        return {row['job_id'] for row in rows
                if row['state'] == 'completed' and row['published'] and newest.get(row['candidate']) == row['job_id'] and row['task'] != publication_reuse.KIND
                and row['job_id'] not in retained and not row['series'] and row['title'] and row['author']}

    def _cleanup(self, job_id):
        """'held' when one of the book's cleanups is on hold (needs attention), else ''. A catalog read only."""
        with connect(self.database) as db:
            for table in ('source_cleanup', 'storage_cleanup_jobs', 'source_folder_cleanup_jobs'):
                if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() and \
                        db.execute('SELECT 1 FROM %s WHERE job_id=? AND state=?' % table, (job_id, 'needs_attention')).fetchone():
                    return 'held'
        return ''

    @staticmethod
    def _memory(prior):
        """Step 4a: {source: {'answer': 'none', 'tries', 'next', 'gave_up', 'reason'}}, what each source has answered for
        this book and how often it could not be reached. A book deferred SOURCE_TRIES times or more before 0.31.0 kept no
        such record: each source its last deferral named as closed (not the app's own limit) gets one last try."""
        memory = {name: dict(value) for name, value in (prior.get('sources') or {}).items() if name in SOURCES and isinstance(value, dict)}
        if 'sources' not in prior and int(prior.get('deferrals') or 0) >= SOURCE_TRIES:
            for wait in prior.get('waits') or []:
                if not isinstance(wait, dict) or wait.get('kind') == 'app_limit':
                    continue
                for name in HOST_SOURCES.get(wait.get('source'), (wait.get('source'),)):
                    if name in SOURCES:
                        memory[name] = {'tries': SOURCE_TRIES - 1, 'reason': str(wait.get('reason') or '')[:200]}
        return memory

    def lookup(self, manifest, memory=None):
        """The series a source names for this book, or None when every source is settled without one; Later while a source
        can still answer. memory (step 4a, kept in the ledger by the caller): a source that answered is not asked again, the
        app's own limits are no try, and a source that could not be reached is given up after SOURCE_TRIES tries."""
        import series_certainty
        from public_research import CHALLENGE_REASON, ResearchWait, edition_volume
        from public_work_identity import EvidenceConflict
        review = manifest['metadata']
        result = {'sources': []}
        budget = {'remaining': 6, 'lane': 'series'}  # 0.22.1: its own share of each site's hourly bound (public_research.LANES)
        pacing = getattr(self, '_pacing', None)
        if callable(pacing):
            budget['pacing'] = pacing  # 0.31.0: the client says when it only waits for a site's pacing (no running row then)
        memory = {} if memory is None else memory
        waits = []
        now = self.clock()

        def closed(name, wait, limit):
            state = memory.setdefault(name, {})
            retry = wait['retry_at'] if isinstance(wait.get('retry_at'), (int, float)) else now + PASS_WAIT
            if limit:
                # The app's own bound (an hourly site share, or this try's six requests): no try; it goes on from here.
                state['next'] = now + PASS_WAIT if wait.get('scope') == 'candidate' else retry
            else:
                state['tries'] = int(state.get('tries') or 0) + 1
                state['reason'] = str(wait.get('reason') or '')[:200]
                if state['tries'] >= SOURCE_TRIES:
                    state['gave_up'] = True
                    state.pop('next', None)
                else:
                    state['next'] = max(retry, now + TRY_SPACING)
            waits.append(wait)

        for name, provider, args in (('goodreads', '_series_goodreads', (review['title'], review['canonical_author'], self.stop, budget, result)),
                                     ('fantlab', '_series_fantlab', (review['title'], review['canonical_author'], False, self.stop, budget, result)),
                                     ('wikidata', '_series_wikidata', (review['title'], review['canonical_author'], self.stop, budget, result)),
                                     ('publisher', '_series_publisher', (review['title'], review['canonical_author'], self.stop, budget, result)),
                                     ('litres', '_series_litres', (review['title'], review['canonical_author'], self.stop, budget, result))):
            state = memory.get(name) or {}
            if state.get('answer') == 'none' or state.get('gave_up'):
                continue  # settled for this book: never asked again
            if isinstance(state.get('next'), (int, float)) and state['next'] > now:
                continue  # not due yet; the book waits for it (below)
            try:
                found = getattr(self.research, provider)(*args)
                # The one rule: certain, or doubtful and so treated as not found (the source has answered for this book).
                verdict = series_certainty.judge(found, {'volume': edition_volume(review['title'])[1]}) if found else None
                if verdict and verdict['verdict'] == series_certainty.CERTAIN:
                    return dict(verdict['series'], receipts=result['sources'], deferred_sources=waits)
                memory[name] = {'answer': 'none', 'at': now}
                if verdict:
                    memory[name].update(doubt=verdict['why'], dropped=series_certainty.dropped(verdict))
            except ResearchWait as wait:
                if wait.reason == CHALLENGE_REASON and wait.source == HUMAN_CHECK_HOST and name in HOST_SOURCES[HUMAN_CHECK_HOST]:
                    # Ruling R32 (Sergei 2026-11-23): a source that only answers with a human check (the two that go through
                    # DuckDuckGo) counts as "nothing found" at once, never a try: it held "All done" back for 12 hours or more.
                    memory[name] = {'answer': 'none', 'at': now, 'reason': str(wait.reason)[:200]}
                    continue
                closed(name, {'source': wait.source, 'reason': wait.reason, 'retry_at': wait.retry_at, 'kind': wait.kind, 'scope': wait.scope},
                       wait.kind == 'app_limit')
            except EvidenceConflict as error:
                # A source that contradicts itself: doubtful, treated as not found (it held the book for review before).
                memory[name] = {'answer': 'none', 'at': now, 'doubt': 'source_conflict', 'reason': str(error)[:200]}
            except (ValueError, TypeError, KeyError, AttributeError) as error:
                closed(name, {'source': name, 'reason': str(error) or type(error).__name__, 'retry_at': now + TRY_SPACING,
                              'kind': 'unverified_response', 'scope': 'candidate'}, False)
        open_sources = [name for name in SOURCES if not ((memory.get(name) or {}).get('answer') == 'none' or (memory.get(name) or {}).get('gave_up'))]
        if open_sources:
            due = [memory[name]['next'] for name in open_sources if isinstance((memory.get(name) or {}).get('next'), (int, float))]
            raise Later('; '.join(item['source'] + ': ' + item['reason'] for item in waits) or 'Waiting for its next try',
                        min(due) if due else now + PASS_WAIT, waits)
        return None

    def _idle(self):
        """File changes wait for the book queue, a cleanup and a scan; series lookups do not. 0.31.0 milestone B (F13): they
        wait for a Pause of the audiobook jobs too (his, or one saved before this launch), as the rules' moves do."""
        merge = self.merge
        paused = getattr(merge, 'filing_paused', None)
        if callable(paused) and paused():
            raise Later('Audiobook jobs are paused', self.clock() + 60)
        jobs = merge.jobs
        if jobs._thread and jobs._thread.is_alive() or merge.cleanup.thread and merge.cleanup.thread.is_alive() or merge.cleanup.current:
            raise Later('A book is being converted or cleaned up', self.clock() + 60)
        if scanning(merge):
            raise Later(SCAN_WAIT, self.clock() + 60)

    def _may_finish(self):
        """R35 (Sergei 2026-11-23; Senua's 0.31.0 delta 2, M6): a write that has begun (left 'writing', 'written', 'renamed'
        or 'cataloged' by a Quit or a crash) is finished without waiting for a Pause of the audiobook jobs (his, or one saved
        before this launch), a conversion or a cleanup (ruling 27: a begun file change finishes once begun). A Choose
        folder… of the book waits for it (MergeService.rewriting), and must not wait for a Start. A library scan still holds
        it, as it holds every file change; a new write still waits for everything _idle() names."""
        if scanning(self.merge):
            raise Later(SCAN_WAIT, self.clock() + 60)

    def _move_registered(self):
        """R35 (Senua's 0.31.0 delta 2, m13): what tells a write that a still-queued move of its book is being run now: run_move's
        own registration (MergeService._move_registered), never recovery's "every move runs" (a queued move is never run by
        recovery). An engine without it: _move_running, as before."""
        return getattr(self.merge, '_move_registered', None) or getattr(self.merge, '_move_running', None)

    # ------------------------------------------------------------------ the update
    def apply(self, job_id, found):
        """Steps 1-5 for one book; any doubt leaves the published file and records why."""
        from metadata import propose
        self._idle()
        rows = self._rows('SELECT * FROM audio_jobs WHERE job_id=?', (job_id,))
        manifest = json.loads(rows[0]['manifest'])
        output = json.loads(rows[0]['output'])
        review = dict(manifest['metadata'], series=found['name'], number=found['number'])
        # 0.31.0 ruling R27: the names the rules approved with this write (an English title, the author's name in order) go
        # into the file in the same rewrite, so the book is rewritten once. Only an approval by the rules carries them.
        approved = self.entry(job_id)
        given = approved['record'] if approved else {}
        names, reasons = {}, []
        if given.get('move_approved') and given.get('approved_by') == 'rules' and isinstance(given.get('approved_names'), dict):
            import name_write
            names = {field: str(value) for field, value in given['approved_names'].items() if field in name_write.FIELDS and str(value).strip()}
            reasons = [dict(reason) for reason in given.get('approved_name_reasons') or [] if isinstance(reason, dict)]
            review = name_write.renamed(review, names)
        facts = copy.deepcopy(manifest.get('metadata_facts'))
        old = ordinary(output['final_path'])
        # Senua 0.21.3 F5 / ruling 17 (Sergei 2026-10-24, series backfill on in Sorted): a book is named relative to the
        # folder it was published in (the output root), not its source root, or every book in Sorted reads as misnamed.
        root = published_root(manifest, output)
        current = propose('', str(root), 'audiobook', {}, manifest['metadata'], automatic_facts=facts)
        record = {'series': found['name'], 'number': found['number'], 'provider': found['provider'], 'source_url': found['source_url'],
                  'old_path': str(old), 'old_sha256': output['sha256'], 'old_size': output['size'],
                  'research_receipts': found.get('receipts', []), 'deferred_sources': found.get('deferred_sources', []),
                  # number_from: series_certainty judged this series certain (judged(); Senua's 0.31.0 review, M3).
                  'series_proof': {key:copy.deepcopy(found[key]) for key in ('work_id','series_id','statement_id','work_revision','series_revision','references','numbering_scheme','isbn','series_url','local_identity','number_from') if key in found}}
        if names:
            record.update(names=names, was={field: manifest['metadata'].get(field) for field in names}, name_reasons=reasons)
        # His approval travels with the record from the start, so a hold at any step below still says it was approved.
        record.update({key: approved['record'][key] for key in APPROVAL_KEYS
                       if approved and key in approved['record']})
        try:
            if self._names_in_hand(job_id):
                raise Later('This audiobook is being renamed now', self.clock() + 60)  # one writer per file (name_write)
            # Rulings 69 and 71h: a book Sergei moved to a folder he chose lives where its move says, not at its receipt;
            # its file is left as it is (never renamed from a stale path), fail closed.
            import book_move
            with connect(self.database) as db:
                moved = book_move.have(db) and db.execute("SELECT 1 FROM book_moves WHERE job_id=? AND state NOT IN ('failed','cancelled') LIMIT 1", (job_id,)).fetchone()
            if moved:
                raise Held('The audiobook was moved to a folder you chose; left as it is')
            # Audit m4: files change only in the sorted output folder, never inside a source folder (rulings 2 and 1a).
            if hasattr(self.merge, '_require_sorted'):
                try:
                    self.merge._require_sorted(old)
                except ValueError:
                    raise Held('The audiobook is not in the sorted output folder; left as it is') from None
            if not current.get('path') or os.path.normcase(current['path']) != os.path.normcase(str(old)):
                raise Held("The audiobook's name does not follow the app's naming; left as it is")
            if facts:
                facts['series_state'] = 'verified'
            if names and isinstance(facts, dict):
                import name_write
                facts = name_write.facts_named(facts, manifest['metadata'], review, reasons)  # as the list names it (sorting_moves.canonical)
                contradiction = name_write.fits(facts, review)
                if contradiction:
                    raise Held(contradiction)
            target = propose('', str(root), 'audiobook', {}, review, automatic_facts=facts)
            if not target.get('path'):
                raise Held('No name for the series: ' + (target.get('reason') or 'unknown'))
            new = ordinary(target['path'])
            if not new.is_relative_to(root) or new.suffix.lower() != '.m4b' or new == old:
                raise Held('The series name is not a valid audiobook name')
            if new.parent != old.parent:
                # 0.30.0 item 2: its series folder is another folder. Only with Sergei's approval of the listed move: the
                # series is written here under its new name, and the usual verified move takes it to the folder later.
                entry = self.entry(job_id)
                prior = entry['record'] if entry else {}
                if not prior.get('move_approved'):
                    raise Held(MOVE_WAITS)
                planned = getattr(self.merge, 'sorting_target', None)
                if callable(planned) and os.path.normcase(str(planned(job_id, found) or '')) != os.path.normcase(str(prior.get('approved_target'))):
                    raise Held('The planned place changed since you approved it; look at the list again. Nothing was changed')
                record.update({key: prior[key] for key in APPROVAL_KEYS if key in prior})
                record['series_folder'] = str(new.parent)
                new = old.parent / new.name
                if new == old:
                    raise Held('The series name is not a valid audiobook name')
            elif WRITE_WITHOUT_APPROVAL != 'allow':
                # The guard (WRITE_WITHOUT_APPROVAL, top of this file): the name with the series stays in the book's own
                # folder, so 0.16.12 wrote it and renamed the file with no approval. Held instead, with the series found
                # kept in the record; it is listed and approved like a series move (sorting_moves), and only then written.
                entry = self.entry(job_id)
                prior = entry['record'] if entry else {}
                if not prior.get('move_approved'):
                    raise Held(WRITE_WAITS)
                # What he approved is the plan's path (sorting_moves: it may also name his one author folder); as for a
                # series folder, the series is written here and the verified move follows when that is another folder.
                planned = getattr(self.merge, 'sorting_target', None)
                expected = str(planned(job_id, found) or '') if callable(planned) else str(new)
                if os.path.normcase(expected) != os.path.normcase(str(prior.get('approved_target') or '')):
                    raise Held('The planned place changed since you approved it; look at the list again. Nothing was changed')
                record.update({key: prior[key] for key in APPROVAL_KEYS if key in prior})
                if os.path.normcase(os.path.dirname(expected)) != os.path.normcase(str(old.parent)):
                    record['series_folder'] = os.path.dirname(expected)
            temp = old.parent / (TEMP_PREFIX + job_id + '.m4b')
            record.update(new_path=str(new), temp=str(temp), review=review)
            record.update(root=str(root), parent_identity=output['parent_identity'])
            self._give_way(job_id, record, 'The audiobook was moved to a folder you chose; left as it is')
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
            self._set(job_id, 'held', APPLY_HOLD + (str(error) or type(error).__name__), record)
            return
        finally:
            self._clear_stage(job_id)
        self.resume(job_id)

    def _tags(self, was, review, record):
        """The Apple metadata items this write puts into the file: the series items, and (0.31.0 ruling R27) the names the
        rules approved with it, in the one rewrite (name_write.tags). was: the book's review before the write."""
        tags = series_tags(review)
        if record.get('names'):
            import name_write
            tags.update(name_write.tags(was, review))
        return tags

    def _read_back(self, before, after, was, review, record):
        """Step 2's tag proof: the series as a converted book carries it, and the approved names with it (R27)."""
        if record.get('names'):
            import name_write
            self.check_tags(before, after, review, name_write.wanted(was, review))
        else:
            self.check_tags(before, after, review)

    def _names_in_hand(self, job_id):
        """0.31.0 R27: a write of names (name_write) is open or approved for this book: one writer per file."""
        with connect(self.database) as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='name_writes'").fetchone():
                return False
            row = db.execute('SELECT state FROM name_writes WHERE job_id=?', (job_id,)).fetchone()
        return bool(row and (row[0] in ACTIVE or row[0] in ('pending', 'deferred', 'blocked')))

    def _write(self, job_id, manifest, output, old, temp, review, record):
        """Steps 1-2: the new metadata in a new file next to the old one, then the proofs."""
        from quicktime_chapters import retag, media_unchanged, ChapterFormatError
        from audio_pipeline import audio_packet_hash, copied_audio_evidence, probe
        try:
            receipt = retag(old, temp, self.stop, self._tags(manifest['metadata'], review, record))
            if receipt['input_sha256'] != output['sha256'] or receipt['input_size'] != output['size']:
                raise Held('The published audiobook changed since it was verified; left as it is')
            media_unchanged(old, temp, self.stop)
        except ChapterFormatError as error:
            raise Held('The audiobook cannot be retagged safely: ' + str(error)) from None
        stage = self.stage / job_id
        stage.mkdir(parents=True, exist_ok=True)
        duration = float(output.get('validation', {}).get('duration') or 0) or 3600.0
        if audio_packet_hash(old, stage, self.stop, duration) != audio_packet_hash(temp, stage, self.stop, duration):
            raise Held('The audio changed while retagging; left as it is')
        if copied_audio_evidence(old, stage, self.stop, duration, source_relative=True) != copied_audio_evidence(temp, stage, self.stop, duration, source_relative=True):
            raise Held('The audio decoder configuration or timing changed while retagging; left as it is')
        before = probe(old, stage, self.stop)
        after = probe(temp, stage, self.stop)
        self._read_back(before, after, manifest['metadata'], review, record)
        stat = temp.stat()
        record.update(new_sha256=sha256(temp, self.stop), new_size=stat.st_size, new_mtime=stat.st_mtime_ns)
        with VerifiedFile(temp) as written:
            if written.facts()['size'] != record['new_size'] or written.sha256() != record['new_sha256']:
                raise Held('The new file changed during verification; the audiobook is unchanged')
            record['new_identity'] = written.facts()['identity']
        self._set(job_id, 'written', '', record)

    @staticmethod
    def check_tags(before, after, review, names=None):
        """The new file carries the series as a converted book would; everything else read back is unchanged. names (0.31.0
        R27): what the approved names must read back as too, by ffprobe's tag names (name_write.wanted; None: the item must
        be gone)."""
        def tags(raw):
            return {k.lower(): str(v) for k, v in raw.get('format', {}).get('tags', {}).items()}
        old, new = tags(before), tags(after)
        wanted = {'album': album(review), 'grouping': review['series'], 'sort_album': album(review)}
        if str(review.get('number', '')).isdigit() and 0 < int(review['number']) < 65536:
            wanted['track'] = str(int(review['number']))
        wanted.update(names or {})
        for key, value in wanted.items():
            if new.get(key) != value:
                raise Held(('The new names did not read back: ' if key in (names or {}) else 'Series tags did not read back: ') + key)
        if {k: v for k, v in old.items() if k not in wanted} != {k: v for k, v in new.items() if k not in wanted}:
            raise Held('Other metadata changed while retagging; left as it is')
        if before.get('chapters') != after.get('chapters'):
            raise Held('Chapters changed while retagging; left as it is')
        streams = lambda raw: [{k: s.get(k) for k in ('codec_type', 'codec_name', 'disposition', 'duration_ts')} for s in raw.get('streams', [])]
        if streams(before) != streams(after):
            raise Held('Streams changed while retagging; left as it is')

    def resume(self, job_id):
        """Steps 3-5 from the recorded state; safe to repeat after a restart at any point."""
        entry = self.entry(job_id)
        record = entry['record']
        state = entry['state']
        temp, new, old = Path(record['temp']), Path(record['new_path']), Path(record['old_path'])
        if state == 'writing':
            # Stopped while writing: the new file is not proven, so it goes; the published file never changed.
            self._discard_temp(job_id, record)
            self._set(job_id, 'pending', '', record)
            return
        try:
            # Ruling 27: the rename, the catalog record and the former file's removal finish once begun.
            with critical_sections.critical(critical_sections.RENAME), self._boundary(record) as boundary:
                self._resume_protected(job_id, record, state, temp, new, old, boundary)
        except (BoundaryError, OSError, Held, KeyError) as error:
            if not isinstance(error, Held) and self._drive_away(record, error):
                # Senua's 0.31.3 review, M2: the drive went away during the step. Not a hold (one would end a retry for good):
                # the book keeps its recorded state and the step runs again once the drive answers.
                raise Later(DRIVE_AWAY, self.clock() + 60) from None
            if isinstance(error, AncestorUnavailable):
                error = Held(FOLDER_CHANGED)  # Senua's re-review M5: the drive answers and the book's folder is gone (N4)
            # Judy's spec 5.3: a reason of section 5 (Held) is stored as it is, without the engine's prefix; any other error
            # keeps RECOVERY_HOLD (so a removal refused again still reads as _removal_retained expects).
            reason = str(error) if isinstance(error, Held) else RECOVERY_HOLD + str(error)
            self._set(job_id, 'held', reason, record)
            if record.get('removal_retry') == REMOVAL_RETRY:
                _log('Old file kept: ' + str((record.get('review') or {}).get('title') or job_id) + ': ' + reason + ' (' + str(record.get('old_path')) + ')')
            return
        self._follow_up(job_id)  # 0.30.0 item 2: an approved book now moves into its series folder

    @contextmanager
    def _boundary(self, record):
        """Rebind persisted ordinary ancestry; legacy unbound recovery records fail closed."""
        root = ordinary(record['root'])
        old, new, temp = (ordinary(record[key]) for key in ('old_path', 'new_path', 'temp'))
        if old == new or old.parent != new.parent or old.parent != temp.parent or temp in (old, new):
            raise Held(NOT_ONE_FOLDER)  # N5; OLD_FOLDER_REASON keeps finding the holds older versions stored with the old words
        with DirectoryBoundary(root, old.parent) as boundary:
            if [list(item) for item in boundary.identities] != record['parent_identity']:
                raise Held(FOLDER_CHANGED)  # N4
            yield boundary

    @contextmanager
    def _protected(self, path, record, kind, delete=False):
        """Hash the exact held file object, never accepting time/size as a byte proof."""
        with VerifiedFile(path, delete=delete) as handle:
            facts = handle.facts()
            if facts['identity'] != record[kind + '_identity'] or facts['size'] != record[kind + '_size'] \
                    or handle.sha256() != record[kind + '_sha256']:
                raise Held(CHANGED[kind])  # 5.1 rows 2a and 2b
            if delete and facts['links'] != 1:
                raise Held(OTHER_NAME[kind])  # N1
            yield handle

    def _resume_protected(self, job_id, record, state, temp, new, old, boundary):
        if state == 'written':
            if temp.exists() and not new.exists():
                if not self._proven(temp, record):
                    self._discard_temp(job_id, record)
                    self._set(job_id, 'held', 'The new file changed before it was renamed; the audiobook is unchanged', record)
                    return
                try:
                    def same_identity(facts):
                        if facts['identity'] != record['new_identity']:
                            raise Held('The verified temporary identity changed')
                    publish_no_replace(temp, new, boundary, record['new_sha256'], record['new_size'], same_identity)
                except FileExistsError:
                    self._discard_temp(job_id, record)
                    self._set(job_id, 'held', 'A file with the series name already exists: ' + new.name, record)
                    return
                except OSError as error:
                    self._discard_temp(job_id, record)
                    self._set(job_id, 'held', 'The audiobook could not be renamed; it is unchanged: ' + str(error), record)
                    return
            elif temp.exists() and new.exists():
                self._discard_temp(job_id, record)
                self._set(job_id, 'held', 'A file with the series name already exists: ' + new.name, record)
                return
            elif not new.exists():
                self._set(job_id, 'held', 'The new file is gone; the audiobook is unchanged', record)
                return
            if not self._proven(new, record):
                self._set(job_id, 'held', 'The renamed file is not the proven one; check ' + new.name, record)
                return
            self._set(job_id, 'renamed', '', record)
            state = 'renamed'
        if state not in ('renamed', 'cataloged'):
            return
        # Every recovery entry point proves and protects the replacement through
        # catalog commit and exact-handle old-file disposal. No pathname unlink.
        withdrawn = False
        if not self._seen(new):
            # Futaba's 0.31.3 QA, m4: a new file already gone failed at its handle's open and was held as engine speech
            # ("Cannot protect exact file: [WinError 2] ..."). It is Judy's row 3; the old file is not touched. (Can it not
            # be seen at all, _seen waits instead: M3.)
            raise Held(NEW_CHANGED_OR_MISSING)
        with self._protected(new, record, 'new') as kept:
            if state == 'renamed':
                try:
                    self.catalog(job_id, record)
                except sqlite3.Error as error:
                    raise Later('The catalog is busy: ' + str(error)) from None
                except Exception as error:
                    if str(error) != MOVED_MEANWHILE:
                        # Preserve both copies on a catalog refusal: no rollback may
                        # remove the only playable copy if the original changed.
                        self._set(job_id, 'held', 'The catalog could not record the series; copies kept: ' + (str(error) or type(error).__name__), record)
                        return
                    withdrawn = True  # its own copy goes once this handle is closed (_withdraw)
            if not withdrawn:
                if self._seen(old):
                    self._names_rewritten(job_id, record)
                    with self._protected(old, record, 'old', delete=True) as former:
                        if record['old_identity'] == record['new_identity']:
                            raise Held(SAME_FILE)  # N3
                        boundary.revalidate()
                        record['removal_intended'] = True
                        record['removal_version'] = REMOVAL_RETRY  # Senua m3: a removal this version began; never one of 0.31.2's holds
                        self._set(job_id, 'cataloged', '', record)
                        former.dispose(remote_legacy=lambda handle: self._last_checks(handle, record, 'old', boundary, kept, new))
                    if self._seen(old):
                        raise Held(OLD_STILL_THERE)  # N6
                elif not record.get('removal_intended'):
                    raise Held(OLD_MISSING)  # N7
                self._forget_temporary(job_id, temp)
                self._set(job_id, 'done', '', record)
        if withdrawn:
            self._withdraw(job_id, record, new, temp, boundary)

    def _seen(self, path):
        """present(path) for the old file's step. Senua's 0.31.3 review, M3: when it cannot be told (a network error), the step
        waits (Later) and runs again; it never reads as "gone", so an old file is recorded removed only when it is."""
        try:
            return present(path)
        except OSError as error:
            raise Later(DRIVE_AWAY + ' (' + (str(error) or type(error).__name__)[:200] + ')', self.clock() + 60) from None

    def _withdraw(self, job_id, record, new, temp, boundary):
        """0.31.0 ruling R33 (Senua's 0.31.0 delta review, M5): a move of the book began before the write's catalog step (a
        move that did not wait for the write; Choose folder… waits for it, MergeService.rewriting), so the catalog keeps the
        receipt the move started from (_no_move_begun). The write's own proven new file was never named by the catalog: it
        goes, through its held, hash-checked single-link handle in its held folder, never by a pathname delete, so no second
        copy stays in Sorted. If it cannot go, it is kept and said so, as before."""
        try:
            with self._protected(new, record, 'new', delete=True) as handle:
                boundary.revalidate()
                handle.dispose(remote_legacy=lambda held: self._last_checks(held, record, 'new', boundary))
            if present(new):  # Senua M3's pattern: an error is not "gone" (OSError: kept, said with N9)
                raise Held('The new file is still there after removal')
            self._forget_temporary(job_id, temp)
        except (BoundaryError, OSError, Held, KeyError) as error:
            # N9: one whole sentence; why the new file stayed goes to the log only.
            self._set(job_id, 'held', WITHDRAW_KEPT, record)
            _log(WITHDRAW_KEPT + ' ' + (str(error) or type(error).__name__) + ' (' + str(new) + ')')
            return
        self._set(job_id, 'held', WITHDRAWN, record)

    def _names_rewritten(self, job_id, record):
        """0.31.3: the former file goes only while the catalog names the rewritten file, the one kept: its path, size and
        SHA-256, read just before the removal (the retry of a 0.31.2 hold may run days after its catalog step)."""
        rows = self._rows('SELECT output FROM audio_jobs WHERE job_id=?', (job_id,))
        try:
            output = json.loads(rows[0]['output']) if rows and rows[0]['output'] else {}
        except (TypeError, ValueError):
            output = {}
        if not isinstance(output, dict) or os.path.normcase(str(output.get('final_path') or '')) != os.path.normcase(str(ordinary(record['new_path']))) \
                or output.get('sha256') != record['new_sha256'] or output.get('size') != record['new_size']:
            raise Held(CATALOG_MISMATCH)  # 5.1 row 1

    @staticmethod
    def _last_checks(handle, record, kind, boundary, kept=None, kept_path=None):
        """Sergei's 2026-11-16 NAS ruling (VerifiedFile.dispose remote_legacy), as source cleanup's _nas_checks: run right
        before the NAS (pre-0.28) removal method, through the same held handles. The file to go is still the one the write
        proved (identity, size, one link, every byte re-hashed: the held handle stops a writer over SMB, not on the NAS
        itself); the file kept is still there and still the proven one (re-read); the folder is the same. Any failure keeps
        every file."""
        facts = handle.refresh()
        if facts['identity'] != record[kind + '_identity'] or facts['size'] != record[kind + '_size'] or facts['links'] != 1 \
                or facts['attributes'] & (0x400 | 0x10) or handle.sha256() != record[kind + '_sha256']:
            raise Held(CHANGED[kind])  # 5.1 rows 2a and 2b, as _protected says it
        if kept is not None:
            now = kept.refresh()
            # m7: present(), not os.path.lexists (False on any OSError): a network error here is raised and waits, never row 3
            if now['identity'] != record['new_identity'] or now['size'] != record['new_size'] or now['links'] < 1 or not present(kept_path):
                raise Held(NEW_CHANGED_OR_MISSING)  # 5.1 row 3
        boundary.revalidate()

    def _proven(self, path, record):
        """The proven new file: its exact native identity and complete held hash."""
        try:
            with self._protected(path, record, 'new'):
                return True
        except (BoundaryError, OSError, Held, KeyError):
            return False

    def catalog(self, job_id, record):
        """Step 4, one transaction: the book reads as verified at once, at its new path."""
        merge = self.merge
        new = ordinary(record['new_path'])
        with connect(self.database) as db:
            row = db.execute('SELECT * FROM audio_jobs WHERE job_id=?', (job_id,)).fetchone()
            manifest = json.loads(row['manifest'])
            output = json.loads(row['output'])
            if output['final_path'] == str(new) and output['sha256'] == record['new_sha256']:
                db.execute("UPDATE series_backfill SET state='cataloged',updated=? WHERE job_id=?", (_stamp(), job_id))
                return  # recorded before a restart
            if output['final_path'] != record['old_path'] or output['sha256'] != record['old_sha256']:
                raise Held('The book changed meanwhile')
            root = published_root(manifest, output)
            with DirectoryBoundary(root, new.parent) as boundary:
                ancestry = [list(item) for item in boundary.identities]
            review = record['review']
            manifest['metadata'] = dict(manifest['metadata'], series=review['series'], number=review['number'])
            manifest['destination'] = str(new)
            source = {'provider': record['provider'], 'url': record['source_url'], 'backfilled': _stamp(),
                      'evidence': record.get('research_receipts', []), 'deferred_sources': record.get('deferred_sources', [])}
            if isinstance(manifest.get('metadata_facts'), dict):
                manifest['metadata_facts'] = dict(manifest['metadata_facts'], series_state='verified', series_source=source)
            validation = dict(output['validation'], sha256=record['new_sha256'], size=record['new_size'])
            validation['tags'] = dict(validation.get('tags') or {}, album=album(review), grouping=review['series'])
            named = None
            if record.get('names'):
                # 0.31.0 R27: the names written with the series, recorded as name_write records its own (one transaction).
                import name_write
                named = name_write.catalog_names(manifest, validation, record['names'], record.get('name_reasons'))
            text, digest = encoded(manifest)
            updated = dict(output, final_path=str(new), sha256=record['new_sha256'], size=record['new_size'], parent_identity=ancestry, validation=validation)
            journal = row['journal']
            if named:
                import name_write
                journal = name_write.journal_named(row['journal'], updated)
            db.execute('BEGIN IMMEDIATE')
            self._no_move_begun(db, job_id)
            changed = db.execute('UPDATE audio_jobs SET manifest=?,manifest_hash=?,output=?,journal=?,updated=? WHERE job_id=? AND output=?',
                                 (text, digest, json.dumps(updated), journal, _stamp(), job_id, row['output'])).rowcount
            if changed != 1:
                raise Held('The book changed meanwhile')
            identity = merge._identity_key(new, record['new_sha256'])
            stat = os.stat(new)
            db.execute('DELETE FROM verified_outputs WHERE job_id=?', (job_id,))
            db.execute('INSERT OR REPLACE INTO verified_outputs VALUES(?,?,?,?,?)',
                       (*identity, job_id, json.dumps([stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns]), _stamp()))
            db.execute("UPDATE owned_artifacts SET path=?,sha256=?,size=? WHERE job_id=? AND kind='output'",
                       (str(new), record['new_sha256'], record['new_size'], job_id))
            group = db.execute('SELECT review FROM book_groups WHERE id=?', (manifest['candidate_id'],)).fetchone()
            if group and group[0]:
                stored = dict(json.loads(group[0]), series=review['series'], number=review['number'])
                db.execute('UPDATE book_groups SET review=? WHERE id=?', (json.dumps(stored, ensure_ascii=False), manifest['candidate_id']))
            context = db.execute('SELECT revision,data FROM candidate_context WHERE id=?', (manifest['candidate_id'],)).fetchone()
            if context and context[0] == manifest['candidate_revision']:
                data = json.loads(context[1])
                if isinstance(data.get('metadata_facts'), dict):
                    data['metadata_facts'] = dict(data['metadata_facts'], series_state='verified', series_source=source)
                why = 'Series and position added after publication from %s (Sergei 2026-10-18 series backfill).' % record['provider']
                for field, value in (('series', review['series']), ('number', review['number'])):
                    data.setdefault('metadata_evidence', []).append({'field': field, 'cited_value': value, 'source_url': record['source_url'],
                                                                    'retrieved_utc': _stamp(), 'reviewer_actor': 'assistant',
                                                                    'reviewer_identity': 'Books Arranger series backfill', 'basis': why})
                db.execute('UPDATE candidate_context SET data=? WHERE id=? AND revision=?',
                           (json.dumps(data, ensure_ascii=False), manifest['candidate_id'], context[0]))
            if named:
                name_write.catalog_list(db, manifest, *named, record.get('name_reasons'))
            db.execute("UPDATE series_backfill SET state='cataloged',updated=? WHERE job_id=?", (_stamp(), job_id))
        self._verified(job_id, stat)
        if hasattr(merge, 'invalidate_status'):
            merge.invalidate_status()

    def _verified(self, job_id, stat):
        """0.31.0 B1 (Futaba's QA round 2): the rewritten file a catalog step recorded is the book's last full verification
        (the write's proofs hashed every byte; verified_outputs keeps the same identity, which a restart reads). The
        converted check compares the live file with it (MergeService.progress_books). It was dropped, so a rewritten book
        the rules did not move read Pending, out of Audiobook Ready, until a restart."""
        validated = self.merge.__dict__.get('_validated_outputs')
        if isinstance(validated, dict):
            validated[job_id] = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)

    def _no_move_begun(self, db, job_id):
        """Senua's 0.31.0 review, M1 and M2: the one move check of both writes' catalog step (this one and the write of
        names'), asked inside its write transaction before the receipt is replaced. A move of the book that has begun
        (book_move.begun: past 'queued', or queued and being run now, MergeService._move_running) starts its chain from
        the receipt as it is, so the receipt is not changed under it: Held, both copies kept, the catalog still names the
        file the move took. The series write had no such check; the write of names read a queued move as not begun while
        the Mover was already hashing the file."""
        import book_move
        if book_move.begun(db, job_id, self._move_registered()):
            raise Held(MOVED_MEANWHILE)

    def _give_way(self, job_id, record, reason):
        """0.31.0 ruling R33 (Sergei 2026-11-23; Senua's delta review, M4 and M5): the write says it is in hand (ledger
        'writing') before it opens the book's file, then gives way to a move of the book that has begun, or that run_move
        registered before this point (book_move.begun with MergeService._move_running): Held with reason, nothing written.
        From the announcement on, a move of this book waits for the write (MergeService.rewriting: the action queue's blocker,
        and run_move, which asks after it registers), so no move meets the file the write holds ("in use") or runs beside
        it, and the write's follow-up re-points it to the rewritten file (R30). A stop here resumes as 'writing' does."""
        import book_move
        self._set(job_id, 'writing', '', record)
        with connect(self.database) as db:
            if book_move.begun(db, job_id, self._move_registered()):
                raise Held(reason)

    def _clear_stage(self, job_id):
        """The proof tools' own output files for this book (never anything else)."""
        from native_io import DirectoryBoundary,DirectoryDispositionUnsupported,VerifiedFile,VerifiedDirectory
        folder = self.stage / job_id
        try:
            if folder.is_dir():
                from source_cleanup import single_stream
                with DirectoryBoundary(folder.anchor,folder):
                    for item in folder.iterdir():
                        if item.is_file() and item.suffix in ('.stdout', '.stderr'):
                            with VerifiedFile(item,delete=True) as held:
                                single_stream(item);held.dispose()
                # Stream-capable directory providers retain the empty folder
                # for the finite data-cleanup workflow rather than pathname
                # rmdir after releasing a race-sensitive native check.
                with DirectoryBoundary(folder.anchor,folder.parent),VerifiedDirectory(folder,delete=True) as held:
                    held.dispose_empty()
        except DirectoryDispositionUnsupported:
            # A safe hold on the empty work directory is not a failed retag.
            import logging
            logging.getLogger(__name__).info('Retained verified work directory after retag: %s',folder)
        except OSError:
            pass

    # ------------------------------------------------------------------ owned temporary file
    def _own_temporary(self, job_id, temp):
        """The new file is app-owned while it exists, so a library scan never catalogs it."""
        with connect(self.database) as db:
            db.execute('INSERT OR REPLACE INTO owned_artifacts VALUES(?,?,?,?,?)', (str(temp), job_id, 'temporary', '', 0))
        if temp.exists():
            self._dispose_temporary(temp)  # our own unproven file from an interrupted pass

    def _discard_temp(self, job_id, record):
        """The write's own unproven temporary file goes (a failed or stopped write). Senua's 0.31.3 review, M4: a refusal was
        swallowed here, which is how 0.31.2 left two temporary files on the NAS with no word anywhere. Now it is logged, and
        recorded in the record the caller stores next ('temp_left': path, why, when), with its ownership row kept."""
        temp = record.get('temp')
        if not temp:
            return
        try:
            if present(Path(temp)):
                self._dispose_temporary(Path(temp))
            self._forget_temporary(job_id, Path(temp))
        except (OSError, ValueError) as error:
            if isinstance(error, FileNotFoundError) and self._absent(record, temp):
                # Senua's re-review M5: its folder is gone while the drive answers (Windows error 3): nothing is there to keep
                self._forget_temporary(job_id, Path(temp))
                return
            reason = (str(error) or type(error).__name__)[:300]
            record['temp_left'] = {'path': str(temp), 'reason': reason, 'at': _stamp()}
            _log('Temporary file kept: ' + reason + ' (' + str(temp) + ')')

    @staticmethod
    def _dispose_temporary(temp):
        """Audit m4: the app's own temporary file goes through a held handle of that exact single-link file, with its
        folder held, never by a pathname delete."""
        temp = ordinary(temp)
        if not temp.name.startswith(TEMP_PREFIX) or temp.suffix.lower() != '.m4b':
            raise BoundaryError('Not a series-update temporary file; kept')
        with DirectoryBoundary(temp.parent, temp.parent), VerifiedFile(temp, delete=True) as handle:
            remove_owned(handle)
        if present(temp):  # Senua M3's pattern: a network error raises; it is never read as removed
            raise BoundaryError(TEMP_STILL_THERE)  # N8

    def _forget_temporary(self, job_id, temp):
        with connect(self.database) as db:
            db.execute("DELETE FROM owned_artifacts WHERE path=? AND job_id=? AND kind='temporary'", (str(temp), job_id))
