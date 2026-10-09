"""Durable injected audio queue. This module never opens media or publishes files."""
import copy
import hashlib
import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone


STAGES = {"checking sources", "creating", "checking", "copying", "publishing"}


def _now():
    return datetime.now(timezone.utc).isoformat()


class AudioJobs:
    """Single-owner queue; do not instantiate twice for the same database.

    runner must synchronously stop all its owned work before returning/raising.
    Validator must check exact recorded output hash/size and validation contract,
    never adopt a file merely because its name exists. Neither callback may hold
    a database transaction. Queue construction never starts pending work.
    """

    def __init__(self, database, runner, revision_guard, output_validator):
        self.database = str(database)
        self.runner = runner
        self.revision_guard = revision_guard
        self.output_validator = output_validator
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread = None
        self._closed = False
        with self._db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS audio_jobs (job_id TEXT PRIMARY KEY, manifest TEXT NOT NULL, manifest_hash TEXT NOT NULL, state TEXT NOT NULL, stage TEXT NOT NULL, attempt_id TEXT, journal TEXT NOT NULL, output TEXT, reason TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL)")
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
                journal = json.loads(row["journal"])
                record = json.loads(row["output"]) if row["output"] else journal.get("publication_intent")
                try:
                    self._check_output(record)
                    if record["job_id"] != row["job_id"]:
                        raise ValueError("Output job identity mismatch")
                    self._update(row["job_id"], state="completed", stage="completed", output=json.dumps(record), reason="")
                except Exception as exc:
                    self._update(row["job_id"], state="needs attention", reason=str(exc) or type(exc).__name__)
            elif state == "running":
                self._update(row["job_id"], state="pending", stage="queued", reason="Interrupted book restarts on explicit resume")

    def enqueue(self, manifest):
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
            existing = self._rows("SELECT * FROM audio_jobs WHERE job_id=?", (frozen["job_id"],))
            if not existing:
                identity = {key: value for key, value in frozen.items() if key != "job_id"}
                existing = [row for row in self._rows() if {key: value for key, value in json.loads(row["manifest"]).items() if key != "job_id"} == identity]
                if existing:
                    frozen["job_id"] = existing[0]["job_id"]
                    digest = existing[0]["manifest_hash"]
            if existing:
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
                db.execute("INSERT INTO audio_jobs VALUES (?,?,?,?,?,?,?,?,?,?,?)", (frozen["job_id"], encoded, digest, "pending", "queued", None, "{}", None, "", timestamp, timestamp))
            return frozen["job_id"]

    def resume(self):
        with self._lock:
            if self._closed:
                raise RuntimeError("Queue is closed")
            if self._thread and self._thread.is_alive():
                return self.status()
            for row in self._rows("SELECT * FROM audio_jobs WHERE state='completed'"):
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
        return {"state": state, **counts, "current_stage": current["stage"] if current else None, "current_job_id": current["job_id"] if current else None, "jobs": [{"job_id": row["job_id"], "state": row["state"], "stage": row["stage"], "attempt_id": row["attempt_id"], "reason": row["reason"], "manifest": json.loads(row["manifest"]), "output": json.loads(row["output"]) if row["output"] else None} for row in rows]}

    def _work(self):
        while not self._stop.is_set():
            pending = self._rows("SELECT * FROM audio_jobs WHERE state='pending' ORDER BY created, job_id LIMIT 1")
            if not pending: return
            row = pending[0]
            job_id = row["job_id"]
            manifest = json.loads(row["manifest"])
            attempt = str(uuid.uuid4())
            journal = {"attempt_id": attempt, "history": []}
            self._update(job_id, state="running", stage="checking sources", attempt_id=attempt, journal=json.dumps(journal), reason="")
            def checkpoint(stage, details=None):
                if stage == "checking_sources": stage = "checking sources"
                if stage not in STAGES:
                    raise ValueError("Unsupported job stage: " + str(stage))
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
                    self._update(job_id, state="needs attention", reason=str(exc) or type(exc).__name__)


class _Connection:
    def __init__(self, connection): self.connection = connection
    def __enter__(self): return self.connection
    def __exit__(self, kind, value, traceback):
        try:
            if kind is None: self.connection.commit()
            else: self.connection.rollback()
        finally:
            self.connection.close()
