# Code Review — Books Arranger v0.16.9

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-18
Tool: Books Arranger
Release: v0.16.9
Status: FINAL; lean pass focused on the file-ID change and the mdat-size repair; dimensions 4, 7 and 8 read lightly
Commit range: 5ff200f..0a2bc63709006d5ef8a2e2ac92fbc3444a6844f6
  5ff200f docs: record v0.16.8 review and QA verdicts for af3a38d (docs only; the v0.16.8 report cleared 1e15943..af3a38d)
  33e6e57 fix: SMB file-ID drift no longer flags unchanged sources; two more M4B shapes
  0a2bc63 chore: release v0.16.9 (package.json, package-lock.json, CHANGELOG in one commit)
Files changed: 11 files, +160 / -27 (code: review_backend.py, audio_jobs.py, m4b_preservation.py, failed_m4b_retry.py)
Stand-down dimensions: none
Release source commit: 0a2bc63709006d5ef8a2e2ac92fbc3444a6844f6
Release artifact manifest SHA256: 9c32a68d676cbb8b3cda4ebc75f27136f6dc03d3227305c947c7abd0abb98ba5
Release installer: dist/builds/fcfb5802-7934-4408-a832-b8d0a6ecf6aa/Books-Arranger-Setup-0.16.9.exe
Release installer SHA256: 8469f8c9caa3d5735082745b24d4ed5d7c38ea049cb4c7f073b9cc31c9f565d5
```

## Summary

v0.16.9 makes four changes:
- Across time, a reviewed source is now screened by size and mtime, and its full content hash decides. Windows file IDs are dropped, because they drift on the SMB library share.
- The worker guard's "Source changed — review required" stop is now Retry-able.
- `alis` self-reference is accepted on the chapter-image (`vide`) track.
- A user-approved repair handles an understated final `mdat` size.

I read every code hunk and the CHANGELOG.

Evidence I gathered myself:
- The installer hashes to the SHA256 above. `dist/release-artifacts.json` hashes to the manifest SHA256 above and names version 0.16.9 and `source_head` 0a2bc63.
- All 51 packaged backend and `web/` files have the same content as HEAD.
- Six focused suites (m4b_preservation, review_backend, attention_actions, failed_m4b_retry, attention_repair, blocked_retry; 159 cases) ran green with the bundled ffmpeg, 0 skipped.

## Release questions

1. **Can ignoring file IDs let a genuinely changed source through or reach a deletion? No.**
   - **`build_manifest`.** It screens by size and mtime and then always compares a full SHA-256 against the reviewed hash (`review_backend.py:578`). `source_hash` still uses the full `identity()`, including dev and ino, for its same-moment checks: before the read, after the read, and against a fresh stat. Changed bytes therefore always refuse.
   - **The worker's revision guard.** It runs `build_manifest`, before the runner and again before publication intent, so the same hash decides.
   - **Conversion.** Snapshot and copy verify the reviewed SHA-256 once more.
   - **The size+mtime-only screen** (`review_backend.py:141`) feeds only the row's create eligibility and reason. It decides nothing that writes or deletes.
   - **Deletion paths are untouched.** Source cleanup's `_match` still requires the reviewed dev/ino plus a full hash (`source_cleanup.py:287`), and every backup purge re-proves the output and each copy's content (the v0.16.8 review).
   - **The new Retry cause `source`** (`audio_jobs.py:72`) matches only the exact guard text on a `ValueError`. `_retry_shape` still refuses anything with `publication_intent`. Pressing Retry requeues the job, and the worker re-runs the hashing guard before any work.
2. **Is the mdat-size repair narrow and proven? Yes.**
   - **Gate.** It runs only when `REPAIR_MDAT_UNDERSTATED` is approved (the Repair press; strict plans are unchanged). It also requires all of:
     - the previous top-level box is the final `mdat`;
     - at most 64 KiB remain;
     - those bytes do not parse as an allowed top-level box (`is_box`).
   - **Shape.** `plan()` then requires:
     - a 32-bit `mdat` header;
     - audio chunk spans that are contiguous, cover `[declared end, EOF)` and end exactly at EOF;
     - no chapter sample past the declared end.
   - **Overlap.** The usual overlap and full-mapping checks still apply.
   - **Patch.** The only change is the 4-byte size field at the `mdat` start (`header_patches`), applied through the same `_patched` path as the moov→free patch.
   - **Proofs.** `verify_candidate` re-reads every other source byte unchanged. On this non-silence path, full decoder/packet evidence and full native PCM equality between source and output still follow, and `confirm()` binds the applied facts to the approved ones.
   - **`alis` on `vide`.** It is accepted only with the exact `00000001` payload, which is the same rule as for text.

## Rubric

### 1. Security

- Status: Pass
- Findings: none.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - `audio_jobs.py:72` [Minor] A source whose content really changed is now grouped under "Can retry", and "Retry all" includes it. Its Retry stops again with the same reason, when the real remedy is a fresh review. This is safe, since the guard re-hashes, but it can mislead.

### 3. Crash / Stability Safety

- Status: Pass
- Findings: none.

### 4. Performance

- Status: Pass
- Findings: none. `is_box` reads at most 16 bytes, within the existing read bound.

### 5. State & Data Safety

- Status: Concerns
- Findings:
  - `source_cleanup.py:287` [Minor] Source cleanup still compares the reviewed file ID (dev/ino). A book whose ID drifted now converts and publishes, but its source cleanup will hold with "Reviewed original file identity changed or cannot be verified". That is safe in direction: the originals and backups are kept. However, it is outside the kept-file groups and inconsistent with the new rule; it is likely the next "Cabal".

### 6. Input Handling

- Status: Pass
- Findings: none. Trailing bytes go through `is_box` with explicit 8- and 16-byte length guards; anything else is refused or takes the strict path.

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
  - The new cases sit in suites that are already in the gate.

## Verdict

- Total Critical: 0
- Total Major: 0
- Total Minor: 2

**Verdict:** RELEASE CLEAR
