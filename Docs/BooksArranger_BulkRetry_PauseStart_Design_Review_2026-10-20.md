# Bulk Retry Pause/start — bounded design review

Scope: original design SHA256 `3cd5b7bbe988eec7bee00aa9ccf5f801be3418ac3f1387e380355d8e167b6a55` and superseding v2 SHA256 `9cea14498d618997d5a6c0105be5333cd2c2f8d3caca7429010c54da6e2ffe58`, with the explicit finite conditions below. Read current MergeService control/scheduler/close regions, AudioJobs.resume/pause/close, and CleanupJobs.resume/pause/worker handoff. This is design review; no frozen source range, execution, QA, native, deployment or release verdict is certified.

Decision: IMPLEMENTATION MAY PROCEED WITH THESE CONDITIONS. No Critical finding identified in this bounded design. V2 resolves the two original Major design findings through the corrections below; source review must verify implementation. One explicit completion of v2 is mandatory: close must establish a permanent closing predicate before joins, and the admission callback must reject it. Generation invalidation alone cannot reject a fresh request captured after closing begins.

## Major 1 — final admission and Pause boundary

The original claim that Pause after the last callback check necessarily stops a worker before it passes its stop check is false. A worker-lock holder can check its generation, Pause can increment the generation, and that holder can launch before Pause obtains its queue lock.

Accepted finite correction: preserve existing completed-Pause semantics. Pause invalidates the generation and bulk submission event first, releases `_BULK_LOCK`, then stops both queues under their respective existing locks, and returns only after both boundaries. CleanupJobs.pause must therefore take `cleanup.lock`. An admission already holding a queue lock may finish during Pause; the existing current-book policy remains applicable. The guarantee is that an older generation cannot clear stop, apply pending start-check results, or launch after Pause has completed. It is not a guarantee of zero activity between clicking Pause and its response.

AudioJobs checks admission before stop.clear and at its existing final locked apply/start boundary. CleanupJobs does likewise under its existing lock. Every handoff uses the same captured generation, including cleanup-to-audio; store that guarded handoff in the individual worker's arguments, rather than replacing shared callback state for another run. Generation rejection cannot clear a newer stop or apply stale results. Callback exceptions fail closed.

## Major 2 — a fresh Start can disappear behind stale work

Cleanup's old-generation handoff can own AudioJobs._resuming after Pause completes. A new explicit Start currently returns early because `_resuming` is true; the old check then cancels, leaving neither start running. The old `_resume_pending` boolean can similarly swallow a newer asynchronous request.

Accepted finite correction: use an explicit retryable busy/stale outcome when the existing checker or pending start prevents a new generation from admission. Do not silently accept it as a successful start or introduce another scheduler. Preserve accepted retry requests. Bulk start_outcome must distinguish stale/paused, retryable busy, actual failure, and an admitted/current-generation start. An old pending task's finally block may clear only its own pending ownership. A same-generation already-running/checking result remains distinguishable from the stale case.

## Mandatory implementation details

- Capture a manual Start's generation before waiting on operation_lock; capture asynchronous and bulk generations when the corresponding request is scheduled/created. Do not recapture the current generation inside delayed work.
- Drain and close invalidate admission before shutdown waits. Close has a permanent closing predicate, so a delayed start cannot reopen work during component teardown; a later ordinary Start cannot override closing/draining.
- Lock order: briefly acquire/release `_BULK_LOCK`, then operation_lock, then the relevant queue lock. A callback under a queue lock reads only the already captured generation and draining/closing state; it never acquires Merge/Bulk locks, invokes status, or performs I/O. Pause never holds `_BULK_LOCK` while acquiring a queue lock.
- Keep published-output hashing, NAS access and long checks outside new control critical sections. Retain existing output/publication guards and cancellation. No new lock may surround those checks.
- Optional admission_check and per-worker handoff defaults preserve existing direct callers. Merge supplies the guarded path at every relevant start and handoff. Existing queue closed/drain checks remain mandatory.

Exact future ownership: Primary Ender owns Merge.pause/resume/internal operation-locked resume, drain/close admission invalidation, `_resume_later`, bulk generation/outcomes, and cleanup handoff initialization; AudioJobs.resume's admission/result boundaries; CleanupJobs.resume, its pause lock, and the narrowly scoped `_work` handoff argument/call. Sources' progress_books/scanner DB changes remain outside this review and ownership.

## Finite proof required at source/QA stage

Use deterministic barriers on the real start methods with fake worker/check inputs: (1) delayed async/bulk start after completed Pause; (2) Pause during output checking, with no later application of stale results; (3) final callback succeeds immediately before Pause waits for the worker lock, demonstrating the corrected completion boundary; (4) stale cleanup-to-audio handoff; (5) fresh Start while an old-generation handoff still owns `_resuming`; (6) fresh request behind old `_resume_pending`, including old finally ownership; (7) repeated current-generation starts; (8) close/drain before delayed start and before final admission; (9) optional-default caller behavior and failed callback; (10) truthful bulk outcomes and saved requests. Assert final stop state and absence of new post-completion work, not merely that Pause sets an Event. Exercise both audio and cleanup start boundaries. Tests remain unrun in this review.

No process, native, media, DB, library, global hook, git or scratch changes were made. Only this review document was added. Findings and conditions are finite; no new ownership framework is needed.
