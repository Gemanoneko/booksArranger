# Code Review — Books Arranger v0.16.12

## Header

Reviewer: Senua (Code Reviewer)
Date: 2026-10-18
Tool: Books Arranger (Electron desktop utility)
Release: v0.16.12
Commit range: 68a7cdc..4aff68677851448f9f51f27d522e1094941ddd3e
Files changed: 21 files, +1431 / -48 (git diff --stat, including handoff and initial review documentation)
Release source commit: 4aff68677851448f9f51f27d522e1094941ddd3e
Release artifact manifest SHA256: 334de7d785a30aa57285d61468f52a885cdd101eb9ca34d4b03bde94144741bf
Release installer: dist/builds/d7fce1bd-d21b-40c0-ad11-136b30588ae2/Books-Arranger-Setup-0.16.12.exe
Release installer SHA256: f18300fb13ef86cbc573fee0c56f41eb331adb5951f334df2e8b34973628221d
Stand-down dimensions: none.

## Summary

Red-team review of the series backfill, metadata rewrite proofs, queue/retry changes, catalog read transaction change, frontend controls, and version/build checks. Initial review of 68a7cdc..14eea66 found two Critical recovery/data-safety defects and blocked the old artifact. Both were corrected in 4aff686 and re-reviewed. This final clearance applies only to the rebuilt artifact bound above. No real library/catalog was opened or modified, and no installer/application was run by this reviewer.

## Rubric

### 1. Security

Status: Pass. No new shell interpolation or Electron security configuration changes were found; corrected publication and former-file removal use protected ancestry and native file handles.

### 2. Correctness & Logic

Status: Pass. Directly resumed `renamed` and `cataloged` states prove replacement identity and full bytes before catalog/destructive transitions; missing or changed files fail closed.

### 3. Crash / Stability Safety

Status: Pass. The original remains through writing/proofs/rename/catalog commit, replacement protection spans retirement, and a persisted removal-intent checkpoint permits restart after disposal but before the final done write.

### 4. Performance

Status: Pass. Series research is paced, metadata/media verification streams bounded blocks, and current catalog groups avoid a page-read write lock. Full replacement/former hashes on destructive recovery are intentional safety work.

### 5. State & Data Safety

Status: Pass. Historical parent ancestry, both file identities, expected sizes and complete hashes are checked; the former must have one link and is disposed by the exact held handle while the replacement remains protected. Catalog refusal preserves both copies.

### 6. Input Handling

Status: Pass. Destination proposals and metadata lengths are checked; recovery requires ordinary distinct paths sharing the original parent and rejects unbound legacy records.

### 7. Maintainability

Status: Pass. Backfill state transitions and proofs are localized; common protected-boundary and exact-file helpers are reused.

### 8. Doc/Code Drift

Status: Pass. The corrected implementation now supports the documented preservation claims; historical findings and evidence remain below.

### 9. Build & Release Hygiene

Status: Pass. Version and lockfile advance together, integrated checks include backfill tests, and independently computed actual installer/manifest hashes match the rebuilt source binding. Source and packaged `series_backfill.py` independently both hash to `83d2221a96f1b490dfd69a86f06fd373e340e26e5594fcea79c3924b962db100`.

## Verification and limits

- Independently inspected the accumulated product diff and correction commit, including protected-handle lifetimes, no-replace publication, missing/corrupt former/replacement handling, and the intent-before-disposal crash boundary.
- Ender's reported focused evidence: 17 backfill tests passed in 77.447 seconds; the explicit held-file/path mutation test passed in 4.124 seconds. Reviewed test source covers missing replacement at both recovery checkpoints, same-size corruption with restored time, changed old bytes/identity, successful cataloged recovery, restart after exact disposal, and denied modification of replacement/original/ancestry while held. These runs are developer evidence, not claimed as independently rerun by Senua.
- Independently hashed the actual current manifest, installer, source backfill module and corresponding unpacked module; manifest source_head is exactly the reviewed 4aff686 commit.
- No broad suite or playback/live-install test was run by this reviewer. Jane reported the canonical receipt read was denied under P9; no canonical entry receipt is asserted. This is the authorized lean handoff, with focused evidence and artifact review retained. Futaba's behavior verdict remains independent.
- No matching local Lessons/Patterns file was found by a filename search through the repository's first two levels.

## Closed findings and initial evidence

| # | Original severity | Original location | Finding | Resolution in 4aff686 |
|---|-------------------|-------------------|---------|----------------------|
| F1 | Critical | `series_backfill.py:397-416` at 14eea66 | Recovery could trust a persisted renamed/cataloged state and delete the only complete former copy when the replacement was absent or damaged. | Both recovery entry states now acquire exact identity/full-hash replacement proof and hold it through former disposal; uncertainty preserves remaining files. |
| F2 | Critical | `series_backfill.py:412-416` at 14eea66 | Former deletion checked historical size only and unlinked an unprotected pathname. | Protected historical ancestry, full old content and identity checks, single-link requirement, and native exact-handle disposition replace pathname deletion. |

Initial bounded reproduction imported `SeriesBackfill`, constructed a private instance without opening a catalog, and supplied a `cataloged` entry with a private original-file stand-in and absent replacement. Actual old `resume()` returned:

```json
{"old_survives": false, "new_exists": false, "final_states": ["done"]}
```

This was a state-machine deletion reproduction, not an audio/playback test; it used no actual book bytes and did not claim the app itself caused the replacement to disappear. Evidence directory retained: `C:/Users/AnGeLZzZ/AppData/Local/Temp/books-codex-20261018/senua-cataloged-recovery-6m231iz8`.

Historical rejected artifact: source `14eea665728116a6f89d0ebd3d365c1b627f9a17`, manifest SHA256 `86f602de252e600b99afc80c7358c9e68abfc9bf158094be728ac211273613ac`, installer SHA256 `b17d3276d4ae9c4c31a4e44a572932e5105b508fa36480055ffebe35bc3cf584`. It is not covered by this clearance.

## Verdict

- Open Critical: 0 (2 closed)
- Open Major: 0
- Open Minor: 0

**Verdict:** RELEASE CLEAR

## Scoped isolated-smoke harness review

Source-only review of the fixed QA-v01612 harness (no run performed by Senua): owner `smoke-owned.mjs` SHA256 `d145578af33b22e23e5440a9477783bc4d1e885ee55aa9574cc31efb9a468f78`, smoke payload `smoke-empty.mjs` SHA256 `8fee445bb06c136bdf7ff281e3e7f58a982d5fcdfca3c6e62613c56b8948ba14`, and `smoke-owner-pins.json` SHA256 `96e95bd5ae83b7c3ba9cb80683130411bb68b00af1eb41837bd223dd118502eb`, under the retained session `shared/tools` folder. No new blocking source finding in this narrow harness. It checks the fixed inventory, leases and rehashes executable/harness/payload inputs, delegates to unchanged canonical runOwned with the remaining 600000ms budget, and accepts success only with closed ownership, zero descendants, no unsignaled processes, no forced termination, no timeout and no output overflow. The smoke requires empty private catalog/profile and private empty library roots, uses windowsHide and inactive display, and quits its bound page rather than killing arbitrary PIDs/names. Synthetic controls cancel before retry submission.

Limits: canonical supervisor implementation/ownership-before-release is inherited from the unchanged reviewed route described by Ender, not newly inspected or independently proved here; the denied canonical receipt-read operation was not rerouted. The bootstrap's JavaScript timer cannot preempt a synchronous filesystem read, so the whole-invocation deadline also depends on the host guard and canonical owner behavior. Passing source review is not runtime closure evidence, a QA GO, or global guard enrollment; the actual transparent invocation still requires its ordinary guard evaluation and an observed closure result. This paragraph changes no product verdict or artifact binding.
