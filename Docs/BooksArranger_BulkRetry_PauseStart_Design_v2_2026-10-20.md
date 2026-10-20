# Bulk Retry Pause/start fence — finite v2

Supersedes the inaccurate no-start-after-final-check statement in v1. Source proposal only; no live operation or Python execution.

Guarantee: preserve existing Pause-completion semantics. A worker start already linearized under its queue lock may finish starting while Pause is in progress. Pause returns only after both queue stop boundaries; no older asynchronous start may subsequently clear that completed Pause. Existing current-book safe-stop behavior remains; zero thread creation between click and response is not promised.

Pause increments a monotonic generation and sets bulk-submission stop under _BULK_LOCK, releases it, then calls cleanup.pause/jobs.pause. Cleanup.pause must set stop under its existing cleanup.lock, matching AudioJobs.pause. No Merge/Bulk lock is held while acquiring a worker lock. Close/drain invalidate generation before joins or normal shutdown/stop calls.

An explicit Merge.resume captures generation before waiting for operation_lock. Async Retry captures when scheduled; bulk captures when accepted. An operation-locked inner resume uses a lock-free allow() closure reading only generation equality and draining. It checks before clearing any stop and during long pruning; stale resumes raise a visible retryable refusal. AudioJobs.resume optionally checks allow under its own lock before clearing stop, and at final checked-results apply/thread-start boundary. CleanupJobs.resume does the equivalent under cleanup.lock. No new lock around DB/NAS/media work; callback acquires no Merge/Bulk/operation lock. Existing native/review/hash/CAS checks remain unchanged.

Cleanup._work carries an optional guarded after-drain callback from Cleanup.resume; Merge supplies a callback that calls AudioJobs.resume with the SAME generation guard. Thus cleanup cannot erase a later completed Pause when handing off. Existing defaults preserve other callers.

Overlap is explicit, never silently accepted: if a prior _resume_pending scheduler or AudioJobs._resuming still owns an old start, a new request remains durable but gets a retryable busy/start-blocked reason, and explicit Start can be retried after that owner stops. No replacement scheduler/coordinator. _resume_pending records are only cleared by their actual owner finally. A rejected stale/closing/busy resume cannot be recorded as requested by bulk. A successful return means current work is already running or the current-generation worker was started; a Pause during the long check is rechecked before reporting success.

Lock order is operation_lock then queue lock where needed; _BULK_LOCK is used only to capture/invalidate generation/scheduler fields and is released before either. Queue-held allow callbacks only read immutable captured generation/current generation/draining. Pause's completion point is after queue stops; attempts already in progress reach existing checkpoints.

Deterministic focused cases, all Python UNRUN pending admitted QA: Pause before delayed start; during long output check; during final queue-lock start; after launch; cleanup-to-audio handoff; repeated Start while stale _resuming or _resume_pending remains (explicit busy, then successful fresh Start); new request remains saved on busy; close/drain invalidation before joins; rejected generation never clears a completed Pause or admits a new attempt. Test separately the admitted-before-Pause-completes case; do not mislabel it a violation or claim stronger zero-thread semantics.

Scope includes Merge pause/resume/close/drain/_resume_later/bulk, AudioJobs.resume, CleanupJobs.resume/pause and _work after-drain argument/line. Sources progress_books/scanner untouched. No new controls/framework, live replay, source/audio deletion or approval.
