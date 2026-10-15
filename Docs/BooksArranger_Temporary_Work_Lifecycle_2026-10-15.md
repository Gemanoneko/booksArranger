# Working-file lifecycle requirements — 2026-10-15

Sergei explicitly requires temporary conversion files not to accumulate. The one-time cleanup removed 154 unused generated files / 59,306,533,081 logical bytes. Permanent behavior must reclaim abandoned generated output after success, failure, cancellation, retry and startup, while preserving genuine resumable/recovery inputs and compact diagnostics.

## Implementation boundaries

Ender owns new `working_lifecycle.py`, focused lifecycle tests, and narrow integrations in `audio_jobs.py`, `audio_pipeline.py`, `merge_service.py` and `storage_cleanup.py` in this maintenance worktree. `source_cleanup.py` and separate focused stream tests implement the already approved Zone.Identifier-only exception after its exact stream/native disposition contract is reviewed. Shared hook components, frozen source snapshots/capsules, the separate automatic-busy worktree, installed application and Electron candidate are excluded. Sully owns all commits and later accepted integration/versioning. No live hotpatch or migration is implied.

## Required behavior

- Keep producer creation/closure evidence durable even when validation fails, publication never starts, a job is cancelled or the process crashes. Journal history and failure diagnostics survive working-file removal. Unknown files and unprovable attempts remain attention items, never name/age-only deletion candidates.
- Retire exact generated checked/compatible outputs, normalized WAVs and bounded diagnostic/metadata scratch using native ordinary ancestry and same-file handles. Current attempt ownership, no running producer, no publication/output/other-attempt dependency, one filesystem link, stream safety and protected source availability must be verified. The three existing unresolved representative pairs retain their current explicit exception until compact evidence/defect proof discharges them. New failures do not create an unlimited full-audio diagnostic archive.
- Persist verified intent before native disposition and durable outcome afterward; reconcile missing files only against exact prior intent. Preserve replacement/changed/unknown entries and report the reason. Crash recovery is idempotent and never claims reclaimed bytes from an ambiguous outcome.
- Sweep only receipt-owned abandoned attempts during startup under app ownership, then after explicit retry and attempt completion. A failed cleanup blocks creating another abandoned working set for that job; reusable sources are reused or separately retired only after original-survival/re-stage proof. Recovery retention remains the existing 24 hours.
- Preserve the existing conservative per-book space estimate and preflight. Account for already retained attempts and cleanup debt before admission/retry, including shared stage/destination volume capacity; no new arbitrary quota/retention preference is invented. A space hold leaves queued work intact.
- The narrow Zone.Identifier exception applies only to the download-marker stream with verified original/publication/recovery policy. Unknown or meaningful streams remain protected. Do not reinterpret stream enumeration as atomic exclusion of arriving streams; exact supported native proof is required before disposition.

## Acceptance proof

Real isolated private Windows fixtures must cover repeated failure/retry without cumulative audio copies, cancellation, crash before/after intent/disposition, restart reconciliation, changed native identity/hash, alias/reparse/extra-stream refusal, active/publication references, and source/recovery/history survival. Space admission must refuse insufficient peak capacity without staging another source copy. Include actual producer-owned process closure and meaningful native file disposition checks; the existing 24-method pure model alone is not sufficient. Stream exception tests must retain meaningful/unknown ADS and preserve the saved cleanup policy.

Implementation and runtime operation graphs will be reviewed independently by Senua and Futaba. The current frozen first13 graph and separate automatic-fix QA graph do not automatically cover these changes. This requirements record is not a test-pass, cleanup operation or release authorization.
