# Code Review — Books Arranger v0.16.12

## Header

Reviewer: Senua (Code Reviewer)
Date: 2026-10-18
Tool: Books Arranger (Electron desktop utility)
Release: v0.16.12
Commit range: 68a7cdc..14eea665728116a6f89d0ebd3d365c1b627f9a17
Files changed: 19 files, +1175 / -48 (git diff --stat)
Release source commit: 14eea665728116a6f89d0ebd3d365c1b627f9a17
Release artifact manifest SHA256: 86f602de252e600b99afc80c7358c9e68abfc9bf158094be728ac211273613ac
Release installer: dist/builds/4be1f71f-0f5c-4bb5-8bcd-b241101d64a6/Books-Arranger-Setup-0.16.12.exe
Release installer SHA256: b17d3276d4ae9c4c31a4e44a572932e5105b508fa36480055ffebe35bc3cf584
Stand-down dimensions: none.

## Summary

Red-team review of the series backfill, metadata rewrite proofs, queue/retry changes, catalog read transaction change, frontend controls, and release version/build checks. The actual manifest and installer were independently hashed and match the handoff. Review stopped at confirmed Critical recovery/data-safety failures, as briefed. No real library/catalog was opened or modified, and no installer/application was run. Existing test source was inspected; the broad suite was not run. No matching local Lessons/Patterns file was found by a filename search through the repository's first two levels.

## Rubric

### 1. Security

Status: Concerns. No new shell interpolation or Electron security configuration changes were found in the accumulated diff; pathname-based deletion lacks the existing protected ancestry/handle discipline (F2).

### 2. Correctness & Logic

Status: Fail. F1: `series_backfill.py:397-416` [Critical] — restarting in `renamed` skips the new-file proof, and restarting in `cataloged` goes straight to deleting the former file without checking whether the replacement exists or remains complete.

### 3. Crash / Stability Safety

Status: Fail. F1 applies to persisted recovery states, including a restart after catalog commit and before former-file removal. The existing restart tests cover `written` and `renamed` with intact files, not a missing/damaged replacement in `cataloged`.

### 4. Performance

Status: Pass. The diff introduces paced background series research and bounded streaming metadata/media hashing; catalog page reads avoid taking a write lock when groups are current.

### 5. State & Data Safety

Status: Fail. F2: `series_backfill.py:412-416` [Critical] — deleting the former file requires only its historical size, ignores `old_sha256`, and uses an unprotected pathname; a different same-size file at that path is removed, and an ancestry/name swap can redirect the deletion. This violates the requirement to remove only the verified former copy. F1 independently permits deleting the sole remaining complete copy.

### 6. Input Handling

Status: Concerns. New destination proposals and metadata lengths are checked, but replayed records and deletion paths lack protected identity/ancestry validation (F2).

### 7. Maintainability

Status: Pass. Backfill state transitions and proofs are localized and documented; the main issue is safety coverage rather than style.

### 8. Doc/Code Drift

Status: Concerns. The module's claim that resumed updates preserve a proven replacement is contradicted by F1; this is supporting evidence for that finding, not a separate count.

### 9. Build & Release Hygiene

Status: Pass. Version and lockfile advance together, integrated checks include backfill tests, and the exact existing installer/manifest hashes match the handoff. This binding does not clear a future rebuilt artifact.

## Reproduction evidence

A bounded Python snippet imported `SeriesBackfill`, constructed a private instance without opening a catalog, and supplied a `cataloged` entry with a private original-file stand-in and an absent replacement. Calling the actual `resume()` implementation produced:

```json
{"old_survives": false, "new_exists": false, "final_states": ["done"]}
```

Evidence directory: `C:/Users/AnGeLZzZ/AppData/Local/Temp/books-codex-20261018/senua-cataloged-recovery-6m231iz8`. This is a state-machine deletion reproduction, not an audio/playback test. It uses no actual book bytes and does not claim the app itself caused the replacement to disappear. The recovery state currently has no defense against that condition. Session scratch is retained for Sergei under the standing scratch exception.

## Verdict

- Total Critical: 2
- Total Major: 0
- Total Minor: 0

**Verdict:** RELEASE BLOCKED

| # | Sev | Dimension | Location | Must fix before release |
|---|-----|-----------|----------|-------------------------|
| F1 | Critical | Correctness / crash recovery / data safety | `series_backfill.py:397-416` | Revalidate the complete replacement at every resumed destructive transition, including directly entered `renamed` and `cataloged`; hold safely and preserve the original if the replacement is missing, changed, unprovable, or unavailable. Add isolated missing/corrupt replacement recovery cases. |
| F2 | Critical | State & data safety | `series_backfill.py:412-416` | Verify the old file's expected content and protected ancestry/identity before disposal, and keep the validated replacement protected through former-file removal. Use the established native handle/boundary safety route or equivalent; same-size changed old files and path swaps must be retained/refused. |

Fixes belong to Ender. Rebuild and bind a fresh review/QA result before Sully releases; this report clears no release artifact.
