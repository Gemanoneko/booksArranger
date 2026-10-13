# Code Review — Books Arranger v0.15.0 round 4

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-13
Tool: Books Arranger
Release: v0.15.0 candidate; urgent operational subset only
Commit range: d3c5526..6bd10c97e355021f4458defd8c390727f573414a
Files changed: 7 files, +495 / -2 (git diff --numstat)
Operational delta: 4 files, +293 / -0 (storage_cleanup.py, cleanup_published_working.py, tests/test_working_cleanup.py, Docs/BooksArranger_WorkingCleanup_Delta_2026-10-13.md)
Stand-down dimensions: none; Electron absent from this subset
```

## Summary

This report clears only the committed urgent working-file cleanup helper and historical caller. Prior R3 covers the application through d3c5526. Commits 8874f53 and 6bd10c9 add working-only cleanup independent of source retirement, an exact historical caller, native tests and documentation. The intervening 04eb08c changes only prior reports/handoff. Uncommitted audio_pipeline.py and future service integration are excluded. This is not v0.15.0 release clearance or live cleanup acceptance.

A's corrected inventory is 136 receipt-matched normalized WAVs totaling 119317276892 bytes across the eight exact UUIDs. The caller pins this scope and an externally reviewed plan hash. Publication proof necessarily reads the eight published destination M4Bs; it never selects originals, snapshots, recovery, unfamiliar content or other attempts. The app must first relinquish the catalog lock by the separately approved supported idle shutdown. No reviewer live data access, app operation or Z:/Y: access occurred.

## Evidence and method

- Read the complete committed helper/caller/test/doc diff, prior R3, handoff, StandingRules, Brief and relevant unchanged native/publication/retirement/storage/locking boundaries.
- Independently created a git-archive copy of 6bd10c9 under scratch/senua-cleanup-2026-10-13/pin-6bd10c9. All 224 source files independently hashed exactly match sender's immutable file map; source digest 67570c0e427110030cd47aff814153c2cbdc33b7a5f9e012922037fb8edc7d49.
- Separately reviewed scratch manual_owned.py and manual_inner.py: finite child, CREATE_SUSPENDED, existing OwnedProcessJob, private UUID source copy, 550-second child deadline and pre/post source/runtime/harness pin checks. Exact context SHA-256 cbed742afe64ca917cc66446c87a6285f4fb2b7e316f20431fb4282e8fec2a86; outer 3494696e5a33aa11426fcbd4b4fbfc3a62c90dcfcc465874cd0420c0698a3a31; inner e3ed777d11d79479113e3cdcfad50bb05aded338457b58ae5efefb821f5d861a.
- Independently ran the identical manual route with C:/Python314/python.exe -I -B: 15/15 native tests passed, owned elapsed 2.88 seconds. Evidence: scratch/cleanup-delta-2026-10-13/manual-log-manual-run-db3c5eaf-4d99-4eee-b5d8-8ee024af402f.txt. This is a separately reviewed manual contract, not an automated package qa-handoff receipt.
- Tested output/source-byte refusal, hardlinks, ADS on working files, unknown absence, terminal identical-byte replacement, traversal receipt, wrong ownership, unknown attempt, frozen native identity, dry-run no removal, source/snapshot preservation and post-disposition crash reconciliation.
- Separately reviewed fixed PLAN-only scratch wrapper run_historical_plan.py, SHA-256 4fb123ddaa7be8942437a1cfe1142db483ffd80d801a32a5da67db4fb3e187c7: hardcoded context digest, exact complete immutable source map before imports and after execution, fixed live-data/backup/new-evidence argv. It selects no apply/shutdown/start operation. This planning route is cleared only for the already authorized exact C working files and eight published destination hashes.
- Separately reviewed fixed shutdown/APPLY wrapper run_historical_apply.py, SHA-256 c1c14ae6550c19e964d2b550264f9ca8baa4a9de390d1c60fa3e2b551da5d3cb. Scope: exact paused v0.14.0 native PID 8424, instance 25fa543d2cc4e0dedfa9e6425810ae3c and creation FILETIME 134363615099387283; unchanged standard verify_idle; token-guarded supported shutdown; exact process exit, ownership-record absence and exclusive port; original exclusive catalog lock plus critical catalog projection and held C snapshots/recovery; frozen plan a6305f64b5e2a114f79021a5f7793686d00af4fe600e0a11a6a312a1776214ac; exact context/source/runtime hashes before imports and after operation. Explicit narrow operation CLEAR sent under Jane’s authorization. No restart/Start/retirement is included; this is static clearance, not an actual success claim.
- Separately reviewed approved-operation supervisor run_historical_apply_owned.py, SHA-256 c3a13a0ca5715e2e61950d25c45120d638411fc46d1d570a24efc6d9b80142b5: fixed c1c14ae operation wrapper hash, immutable source/context, suspended isolated child within OwnedProcessJob, 550-second deadline and exclusive evidence log, source/wrapper postchecks. Child verifies pinned runtimes before any live action. Static clearance extends only to this one bounded previously approved operation.
- Inspected corrected caller resume: remaining native names plus absent names backed by exact frozen-plan job/kind/hash/size/facts removal-intent or completion receipts. Original total approval remains fixed; unknown absence does not reduce scope silently.

## Actual urgent operation evidence

Independently read Ender’s owned result, operation result and inner log after execution: exit 0, owned elapsed 271.246 seconds; exactly 136 approved WAV names absent and 119317276892 logical bytes removed. C: free bytes changed from 36622192640 to 155916890112 (actual gain 119294697472). The wrapper held 148 source snapshots/recovery files/ownership markers, and protected catalog projection 62a66312ce867ff9430afc1596b5e1f5c3ff1661000b2f276f7ca9b61d6c2ffa remained identical. Plan hash matches a6305f64b5e2a114f79021a5f7793686d00af4fe600e0a11a6a312a1776214ac. Evidence files are scratch/cleanup-delta-2026-10-13/historical-A-apply-owned-result.json, historical-A-apply-result.json and historical-A-apply-inner.txt. The app remains stopped. No restart/Start or original retirement is claimed. This confirms the narrow urgent operation, not acceptance of the pending full media/service delta.

## Rubric

Severity and safety floor follow Team/Docs/ProcessRules.md § Severity definitions.

### 1. Security

- Status: Pass. No new shell execution; allowlisted basename/attempt/job selection, held ancestry/native handles, link/stream checks and frozen plan identity prevent arbitrary-path disposal.

### 2. Correctness & Logic

- Status: Pass. Exact published-attempt receipts select disposable working files; normalized-only historical caller restricts eight UUIDs and corrected 136-file/119317276892-byte scope.

### 3. Crash / Stability Safety

- Status: Pass. Per-file CAS intent/disposition journals converge after partial cleanup; frozen-plan remaining-name validation refuses unknown absence and native replacements.

### 4. Performance

- Status: Pass. Bounded eight-job scope and streaming native hashes; no library discovery, bulk PCM export or new background worker.

### 5. State & Data Safety

- Status: Pass. Working cleanup never completes full storage_cleanup_jobs, retires originals, removes snapshots/recovery, changes the 24-hour policy or starts retention; published output handles remain held during disposition.

### 6. Input Handling

- Status: Pass. Hash-bound plan, exact catalog publication records, UUID/name policy, ownership marker, file facts and producer-byte checks fail closed on changed input.

### 7. Maintainability

- Status: Pass. Reuses existing native disposal/CAS primitives and keeps the historical operation separate from full cleanup obligations.

### 8. Doc/Code Drift

- Status: Pass. Document explicitly corrects handoff count, describes subset exclusions, exclusive shutdown requirement and resumable frozen approval.

### 9. Build & Release Hygiene

- Status: Pass. Committed source pin normally pushed; version unchanged for operational subset; separately reviewed finite manual runner/source/runtime pins match independent rerun.

## Verdict

- Total Critical: 0
- Total Major: 0
- Total Minor: 0

**Verdict:** RELEASE CLEAR

Scope: urgent operational subset at 6bd10c97 only. Independent Futaba subset GO, the exact reviewed plan/native checks, supported idle shutdown and exclusive catalog ownership preceded the successful narrow A operation documented above. No source retirement is cleared by this report. Full v0.15.0 cleanup/media/service delta requires a later committed pin, QA and review before release.
