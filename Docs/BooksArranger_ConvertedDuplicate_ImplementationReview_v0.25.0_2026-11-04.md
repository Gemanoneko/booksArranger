# Books Arranger 0.25.0 — incremental duplicate-cleanup review

Reviewer: Senua. Date: 2026-11-04.

This is an implementation pre-review, not release clearance. The comparison baseline is `d9c0da2c0cb47abae4c75e8d722e06268d6ee600`. The inspected implementation is the changing, uncommitted tree at `C:/Antigravity Projects/Worktrees/Books Arranger/converted-duplicate-20261104`; its old checkout HEAD is not the candidate source pin. A frozen commit, complete accumulated review, independent QA and exact packaged-build binding remain necessary. Previously reviewed editor/Tolkien changes are excluded here.

## Findings delivered to Ender

1. **Chapter-plan correspondence (Major): corrected in the inspected implementation.** The initial resolver compared source-byte order and M4B source/part chapter digests but omitted ordinary `manifest.chapters`. Thus an MP3 duplicate with a different requested chapter plan could qualify for cleanup using the existing output. `publication_reuse.same_recording()` now compares the complete ordinary chapter plan exactly as well. The new resolver test includes a different requested ordinary chapter plan. No test was run by this reviewer.

2. **Failure reporting could abort startup (Critical): corrected in the inspected implementation; regression result pending.** A completed cleanup child with no enrolled intent after a crash can have an invalidated parent publication. Enrollment correctly refuses, but `_enrollment_attention()` previously repeated `checked_result()` while handling that refusal, allowing the second exception to escape the constructor's completed-task loop. The handler now records the frozen parent receipt with `blocked_verification=True` without requiring the refused authority. `_cleanup_guard()` rejects that flag before any disposition authority checks. The correction preserves an inert attention outcome; it does not authorize cleanup from stale proof. Ender is adding the completed-child-before-enrollment/invalid-parent regression.

## Destructive-boundary checks

Read-only inspection covered `publication_reuse.py`, the new AudioJobs verification branch, MergeService admission/worker/enrollment/cleanup guards, SourceCleanup, StorageCleanup, RecoveryRetention, publication binding, ownership indexing, current-publication projection, and the small backfill/UI exclusions.

The current resolver keeps the parent manifest/output receipt and child cleanup identity separate, rejects reuse chains and replacement lineage, requires one unambiguous complete ordered recording, and re-derives the relation from durable rows. The child creates a verification result rather than a publication record, skips the media producer and cannot enter the publishing checkpoint. Existing publication-only consumers continue to reject a cleanup child.

Before removal, the child uses the existing reviewed source device/file-ID checks, size/time/full hashes, native alias/stream checks and held parent output. All source backups are verified and durable before the first disposition. Both the current child/parent relation and source review are rechecked in the destructive write transaction, followed by the current publication-location generation check. A parent published in place does not send the duplicate child through the parent's rename-retirement shortcut.

Retention and storage cleanup select the child's own source/recovery receipts while protecting the parent's publication. The child has no staging targets and does not discharge the parent's producer working files. Ready/publication totals exclude cleanup children; the child's removal label requires a completed source-cleanup receipt. No additional concrete destructive-boundary flaw was found in this inspected slice.

## Limits and remaining handoff

No tests, app launches, native probes, live-library access, UI focus changes or product edits were performed by Senua. Ender's initial private E2E and boundary successes are reported evidence, not independently executed here. Cancellation, changed sources/output, partial removal, concurrency, crash/restart, native in-place-parent handling and inert startup-attention results must be included in the final frozen evidence. The two corrections above must be retained and rechecked against the pushed final source; this document certifies neither the dirty tree nor a release artifact.
