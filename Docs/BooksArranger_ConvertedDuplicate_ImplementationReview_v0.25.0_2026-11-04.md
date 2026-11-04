# Books Arranger 0.25.0 — committed duplicate-cleanup source review

Reviewer: Senua. Date: 2026-11-04.

This is a completed source-slice review, not release clearance. Reviewed commit range: `d9c0da2c0cb47abae4c75e8d722e06268d6ee600..87b568143a5f803154c2564cae0487cc83fe0f6c` (18 product/test files, +655 / -56; documentation/evidence excluded from those totals). The committed main source was inspected after the earlier dirty-tree pre-review. Previously reviewed editor/Tolkien changes and the pending folder-latency correction are excluded here. The final accumulated review must begin at the previous release-review endpoint `bf4425de09c355d2a0743771ca4209b24c8f0de1` and bind the resulting exact release build.

## Findings delivered to Ender

1. **Chapter-plan correspondence (Major): resolved in `87b5681`.** The initial resolver compared source-byte order and M4B source/part chapter digests but omitted ordinary `manifest.chapters`. Thus an MP3 duplicate with a different requested chapter plan could qualify for cleanup using the existing output. `publication_reuse.same_recording()` now compares the complete ordinary chapter plan exactly as well. `test_complete_source_order_chapter_and_manual_choice_mismatches_refuse` covers this refusal and passes in the supplied review-regression receipt. No test was run by this reviewer.

2. **Failure reporting could abort startup (Critical): resolved in `87b5681`.** A completed cleanup child with no enrolled intent after a crash can have an invalidated parent publication. Enrollment correctly refuses, but `_enrollment_attention()` previously repeated `checked_result()` while handling that refusal, allowing the second exception to escape the constructor's completed-task loop. The handler now records the frozen parent receipt with `blocked_verification=True` without requiring the refused authority. `_cleanup_guard()` rejects that flag before any disposition authority checks. `test_failed_startup_enrollment_records_inert_attention_without_revalidating_parent` exercises the real enrollment/failure handler with a held parent, asserts the inert receipt and rejected guard, and passes in the supplied review-regression receipt.

## Destructive-boundary checks

Read-only inspection covered `publication_reuse.py`, the new AudioJobs verification branch, MergeService admission/worker/enrollment/cleanup guards, SourceCleanup, StorageCleanup, RecoveryRetention, publication binding, ownership indexing, current-publication projection, and the small backfill/UI exclusions.

The current resolver keeps the parent manifest/output receipt and child cleanup identity separate, rejects reuse chains and replacement lineage, requires one unambiguous complete ordered recording, and re-derives the relation from durable rows. The child creates a verification result rather than a publication record, skips the media producer and cannot enter the publishing checkpoint. Existing publication-only consumers continue to reject a cleanup child.

Before removal, the child uses the existing reviewed source device/file-ID checks, size/time/full hashes, native alias/stream checks and held parent output. All source backups are verified and durable before the first disposition. Both the current child/parent relation and source review are rechecked in the destructive write transaction, followed by the current publication-location generation check. A parent published in place does not send the duplicate child through the parent's rename-retirement shortcut.

Retention and storage cleanup select the child's own source/recovery receipts while protecting the parent's publication. The child has no staging targets and does not discharge the parent's producer working files. Ready/publication totals exclude cleanup children; the child's removal label requires a completed source-cleanup receipt. No additional concrete destructive-boundary flaw was found in this inspected slice.

Restoration of a child's backups uses the protected parent/child resolver and the existing no-replace restore path; it cannot overwrite a current source or assume the parent's in-place rename authority. Gap/series backfill entry points reject cleanup-only tasks. Historical Held entries receive one normal proof opportunity only for the prior exact-identical/collision reason class, recorded with `duplicate_cleanup_policy=1`; ordinary admission, current source/review checks and destructive guards remain required.

## Review dimensions

| Dimension | Status for this source slice |
|---|---|
| Security | Pass: no new shell, IPC, credential or Electron authority; native path and disposition guards remain in force. |
| Correctness and logic | Pass: exact ordered byte/chapter/work correspondence, explicit parent/child ownership, narrow old-hold refresh, and publication-count exclusions. |
| Crash and stability | Pass after startup-handler correction; interrupted verification is retried without publishing, and partial source disposition retains per-file outcome authority. |
| Performance | Pass for the added flow: no second codec run or producer; final parent/source byte verification remains mandatory. The separate folder-latency issue is outside this slice. |
| State and data safety | Pass: immutable parent receipts, verified child backups, current relation/location transaction checks, no-replace restore and child-owned retention. |
| Input handling | Pass: typed task/result schemas and server-derived relation; ambiguity, mismatched sources/plans and reuse chains refuse. |
| Maintainability | Pass for this slice: ownership resolution is centralized without weakening ordinary publication-only contracts. |
| Doc/code drift | Pass: source/task activity language and completed-output counts agree with the supplied decision/UX scope. |
| Build/release hygiene | Source checks pass: version remains 0.25.0, and the unchanged root-Python module glob includes `publication_reuse.py`. Final package, full milestone QA and exact build binding are pending. |

## Evidence audit

Verified `Docs/Evidence/converted-duplicate_2026-11-04/duplicate-core/summary.json` SHA256 `3d57f8c57182ab4a57c021b01727c4537a49131d695c9e3ad9e0964e84843594` and `source.patch` SHA256 `d8f9f09c5a35e4d75f9ba9c1b025a2c08ff11fc765671a41338dadf890a4aed2`. All 18 committed source/test files match their frozen LF-normalized hashes, and all 31 listed evidence files match their exact hashes.

Read the actual tests and receipts: the two-source real codec/publication E2E passes in 12.438 seconds and asserts no child conversion/publication, unchanged parent row/output bytes, removal of both extra sources and converted total one. The single-M4B NFC/NFD case passes with an in-place parent and covers changed output, changed source bytes, cancel/resume, child recovery and restore. The 10-case review cohort passes, including both review corrections, transactional parent invalidation, concurrent admission, partial removal/resume, ambiguous parent refusal and unknown-absence refusal. The final boundary log records 13 actual cases passing, including the historical-hold policy case and typed activity rows, plus an erroneous test-class selector loader error.

The broader 112-case and 92-case runs are not represented as fully passing: their sole failures were respectively a minimal startup fixture missing `manifest` (corrected lookup, then passing in the 10-case receipt) and an existing fixture exceeding the supported Windows path length (passing in the separately preserved shortened-private-root rerun). The mistaken final selector's correct existing held-book case passes in the consumer cohort. All 12 preserved owned receipts, including failing runs, close with complete output, native zero, no force and no timeout. These are focused evidence only, not a full-gate result.

## Limits and remaining handoff

No tests, app launches, native probes, live-library access, UI focus changes or product edits were performed by Senua. Open findings in this source slice: Critical 0, Major 0, Minor 0; both pre-review findings are resolved with supplied regression evidence, and no safety-floor violation was identified. Independent focused/full QA, the pending folder and newly requested media corrections, the final accumulated source review and exact packaged-build binding remain outstanding. This document does not supply the machine-readable final release verdict or certify a release artifact.
