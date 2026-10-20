# Queued legacy destination admission — bounded source proposal

2026-10-20, primary Ender. Proposal only; no app-source changes or live queue controls. Implements the already authorized output-root/hierarchy behavior for existing saved queue entries, without running those conversions automatically or rewriting an immutable intent. Judy§9 is the sole UI wording scope.

## Actual current gap

Read-only10:47:59Z snapshot found18pending current approved jobs, all attempt-null/queued, without output_root or v2 routing policy, frozen under Z:/Audiobooks. Matching group/context revisions and structurally equal review are recorded in session/shared/activation-pending-intents-readonly.json. This supersedes only the count, not the earlier dated19observation. Hidden startup preserves the queue Paused; explicit Start/Create/Retry/automatic Start can resume the shared queue. Current guard intentionally normalizes missing output_root to its frozen root, so an unchanged legacy intent can still run at the old location. No per-pending Retry child currently exists.

## Earliest admission and durable typed hold

Add a pure desired-route check at the start of MergeService._attempt_boundary, before the existing retained-parent native fence, before AudioJobs._work_attempt, before working.admit, archive_attempt, UUID allocation or any source/staging/destination IO. Effective frozen root is manifest.output_root only when present, else manifest.root. Desired root is the configured output root when present, else the exact manifest source root. Compute organization.plan(desired_root, frozen metadata with organization_policy=books-hierarchy-v2). Canonical identity/author credit is unchanged. Compare normalized ordinary output-root and full destination, not just a policy string. Already current root+path passes unchanged. A malformed routing input refuses normally; it cannot authorize an invented title/universe/order or path.

Mismatch raises a private typed DestinationReviewNeeded with deterministic payload. AudioJobs catches this type before its existing generic attempt-boundary refusal. It must not allocate an attempt, call working.admit, archive a prior attempt, hash/copy a source, create a directory, remove anything or automatically create a successor.

In one SQLite BEGIN IMMEDIATE, reread and require the entire selected pending row exactly unchanged, state pending, no output or publication intent, canonical manifest/hash intact, and still current/non-set-aside/newest candidate work. CAS updates only state needs attention, reason and updated; manifest/hash/job id/journal/attempt id/created stay exactly preserved. Store a separate audio_destination_holds row binding job id+manifest hash+old/proposed roots/paths+policy and timestamp. Record is an observation of desired routing, not metadata/source/media approval. If any row/CAS changed or write fails, preserve both queue/evidence and stop that worker safely with no unbounded retry or side effects. No direct SQL operator edits.

After a successful hold, the explicitly started worker may continue admission checks for the next already-pending item; it creates no successor for a held item. This may place multiple old-route entries in Need attention, truthfully counted; no audio conversion is performed for them. Pause/Quit still win and no hidden launch starts this loop.

Typed projection, only while the durable hold matches the exact current held job/manifest:

    attention.destination_review = {
      schema: 'books-queued-destination-review-v1',
      state: 'needs_review',
      old_root, proposed_root, old_destination, proposed_destination,
      routing_policy_version: 'books-hierarchy-v2',
      can_retry: <existing structural Retry/working/revision eligibility>
    }

No HTTP accepts these paths or a true capability flag. UI uses Judy§9 existing Need attention/Retry controls and Technical detail old/proposed paths. It says checks run when Retry is requested, not that every source was already reverified. Current source/review/order/cover/space/collision/refusal reasons remain truthful; do not mask them with a destination-success claim.

## Existing explicit Retry and smallest required connection

An attempt-null needs-attention parent with unchanged manifest, empty/no-failure journal, no output/publication and latest candidate identity is accepted by existing AudioJobs._retry_shape. In configured Sorted mode, MergeService.retry_blocked_job already queues a kind retry readmission; _admit_m4b_readmission sends a non-preservation parent to _admit_new_retry. That rebuilds the current approved manifest, hashes the originals and cover through existing gates, checks working debt, and creates a distinct retry_intent child in the current hierarchy under a whole-row/group/context CAS. The old held job remains unchanged from that point.

For a SAME-root hierarchy-only mismatch when no explicit output_root is configured, extend only the existing route-child branch condition to also recognize this exact typed durable destination hold. Otherwise Retry would requeue the same old job indefinitely. A current successful child has the exact desired root+path and passes the new earliest check; its already reviewed retry relation/Ready proof remain unchanged. No new button, browser-supplied metadata override, automatic approval, auto-child or Start-over trick.

Before admitting a child, the desired output must still be reachable with safe ancestry, and an existing unowned destination collision must refuse rather than enqueue an expected overwrite. This is a read-only target preflight using the same desired root/path; it grants no publication ownership. Preserve normal no-replace publication as the final gate. Full current source/review validation still happens in the existing worker, so a changed review/source holds and asks for that actual remedy; the typed destination observation is not a waiver.

## Exact source ownership and exclusions

Primary Ender, after pinned design+Judy§9: new pure destination_admission.py (route comparison/payload/type), audio_jobs.py exact boundary catch/CAS/table+attention projection, merge_service.py earliest route check and existing Retry branch/target preflight, existing web/app.js attention reason/details only per Judy, narrow tests and check-desktop declaration. Preserve all existing recovery/retained-file/real-provider-choice/native publication consumers, source code outside these regions, canonical helpers, global hooks, runtime/compiler work, releases and live settings/catalog/media. Sully alone commits/releases. No change to legacy normalization or publication receipt binding.

## Meaningful fault and acceptance matrix

1. Exact target/root/path: pending job runs through unchanged normal admission. Legacy root mismatch and same-root v1 cycle layout mismatch each become typed holds; no blanket version-based hold when actual paths already match.
2. Instrument working.admit/archive_attempt/UUID factory/runner/filecopy/cleanup to fail if called before the mismatch hold. Assert zero calls, attempt remains null, no staging path, original sources unchanged and full parent manifest/hash/journal/created unchanged.
3. Deterministic interleaving changes pending row/revision/currentness between observation and CAS. No hold evidence/partial state update, no source or cleanup action, no running attempt; the new row stays untouched. SQLite busy or stop/closing refuses safely, no loop.
4. Hidden normal startup+published check+retention does not start saved pending work. Start is explicit; Pause/Quit prevent later admission and preserve pending rows. Guard never implicitly resumes work.
5. Explicit existing Retry after a typed hold returns normal acknowledgement; worker creates exactly one distinct route-bound child with current root/v2path and original parent exact. Test actual tiny legacy source→child native conversion→Current/Ready, without forged output/cache proof; existing normal source/temporary cleanup policy remains in force.
6. Same-root hierarchy hold Retry also creates a child, never requeues the old manifest into an infinite hold cycle. Child desired-route check passes.
7. Changed current review/source/hash/order/cover or candidate revision refuses the child; collision/unavailable target refuses without overwrite. Stale hold hash/forged browser path cannot enable Retry. Second child and stale CAS refuse atomically. True provider choices and manual evidence remain intact.
8. Mixed saved queue: old-route job holds, already-current job remains eligible under existing checks; no old job is cancelled, deleted or auto-rebound. No mass conversion is triggered by install/hidden launch.
9. Existing Retry/Quit/failure and retained-parent-attempt-fence regression suites remain declared. Add new tests to scripts/check-desktop.mjs and existing exact frontend test discovery; no formal QA result is implied by developer cases.

This proposal requires Senua and Judy pinned acceptance before implementation. Until then the supported activation restriction is global queue Paused, no conversion-starting controls, and a final migration claim scoped to the actual final drained successful-publication inventory.
