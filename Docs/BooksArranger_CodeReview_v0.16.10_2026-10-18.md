# Code Review — Books Arranger v0.16.10

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-18
Tool: Books Arranger
Release: v0.16.10
Status: FINAL; lean pass focused on the revision-guard comparison and the now-live conversion-time repair checks; dimensions 4, 7 and 8 read lightly
Commit range: 0a2bc63709006d5ef8a2e2ac92fbc3444a6844f6..1dea7494bf158a17e225381747e799606e00d89e
  f984a4b docs: record v0.16.9 review and QA verdicts (docs only; the v0.16.9 report cleared 5ff200f..0a2bc63)
  5ca7dee fix: retry and repair jobs no longer fail the start-of-book source check
  1dea749 chore: release v0.16.10 (package.json, package-lock.json, CHANGELOG in one commit)
Files changed: 9 files, +281 / -9 (code: merge_service.py, audio_jobs.py)
Stand-down dimensions: none
Release source commit: 1dea7494bf158a17e225381747e799606e00d89e
Release artifact manifest SHA256: aaf2b0cac455eb4419cd0138dcf7d15d08d0e1772cc0d752ba9161cc86a6778c
Release installer: dist/builds/e10961b5-abe1-41fd-b4e9-51e8ebdafe98/Books-Arranger-Setup-0.16.10.exe
Release installer SHA256: b9cbfc40ebd42bdf74460d688dfcd9e4d936b6006237c6060823fc00e188305e
```

## Summary

v0.16.10 changes three things:
- The worker's revision guard (`MergeService._guard`) now leaves the job-only fields (`job_id`, `attempt_id`, `m4b_repair`) out of its comparison against a freshly rebuilt manifest. From 0.16.7 through 0.16.9, the `m4b_repair` binding made every Retry/Repair child fail the guard before any work.
- A child stopped only by that guard can be retried as itself, keeping its approved repair.
- Repair children are grouped under "Repair".

I read every code hunk and the CHANGELOG.

Evidence I gathered myself:
- The installer hashes to the SHA256 above. `dist/release-artifacts.json` hashes to the manifest SHA256 above and names version 0.16.10 and `source_head` 1dea749.
- All 51 packaged backend and `web/` files have the same content as HEAD.
- Seven focused suites (attention_repair, attention_actions, blocked_retry, m4b_preservation, failed_m4b_retry, review_backend, status_snapshot; 182 cases) ran green with the bundled ffmpeg, 0 skipped.

## Release questions

1. **Can excluding the job-only fields let a changed review or source through? No.**
   - `build_manifest` never produces `m4b_repair` or `attempt_id`. It produces a fresh `job_id`, which the old comparison already ignored.
   - Every review-decided field is still compared for equality: sources with their re-verified hashes, metadata, cover, destination, profile, evidence and cleanup policy.
   - `build_manifest` still re-hashes every source in full (size+mtime screen, full SHA-256, same-moment `identity()`). A changed review or source therefore still stops the job, both before the runner and again before publication intent.
   - The excluded binding is no review property. It is checked elsewhere:
     - at admission, by the `enqueue` CAS on the parent row, manifest hash, `book_groups`/`candidate_context` and `audio_repair_admissions`;
     - at conversion, by `approved_repairs()` plus `confirm()`, which requires the applied repair to equal the approved one in kinds and facts.
   - Replacement manifests keep their own exact-equality branch.
   - The E5 relaxation (`audio_jobs.py:525`) is narrow. It applies only to a child whose recorded failure is exactly the guard's `ValueError` (`failure_cause == 'source'`). The child must not be a parent of another child, the newest job for the book, and pass E4 and E7-E10. Busy and space failures of a child stay non-retryable.
2. **The conversion-time repair checks, now reached live: sound.** I reviewed them in v0.16.7 (`c654593`) and v0.16.9 (`33e6e57`).
   - The approved kinds are passed to `plan()`, and `confirm()` binds the facts. The facts do not depend on tags or cover, so the stage-snapshot plan reproduces the admission diagnosis exactly.
   - `verify_candidate` re-reads every source byte apart from the planned patches.
   - The silence repair is proven by `prove_silenced_tail`.
   - The other repairs (dangling chapter, tail overrun, understated `mdat`) are proven by full decoder/packet evidence and full native PCM equality.
   - Before this release those checks had run only through Ender's direct `create_private()` harness and the unit suites, never through the worker. The first live repairs are worth Futaba's attention on scratch copies; that is a QA matter, not a code finding.

## Rubric

### 1. Security

- Status: Pass
- Findings: none.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - `merge_service.py:1086` [Minor] `_queue_next_same` writes the ledger row with `INSERT OR REPLACE` keyed by the job id. For a child, its `child_job_id` (the job itself) collides with the `UNIQUE child_job_id` of the parent's admission row, and `REPLACE` deletes that row. Queue order is still right, but the parent's ledger record of the admission is lost, so `describe(parent)` returns nothing. This is cosmetic; the parent is superseded and hidden.

### 3. Crash / Stability Safety

- Status: Pass
- Findings: none.

### 4. Performance

- Status: Pass
- Findings: none.

### 5. State & Data Safety

- Status: Pass
- Findings: none. The guard still decides on fully re-hashed sources and the frozen review. A requeued child keeps its hash-bound manifest and approved repair. No deletion path changed.

### 6. Input Handling

- Status: Pass
- Findings: none.

### 7. Maintainability

- Status: Pass
- Findings: none.

### 8. Doc/Code Drift

- Status: Pass
- Findings: none. The CHANGELOG matches the code.

### 9. Build & Release Hygiene

- Status: Pass
- Findings: none.
  - The version bump and lockfile are in the same commit.
  - The artifact and manifest hashes match the brief, and the packaged files match HEAD.
  - The new cases are in `test_attention_repair.py`, which is in the gate.

## Verdict

- Total Critical: 0
- Total Major: 0
- Total Minor: 1

**Verdict:** RELEASE CLEAR
