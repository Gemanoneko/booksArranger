"""Durable injected audio queue. This module never opens media or publishes files."""
import errno
import contextlib
import copy
import hashlib
import json
import math
import os
import sqlite3
import time
import threading
import uuid
from datetime import datetime, timezone
from sqlite_retry import transaction
import retry_refusal
import destination_admission


STAGES = {"checking sources", "creating", "checking", "copying", "publishing"}
# Measured progress a running attempt may report, per journal stage: step -> unit. Not journaled.
MEASURED = {"checking sources": {"preparing": "files", "source copies": "bytes", "checking audio": "seconds",
                                 "matching format": "seconds", "normalizing": "seconds", "joined audio": "seconds"},
            "creating": {"encoding": "seconds"}, "copying": {"publishing": "bytes"}}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _epoch_ms():
    return int(time.time() * 1000)


def _failure_details(error, stage, now=None):
    """Classify only a typed pre-publication error; never infer from its message."""
    retryable = isinstance(error, (OSError, TimeoutError)) and not isinstance(error, InterruptedError)
    code = getattr(error, 'sqlite_errorcode', None) if isinstance(error, sqlite3.Error) else None
    if isinstance(error, sqlite3.OperationalError):
        retryable = type(code) is int and code >= 0 and (code & 255) in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)
    details = {'exception_class': type(error).__name__, 'at': time.time() if now is None else now,
               'retryable': retryable, 'stage': stage}
    if isinstance(error, sqlite3.Error):
        details['sqlite_errorcode'] = code
        details['sqlite_errorname'] = getattr(error, 'sqlite_errorname', None)
    if isinstance(error, OSError) and type(error.errno) is int:
        details['errno'] = error.errno  # typed, so a full disk is told apart without reading the message
    if isinstance(error, OSError) and type(getattr(error, 'winerror', None)) is int:
        details['winerror'] = error.winerror  # typed, so a drive or share that went away is told apart (UNREACHABLE)
    if getattr(error, 'tag_repair_checked', False) is True:
        details['tag_repair_checked'] = True  # an MP3 decode failure from a version with the trailing-tag repair
    return details


REVISION_GUARD_REFUSAL = "Source changed — review required"  # the worker's own guard, before any work is published
ANCESTOR_UNAVAILABLE = 'An inspected destination ancestor is unavailable'  # native_io.AncestorUnavailable's text
# Windows errors of a drive or share that went away: the device not ready; a network path, name or network that is gone,
# absent or unreachable; an unexpected network error; a semaphore timeout.
UNREACHABLE = frozenset({21, 51, 53, 59, 64, 67, 121, 1222, 1231})


def source_remedy(row,journal,manifest):
    """Identify the exact source checked by the production full-decode failure.

    Legacy failures are admitted only by the fixed producer prefix, typed stage
    and a single MP3 input; ambiguous multi-input/output failures stay unclassified.
    """
    failure=journal.get('failure',{}) if isinstance(journal,dict) else {}
    sources=manifest.get('sources') if isinstance(manifest,dict) else None
    if failure.get('exception_class')!='ValidationError' or failure.get('stage')!='checking sources' or not str(row.get('reason') or '').startswith('Full audio decode failed: '):return None
    if not isinstance(sources,list) or len(sources)!=1 or not isinstance(sources[0],dict) or not str(sources[0].get('path','')).lower().endswith('.mp3'):return None
    return {'kind':'replace_source','cause':'source_decode_failed','path':sources[0]['path'],'sha256':sources[0].get('sha256'),'original_retained':True}


def tag_repair_retry(row):
    """Iron Inferno (0.21.1): a single-MP3 full-decode failure recorded before the app had the trailing-tag repair.

    Retry (or the automatic pass) admits one separate new job, whose check runs the existing repair. A failure recorded
    since carries tag_repair_checked, and a Retry/Repair/replacement child never qualifies, so it is offered once."""
    try:
        journal, manifest = json.loads(row['journal']), json.loads(row['manifest'])
        if row['state'] != 'needs attention' or row.get('output') or not isinstance(journal, dict) or not isinstance(manifest, dict) or 'publication_intent' in journal:
            return False
        if any(key in manifest for key in ('retry_intent', 'm4b_repair', 'replacement_id', 'replacement_parent_job_id')):
            return False
        return source_remedy(row, journal, manifest) is not None and 'tag_repair_checked' not in journal['failure']
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def failure_cause(row, journal):
    """'busy', 'space', 'source' or 'unreachable' when a recorded pre-publication failure is one a Retry can resolve;
    otherwise None.

    Typed where the record is typed (sqlite_errorcode, errno). Older records carry no code, so two
    exact, fixed shapes are accepted: SQLite's own SQLITE_BUSY text as the whole reason of an untyped
    OperationalError (the v0.16.5 cleanup migration's precedent), and OSError's canonical
    "[Errno 28] " prefix for an untyped OSError.
    """
    failure = journal.get('failure') if isinstance(journal, dict) else None
    if not isinstance(failure, dict):
        return None
    kind, code, number = failure.get('exception_class'), failure.get('sqlite_errorcode'), failure.get('errno')
    if kind == 'OperationalError':
        if type(code) is int and code >= 0 and (code & 255) in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
            return 'busy'
        if code is None and row.get('reason') == 'database is locked':
            return 'busy'
    if kind == 'OSError':
        if number == errno.ENOSPC or number is None and str(row.get('reason') or '').startswith('[Errno 28] '):
            return 'space'
    # The worker's revision guard refused before publication (v0.16.9, "Cabal"): until 0.16.9 a shifted file ID
    # on the library share failed it with identical bytes. A Retry is safe: the worker runs the guard again
    # before any work, so a source whose content really changed stops again with the same reason.
    if kind == 'ValueError' and row.get('reason') == REVISION_GUARD_REFUSAL:
        return 'source'
    # 0.22.1 (Futaba's 0.22.0 QA, O-3): the drive or share of the job's folders went away while it ran, before anything
    # was copied into Sorted (a failure in 'copying' may leave a partial file there, so it stays out). The worker runs
    # every check again on a Retry, which is offered once every folder of the job is reachable (_retry_allowed). Typed
    # (the class, or the Windows error); a record from before the typed class: the exact BoundaryError text.
    if failure.get('stage') not in ('copying', 'publishing'):
        winerror = failure.get('winerror')
        if kind == 'AncestorUnavailable' or winerror in UNREACHABLE or kind == 'BoundaryError' and row.get('reason') == ANCESTOR_UNAVAILABLE:
            return 'unreachable'
        reason = str(row.get('reason') or '')
        if winerror is None and kind in ('OSError', 'FileNotFoundError') and any(reason.startswith('[WinError %d] ' % code) for code in UNREACHABLE):
            return 'unreachable'
    return None


def unreachable(manifest, reach=None):
    """The first folder of this job the app cannot reach now, else None: the folder it publishes into (its output root),
    then each source's folder. Read-only: one directory check each, never a file read. reach: {folder: reachable}, shared
    by the rows of one list, so a drive that is away is asked once."""
    output = manifest.get('output_root', manifest.get('root'))
    if not output and manifest.get('destination'):
        output = os.path.splitdrive(str(manifest['destination']))[0] + os.sep
    folders = [output] + [os.path.dirname(str(s.get('path') or '')) for s in manifest.get('sources') or [] if isinstance(s, dict)]
    reach = {} if reach is None else reach
    for folder in dict.fromkeys(f for f in folders if f):
        if folder not in reach:
            reach[folder] = os.path.isdir(folder)
        if not reach[folder]:
            return folder
    return None


class RetryRefused(ValueError):
    """A Retry request that changed nothing. Its message is shown to the user exactly as written. cause, when given, is
    a typed reason the page picks its words from (Start over, release and Clear working files), never the message."""
    def __init__(self, message, cause=None):
        super().__init__(message)
        self.cause = cause


# Retry copy shown in the app: one fact, then the fix.
RETRY_FILES_PRESENT = 'Working files from an earlier attempt are still present. Retry after they are cleared.'
# The same fact for a refused Repair: the verb follows the refusal's kind (RefusedRetry follow-up, point 3b).
REPAIR_FILES_PRESENT = 'Working files from an earlier attempt are still present. Repair after they are cleared.'
# Retry and Repair clear leftover working files first (decisions A and O10); when that fails nothing is queued.
RETRY_NOT_CLEARED = "Retry was not accepted: the working files weren't cleared. Nothing was queued."
REPAIR_NOT_CLEARED = "Repair was not accepted: the working files weren't cleared. Nothing was queued."
# Clear working files (decision B): refusals by typed cause; the page picks its own words from the cause.
# Ruling 35 (Sergei 2026-10-26): busy and a file held open are no refusals for Sergei: the page keeps the press and sends it
# again (a scan: when it ends; a busy catalog: every few seconds; a file held open: a few times, then the sentence with
# what to do). S10: a file the app can't prove it made says why and where it is.
WORKING_BUSY = "The app is busy, so Clear working files waits and runs when it is free. Nothing was removed yet."
WORKING_NOT_SAFE = "Some working files weren't cleared. The app keeps any file it can't confirm is safe to delete."
# Judy 14.6: {reason} is a plain-language clause, never an engine code; {folder} the full path, selectable in the row.
WORKING_NOT_SAFE_AT = "Some working files weren't cleared: %s. If you don't need this earlier attempt, delete %s in File Explorer; the row then offers Retry."
WORKING_FILE_PROBLEM = ("Some working files weren't cleared: another program, often an antivirus scan, still has a file open. "
                        "Wait a minute or close that program, then press Clear working files again.")
# S9 (ruling 35's refusal texts): an M4B Retry or Repair from an outdated view, each cause in its own words.
RETRY_GATE_UPDATE = "%s was not accepted: the app doesn't support how this M4B is built. Nothing was queued."
RETRY_GATE_REVIEW = "%s was not accepted: the book's review or source files changed. Start over sends it back to automatic processing."
RETRY_GATE_WAIT = '%s was not accepted: working files from an earlier attempt are still present. %s after they are cleared.'
RETRY_GATE_STOPS = "%s was not accepted: working files from an earlier attempt are still present, and the app can't clear them safely. The row says what to do."
RETRY_GATE_REFUSED = "Retry was not accepted: the app's check says this M4B can't be converted as it is. The row shows why."
# An M4B row whose read-only dry run has not finished yet (RefusedRetry follow-up, section 2, state a).
RETRY_CHECKING = 'The app is checking this M4B before offering Retry. The row updates itself.'
# Retry pressed on an outdated view (for example, the job was already queued); the panel updates itself.
RETRY_BOOK_CHANGED = "This book's status changed. Check the updated status above."
RETRY_JOB_CHANGED = RETRY_BOOK_CHANGED
RETRY_REVIEW_CHANGED = "The book's review or source files changed. Review the book again."
RETRY_CLOSING = 'Books Arranger is closing. Retry after it restarts.'
RETRY_SCANNING = 'Scanning is running. Retry when it stops.'
RETRY_QUEUED = 'Queued again by Retry.'
RETRY_SPACE = 'Not enough free disk space yet. Free up space, then retry.'
RETRY_UNREACHABLE = "Can't reach %s. Retry when it's connected again."  # the folder (audio_jobs.unreachable)
# M4B Retry and Repair admit a new child job, and only while no audiobook is being created.
RETRY_WORKER_BUSY = 'Retry can start when the current audiobook finishes.'
REPAIR_WORKER_BUSY = 'Repair can start when the current audiobook finishes.'
REPAIR_SCANNING = 'Scanning is running. Repair when it stops.'
REPAIR_CLOSING = 'Books Arranger is closing. Repair after it restarts.'
RETRY_ALL_RUNNING = 'Retry all is already running.'
RETRY_ALL_NONE = 'No books can be retried right now.'
# Rows Start over set aside (book_restart) are kept, never listed: not a book's current job, not attention, not counted.
CURRENT = 'job_id NOT IN (SELECT job_id FROM audio_job_set_aside)'


# Finished repair checks by (job id, manifest hash, preservation module sha256), filled from the catalog's
# m4b_repair_checks table and by the background checker: a check runs once per job and module, not per launch.
REPAIR_CHECKS = {}
_REPAIR_CHECKS_LOCK = threading.Lock()


def repair_check_key(row):
    """The key a repair check stays valid for; None if the module cannot be read."""
    try:
        import m4b_repair
        return (row['job_id'], row['manifest_hash'], m4b_repair._MODULE_SHA256)
    except Exception:
        return None


def remember_repair_check(key, result):
    with _REPAIR_CHECKS_LOCK:
        if len(REPAIR_CHECKS) >= 4096:
            REPAIR_CHECKS.clear()
        REPAIR_CHECKS[key] = dict(result)


def _m4b_fields(row):
    """(repair field, M4B retry eligibility) of a raw needs-attention row. No I/O; display only, never raises.

    repair: m4b_repair.classify (None, unchecked, or the cached check), or a remembered finished check.
    retry: failed_m4b_retry.eligible, a reason this version can now preserve (its REASONS), re-admitted as
    new, proven work.
    """
    try:
        import failed_m4b_retry
        import m4b_repair
    except Exception:
        return None, False
    try:
        repair = m4b_repair.classify(row)
        if repair == {'state': 'unchecked'}:
            with _REPAIR_CHECKS_LOCK:
                found = REPAIR_CHECKS.get(repair_check_key(row))
            if found:
                repair = dict(found)
    except Exception:
        repair = None
    try:
        retry = bool(failed_m4b_retry.eligible(row))
    except Exception:
        retry = False
    return (repair if isinstance(repair, dict) else None), retry


def _m4b_job(row):
    """A failed, unpublished single-.m4b job (m4b_repair.eligible): only .m4b/.wav leftovers stop its Retry or Repair."""
    try:
        import m4b_repair
        return bool(m4b_repair.eligible(row))
    except Exception:
        return False


def dry_run_refused(repair):
    """The read-only plan() dry run on the source (the repair check, m4b_repair.check) refused it under this build.

    None, unchecked or an unreadable source is not a refusal. The check is keyed by job, manifest and preservation
    module, so a build whose module changed checks the book again by itself.
    """
    return isinstance(repair, dict) and repair.get('state') == 'refused' and repair.get('unavailable') is not True


def files_present(kind):
    """The disabled reason while working files block a Retry or Repair; the verb follows the kind."""
    return REPAIR_FILES_PRESENT if kind == 'repair' else RETRY_FILES_PRESENT


def precheck(repair, failed=None):
    """(state, raw text) of the read-only dry run for an M4B row that Retry covers (RefusedRetry follow-up, section 2).

    'refused': this build's plan() refuses the source. 'unavailable': the check could not open the source, or it
    stopped with an error (failed: its raw text), so it will not finish by itself. 'pending': not finished yet.
    'passed': finished and not refused. A finished result wins over a recorded failure; an unreadable repair field
    reads as unavailable, so no row ever waits as pending for a check that cannot end.
    """
    if isinstance(repair, dict) and repair.get('state') in ('intact', 'refused', 'repairable'):
        if repair.get('state') != 'refused':
            return 'passed', ''
        if repair.get('unavailable') is True:
            return 'unavailable', str(repair.get('reason') or '')
        return 'refused', str(repair.get('reason') or '')
    if failed:
        return 'unavailable', str(failed)
    if isinstance(repair, dict) and repair.get('state') == 'unchecked':
        return 'pending', ''
    return 'unavailable', 'Source check unavailable'


def repair_record(job):
    """The user-approved damage repair a job carries (the Repair button made it), else None.

    job: a status() job. applied is True once the verified output records the patch; until then the
    record is the approved repair. patched: [{kind, padding | removed}]; detail: the technical note.
    """
    try:
        import m4b_repair
        manifest = job.get('manifest')
        binding = manifest.get('m4b_repair') if isinstance(manifest, dict) else None
        if not isinstance(binding, dict) or binding.get('schema') != m4b_repair.SCHEMA:
            return None
        output = job.get('output') if isinstance(job.get('output'), dict) else {}
        validation = output.get('validation') if isinstance(output.get('validation'), dict) else {}
        applied = validation.get('damage_repair') if isinstance(validation.get('damage_repair'), dict) else None
        source = applied or binding
        patched = [{key: item[key] for key in ('kind', 'padding', 'removed', 'frames', 'replaced_ticks', 'timescale') if key in item} for item in source.get('repairs') or [] if isinstance(item, dict)]
        return {'applied': applied is not None, 'patched': patched, 'detail': source.get('note') if isinstance(source.get('note'), str) else ''}
    except Exception:
        return None


class _Any:
    """is_set() over several events: any one stops a cooperative check."""
    def __init__(self, *events):
        self.events = events

    def is_set(self):
        return any(event.is_set() for event in self.events)


class AudioJobs:
    """Single-owner queue; do not instantiate twice for the same database.

    runner must synchronously stop all its owned work before returning/raising.
    Validator must check exact recorded output hash/size and validation contract,
    never adopt a file merely because its name exists. Neither callback may hold
    a database transaction. Queue construction never starts pending work.
    """

    def __init__(self, database, runner, revision_guard, output_validator, historical_retirement=None):
        self.database = str(database)
        self.runner = runner
        self.revision_guard = revision_guard
        self.output_validator = output_validator
        self.historical_retirement=historical_retirement
        self.pending_postprocessing=None
        self.postprocessing=None
        self._lock = threading.RLock()
        self._stop = threading.Event()
        # Desktop Quit: no new book starts; the book in progress is not interrupted.
        self._drain = threading.Event()
        self._thread = None
        self._closed = False
        self.after_completed = None
        self.after_failed = None
        self.before_attempt = None
        self.destination_policy = None # Server-derived effective root/hierarchy snapshot.
        self.attempt_boundary = None # Optional native capability held across admission, runner and closure.
        self._priority_status={'state':'idle','job_id':None,'reason':''}
        self.next_priority = None  # m4b_readmission hook: the job id that runs next, or None
        self.m4b_working_clear = None  # MergeService hook: job id -> True once no prior audio working files remain
        self.repair_check_failed = None  # MergeService hook: job id -> raw text when its check could not finish, else None
        # MergeService hook: (row, audio_only) -> None or the live state of the job's leftover working files.
        self.working_state = None
        self.after_attempt = None
        # Edit names (Judy 0.22.2 section 1.4: after a Save no job starts under the old names). MergeService hooks:
        # names_stamp() -> a value any Save or Forget changes; names_stale(row) -> True when the job was planned under other
        # names than those in force; names_replan(row) -> sets the job aside and sends its book back to research.
        self.names_stamp = None
        self.names_stale = None
        self.names_replan = None
        self._claimed = None  # the job the worker took, from its claim until its attempt ends (a Save refuses it)
        self.on_working_hold = None
        self.on_space_hold = None
        self._progress = {}
        # Startup re-verification of published outputs runs after construction (start_published_check).
        self._verify_stop = threading.Event()
        self._verifier = None
        # Optional routine check output_current(record, stop, pace): unchanged verified file identity, else a
        # full interruptible hash. Without it, routine checks use output_validator (always a full check).
        self.output_current = None
        self.verify_pace = None
        self._resuming = False
        # Books checked of total while a finished-book check runs (after launch, or at Start); None otherwise.
        self._check_progress = None
        with self._db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS audio_jobs (job_id TEXT PRIMARY KEY, manifest TEXT NOT NULL, manifest_hash TEXT NOT NULL, state TEXT NOT NULL, stage TEXT NOT NULL, attempt_id TEXT, journal TEXT NOT NULL, output TEXT, reason TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL)")
            destination_admission.ensure(db)
            db.execute('CREATE TABLE IF NOT EXISTS audio_retry_intents(parent_job_id TEXT PRIMARY KEY,child_job_id TEXT UNIQUE NOT NULL,binding TEXT NOT NULL,created TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS audio_repair_admissions(parent_job_id TEXT PRIMARY KEY,child_job_id TEXT UNIQUE NOT NULL,binding TEXT NOT NULL,created TEXT NOT NULL)')
            # Status reads look jobs up by state and a book's newest job by candidate; both scanned every manifest.
            db.execute('CREATE INDEX IF NOT EXISTS audio_jobs_state ON audio_jobs(state)')
            db.execute("CREATE INDEX IF NOT EXISTS audio_jobs_candidate ON audio_jobs(json_extract(manifest,'$.candidate_id'),created,job_id)")
            # Start over (book_restart): a set-aside job is kept as it is but is no longer its book's current job.
            import book_restart
            db.execute(book_restart.SET_ASIDE)
        self._recover()

    def _db(self):
        db = sqlite3.connect(self.database, timeout=5)
        db.row_factory = sqlite3.Row
        return _Connection(db)

    def _rows(self, query="SELECT * FROM audio_jobs ORDER BY created, job_id", params=()):
        with self._db() as db:
            return [dict(row) for row in db.execute(query, params)]

    def _update(self, job_id, **fields):
        fields["updated"] = _now()
        with self._db() as db:
            db.execute("UPDATE audio_jobs SET " + ",".join(key + "=?" for key in fields) + " WHERE job_id=?", (*fields.values(), job_id))

    def _check_output(self, record, routine=False, stop=None, pace=None):
        self._validate_record(record)
        if routine and self.output_current is not None:
            valid = self.output_current(copy.deepcopy(record), stop, pace)
        else:
            valid = self.output_validator(copy.deepcopy(record))
        if valid is not True:
            raise ValueError("Recorded output is missing, changed, or failed validation")

    def _historical(self, row, stop=None):
        if not self.historical_retirement:
            return False
        if stop is None:
            return self.historical_retirement(copy.deepcopy(row)) is True
        return self.historical_retirement(copy.deepcopy(row), stop=stop) is True

    @staticmethod
    def _validate_record(record):
        if not isinstance(record, dict):
            raise ValueError("Output record must be an object")
        for key in ("job_id", "final_path", "owned_temp", "sha256"):
            if not isinstance(record.get(key), str) or not record[key]:
                raise ValueError("Missing output identity: " + key)
        if len(record["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in record["sha256"].lower()):
            raise ValueError("Invalid output SHA256")
        if type(record.get("size")) is not int or record["size"] <= 0:
            raise ValueError("Invalid output size")
        if not isinstance(record.get("validation"), dict) or record["validation"].get("passed") is not True:
            raise ValueError("Output checks did not pass")

    def _recover(self):
        """Construction settles only rows a crash left running.

        Completed rows are not hashed here: re-reading every published book over
        the library share kept the engine from answering health past the desktop's
        3-minute start window. start_published_check() runs that same check after
        startup, and resume() repeats it before any new work.
        """
        import inplace_m4b
        failure = None
        try:
            inplace_m4b.recover_all(self.database)  # undo interrupted in-place edits before a scan or attempt sees them
            held = inplace_m4b.unresolved(self.database)
        except (ValueError, OSError, sqlite3.Error) as error:
            held = {}; failure = inplace_m4b.ATTENTION + (str(error) or type(error).__name__)
        for row in self._rows("SELECT * FROM audio_jobs WHERE state='running' ORDER BY created, job_id"):
            if row["stage"] == "publishing":
                change = self._settle(row)
                if change:
                    self._update(row["job_id"], **change)
            else:
                self._update(row["job_id"], state="pending", stage="queued", reason="Interrupted book restarts on explicit resume")
                if failure and inplace_m4b.offered(json.loads(row["manifest"])):
                    held[row["job_id"]] = failure  # the journal could not be read or settled: any of these may be edited
        # 0.21.0 F4: an edit recovery could not settle shows on its interrupted book now, not only when Start reaches it.
        # Each such edit keeps its journal, and _work_attempt still refuses its source until it is undone.
        for job_id, reason in held.items():
            with self._db() as db:
                db.execute("UPDATE audio_jobs SET state='needs attention', reason=?, updated=? WHERE job_id=? AND state='pending'", (reason, _now(), job_id))

    def _settle(self, row, routine=False, stop=None, pace=None):
        """Recorded-output check for one completed or publishing row; returns its row change, if any.

        routine=True (startup re-check, Start) uses the cheap identity check when available and treats
        an exact authorized former-output retirement as history. A stop is raised, never a verdict.
        """
        journal = json.loads(row["journal"])
        record = json.loads(row["output"]) if row["output"] else journal.get("publication_intent")
        try:
            self._check_output(record, routine, stop, pace)
            if record["job_id"] != row["job_id"]:
                raise ValueError("Output job identity mismatch")
            if row["state"] != 'completed' or json.loads(row['output'] or '{}') != record:
                return {"state": "completed", "stage": "completed", "output": json.dumps(record), "reason": ""}
            return None
        except InterruptedError:
            raise
        except Exception as exc:
            if routine and row["state"] == "completed" and self._historical(row, stop):
                return None  # Exact authorized former-output retirement; preserve immutable history.
            return {"state": "needs attention", "reason": str(exc) or type(exc).__name__}

    def _apply_unchanged(self, changes):
        """Caller holds the lock. A row changes only if it is still exactly what was checked."""
        for row, change in changes:
            if self._rows("SELECT * FROM audio_jobs WHERE job_id=?", (row["job_id"],)) == [row]:
                self._update(row["job_id"], **change)

    def start_published_check(self):
        """Re-verify every completed row's published output in the background, once, after startup.

        It yields to resume() (which runs the same check itself before any new
        work) and to close(), and changes a row only if that row is still exactly
        what it read. It never starts or touches pending work.
        """
        with self._lock:
            if self._closed or self._verifier is not None or self._verify_stop.is_set():
                return
            self._verifier = threading.Thread(target=self._verify_published, name="BooksArrangerPublishedCheck", daemon=True)
            self._verifier.start()

    def _verify_published(self):
        try:
            rows = self._rows("SELECT * FROM audio_jobs WHERE state='completed' ORDER BY created, job_id")
        except sqlite3.Error:
            return  # resume() still verifies before any new work
        try:
            self._verify_rows(rows)
        finally:
            with self._lock:
                if self._check_progress and self._check_progress['kind'] == 'background':
                    self._check_progress = None

    def _verify_rows(self, rows):
        for index, row in enumerate(rows):
            if self._verify_stop.is_set():
                return
            with self._lock:
                if not self._resuming:
                    started = self._check_progress['started'] if self._check_progress and self._check_progress['kind'] == 'background' else _epoch_ms()
                    self._check_progress = {'kind': 'background', 'completed': index, 'total': len(rows), 'started': started}
            try:
                change = self._settle(row, True, self._verify_stop, self.verify_pace)
                if not change:
                    continue
                with self._lock:
                    if self._verify_stop.is_set():
                        return
                    self._apply_unchanged([(row, change)])
            except InterruptedError:
                return  # resume() or close() took over; nothing is written after a stop.
            except Exception:
                continue  # resume() repeats this exact check before any new work

    def enqueue(self, manifest, *, approval_context=None,replacement_context=None,repair_context=None,retry_context=None):
        """Freeze JSON-safe authoritative server manifest. Never HTTP path input."""
        frozen = json.loads(json.dumps(manifest, ensure_ascii=False, allow_nan=False))
        if not isinstance(frozen, dict):
            raise ValueError("Manifest must be an object")
        for key in ("job_id", "candidate_id"):
            try:
                uuid.UUID(frozen[key])
            except (KeyError, ValueError, TypeError, AttributeError):
                raise ValueError("Manifest requires UUID " + key) from None
        for key in ("candidate_revision", "sources", "metadata", "destination", "profile", "evidence", "cover"):
            if key not in frozen:
                raise ValueError("Missing frozen manifest field: " + key)
        if not isinstance(frozen["sources"], list) or not frozen["sources"]:
            raise ValueError("Manifest requires ordered sources")
        for source in frozen["sources"]:
            if not isinstance(source, dict) or not source.get("sha256") or "fingerprint" not in source:
                raise ValueError("Each source needs approved hash and fingerprint")
            digest_value = source["sha256"]
            if not isinstance(digest_value, str) or len(digest_value) != 64 or any(c not in "0123456789abcdef" for c in digest_value.lower()):
                raise ValueError("Source requires SHA256 identity")
        encoded = json.dumps(frozen, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        import reacquire_sources
        with self._db() as db:reacquire_sources.require_admission(db,frozen['candidate_id'])
        with self._lock:
            if self._closed:
                raise RuntimeError("Queue is closed")
            if retry_context is not None and (approval_context is not None or replacement_context is not None):raise ValueError('Explicit retry cannot replace another approval boundary')
            if repair_context is not None and (approval_context is not None or replacement_context is not None):
                raise ValueError('Repair admission cannot replace another approval boundary')
            existing = self._rows("SELECT * FROM audio_jobs WHERE job_id=?", (frozen["job_id"],))
            if not existing:
                identity = {key: value for key, value in frozen.items() if key != "job_id"}
                existing = [row for row in self._rows() if {key: value for key, value in json.loads(row["manifest"]).items() if key != "job_id"} == identity]
                if existing:
                    frozen["job_id"] = existing[0]["job_id"]
                    digest = existing[0]["manifest_hash"]
            if existing:
                if retry_context is not None:raise ValueError('Explicit retry already has bound work')
                if repair_context is not None:raise ValueError('Repair UUID is already bound; inspect its relation instead')
                if replacement_context is not None:raise ValueError('Replacement UUID is already bound; inspect its relation instead')
                if approval_context is not None:raise ValueError("Automatic candidate already has a bound job")
                if existing[0]["manifest_hash"] != digest:
                    raise ValueError("Job UUID already binds a different manifest")
                if existing[0]["state"] == "completed":
                    try:
                        self._check_output(json.loads(existing[0]["output"]))
                    except Exception as exc:
                        self._update(frozen["job_id"], state="needs attention", reason=str(exc))
                return frozen["job_id"]
            timestamp = _now()
            with self._db() as db:
                if not db.in_transaction:db.execute('BEGIN IMMEDIATE')
                reacquire_sources.require_admission(db,frozen['candidate_id'])
                if retry_context is not None:
                    parent,group,context=retry_context[:3]
                    expected_destination=retry_context[3] if len(retry_context)>3 else None
                    if not db.in_transaction:db.execute('BEGIN IMMEDIATE')
                    if expected_destination and (not self.destination_policy or destination_admission.current(db,parent,self.destination_policy())!=expected_destination):raise ValueError(destination_admission.STALE)
                    actual=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(parent['job_id'],)).fetchone()
                    if not actual or dict(actual)!=parent or parent['state']!='needs attention' or parent['output'] or 'publication_intent' in json.loads(parent['journal']):raise ValueError('Failed retry parent changed')
                    latest=db.execute("SELECT job_id FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id')=? AND "+CURRENT+" ORDER BY created DESC,job_id DESC LIMIT 1",(frozen['candidate_id'],)).fetchone()
                    if not latest or latest[0]!=parent['job_id']:raise ValueError('Retry candidate has newer work')
                    current_group=db.execute('SELECT revision,fingerprint FROM book_groups WHERE id=?',(frozen['candidate_id'],)).fetchone()
                    current_context=db.execute('SELECT revision,data FROM candidate_context WHERE id=?',(frozen['candidate_id'],)).fetchone()
                    if not current_group or tuple(current_group)!=group or not current_context or tuple(current_context)!=context:raise ValueError('Approved retry evidence changed')
                    binding=frozen.get('retry_intent')
                    if not isinstance(binding,dict) or binding.get('parent_job_id')!=parent['job_id'] or binding.get('parent_manifest_hash')!=parent['manifest_hash']:raise ValueError('Explicit retry parent binding missing')
                    db.execute('INSERT INTO audio_retry_intents VALUES(?,?,?,?)',(parent['job_id'],frozen['job_id'],json.dumps(binding,sort_keys=True),timestamp))
                if repair_context is not None:
                    parent,group,context=repair_context
                    if not db.in_transaction:db.execute('BEGIN IMMEDIATE')
                    actual=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(parent['job_id'],)).fetchone()
                    if not actual or dict(actual)!=parent or parent['state']!='needs attention' or parent['output'] or 'publication_intent' in json.loads(parent['journal']):
                        raise ValueError('Failed parent changed; repair admission cancelled')
                    latest=db.execute("SELECT job_id FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id')=? AND "+CURRENT+" ORDER BY created DESC,job_id DESC LIMIT 1",(frozen['candidate_id'],)).fetchone()
                    if not latest or latest[0]!=parent['job_id']:raise ValueError('Candidate already has newer work')
                    current_group=db.execute('SELECT revision,fingerprint FROM book_groups WHERE id=?',(frozen['candidate_id'],)).fetchone()
                    current_context=db.execute('SELECT revision,data FROM candidate_context WHERE id=?',(frozen['candidate_id'],)).fetchone()
                    if not current_group or tuple(current_group)!=group or not current_context or tuple(current_context)!=context:
                        raise ValueError('Reviewed candidate changed during repair admission')
                    binding=frozen.get('m4b_repair')
                    if not isinstance(binding,dict) or binding.get('parent_job_id')!=parent['job_id'] or binding.get('parent_manifest_hash')!=parent['manifest_hash']:
                        raise ValueError('Repair manifest does not bind its failed parent')
                    db.execute('INSERT INTO audio_repair_admissions VALUES(?,?,?,?)',(parent['job_id'],frozen['job_id'],json.dumps(binding,sort_keys=True),timestamp))
                if replacement_context is not None:
                    if approval_context is not None:raise ValueError('Replacement and automatic approval cannot be combined')
                    store,binding=replacement_context
                    if not db.in_transaction:db.execute('BEGIN IMMEDIATE')
                    store.admission(db,frozen,binding)
                if approval_context is not None:
                    # Only the private automatic caller provides this exact checked context.
                    id,revision,expected,approved=approval_context
                    if id!=frozen['candidate_id'] or revision!=frozen['candidate_revision']:raise ValueError('Automatic context identity changed')
                    if not expected.get('automatic_pending') or not expected.get('metadata_approved'):raise ValueError('Automatic approval checkpoint missing')
                    delta=dict(expected);delta.pop('automatic_pending',None);delta['automatic_approval']=approved.get('automatic_approval')
                    if delta!=approved or not isinstance(delta['automatic_approval'],dict):raise ValueError('Unexpected automatic approval mutation')
                    if not db.in_transaction:db.execute('BEGIN IMMEDIATE')
                    group=db.execute('SELECT revision FROM book_groups WHERE id=?',(id,)).fetchone()
                    context=db.execute('SELECT revision,data FROM candidate_context WHERE id=?',(id,)).fetchone()
                    if not group or not context or group[0]!=revision or context[0]!=revision or json.loads(context[1])!=expected:raise ValueError('Automatic approval checkpoint changed')
                    db.execute('UPDATE candidate_context SET data=? WHERE id=? AND revision=?',(json.dumps(approved,ensure_ascii=False,allow_nan=False),id,revision))
                db.execute("INSERT INTO audio_jobs VALUES (?,?,?,?,?,?,?,?,?,?,?)", (frozen["job_id"], encoded, digest, "pending", "queued", None, "{}", None, "", timestamp, timestamp))
            return frozen["job_id"]

    def _step_started(self, job_id, attempt, phase):
        """Caller holds the lock. When this step began: kept while the same step reports again."""
        prior = self._progress.get(job_id) or {}
        if prior.get('attempt_id') == attempt and prior.get('phase') == phase and type(prior.get('started')) is int:
            return prior['started']
        return _epoch_ms()

    def _archive_attempt(self, row, now=None):
        if not row.get('attempt_id'):
            return
        values=(row['job_id'],row['attempt_id'],row['journal'],time.time() if now is None else now)
        def append(db):
            db.execute('CREATE TABLE IF NOT EXISTS audio_failure_history(job_id TEXT,attempt_id TEXT,record TEXT,at REAL,PRIMARY KEY(job_id,attempt_id))')
            prior=db.execute('SELECT record FROM audio_failure_history WHERE job_id=? AND attempt_id=?',values[:2]).fetchone()
            if prior:
                if prior['record']!=row['journal']:raise ValueError('Prior attempt history changed; preserved')
                return
            db.execute('INSERT INTO audio_failure_history VALUES(?,?,?,?)',values)
        transaction(self.database,append)

    def retry_failed(self,job_id,now=None):
        """Retry only a classified pre-publication I/O failure on its exact frozen manifest."""
        now=time.time() if now is None else now
        with self._lock:
            if self._closed:raise RuntimeError('Queue is closed')
            row=next(iter(self._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,))),None)
            if not row or row['state']!='needs attention':return {'retryable':False,'reason':'No failed job'}
            journal=json.loads(row['journal']);failure=journal.get('failure',{})
            if row.get('output') or journal.get('publication_intent') or failure.get('retryable') is not True:
                return {'retryable':False,'reason':'Published or unclassified failure retained for evidence'}
            retry_at=float(failure['at'])+3600
            if now<retry_at:return {'retryable':True,'retry_at':retry_at,'requeued':False}
            if self._thread and self._thread.is_alive():return {'retryable':True,'retry_at':now+300,'requeued':False}
            manifest=json.loads(row['manifest'])
            if self.revision_guard(copy.deepcopy(manifest)) is not True:return {'retryable':False,'reason':'Frozen source/review changed; failed job preserved'}
            self._archive_attempt(row,now)
            self._update(job_id,state='pending',stage='queued',reason='Retrying verified pre-publication I/O failure; prior attempt retained')
            return {'retryable':True,'retry_at':now+3600,'requeued':True}

    @staticmethod
    def _newest_jobs(db, candidates=None):
        """{candidate id: newest job id}, in one pass (E6 for many rows at once); candidates limits it to those
        books through the candidate index instead of reading every manifest."""
        newest = {}
        if candidates is None:
            found = db.execute("SELECT job_id, json_extract(manifest,'$.candidate_id') FROM audio_jobs WHERE " + CURRENT + " ORDER BY created, job_id")
        else:
            found = db.execute("SELECT job_id, json_extract(manifest,'$.candidate_id') FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id') IN (SELECT value FROM json_each(?)) AND " + CURRENT + " ORDER BY created, job_id",
                               (json.dumps(sorted(str(c) for c in candidates if c is not None)),))
        for job_id, candidate in found:
            newest[candidate] = job_id
        return newest

    def _retry_shape(self, db, row, latest=None):
        """The frozen manifest when this row was refused before any attempt started (Retry rules E1-E7), else None.

        Only the admission hold in _work writes 'needs attention' with no output, no publication
        intent and no recorded failure; every runtime failure records one. Structural, never the
        reason text. Runtime failures stay with retry_failed and the M4B repair.
        """
        if row['state'] != 'needs attention' or row['output'] is not None:
            return None  # E1, E2
        try:
            journal = json.loads(row['journal']); manifest = json.loads(row['manifest'])
        except (TypeError, ValueError):
            return None
        if not isinstance(journal, dict) or not isinstance(manifest, dict):
            return None
        # E2, E3: nothing published; and either refused before any attempt (no failure), or a failure a
        # Retry can resolve (a busy catalog, or a full disk). Every other runtime failure stays out.
        if 'publication_intent' in journal or 'failure' in journal and failure_cause(row, journal) is None:
            return None
        if hashlib.sha256(row['manifest'].encode('utf-8')).hexdigest() != row['manifest_hash'] or manifest.get('job_id') != row['job_id']:
            return None  # E4
        # E5: no replacement and no Retry/Repair child, except (v0.16.10) a child whose only failure was the
        # revision guard: until 0.16.10 that guard refused every child for its job-only m4b_repair field. It
        # requeues as itself, keeping the repair it was admitted with; a parent with a child never does.
        child = bool(manifest.get('m4b_repair'))
        if manifest.get('replacement_id') or child and failure_cause(row, journal) != 'source':
            return None  # E5
        if db.execute('SELECT 1 FROM audio_repair_admissions WHERE parent_job_id=?' + ('' if child else ' OR child_job_id=?'),
                      (row['job_id'],) if child else (row['job_id'], row['job_id'])).fetchone():
            return None  # E5
        newest = latest.get(manifest.get('candidate_id')) if latest is not None else (lambda found: found[0] if found else None)(db.execute(
            "SELECT job_id FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id')=? AND " + CURRENT + " ORDER BY created DESC, job_id DESC LIMIT 1", (manifest.get('candidate_id'),)).fetchone())
        if newest != row['job_id']:
            return None  # E6
        if row['attempt_id'] and db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='audio_failure_history'").fetchone():
            prior = db.execute('SELECT record FROM audio_failure_history WHERE job_id=? AND attempt_id=?', (row['job_id'], row['attempt_id'])).fetchone()
            if prior is not None and prior[0] != row['journal']:
                return None  # E7: the worker's archive step would refuse and hold the queue again
        return manifest

    def _retry_allowed(self, row, cause, manifest, admission_clear, space_ready, reach=None):
        """E8: the cause is clear now. Read-only; returns (allowed, reason). reach: one list's folder checks (unreachable)."""
        try:
            admission_clear(copy.deepcopy(row))
        except Exception:
            return False, RETRY_FILES_PRESENT
        if cause == 'space' and (space_ready is None or space_ready(manifest) is not True):
            return False, RETRY_SPACE
        away = unreachable(manifest, reach) if cause == 'unreachable' else None
        if away:
            return False, RETRY_UNREACHABLE % away
        return True, ''

    def _m4b_working_clear(self, job_id):
        """Read-only: the listing that refused a Retry/Repair on working files now passes. False without the hook."""
        check = self.m4b_working_clear
        try:
            return bool(check and check(job_id) is True)
        except Exception:
            return False

    def _working(self, row, audio_only):
        """Read-only: the job's leftover working files (Follow-up 2, section 2), or None. Never raises."""
        hook = self.working_state
        try:
            return hook(row, audio_only) if hook else None
        except Exception:
            return None

    def _check_failed(self, job_id):
        """Read-only: the raw text of a repair check that could not finish for this job, else None."""
        hook = self.repair_check_failed
        try:
            found = hook(job_id) if hook else None
        except Exception:
            return None
        return str(found) if found else None

    def attention_summary(self, admission_clear=None, space_ready=None, job_ids=None, retry=True):
        """{job_id: {'group', 'cause', 'originals_untouched', 'retry'}} for every job that needs attention.

        group: 'repair' (a single M4B whose damage m4b_repair proved repairable; Repair, never Retry),
        'retry' (refused before starting, a busy catalog or a full disk, or an M4B failure this version
        can preserve: Retry can resolve it), 'unsupported' (an M4B the app cannot preserve: a validation
        refusal of a single M4B/M4A source), or 'other'. Structural, never the English reason. Only each
        book's newest job is listed: a superseded failure (say, the parent of a retry child) is history.
        A current refused Retry/Repair record (m4b_readmission, typed by retry_refusal) moves the row to
        'unsupported' (cause unsupported_file) or 'other', and its fix alone decides the offer: none for
        'update' and 'review', a live working-file check for 'wait', always for 'user'.
        retry=False skips the read-only E8 checks (counts on every poll); with retry=True, 'retry' or
        'repair' holds {'allowed', 'reason'}. 'repair_check': the M4B repair check has not run yet.
        An M4B row Retry covers (failed_m4b_retry.eligible) and with no current refusal carries 'precheck', the state of
        its read-only dry run (precheck()): 'pending' is group 'checking' with Retry disabled; 'unavailable' is group
        'other' with Retry enabled and the check's raw text in 'precheck_reason'; 'passed' stays in 'retry'.
        """
        query = "SELECT * FROM audio_jobs WHERE state='needs attention'" + (" AND job_id IN (%s)" % ','.join('?' * len(job_ids)) if job_ids else "") + " ORDER BY created, job_id"
        if job_ids is not None and not job_ids:
            return {}
        with self._db() as db:
            rows = [dict(r) for r in db.execute(query, tuple(job_ids or ()))]
            wanted = set()
            for row in rows:
                try:
                    wanted.add(json.loads(row['manifest']).get('candidate_id'))
                except (TypeError, ValueError, AttributeError):
                    pass
            latest = self._newest_jobs(db, wanted) if rows else {}
            cleaned = {r[0] for r in db.execute("SELECT job_id FROM source_cleanup")} if rows and db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_cleanup'").fetchone() else set()
            shapes = {row['job_id']: self._retry_shape(db, row, latest) for row in rows}
            import m4b_readmission
            readmission = m4b_readmission.status(db, [row['job_id'] for row in rows]) if rows else {}
            import reacquire_sources
            reacquire={row['job_id']:reacquire_sources.project(db,row['job_id']) for row in rows}
        summary, reach = {}, {}
        worker = bool(self._thread and self._thread.is_alive())
        for row in rows:
            try:
                journal = json.loads(row['journal']); manifest = json.loads(row['manifest'])
            except (TypeError, ValueError):
                journal, manifest = {}, {}
            if latest.get(manifest.get('candidate_id') if isinstance(manifest, dict) else None) != row['job_id']:
                continue  # superseded by newer work for the same book
            repair, m4b_retry = _m4b_fields(row)
            sources = manifest.get('sources') if isinstance(manifest, dict) else None
            single_m4b = isinstance(sources, list) and len(sources) == 1 and str(sources[0].get('path', '')).lower().endswith(('.m4b', '.m4a'))
            cause = failure_cause(row, journal) if isinstance(journal, dict) and 'failure' in journal else 'files'
            failure = journal.get('failure') if isinstance(journal, dict) else None
            binding = manifest.get('m4b_repair') if isinstance(manifest, dict) else None
            repair_child = shapes[row['job_id']] is not None and isinstance(binding, dict) and binding.get('user_requested') is True
            check, check_reason = None, ''
            if repair and repair.get('state') == 'repairable':
                group, cause = 'repair', None
            elif repair_child:
                group, cause, repair = 'repair', None, {'repairs': binding.get('repairs') or []}  # Repair again, as itself
            elif shapes[row['job_id']] is not None:
                group = 'retry'
            elif m4b_retry:
                # "Ready to retry" is a promise that Retry will be accepted: a source this build's read-only plan()
                # refuses is an M4B the app cannot convert now (RefusedRetry spec O1, Sergei-approved pre-check). Until
                # the check finishes the row is Checking; a check that cannot finish is Other (follow-up, section 2).
                check, check_reason = precheck(repair, self._check_failed(row['job_id']))
                group, cause = {'refused': 'unsupported', 'unavailable': 'other', 'pending': 'checking'}.get(check, 'retry'), None
            elif single_m4b and isinstance(failure, dict) and failure.get('exception_class') == 'ValidationError':
                group, cause = 'unsupported', None
            elif tag_repair_retry(row):
                group, cause = 'retry', None  # accepted now through the separate-job route, like an M4B Retry
            else:
                group, cause = 'other', None
            # A refused M4B Retry/Repair (RefusedRetry spec): while its record is current, the row leaves Can retry
            # and Can repair, and only its fix decides what it offers. A stale record (the deciding code changed) is
            # ignored here, so the book is offered again; the next refusal stores a new record.
            refusal = readmission.get(row['job_id'])
            # A working-files refusal no longer decides the row: the live state of the files does (Follow-up 2, section
            # 2.2); its record stays for the Technical detail line only.
            refusal = refusal if isinstance(refusal, dict) and refusal.get('state') == 'refused' and refusal.get('stale') is not True and refusal.get('cause') != 'working_files' else None
            if refusal:
                group, cause, check = retry_refusal.group(refusal), None, None  # precedence: a current refusal first
            value = {'group': group, 'cause': cause, 'originals_untouched': row['output'] is None and row['job_id'] not in cleaned}
            remedy=source_remedy(row,journal,manifest)
            if remedy and tag_repair_retry(row):remedy=dict(remedy,kind='tag_repair',cause='legacy_decode_failed')
            if remedy and value['originals_untouched']:value['remedy']=remedy
            if check in ('pending', 'unavailable', 'passed'):
                value['precheck'] = check
                if check == 'unavailable':
                    value['precheck_reason'] = check_reason
            if refusal:
                if retry and refusal.get('fix') == 'user':
                    value['repair' if refusal.get('kind') == 'repair' else 'retry'] = {'allowed': True, 'reason': ''}
                if repair and repair.get('state') == 'unchecked':
                    value['repair_check'] = True
            elif group == 'repair':
                value['damage'] = [{key: item[key] for key in ('kind', 'padding', 'removed', 'frames', 'replaced_ticks', 'timescale', 'description') if key in item}
                                   for item in repair.get('repairs') or [] if isinstance(item, dict)]
                if retry:
                    value['repair'] = {'allowed': True, 'reason': ''}  # accepted now, runs right after the current book
            elif repair and repair.get('state') == 'unchecked':
                value['repair_check'] = True
            if refusal:
                pass  # its fix decided the offer above: none for 'update' and 'review'
            elif retry and check == 'pending':
                value['retry'] = {'allowed': False, 'reason': RETRY_CHECKING}  # clears by itself once the check ends
            elif retry and check == 'unavailable':
                value['retry'] = {'allowed': True, 'reason': ''}  # Sergei can fix it; a press does the real read
            elif retry and group == 'retry' and shapes[row['job_id']] is None:
                value['retry'] = {'allowed': True, 'reason': ''}  # M4B: accepted now, runs right after the current book
            elif retry and group == 'retry' and admission_clear is not None:
                allowed, reason = self._retry_allowed(row, cause, shapes[row['job_id']], admission_clear, space_ready, reach)
                value['retry'] = {'allowed': allowed, 'reason': reason}
            # Leftover working files (Follow-up 2, section 2): cleanable rows keep their natural state and Retry/Repair
            # clear the files first; blocked files stop a row that would otherwise offer Retry or Repair (group Other, no
            # control), unless a current refusal of another cause decides the row.
            working = self._working(row, True) if _m4b_job(row) else self._working(row, False) if shapes[row['job_id']] is not None else None
            if working:
                value['working'] = working
                if working['state'] == 'blocked' and not refusal and (group in ('retry', 'repair', 'checking') or check == 'unavailable'):
                    value['group'] = 'other'
                    working['stops'] = True
                    value.pop('retry', None)
                    value.pop('repair', None)
                elif working['state'] == 'cleanable':
                    for key in ('retry', 'repair'):
                        offer = value.get(key)
                        if isinstance(offer, dict) and offer.get('reason') in (RETRY_FILES_PRESENT, REPAIR_FILES_PRESENT):
                            value[key] = {'allowed': True, 'reason': ''}
            if self.destination_policy:
                try:
                    with self._db() as destination_db:destination=destination_admission.current(destination_db,row,self.destination_policy())
                except (ValueError,sqlite3.Error,KeyError,TypeError):
                    destination=None
                    with self._db() as destination_db:stale=destination_db.execute('SELECT 1 FROM audio_destination_holds WHERE job_id=?',(row['job_id'],)).fetchone()
                    if stale:
                        value['destination_review']={'schema':destination_admission.SCHEMA,'state':'stale','can_retry':False,'reason':destination_admission.STALE};value.pop('retry',None)
                if destination:
                    destination['can_retry']=bool(shapes[row['job_id']] is not None and value.get('retry',{}).get('allowed') is True and row['attempt_id'] is None)
                    value['destination_review']=destination
            if row['job_id'] in readmission:value['readmission'] = readmission[row['job_id']]  # queued_next + position, or a refusal reason
            if readmission.get(row['job_id'],{}).get('state')=='queued':
                value={'group':'checking','cause':None,'originals_untouched':value.get('originals_untouched',False),'readmission':readmission[row['job_id']],'retry_wait':True}

            if reacquire.get(row['job_id']):
                value={'group':'reacquire','cause':None,'originals_untouched':True,'reacquire':reacquire[row['job_id']]}
            summary[row['job_id']] = value
        return summary

    def retry_statuses(self, admission_clear, job_id=None, space_ready=None):
        """{job_id: {'allowed', 'reason'}} for jobs a Retry can resolve; absent means hidden.

        One catalog read, then read-only E8 checks per such job (a folder listing, and a free-space
        check for a full-disk failure). It never runs the revision guard and never reads media.
        """
        summary = self.attention_summary(admission_clear, space_ready, [job_id] if job_id else None)
        return {key: value['retry'] for key, value in summary.items() if 'retry' in value}

    def retry_admission_hold(self, job_id, candidate_id, revision, admission_clear, space_ready=None, review=True):
        """Retry: requeue the same job, refused before any attempt started, once that refusal has cleared.

        Rules E1-E10, then a compare-and-set on the whole row as read. The frozen manifest, job id,
        attempt id and journal are kept, so the worker's own admission runs again and archives the
        old journal before a new attempt. The revision guard re-reads the book's sources, so it runs
        outside the queue lock (Pause and the running book stay responsive); the compare-and-set
        refuses if anything changed meanwhile. Otherwise raises RetryRefused with nothing changed.
        """
        def refuse_if_closing():
            if self._closed or self._drain.is_set():
                raise RetryRefused(RETRY_CLOSING)
        with self._lock:
            refuse_if_closing()
            rows = self._rows('SELECT * FROM audio_jobs WHERE job_id=?', (job_id,))
            if not rows:
                raise RetryRefused(RETRY_BOOK_CHANGED)
            row = rows[0]
            with self._db() as db:
                import reacquire_sources
                reacquire_sources.require_admission(db,candidate_id)
                manifest = self._retry_shape(db, row)  # E1-E7
                cause = failure_cause(row, json.loads(row['journal'])) if manifest is not None and 'failure' in json.loads(row['journal']) else 'files'
                group = None
                if manifest is not None and db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='book_groups'").fetchone():
                    group = db.execute('SELECT revision FROM book_groups WHERE id=?', (candidate_id,)).fetchone()
            # E9: the book and revision on screen are this job's, and still current.
            if manifest is None or manifest.get('candidate_id') != candidate_id or manifest.get('candidate_revision') != revision or group is None or group[0] != revision:
                raise RetryRefused(RETRY_BOOK_CHANGED)
        allowed, reason = self._retry_allowed(row, cause, manifest, admission_clear, space_ready)  # E8, re-checked now
        if not allowed:
            raise RetryRefused(reason)
        # E10 re-reads the book's sources. review=False (a press, v0.16.8) leaves it to the worker's own
        # admission, which runs it again before any work; the press answers at once.
        try:
            current = not review or self.revision_guard(copy.deepcopy(manifest)) is True  # E10
        except Exception:
            current = False
        if not current:
            raise RetryRefused(RETRY_REVIEW_CHANGED)
        with self._lock:
            refuse_if_closing()
            with self._db() as db:
                db.execute('BEGIN IMMEDIATE')
                reacquire_sources.require_admission(db,candidate_id)
                changed = db.execute(
                    "UPDATE audio_jobs SET state='pending', stage='queued', reason=?, updated=? WHERE job_id=? AND state='needs attention' AND output IS NULL"
                    " AND attempt_id IS ? AND journal=? AND manifest=? AND manifest_hash=? AND reason=? AND stage=? AND updated=?",
                    (RETRY_QUEUED, _now(), job_id, row['attempt_id'], row['journal'], row['manifest'], row['manifest_hash'], row['reason'], row['stage'], row['updated'])).rowcount
            if changed != 1:
                raise RetryRefused(RETRY_JOB_CHANGED)
        return {'job_id': job_id, 'requeued': True}

    def resume(self,admission_check=None,admission_token=None,settle=True):
        """Check published outputs, then start under the original queue lock.

        A guarded stale start cannot undo a completed Pause. No Merge lock is acquired
        by admission_check, and published-output hashing remains outside the queue lock.
        settle=False (a book an approval just queued, 0.22.1): starts the worker without the published-output check of
        every finished book (Start runs it; so does the background published check) and answers no full status.
        """
        def permitted():
            if admission_check is not None and admission_check() is not True:
                raise StartRefused('stale','Pause or closing stopped this start. Press Resume audiobook jobs to start again.')
        def answer(kind):
            value=self.status() if settle else {}
            if admission_check is not None:value['start_admission']={'state':kind,'generation':admission_token}
            return value
        with self._lock:
            if self._closed or self._drain.is_set():raise StartRefused('closing','The audiobook queue is closing; saved requests are retained.')
            permitted()
            self._verify_stop.set()
            if self._thread and self._thread.is_alive():
                if admission_check is not None and self._stop.is_set():raise StartRefused('busy','The previous audiobook worker is still pausing. Retry Start after it stops.')
                return answer('running')
            if self._resuming:
                if admission_check is not None and getattr(self,'_resuming_token',None)!=admission_token:
                    raise StartRefused('busy','A previous start is still reaching its pause checkpoint. Retry Start after it stops.')
                return answer('checking')
            self._resuming=True;self._resuming_token=admission_token
            self._stop.clear()
            stop=_Any(self._stop,self._drain)
        try:
            changes=[]
            try:
                rows=self._rows("SELECT * FROM audio_jobs WHERE state='completed' ORDER BY created, job_id") if settle else []
                for index,row in enumerate(rows):
                    permitted()
                    if stop.is_set():
                        if admission_check is not None:raise StartRefused('stale','Audiobook startup was paused; saved requests are retained.')
                        return answer('paused')
                    with self._lock:
                        started=self._check_progress['started'] if self._check_progress and self._check_progress['kind']=='start' else _epoch_ms()
                        self._check_progress={'kind':'start','completed':index,'total':len(rows),'started':started}
                    change=self._settle(row,True,stop)
                    if change:changes.append((row,change))
            except InterruptedError:
                permitted()
                if admission_check is not None:raise StartRefused('stale','Audiobook startup was interrupted; saved requests are retained.')
                return answer('paused')
            with self._lock:
                permitted()
                if self._closed or self._drain.is_set():raise StartRefused('closing','The audiobook queue is closing; saved requests are retained.')
                if stop.is_set():
                    if admission_check is not None:raise StartRefused('stale','Audiobook startup was paused; saved requests are retained.')
                    return answer('paused')
                if self._thread and self._thread.is_alive():return answer('running')
                self._apply_unchanged(changes)
                self._thread=threading.Thread(target=self._work,name='BooksArrangerAudioJobs',daemon=False)
                self._thread.start()
        finally:
            with self._lock:
                self._resuming=False;self._resuming_token=None;self._check_progress=None
        return answer('started')

    def pause(self):
        with self._lock:
            self._stop.set()
        return self.status()

    def drain(self):
        """Let the current book (and its cleanup) finish, then stop before the next one."""
        with self._lock:
            self._drain.set()
        return self.status()

    def close(self, timeout=30):
        with self._lock:
            self._closed = True
            self._stop.set()
            self._verify_stop.set()
            worker = self._thread
            verifier = self._verifier
        if worker and worker is not threading.current_thread():
            worker.join(timeout)
            if worker.is_alive():
                raise TimeoutError("Owned runner has not stopped; queue is still pausing")
        if verifier and verifier is not threading.current_thread():
            # Read-only until its locked stop check, so a file still being hashed never writes after this.
            verifier.join(min(timeout, 5))

    def status(self):
        import m4b_readmission
        with self._db() as db:waiting_requests=m4b_readmission.pending_count(db)
        rows = self._rows("SELECT * FROM audio_jobs WHERE " + CURRENT + " ORDER BY created, job_id")
        counts = {"queued": 0, "completed": 0, "failed": 0}
        current = None
        for row in rows:
            if row["state"] == "pending": counts["queued"] += 1
            elif row["state"] == "completed": counts["completed"] += 1
            elif row["state"] == "needs attention": counts["failed"] += 1
            elif row["state"] == "running": current = row
        running = bool(self._thread and self._thread.is_alive())
        state = "Pausing" if running and self._stop.is_set() else "Running" if running else "Paused" if counts["queued"] else "Needs attention" if counts["failed"] else "Completed"
        with self._lock:
            check = copy.deepcopy(self._check_progress)
        if not running and not counts['queued'] and waiting_requests:state='Waiting for retry checks'
        return {"retry_checks":{"waiting":waiting_requests,"worker":copy.deepcopy(self._priority_status)},"state": state, **counts, "published_check": check, "current_stage": current["stage"] if current else None, "current_job_id": current["job_id"] if current else None, "jobs": [{"job_id": row["job_id"], "state": row["state"], "stage": row["stage"], "attempt_id": row["attempt_id"], "reason": row["reason"], "manifest": json.loads(row["manifest"]), "output": json.loads(row["output"]) if row["output"] else None,"progress":copy.deepcopy(self._progress.get(row["job_id"]))} for row in rows]}

    def report_priority(self,value):
        with self._lock:self._priority_status=dict(value)

    def has_unfinished(self):
        """Same answer as scanning status()['jobs'] for pending/running rows, without loading every manifest."""
        with self._db() as db:
            import m4b_readmission
            return db.execute("SELECT 1 FROM audio_jobs WHERE state IN ('pending','running') LIMIT 1").fetchone() is not None or m4b_readmission.pending_count(db)>0

    def _work(self):
        # Resume only explicitly paused durable postprocessing; never loop unclassified failures.
        if self.pending_postprocessing and self.postprocessing:
            for job_id in self.pending_postprocessing():
                if self._stop.is_set() or self._drain.is_set():return
                try:self.postprocessing(job_id)
                except InterruptedError:return
                except Exception:pass # The postprocessor retains original/secondary failure evidence.
        while not self._stop.is_set() and not self._drain.is_set():
            # Retry/Repair clicks run right after the current book, in click order (m4b_readmission).
            try:priority = self.next_priority() if self.next_priority else None
            except Exception as error:
                self.report_priority({'state':'blocked','job_id':None,'reason':str(error) or type(error).__name__})
                priority = None # Durable requests are kept; expose the actual failed admission.
            pending = (self._rows("SELECT * FROM audio_jobs WHERE job_id=? AND state='pending'", (priority,)) if priority else []) or self._rows("SELECT * FROM audio_jobs WHERE state='pending' ORDER BY created, job_id LIMIT 1")
            if not pending: return
            row = pending[0]
            claim = self._claim(row)
            if claim == 'gone':continue  # taken out meanwhile (a Save set it aside)
            if claim == 'stale':
                self._replan(row)
                continue
            try:
                boundary=self.attempt_boundary(copy.deepcopy(row)) if self.attempt_boundary else contextlib.nullcontext()
                with boundary:proceed=self._work_attempt(row)
            except destination_admission.DestinationReviewNeeded as error:
                if not self._hold_destination(row,error.observation):
                    self._stop.set();return
                if self._stop.is_set() or self._drain.is_set():return
                continue
            except Exception as error:
                self._update(row['job_id'],state='needs attention',reason='Working cleanup requires attention: '+str(error))
                self._stop.set()
                if self.on_working_hold:self.on_working_hold()
                return
            finally:
                with self._lock:
                    if self._claimed == row['job_id']:self._claimed = None
            if proceed is False:return

    NAMES_CHANGED = 'Names changed since this job was queued. Press Retry to queue it with these names.'

    def _claim(self, row):
        """The worker takes a pending job: 'claimed', 'gone' (no longer pending, or set aside) or 'stale' (planned under other
        names than Sergei's saved ones). The names check reads outside the lock; the stamp, read again under it, proves no
        Save or Forget came between (a Save writes under this lock, so it either sees the claim or the claim sees it)."""
        for _ in range(5):
            stamp = None
            stale = False
            if self.names_stale:
                try:
                    stamp = self.names_stamp()
                    stale = bool(self.names_stale(copy.deepcopy(row)))
                except Exception:
                    stamp, stale = None, False  # an unreadable store never stops the queue; the job runs as planned
            with self._lock:
                current = self._rows('SELECT state FROM audio_jobs WHERE job_id=? AND ' + CURRENT, (row['job_id'],))
                if not current or current[0]['state'] != 'pending':
                    return 'gone'
                if stamp is not None:
                    try:
                        if self.names_stamp() != stamp:
                            continue
                    except Exception:
                        pass
                if stale:
                    return 'stale'
                self._claimed = row['job_id']
                return 'claimed'
        return 'gone'

    def claimed(self, job_id):
        with self._lock:
            return self._claimed == job_id

    def _replan(self, row):
        """A job planned under other names never starts: it is set aside and its book researched again with the names in
        force (names_replan). If that cannot be done now the job stops with NAMES_CHANGED (nothing ran; Retry checks
        again)."""
        try:
            self.names_replan(copy.deepcopy(row))
        except Exception:
            with self._lock, self._db() as db:
                db.execute("UPDATE audio_jobs SET state='needs attention',reason=?,updated=? WHERE job_id=? AND state='pending'", (self.NAMES_CHANGED, _now(), row['job_id']))

    def _hold_destination(self,expected,observation):
        """Atomic admission refusal: immutable queue intent and journal stay exact."""
        if self._closed or self._stop.is_set() or self._drain.is_set() or not self.destination_policy:return False
        target=None;binding=None
        try:
            with self._lock,self._db() as db:
                db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE')
                actual=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(expected['job_id'],)).fetchone()
                if actual is None or dict(actual)!=expected or expected['state']!='pending' or expected['attempt_id'] is not None or expected['output'] is not None:return False
                manifest=json.loads(expected['manifest']);journal=json.loads(expected['journal'])
                if not isinstance(journal,dict) or 'publication_intent' in journal or destination_admission.digest(manifest)!=expected['manifest_hash']:return False
                if destination_admission.observe(manifest,self.destination_policy())!=observation:return False
                latest=db.execute("SELECT job_id FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id')=? AND "+CURRENT+" ORDER BY created DESC,job_id DESC LIMIT 1",(manifest['candidate_id'],)).fetchone()
                group=db.execute('SELECT revision,review,superseded FROM book_groups WHERE id=?',(manifest['candidate_id'],)).fetchone()
                context=db.execute('SELECT revision FROM candidate_context WHERE id=?',(manifest['candidate_id'],)).fetchone()
                if latest is None or latest[0]!=expected['job_id'] or group is None or group['superseded'] or group['revision']!=manifest['candidate_revision'] or json.loads(group['review'])!=manifest['metadata'] or context is None or context['revision']!=group['revision']:return False
                if self._closed or self._stop.is_set() or self._drain.is_set() or destination_admission.observe(manifest,self.destination_policy())!=observation:return False
                target=dict(expected,state='needs attention',reason=destination_admission.REASON,updated=_now())
                binding={'observation':observation,'pending_row_sha256':destination_admission.digest(expected),'held_row':target}
                changed=db.execute("UPDATE audio_jobs SET state=?,reason=?,updated=? WHERE job_id=? AND state='pending'",(target['state'],target['reason'],target['updated'],expected['job_id']))
                if changed.rowcount!=1:raise ValueError('Queued destination hold CAS failed')
                db.execute('INSERT OR REPLACE INTO audio_destination_holds VALUES(?,?,?,?)',(expected['job_id'],expected['manifest_hash'],destination_admission.packed(binding),_now()))
                if self._closed or self._stop.is_set() or self._drain.is_set() or destination_admission.observe(manifest,self.destination_policy())!=observation:raise ValueError('Pause or destination policy changed before hold commit')
                db.commit()
            with self._db() as db:
                actual=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(expected['job_id'],)).fetchone()
                saved=db.execute('SELECT binding FROM audio_destination_holds WHERE job_id=?',(expected['job_id'],)).fetchone()
                return actual is not None and dict(actual)==target and saved is not None and json.loads(saved[0])==binding
        except (ValueError,sqlite3.Error,OSError):return False # Unknown commit is not an acknowledged hold.

    def _work_attempt(self,row):
        """Exactly one prior work-loop body, inside its retained admission capability."""
        job_id = row["job_id"]
        manifest = json.loads(row["manifest"])
        try:
            import inplace_m4b
            inplace_m4b.clear(self.database, manifest)
        except Exception as error:
            self._update(job_id, state='needs attention', reason=str(error) or type(error).__name__)
            return True  # this source stays journaled; other books continue
        try:
            import reacquire_sources
            with self._db() as db:reacquire_sources.require_admission(db,manifest['candidate_id'])
            if self.before_attempt:self.before_attempt(copy.deepcopy(row))
            self._archive_attempt(row)
        except Exception as error:
            self._update(job_id,state='needs attention',reason='Working cleanup requires attention: '+str(error))
            self._stop.set()
            if self.on_working_hold:self.on_working_hold()
            return False # No new attempt or source copy exists before admission.
        attempt = str(uuid.uuid4())
        journal = {"attempt_id": attempt, "history": []}
        with self._lock: self._progress[job_id] = {"attempt_id":attempt,"phase":"checking sources","started":_epoch_ms()}
        self._update(job_id, state="running", stage="checking sources", attempt_id=attempt, journal=json.dumps(journal), reason="")
        def checkpoint(stage, details=None):
            if stage == "checking_sources": stage = "checking sources"
            if stage not in STAGES:
                raise ValueError("Unsupported job stage: " + str(stage))
            if isinstance(details,dict) and 'progress' in details:
                measured=details['progress'];units=MEASURED.get(stage,{})
                if not isinstance(measured,dict) or measured.get('phase') not in units or measured.get('unit',units.get(measured.get('phase')))!=units[measured['phase']]:
                    raise ValueError('Unsupported progress measurement')
                done,total=measured.get('completed'),measured.get('total')
                if type(done) not in (int,float) or type(total) not in (int,float) or not math.isfinite(done) or not math.isfinite(total) or total<=0 or not 0<=done<=total:
                    raise ValueError('Invalid progress denominator')
                if ('item' in measured or 'items' in measured) and not (type(measured.get('item')) is int and type(measured.get('items')) is int and 1<=measured['item']<=measured['items']):
                    raise ValueError('Invalid progress item')
                if 'fraction' in measured and not (type(measured['fraction']) in (int,float) and math.isfinite(measured['fraction']) and 0<=measured['fraction']<=1):
                    raise ValueError('Invalid progress fraction')
                measured={key:measured[key] for key in ('phase','completed','total','unit','item','items','fraction') if key in measured}
                measured['unit']=units[measured['phase']]
                # Never wait for the queue lock: it can be held across catalog I/O (busy timeout), and an
                # FFmpeg drain thread blocked here fails the attempt. A dropped progress tick is harmless.
                if not self._lock.acquire(blocking=False):return
                try:self._progress[job_id]={'attempt_id':attempt,**measured,'started':self._step_started(job_id,attempt,measured['phase'])}
                finally:self._lock.release()
                return
            with self._lock:self._progress[job_id]={'attempt_id':attempt,'phase':stage,'started':self._step_started(job_id,attempt,stage)}
            entry = {"stage": stage, "at": _now(), "details": details}
            if stage == "publishing":
                if self._stop.is_set(): raise InterruptedError("Paused before publication")
                if self.revision_guard(copy.deepcopy(manifest)) is not True:
                    raise ValueError(REVISION_GUARD_REFUSAL)
                self._validate_record(details)
                if details["job_id"] != job_id: raise ValueError("Publication job identity mismatch")
                journal["publication_intent"] = copy.deepcopy(details)
            journal["history"].append(entry)
            self._update(job_id, stage=stage, journal=json.dumps(journal, ensure_ascii=False))
        damage_assessment=None
        attempt_closed=False
        import source_proofs
        proofs=contextlib.ExitStack();proofs.enter_context(source_proofs.attempt(attempt))  # one full source hash per attempt
        try:
            try:
                if self.revision_guard(copy.deepcopy(manifest)) is not True:
                    raise ValueError(REVISION_GUARD_REFUSAL)
                if self._stop.is_set(): raise InterruptedError("Paused before starting book")
                runner_manifest = copy.deepcopy(manifest)
                runner_manifest["attempt_id"] = attempt
                record = self.runner(runner_manifest, self._stop, checkpoint)
                intent = journal.get("publication_intent")
                if intent is None or record != intent:
                    raise ValueError("Runner completion does not match durable publication intent")
                self._check_output(record)
                self._update(job_id, state="completed", stage="completed", output=json.dumps(record), reason="")
            except Exception as exc:
                damage_assessment=getattr(exc,'source_damage_analysis',None)
                # A publication boundary cannot be blindly reset to pending.
                if journal.get("publication_intent"):
                    try:
                        record = journal["publication_intent"]
                        self._check_output(record)
                        self._update(job_id, state="completed", stage="completed", output=json.dumps(record), reason="")
                    except Exception as validation_exc:
                        self._update(job_id, state="needs attention", reason=str(validation_exc) or type(validation_exc).__name__)
                elif isinstance(exc, InterruptedError) and self._stop.is_set():
                    self._update(job_id, state="pending", stage="queued", reason="Interrupted book restarts on explicit resume")
                else:
                    failure_stage = journal['history'][-1]['stage'] if journal['history'] else 'checking sources'
                    journal['failure'] = _failure_details(exc, failure_stage)
                    self._update(job_id,state='needs attention',journal=json.dumps(journal),reason=str(exc) or type(exc).__name__)
                    if isinstance(exc,OSError) and exc.errno==errno.ENOSPC:
                        self._stop.set()
                        if self.on_space_hold:self.on_space_hold()
                        return False # Preserve the rest of the queue without producing more attempts.
        finally:
            proofs.close()  # fingerprints never outlive the attempt (cleanup proofs always hash in full)
            if self.after_attempt:
                try:
                    self.after_attempt(job_id,attempt)
                    attempt_closed=True
                except Exception as cleanup_error:
                    self._stop.set()
                    latest=self._rows('SELECT state,reason FROM audio_jobs WHERE job_id=?',(job_id,))
                    if latest and latest[0]['state'] in {'pending','needs attention'}:
                        self._update(job_id,reason=(latest[0]['reason']+'; ' if latest[0]['reason'] else '')+'Working cleanup requires attention: '+str(cleanup_error))
                    if self.on_working_hold:self.on_working_hold()
        if damage_assessment is not None and attempt_closed and self.after_failed:
            try:self.after_failed(job_id,attempt,damage_assessment)
            except (ValueError,OSError):pass # No marker without exact supported assessment and closure.
        if self.after_completed and self._rows('SELECT state FROM audio_jobs WHERE job_id=?',(job_id,))[0]['state']=='completed':
            try:self.after_completed(job_id)
            except InterruptedError:return False
            except Exception:pass # Durable postprocessing diagnostics preserve the completed audio row.

        return True


class _Connection:
    def __init__(self, connection): self.connection = connection
    def __enter__(self): return self.connection
    def __exit__(self, kind, value, traceback):
        try:
            if kind is None: self.connection.commit()
            else: self.connection.rollback()
        finally:
            self.connection.close()

class StartRefused(RetryRefused):
    """A saved request remains saved; this particular queue start was not admitted."""
    def __init__(self,state,message):
        super().__init__(message);self.start_state=state

