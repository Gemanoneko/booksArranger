"""Durable injected audio queue. This module never opens media or publishes files."""
import errno
import copy
import hashlib
import json
import math
import sqlite3
import time
import threading
import uuid
from datetime import datetime, timezone
from sqlite_retry import transaction


STAGES = {"checking sources", "creating", "checking", "copying", "publishing"}


def _now():
    return datetime.now(timezone.utc).isoformat()


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
    return details


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
        self.before_attempt = None
        self.after_attempt = None
        self.on_working_hold = None
        self.on_space_hold = None
        self._progress = {}
        with self._db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS audio_jobs (job_id TEXT PRIMARY KEY, manifest TEXT NOT NULL, manifest_hash TEXT NOT NULL, state TEXT NOT NULL, stage TEXT NOT NULL, attempt_id TEXT, journal TEXT NOT NULL, output TEXT, reason TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL)")
            db.execute('CREATE TABLE IF NOT EXISTS audio_repair_admissions(parent_job_id TEXT PRIMARY KEY,child_job_id TEXT UNIQUE NOT NULL,binding TEXT NOT NULL,created TEXT NOT NULL)')
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

    def _check_output(self, record):
        self._validate_record(record)
        if self.output_validator(copy.deepcopy(record)) is not True:
            raise ValueError("Recorded output is missing, changed, or failed validation")

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
        for row in self._rows():
            state = row["state"]
            if state == "completed" or (state == "running" and row["stage"] == "publishing"):
                if state=='completed' and self.historical_retirement and self.historical_retirement(copy.deepcopy(row)) is True:
                    continue # Exact authorized former-output retirement; preserve immutable history.
                journal = json.loads(row["journal"])
                record = json.loads(row["output"]) if row["output"] else journal.get("publication_intent")
                try:
                    self._check_output(record)
                    if record["job_id"] != row["job_id"]:
                        raise ValueError("Output job identity mismatch")
                    if state!='completed' or json.loads(row['output'] or '{}')!=record:
                        self._update(row["job_id"], state="completed", stage="completed", output=json.dumps(record), reason="")
                except Exception as exc:
                    self._update(row["job_id"], state="needs attention", reason=str(exc) or type(exc).__name__)
            elif state == "running":
                self._update(row["job_id"], state="pending", stage="queued", reason="Interrupted book restarts on explicit resume")

    def enqueue(self, manifest, *, approval_context=None,replacement_context=None,repair_context=None):
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
        with self._lock:
            if self._closed:
                raise RuntimeError("Queue is closed")
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
                if repair_context is not None:
                    parent,group,context=repair_context
                    db.execute('BEGIN IMMEDIATE')
                    actual=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(parent['job_id'],)).fetchone()
                    if not actual or dict(actual)!=parent or parent['state']!='needs attention' or parent['output'] or 'publication_intent' in json.loads(parent['journal']):
                        raise ValueError('Failed parent changed; repair admission cancelled')
                    latest=db.execute("SELECT job_id FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id')=? ORDER BY created DESC,job_id DESC LIMIT 1",(frozen['candidate_id'],)).fetchone()
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
                    db.execute('BEGIN IMMEDIATE')
                    store.admission(db,frozen,binding)
                if approval_context is not None:
                    # Only the private automatic caller provides this exact checked context.
                    id,revision,expected,approved=approval_context
                    if id!=frozen['candidate_id'] or revision!=frozen['candidate_revision']:raise ValueError('Automatic context identity changed')
                    if not expected.get('automatic_pending') or not expected.get('metadata_approved'):raise ValueError('Automatic approval checkpoint missing')
                    delta=dict(expected);delta.pop('automatic_pending',None);delta['automatic_approval']=approved.get('automatic_approval')
                    if delta!=approved or not isinstance(delta['automatic_approval'],dict):raise ValueError('Unexpected automatic approval mutation')
                    db.execute('BEGIN IMMEDIATE')
                    group=db.execute('SELECT revision FROM book_groups WHERE id=?',(id,)).fetchone()
                    context=db.execute('SELECT revision,data FROM candidate_context WHERE id=?',(id,)).fetchone()
                    if not group or not context or group[0]!=revision or context[0]!=revision or json.loads(context[1])!=expected:raise ValueError('Automatic approval checkpoint changed')
                    db.execute('UPDATE candidate_context SET data=? WHERE id=? AND revision=?',(json.dumps(approved,ensure_ascii=False,allow_nan=False),id,revision))
                db.execute("INSERT INTO audio_jobs VALUES (?,?,?,?,?,?,?,?,?,?,?)", (frozen["job_id"], encoded, digest, "pending", "queued", None, "{}", None, "", timestamp, timestamp))
            return frozen["job_id"]

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

    def resume(self):
        with self._lock:
            if self._closed:
                raise RuntimeError("Queue is closed")
            if self._thread and self._thread.is_alive():
                return self.status()
            for row in self._rows("SELECT * FROM audio_jobs WHERE state='completed'"):
                if self.historical_retirement and self.historical_retirement(copy.deepcopy(row)) is True:continue
                try:
                    self._check_output(json.loads(row["output"]))
                except Exception as exc:
                    self._update(row["job_id"], state="needs attention", reason=str(exc) or type(exc).__name__)
            self._stop.clear()
            self._thread = threading.Thread(target=self._work, name="BooksArrangerAudioJobs", daemon=False)
            self._thread.start()
        return self.status()

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
            worker = self._thread
        if worker and worker is not threading.current_thread():
            worker.join(timeout)
            if worker.is_alive():
                raise TimeoutError("Owned runner has not stopped; queue is still pausing")

    def status(self):
        rows = self._rows()
        counts = {"queued": 0, "completed": 0, "failed": 0}
        current = None
        for row in rows:
            if row["state"] == "pending": counts["queued"] += 1
            elif row["state"] == "completed": counts["completed"] += 1
            elif row["state"] == "needs attention": counts["failed"] += 1
            elif row["state"] == "running": current = row
        running = bool(self._thread and self._thread.is_alive())
        state = "Pausing" if running and self._stop.is_set() else "Running" if running else "Paused" if counts["queued"] else "Needs attention" if counts["failed"] else "Completed"
        return {"state": state, **counts, "current_stage": current["stage"] if current else None, "current_job_id": current["job_id"] if current else None, "jobs": [{"job_id": row["job_id"], "state": row["state"], "stage": row["stage"], "attempt_id": row["attempt_id"], "reason": row["reason"], "manifest": json.loads(row["manifest"]), "output": json.loads(row["output"]) if row["output"] else None,"progress":copy.deepcopy(self._progress.get(row["job_id"]))} for row in rows]}

    def _work(self):
        # Resume only explicitly paused durable postprocessing; never loop unclassified failures.
        if self.pending_postprocessing and self.postprocessing:
            for job_id in self.pending_postprocessing():
                if self._stop.is_set() or self._drain.is_set():return
                try:self.postprocessing(job_id)
                except InterruptedError:return
                except Exception:pass # The postprocessor retains original/secondary failure evidence.
        while not self._stop.is_set() and not self._drain.is_set():
            pending = self._rows("SELECT * FROM audio_jobs WHERE state='pending' ORDER BY created, job_id LIMIT 1")
            if not pending: return
            row = pending[0]
            job_id = row["job_id"]
            manifest = json.loads(row["manifest"])
            try:
                if self.before_attempt:self.before_attempt(copy.deepcopy(row))
                self._archive_attempt(row)
            except Exception as error:
                self._update(job_id,state='needs attention',reason='Working cleanup requires attention: '+str(error))
                self._stop.set()
                if self.on_working_hold:self.on_working_hold()
                return  # No new attempt or source copy exists before admission.
            attempt = str(uuid.uuid4())
            journal = {"attempt_id": attempt, "history": []}
            with self._lock: self._progress[job_id] = {"attempt_id":attempt,"phase":"checking sources"}
            self._update(job_id, state="running", stage="checking sources", attempt_id=attempt, journal=json.dumps(journal), reason="")
            def checkpoint(stage, details=None):
                if stage == "checking_sources": stage = "checking sources"
                if stage not in STAGES:
                    raise ValueError("Unsupported job stage: " + str(stage))
                if isinstance(details,dict) and 'progress' in details:
                    measured=details['progress']
                    if stage!='creating' or not isinstance(measured,dict) or measured.get('phase')!='encoding':
                        raise ValueError('Unsupported progress measurement')
                    done,total=measured.get('completed'),measured.get('total')
                    if type(done) not in (int,float) or type(total) not in (int,float) or not math.isfinite(done) or not math.isfinite(total) or total<=0 or not 0<=done<=total:
                        raise ValueError('Invalid progress denominator')
                    with self._lock:self._progress[job_id]={'attempt_id':attempt,**measured}
                    return
                with self._lock:self._progress[job_id]={'attempt_id':attempt,'phase':stage}
                entry = {"stage": stage, "at": _now(), "details": details}
                if stage == "publishing":
                    if self._stop.is_set(): raise InterruptedError("Paused before publication")
                    if self.revision_guard(copy.deepcopy(manifest)) is not True:
                        raise ValueError("Source changed — review required")
                    self._validate_record(details)
                    if details["job_id"] != job_id: raise ValueError("Publication job identity mismatch")
                    journal["publication_intent"] = copy.deepcopy(details)
                journal["history"].append(entry)
                self._update(job_id, stage=stage, journal=json.dumps(journal, ensure_ascii=False))
            try:
                try:
                    if self.revision_guard(copy.deepcopy(manifest)) is not True:
                        raise ValueError("Source changed — review required")
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
                            return  # Preserve the rest of the queue without producing more attempts.
            finally:
                if self.after_attempt:
                    try:self.after_attempt(job_id,attempt)
                    except Exception as cleanup_error:
                        self._stop.set()
                        latest=self._rows('SELECT state,reason FROM audio_jobs WHERE job_id=?',(job_id,))
                        if latest and latest[0]['state'] in {'pending','needs attention'}:
                            self._update(job_id,reason=(latest[0]['reason']+'; ' if latest[0]['reason'] else '')+'Working cleanup requires attention: '+str(cleanup_error))
                        if self.on_working_hold:self.on_working_hold()
            if self.after_completed and self._rows('SELECT state FROM audio_jobs WHERE job_id=?',(job_id,))[0]['state']=='completed':
                try:self.after_completed(job_id)
                except InterruptedError:return
                except Exception:pass # Durable postprocessing diagnostics preserve the completed audio row.


class _Connection:
    def __init__(self, connection): self.connection = connection
    def __enter__(self): return self.connection
    def __exit__(self, kind, value, traceback):
        try:
            if kind is None: self.connection.commit()
            else: self.connection.rollback()
        finally:
            self.connection.close()
