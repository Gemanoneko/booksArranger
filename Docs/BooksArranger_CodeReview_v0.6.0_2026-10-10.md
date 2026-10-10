# Code Review — Books Arranger v0.6.0

## Header — final candidate v3

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-10
Tool: Books Arranger
Release: v0.6.0 candidate; VERSION still 0.5.0 pending Sully
Commit range: e7001bbd41e8b7d853a84339d47ef20c9cf91dc4..205a16d96e27aa207ac250a8e88c1ce3d8ea30ec, plus exact uncommitted candidate-v3 overlay
Files changed: 18 files, +1019 / -42 (Git-normalized text; includes three audit/evidence documents)
Stand-down dimensions: Electron-specific checks N/A — Python loopback utility, no Electron renderer or installer
```

**Final source identity:** `scratch/retention-cleanup-2026-10-10/candidate-v3`, 99 manifest-listed files; base HEAD `205a16d96e27aa207ac250a8e88c1ce3d8ea30ec`, dirty=true. Source digest `a83f0ad64bc67b4c26d655f3fc02bfa737678c9bee8720d919417668af4d3f8f`; `manual-contract-v3.json` SHA256 `7a087010a570204d12b69e7a8e6a8e45b60cc73d421de52bb0b4607aa41663b1`. Independently recomputed 99/99 listed file sizes and SHA256 values, zero mismatches. The snapshot includes copies of the original blocked review and QA reports as historical documents; those copies are not a claim of final clearance. Updating the working report does not modify candidate-v3. The accepted logic is this overlay, not an unspecified later commit at the base HEAD.

Latest prior implementation mapping and first-round manifest provenance are preserved below. The committed accumulated range adds three docs, +106 / -0; v3 overlay changes fifteen files, +913 / -42. Counts use Git numstat after verifying the working bytes matched all 99 snapshot hashes, normalized new-file counts, and independent candidate Git-blob comparison. `tests/test_metadata_frontend.js` remains unchanged from base.

## Summary

Focused rereview of the first-round findings traced the newly frozen producer-artifact contract across audio_pipeline, quicktime normalization, durable output validation and storage deletion. Both Critical findings and all three Major findings closed in v2; the focused v3 status-only review also closes the remaining Minor finding. New staging targets require independently expected bytes; exact repaired-final protection now remains held through retained-copy deletion. Existing-data legacy authorization and the actual finite deletion caller are separate, still-unreviewed inputs and are not cleared by this source verdict.

## Rubric — final candidate v3

Severity definitions and the always-blocking safety floor: `Team/Docs/ProcessRules.md` § Severity definitions.

### 1. Security

- Status: **Pass** — deletion requires independent expected bytes; native ordinary-path, ancestry, reparse, hard-link, alternate-stream and nested-Git guards remain intact; no new shell or arbitrary-path HTTP surface.

### 2. Correctness & Logic

- Status: **Pass** — intact recovery can restore after a purge preflight error; the LEGACY_PROFILE exception is limited to staging with unchanged protected originals, while source-retirement recovery retains the full modern validation contract.

### 3. Crash / Stability Safety

- Status: **Pass** — durable per-file intent/reconciliation retains the original exact-handle and replacement safeguards; audio success remains separate from purge failure.

### 4. Performance

- Status: **Pass** — MergeService._prune_completed skips completed storage receipts before expensive output inspection, closing the repeated completed-library purge sweep.

### 5. State & Data Safety

- Status: **Pass** — producer-owned bytes are independently pinned before cleanup; changed recognized-name files fail admission, and the corrected repaired output is held and hash/size checked throughout repair-copy disposition.

### 6. Input Handling

- Status: **Pass** — unknown or unproved content is refused/preserved; the new runtime still accepts only ordinary bounded paths and completed job associations.

### 7. Maintainability

- Status: **Pass** — isolated receipt generation/consumption preserves durable audio and cleanup separation with no new independent advisory construction finding.

### 8. Doc/Code Drift

- Status: **Pass** — successful status identifies verified temporary copies, and a separate authoritative count reports existing ordinary retained legacy evidence. Judy approved “files” when that count is strictly files.

### 9. Build & Release Hygiene

- Status: **Pass** — final manual source/runtime/check pins and version action are explicit; no package/lockfile/installer applies. Independent QA must name candidate-v3 and Sully must carry only accepted source plus its release marker.

## Closure evidence and scope

| Finding | Final disposition | Mechanism inspected |
|---|---|---|
| F1 Critical | Closed | storage_cleanup.py:105 refuses missing expected bytes. _staging consumes output.validation.staging_artifacts for the exact attempt, immutable source/cover/final hashes or separately reviewed legacy authorizations. Unproved tiny legacy diagnostics/chapters are preserved. audio_pipeline.py:44-77 generates exact metadata bytes and captures diagnostics from exclusive producer-created descriptors with identity/size/timestamp correspondence. Normalization records the protected input's full SHA256 at quicktime_chapters.py:108-122. New regression cases cover recognized-name replacement before first receipt and substitution after retirement. |
| F2 Critical | Closed for helper source | storage_cleanup.py:294-304 derives only the parent-associated corrected destination, protects its ancestry and holds VerifiedFile(final), checks its completed-journal full hash/size, then disposes the expected repair copy while that final remains held. The caller's expected repair-copy hash provenance is still an independently reviewed input; no historical caller was part of this snapshot. |
| F3 Major | Closed | source_cleanup.py:132 permits restoration after needs_attention only when all recovery members still exist and no checking/removing/completed purge is active; restore still verifies each exact backup and refuses destination collisions. The preflight-error regression exercises successful restoration of the intact set. |
| F4 Major | Closed | storage_cleanup.py:51-60 admits legacy staging-only output validation only without source-retirement enrollment or enabled cleanup policy. _source_safety then holds and full-hash checks every unchanged original. No retired-source recovery proof is relaxed. |
| F5 Major | Closed | merge_service.py:170-171 returns for completed storage receipts before calling storage_cleanup.run; destructive runs still require fresh held final-output checks. |
| F6 Minor | Closed in v3 | source_cleanup.py:22-25 uses lstat and rejects reparse/non-regular entries when counting persistent preserved paths; completed status says “Originals removed; verified temporary recovery and working copies removed”. web/app.js:300 separately renders “Unverified legacy evidence retained: [count] files”. Both frontend and backend fixture expectations were updated. |

The v3 delta changes only source_cleanup.py status/counting, web/app.js status/count rendering, two relevant fixture expectations, and audit/evidence docs. Storage deletion, artifact receipts, normalization and output protection match the cleared v2 hashes exactly. No broad rereview or tests were performed for the v3 copy delta.

Producer reports 18 retention/substitution fixtures, five actual-media merge fixtures with no staging/recovery media leftovers, and four normalization fixtures passing. This reviewer read their code and the final immutable source; it did not run tests, native deletion, media conversion or real-data mutation. Independent QA is separate. Constructor inspection still finds no destructive startup sweep; explicit Resume and durable completion callbacks retain the authorized policy. Failed/interrupted work and unproved bytes are preserved.

The storage_cleanup_authorizations table is a trust boundary for legacy proof: an actual finite caller must establish its exact bound hashes from existing immutable evidence or independently validated derivation, exclude unproved bytes, and be frozen/reviewed before it writes authorizations or deletes real copies. This RELEASE CLEAR certifies runtime/helper construction, not that such a caller has already been accepted or executed. Historical repair-copy purge likewise requires the exact caller's copy-hash binding. No source deletion, restore, app/focus, server restart or Git operation occurred in this review; no disposable probe was created, and all unique/unresolved evidence is preserved.

## Retained round-1 findings and history

The following review applies only to the original 96-file candidate. Its finding counts and blocked decision are historical; the closure table above governs candidate-v3.


## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-10
Tool: Books Arranger
Release: v0.6.0 candidate; VERSION still 0.5.0
Commit range: e7001bbd41e8b7d853a84339d47ef20c9cf91dc4..205a16d96e27aa207ac250a8e88c1ce3d8ea30ec, plus exact uncommitted candidate overlay below
Files changed: 12 files, +580 / -28 (Git-normalized text)
Stand-down dimensions: Electron-specific checks N/A — Python loopback web utility; no Electron renderer or installer
```

**Exact reviewed overlay:** `scratch/retention-cleanup-2026-10-10/candidate`, 96 files. `manual-contract.json` SHA256 `e122082becaf4d04c9f5d17f9655f18c5356cc2bc90b419c27541e5c033f0159`; declared source digest `1ed431958fb9c25af1560e2ccda615fa3b13571dad99cf7687398ed7ba67cff7`; base HEAD `205a16d96e27aa207ac250a8e88c1ce3d8ea30ec`, dirty=true. Independently recomputed every listed file's size and SHA256 twice: 96/96 match, zero mismatches. This report certifies these candidate bytes, not a later commit bearing the base HEAD.

The latest prior audit is `BooksArranger_SourceCleanup_Safety_v0.5.0_2026-10-10.md`, a focused safety audit rather than a formal nine-dimension release report. Its frozen-2 manifest SHA256 is `5666525f9421357fcd69c6f6440c3aba0c476059c0cd35c0cd146df4cb4d8eb9`. The prior source-cleanup, merge-service, review-backend and native-I/O pins map exactly to Git commit `e7001bbd41e8b7d853a84339d47ef20c9cf91dc4`, allowing for Git LF / Windows CRLF checkout representation. The subsequent committed range contains three documentation files, +106 / -0. The overlay adds nine changed files, +474 / -28, including new `storage_cleanup.py` and `tests/test_storage_cleanup.py`. `tests/test_metadata_frontend.js` is unchanged from base despite its inclusion in the brief. Counts come from Git numstat plus normalized new-file line counts and independent candidate Git-blob comparison.

## Summary

The candidate automatically discards conversion staging and temporary source-recovery copies after durable audio/source-cleanup success, records per-file native removal intent, and replaces permanent-recovery copy with retention status. Review covered all nine dimensions and traced output protection, source-retirement proof, ownership admission, native disposition, interrupted receipts, restoration and constructor/Resume/completion integrations. The output/recovery guards preserve many boundaries, but two new deletion paths can discard bytes without protecting the correct independently proved surviving artifact. Neither release nor the existing-copy purge is cleared for this candidate.

## Rubric

Severity definitions and the always-blocking safety floor: `Team/Docs/ProcessRules.md` § Severity definitions.

### 1. Security

- Status: **Fail** — F1 admits deletion without independent file ownership.
- **F1 [Critical] — `storage_cleanup.py:188`, `:196`, `:101`, `:110`.** Staging ownership is inferred from names for `checked.m4b`, `compatible.m4b`, `inputs.txt`, `chapters.txt` and UUID-shaped stdout/stderr. They receive `expected=None`; first observation is then inserted as a verified disposable receipt. The valid job-level `ownership.json` proves the job manifest but does not bind attempt directories or those file identities/bytes. Replacing `checked.m4b` with unique unrelated audio before the first cleanup, or inserting it under another UUID directory, passes admission and deletes that unique file while the unrelated final output remains healthy. The unknown-content test covers only an unrecognized filename. A full hash of the currently encountered file proves its present bytes, not that those bytes are an owned disposable copy.

No new shell execution or renderer privilege surface is added. Native deletion uses exact handles; ordinary-path checks reject traversal/device names; ancestor handles reject symlinks/junctions/reparse entries; deletion candidates reject hard links and additional streams; unknown filenames and nested Git entries fail closed. These mechanisms do not close F1.

### 2. Correctness & Logic

- Status: **Concerns**.
- **F3 [Major] — `source_cleanup.py:122`, `:230`.** Any storage-cleanup `needs_attention` state disables restoration, including a preflight failure before a single recovery copy was removed. Example: complete source retirement, add `unique.txt` to staging, run purge; all recovery MP3s remain intact, but status returns `restore_available=false` and restore immediately raises that files are unavailable after successful cleanup. The helper already verifies retained recovery bytes and refuses destination collisions. Capability should follow surviving verified member evidence and active work, rather than treating every purge error as a successful purge.
- **F4 [Major] — `storage_cleanup.py:49`.** Unconditional application of the new source-retirement validation contract rejects historical staging-only jobs whose valid output predates saved source PCM-frame evidence, even when every protected original is unchanged. Ender's separate read-only existing-data dry run reports this on Eye of God; MirrorMask/Snapshot pass its preflight. This refusal preserves data, but the requested historical leftover cleanup remains incomplete. No relaxation of source-retirement/recovery-deletion proof is cleared here.

### 3. Crash / Stability Safety

- Status: **Pass** — durable per-file intent precedes exact-handle disposition; interrupted outcomes/replacements fail closed or reconcile only registered intent, and purge errors leave completed audio status intact.

### 4. Performance

- Status: **Concerns**.
- **F5 [Major] — `merge_service.py:97`, `storage_cleanup.py:210`, `:213`.** Every Resume, including Resume invoked by Create/Queue, synchronously walks every completed job and hashes its whole final M4B before checking whether its storage cleanup is already completed. This runs under `operation_lock` on the caller's thread, so repeated additions can reread the whole completed library over Z: before starting new work. Completed purge receipts need bounded scheduling/admission so a growing library does not turn ordinary creation into an all-output reread. Destructive work must retain its fresh output protection.

### 5. State & Data Safety

- Status: **Fail** — F1 and F2.
- **F2 [Critical] — `storage_cleanup.py:253`, `:258`, `:260`.** `discard_repair_copy` protects and hashes the parent job's original final M4B. The repair journal check tests IDs and initial/final state labels, but does not bind, hash or hold the repaired final destination against the repair's recorded validated hash/size. A previously completed corrected artifact can be missing or changed while its retained `checked.m4b` is the last matching repair copy; this helper still deletes it because the older parent output passes. The docstring's instruction to validate the journal beforehand cannot protect the surviving corrected destination through disposition. No finite actual caller providing that missing held-output guarantee was included in the candidate contract.

For ordinary job cleanup, the completed manifest hash, complete validation record, exact final destination/parent identity and full output size/hash are checked under a held output handle. Retained sources are held and hashed; retired-source deletion requires matching completed intent, removed member/retirement records and absent originals. All targets are prepared before disposition. Per-file facts and intent survive restart; terminal paths reject replacements; unknown absence without removal intent fails. These protections do not establish F1's file ownership or F2's corrected final artifact.

### 6. Input Handling

- Status: **Pass** — UUID/path/ancestry checks and bounded ownership/repair journals fail closed; the new purge helper exposes no arbitrary-path HTTP endpoint.

### 7. Maintainability

- Status: **Pass** — the storage-disposal implementation is isolated and durable status separates cleanup from audio completion; no independent advisory construction issue found in this range.

### 8. Doc/Code Drift

- Status: **Concerns** — the current retention addendum correctly supersedes historical persistent-backup claims, but F1 contradicts the current exact-owned/unknown-content preservation promise, and F3 contradicts the promised recovery behavior after errors. These are counted in their owning safety/correctness dimensions only.

### 9. Build & Release Hygiene

- Status: **Pass** — the manual Python/Node snapshot contract names runtimes, checks and a 600000 ms deadline; no package.json/lockfile/installer applies. The 0.6.0 bump remains Sully's pending release action, and independent QA clearance is required against a corrected immutable candidate.

## Evidence and limits

The producer reported 37 relevant Python/Node checks passing; this review inspected their coverage but did not accept that count as evidence of independent staging ownership or correct repaired-final protection. `tests/test_storage_cleanup.py` covers changed outputs, incomplete retirement, unknown filenames, hard links, nested Git, interruption and changed replacements after a receipt already exists; it lacks pre-first-receipt replacement of a recognized temporary name and missing/changed repaired-final cases.

Constructor inspection found no destructive startup sweep. Explicit Resume scans completed jobs, and successful audio/source-cleanup callbacks invoke purge. Audio completion remains separate from storage failure. User authorization permits no backups after successful verification and removal of verified existing copies; it does not remove the need to prove which exact bytes are eligible or to protect their surviving output.

Senua performed read-only source/Git/hash inspection and wrote this report. No test, probe, media conversion, real deletion/restore, library/catalog mutation, app launch/focus, server restart or Git mutation occurred. No owned disposable output was created; candidate snapshots and unresolved review evidence are preserved. Actual deletion callers and future candidate changes require their own exact binding. This report does not certify corrected source that has not yet been frozen and reviewed.

## Verdict

- Total Critical: 2
- Total Major: 3
- Total Minor: 0

**Historical round-1 verdict:** RELEASE BLOCKED

| # | Sev | Dim | file:line | Finding | Must fix before release |
|---|---|---|---|---|---|
| F1 | Critical | 1 Security / 5 State & Data Safety | `storage_cleanup.py:188` | Recognized staging names enroll unknown current bytes as disposable. | Require an independent exact ownership/content binding established before cleanup for each deletable asset; preserve unproved recognized-name files. Add pre-first-receipt replacement/foreign-attempt cases. |
| F2 | Critical | 5 State & Data Safety | `storage_cleanup.py:253` | Repair copy deletion protects the older parent rather than the corrected final artifact. | Bind the retained copy and completed journal to the independently validated corrected final hash/size/path/ancestry, and hold that surviving corrected artifact through disposition; preserve on missing/changed/colliding evidence. Include the finite caller in the accepted source contract. |


## Verdict — final candidate v3

- Total open Critical: 0
- Total open Major: 0
- Total open Minor: 0

**Verdict:** RELEASE CLEAR
