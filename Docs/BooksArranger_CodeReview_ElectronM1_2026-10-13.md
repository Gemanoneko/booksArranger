# Books Arranger — Electron M1 code review

Reviewer: Senua. Date: 2026-10-13. Scope: frozen integrated M1, not final v0.16 installer acceptance.

Commit range: `57ab44b4583f5b2f55ca3bbb074fe9d8cc6edcf7..e827b5bf866be2690279c155bb729afbf73c9d1d`. Read immutable Git blobs, not concurrent M2 working files. Diff: 20 paths, +5075/-44 text lines; icon is binary and excluded from text totals. Existing v0.15 conversion/source/publication/recovery checks are inherited and not recertified by this limited M1 review.

## Findings

### C1 — Critical: PID-only forced tree termination

`desktop/main.js:217` invokes taskkill /PID /T /F using only child.pid and an asynchronously updated exit flag. Startup failure and a single failed authenticated Quit GET/POST reach this path; 90 seconds without HTTP also forces it. Neither lost HTTP nor delayed exit delivery proves an idle engine or the current process generation. PID reuse can target an unrelated process tree; a genuine engine can be terminated during publication, retirement or recovery. Must remove numeric-PID force termination, retain native process-generation ownership and use safe-checkpoint shutdown. Do not equate unreachable with nothing to finish.

### C2 — Critical: shutdown timeout releases ownership despite active work

`desktop_backend.py:96` catches finish_shutdown failure and always calls server.shutdown. An actual close TimeoutError means a worker has not reached its safe checkpoint. Returning serve_forever releases owned_instance_record before the final server_close retry; a further timeout can end the process/release the catalog while daemon workers remain. The new test named test_shutdown_still_stops_serving_when_close_fails explicitly expects this unsafe fallback. Must hold owner/catalog and surface a blocked shutdown until workers actually park; never replace failed safe close with unconditional shutdown or successful exit.

### C3 — Critical: stale-record rename precedes source/data authorization

`desktop_backend.py:237` runs retire_stale_record before web_server.main validates the selected catalog against protected source roots and acquires its catalog lease. At lines 196–209 it accepts any small JSON containing an ended PID, lacks application/schema/native identity checks, and renames a path after an unleased read. An inventory path within a source-library folder can rename that folder's web-instance.json before catalog_lock refuses; a replaced record may be renamed instead of the read record. Must establish ordinary data ancestry/source exclusion and startup/catalog ownership before mutation, and retire only the exact verified application record through identity/content/stream/link checks. Preserve substitutions.

### C4 — Critical: build cleanup follows unchecked ancestor junctions

`scripts/fetch-runtime.mjs:94`, `:102` and `scripts/stage-backend.mjs:31` recursively delete targets under build-cache without verifying resolved/reparse-safe ancestor ownership. A junction at build-cache or its runtime/extract ancestors redirects deletion and subsequent extraction/copy outside the owned build tree. A final target symlink not being followed does not protect intermediate ancestors. Must validate exact absolute resolved owned targets and native ancestry before every destructive delete/extract/copy. No arbitrary existing folder may be adopted as disposable.

### M1 — Major: integrated backend version regresses

`package.json:4` and lockfile report 0.14.0 while this integrated range follows accepted v0.15.0 and removes tracked VERSION. Source and staged backend now advertise 0.14.0 through the new single version source. Sully must set the actual release version consistently before final installer acceptance; M1 is not a release-ready version claim.

### m1 — Minor: M1 document describes a different state

`Docs/BooksArranger_Electron_M1_2026-10-13.md:3` says uncommitted on an earlier base and describes obsolete overlap with uncommitted split work, whereas this review pins an integrated committed export. Update final release documentation to distinguish historical tests from this integrated pin and from unproven installer/tray/sign-out evidence.

## Method and limits

Static red-team review of complete new shell/backend/catalog-owner/runtime-fetch/backend-stage/cleanup/package/configuration code and all modified worker/server hunks; reviewed desktop quit tests, UX contract and M1/Brief changes. Inspected unchanged owner-record native handle lifetime, finish_shutdown/server_close ordering, worker close timeouts and retained native/source safeguards. Lockfile: 285 entries; all resolved dependencies HTTPS with integrity values. Runtime archive URLs/hashes/license-source metadata are pinned in source; no independent download, provenance attestation, installer run or signed-runtime claim made here.

No private execution was needed to identify these source-level blockers. Existing sender M1 test claims are historical evidence, not an independent pass on this frozen integrated pin. No live app, process kill, data, source library, Z:/Y:, migration, install or Git mutation performed by reviewer. No product code edited. Concurrent M2 changes remain excluded; corrected source needs a new pin and independent tests/review.

## Nine dimensions

1. Security — **Fail**: C1 PID-only tree kill and C4 out-of-scope junction writes/deletes; renderer isolation/sandbox/no Node and desktop token separation otherwise inspected.
2. Correctness & Logic — **Fail**: C2 converts safe-close refusal into shutdown; drain stops subsequent jobs on the ordinary successful path.
3. Crash / Stability Safety — **Fail**: C1/C2 bypass safe checkpoints on HTTP/worker failure.
4. Performance — **Pass**: bounded diagnostic log and streamed download/hash paths; no throughput or full-library timing claim.
5. State & Data Safety — **Fail**: C2 ownership release and C3 unauthorized/racy stale-record mutation; existing source/recovery/24-hour guards unchanged.
6. Input Handling — **Fail**: C3 record adoption and C4 ancestry gaps; shell options use argument lists and strict ports.
7. Maintainability — **Pass**: catalog lease extracted without GUI imports; desktop control/drain responsibilities explicit.
8. Doc/Code Drift — **Concerns**: m1 historical/uncommitted claims do not describe integrated pin.
9. Build & Release Hygiene — **Concerns**: M1 version regression; final installer, license/archive provenance and artifact content still require exact release evidence.

Severity and always-blocking safety floor follow Team/Docs/ProcessRules.md § Severity definitions. Wrong-original retirement or out-of-scope source mutation always blocks.

## Verdict

Open findings: Critical 4; Major 1; Minor 1. C1–C4 must be fixed before installer release.

**Verdict:** RELEASE BLOCKED

This is the M1 construction verdict only. It does not replace final v0.16 review, QA, runtime/installer validation, or authorize launch/update/source retirement.
