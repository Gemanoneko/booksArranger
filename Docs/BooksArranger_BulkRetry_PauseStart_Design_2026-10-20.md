# Bulk Retry Pause/start generation fence — source proposal

Scope: MergeService.pause/resume/_resume_later/_retry_all_work and the final start boundaries of AudioJobs.resume and CleanupJobs.resume. No live action.

A private monotonic pause generation is read/incremented under existing _BULK_LOCK. Pause increments first and sets the bulk submission stop event, then releases _BULK_LOCK before calling cleanup.pause/jobs.pause. An explicit Start captures its generation BEFORE waiting on operation_lock; an asynchronous Retry start captures at scheduling, and bulk captures at request creation. A later Pause invalidates all older scheduled/checking starts; a later explicit Start captures the new generation.

Public Merge.resume captures (or receives the already captured) generation, then calls an operation-locked internal resume implementation. Its allow() closure only reads generation equality and draining; it acquires NO Merge/Bulk locks. It checks before clearing stop flags and is included in the long prune/check cancellation flag. It passes the same allow closure to the selected CleanupJobs/AudioJobs start. Stale output-check results are not applied and no worker is started. The callback grants no review/media/publication authority.

AudioJobs.resume(admission_check=None) checks under its existing worker lock before clearing its stop flag and again before applying check results/creating the worker. All published-output checks and existing stop/drain/closed checks remain. CleanupJobs.resume gains the same optional callback, checks before AND after stop.clear under its existing lock, and refuses stale starts. A Pause after the last check still sets the stop event before work can pass its existing per-book checks.

Necessary additional handoff boundary: CleanupJobs._work currently calls after_drain=lambda:jobs.resume(), which could itself erase a later Pause. The SAME generation must reach that handoff: optional guarded after-drain callback is captured by CleanupJobs.resume and passed only to its existing _work handoff; Merge supplies lambda:jobs.resume(admission_check=allow). Existing unguarded callers preserve existing defaults. This is one existing handoff, no new worker/coordinator.

Lock order: capture generation under _BULK_LOCK, release, then operation_lock, then either queue lock. Callback under a queue lock never acquires operation_lock/_BULK_LOCK. Pause releases _BULK_LOCK before queue pause calls. No long hash/SQLite/NAS action under _BULK_LOCK and no new locks around I/O.

Bulk startup records paused if its captured generation became stale; a failed start records actual failure. Accepted requests remain saved, no child is manufactured. Async status cache treats _resume_pending as busy.

Focused Python controls (WRITTEN/UNRUN until admitted): Pause before delayed async resume; during long published-output check; between clear and final start; after worker launch; stale cleanup-to-audio handoff; fresh explicit Start after Pause; repeated Starts while one is checking; drain/close; rejected generation never applies stale output checks or clears a newer stop. Exercise real start methods with deterministic fake thread/settle barriers, no filesystem/media.

Requires ownership confirmation for the narrowly identified CleanupJobs._work after_drain line/argument plus Merge cleanup.after_drain initialization; otherwise STOP before those edits. Existing Sources progress_books/scanner changes untouched.
