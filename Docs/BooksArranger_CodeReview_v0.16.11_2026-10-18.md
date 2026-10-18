# Code Review — Books Arranger v0.16.11

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-18
Tool: Books Arranger
Release: v0.16.11
Status: FINAL; lean pass focused on hostile page content, network containment and the sweep's new temporary-cleanup path; dimensions 7 and 8 read lightly
Commit range: d6a10c7..2befe71e64ad482834f0b7cb159d91eb1cba6bd2
  d6a10c7 docs: record v0.16.10 review and QA verdicts (docs only; the v0.16.10 report cleared 0a2bc63..1dea749)
  1a69587 feat: series from Goodreads with FantLab fallback; finish orphaned temp cleanup
  2befe71 chore: release v0.16.11 (package.json, package-lock.json, CHANGELOG in one commit)
Files changed: 11 files, +374 / -15 (code: public_research.py, merge_service.py, scripts/check-desktop.mjs)
Stand-down dimensions: none
Release source commit: 2befe71e64ad482834f0b7cb159d91eb1cba6bd2
Release artifact manifest SHA256: e8e0aa44d6790d4e71428a911efd14a0fbe7e7a308e497cdef5516d4f033bf5b
Release installer: dist/builds/8102e126-aa3a-458a-abf1-1ed2f223b519/Books-Arranger-Setup-0.16.11.exe
Release installer SHA256: f92fbfca58e54d17e66e27d8d6f97ed83793ba9451e4db293de6c58fe4984712
```

## Summary

v0.16.11 adds two things:
- Series research from Goodreads book pages, with the cycle order on FantLab as a fallback.
- Temporary-cleanup errors after a book are now persisted, and a once-per-run sweep step (`_finish_temporary_cleanups`) runs the normal post-book cleanup for completed books that have no temporary-cleanup record.

I read every code hunk and the CHANGELOG. I also traced how the series name reaches the output path (`metadata.propose`, `safe_name`) and how the shared HTTP client maps errors.

Evidence I gathered myself:
- The installer hashes to the SHA256 above. `dist/release-artifacts.json` hashes to the manifest SHA256 above and names version 0.16.11 and `source_head` 2befe71.
- All 51 packaged backend and `web/` files have the same content as HEAD.
- Seven suites (series_research, local_identity, recovery_retention, local_admission, split_books, storage_cleanup, backup_rule; 144 cases) ran green, 0 skipped.

## Release questions

1. **Can hostile page content inject into paths or names? No.**
   - **Text.**
     - Goodreads and FantLab names pass through `text()`, which collapses whitespace and caps at 300 characters.
     - The number must be a whole number: `[1-9]\d{0,3}` for Goodreads, a counted integer for FantLab.
     - The page's own record must match the local title (`title_key`) and every credited person (`_same_people`).
   - **Path.** In the output path the series goes through `metadata.safe_name`:
     - Windows-reserved characters and control characters (`<>:"/\|?*`, `\x00-\x1f`) become `_`;
     - trailing dots and spaces are stripped, so `..` becomes `_`;
     - reserved device names get a prefix;
     - the value is capped at 160.
     - The whole proposed path is refused above 240 characters.
   - **Tags and comments.** Tags go to ffmpeg as argument-list `-metadata` values (`shell=False`), and comments are escaped.
   - **Parsing.** Pages are parsed by regex and `strict_json`, with bounded captures (`\d{1,12}` ids). Every lookup error is caught inside `goodreads_book`.
2. **Network failure contained? Yes.**
   - Goodreads requests go through the shared client: the `www.goodreads.com` allowlist entry, pinned TLS, `MAX_BYTES`, challenge detection, and `HOST_POLICY` (120 per hour, 5 s spacing) with its cache.
   - The client turns every failure except `InterruptedError` into `ResearchWait`.
   - On the main research path, the series lookup catches `ResearchWait`, `ValueError`, `TypeError`, `KeyError` and `AttributeError` and carries on without a series. On the gap path it runs inside `attempt()`. Pause still propagates.
3. **Is the sweep's new completion path deletion-safe? Yes.**
   - `_finish_temporary_cleanups` (`merge_service.py:702`) only calls the existing `_prune_completed` under `operation_lock`. It passes a stop flag, which skips the recovery purge.
   - That runs `storage_cleanup.run` without recovery copies. It starts with `protected_output` (a full output hash), then `_source_safety`: completed retirement, or a full hash of the retained originals. A cleanup-enrolled book whose source retirement is not complete is refused.
   - Then `run_folders`, which itself starts with `protected_output`. Then `_prune_working`, whose receipts are verified.
   - A book is skipped when its source cleanup is not complete, when it is in its own post-processing (`_post_jobs`), or when it was already tried this run.
   - Failures are recorded through `_diagnose`. Nothing deletes on catalog state alone.

## Rubric

### 1. Security

- Status: Pass
- Findings: none (release questions 1-2).

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - `public_research.py:920-923` [Minor] On the gap path, a FantLab-only series answer re-adds `goodreads` to `closed` whenever Goodreads was unavailable, so the book's gap is deferred until Goodreads reopens. That is intended ("Goodreads decides"), but it sits awkwardly with the CHANGELOG's "an unavailable Goodreads never holds a book" if Goodreads stays challenged for long. Confirm the deferral is bounded.

### 3. Crash / Stability Safety

- Status: Concerns
- Findings:
  - `merge_service.py:702` with `:768` [Minor] The jobs thread marks a book `completed` before `_after_completed` adds it to `_post_jobs`. In that window, the sweep can start `_prune_completed` on the same book alongside the converter's own post-processing. Receipt CAS and handle leases make one side fail safely. A cleanup-enrolled book is refused outright until its retirement completes. At worst there is a transient temporary-cleanup attention record, and the next run retries it.

### 4. Performance

- Status: Concerns
- Findings:
  - `merge_service.py:702` [Minor] On the first run after upgrade, every completed job without a temporary-cleanup record gets the full verified cleanup. That means a full hash of its output on the library share, and, for books without source cleanup, of its retained originals, one book at a time under `operation_lock`. If many old jobs lack a record, that is a long first-start read. Any job that cannot prove its staging will show a temporary-cleanup reason (safe direction). Futaba can count such jobs on the catalog copy.

### 5. State & Data Safety

- Status: Pass
- Findings: none new (release question 3). The v0.16.8 Minor, that working and temporary paths do not consult `kept_files`, stands. It is now reachable once per run from the sweep too, and it still deletes only redundant verified copies.

### 6. Input Handling

- Status: Pass
- Findings: none. Page bytes are bounded by `MAX_BYTES`, captures are bounded, and malformed records give "no series" or a refusal.

### 7. Maintainability

- Status: Pass
- Findings: none.

### 8. Doc/Code Drift

- Status: Pass
- Findings: none beyond the gap-deferral note in dimension 2.

### 9. Build & Release Hygiene

- Status: Pass
- Findings: none.
  - The version bump and lockfile are in the same commit.
  - The artifact and manifest hashes match the brief, and the packaged files match HEAD.
  - `test_series_research.py` and `test_local_identity.py` were added to the gate.

## Verdict

- Total Critical: 0
- Total Major: 0
- Total Minor: 3

**Verdict:** RELEASE CLEAR
