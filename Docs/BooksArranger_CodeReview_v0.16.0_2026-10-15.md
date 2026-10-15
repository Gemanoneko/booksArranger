# Code Review — Books Arranger v0.16.0

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-15
Tool: Books Arranger
Release: v0.16.0
Status: PRELIMINARY; final source/artifact binding and integrated validation pending
Commit range: 95febcdd4f4de4ffb59a3507053c4eb86f53936a..f56739b0911da133cef759fbfa71d6110bbbf941
Accumulated committed diff: 98 files, +12118 / -197
Stand-down dimensions: none
Release source commit: f56739b0911da133cef759fbfa71d6110bbbf941
Release artifact manifest SHA256: pending new verified installer
```

This is the accumulated release review, including the earlier Electron M1/M2 reviews and their corrections, rather than a review of only today's last patch. This preliminary document deliberately has no machine-readable release verdict. It must be completed against the final committed source and real validation evidence before it is consumed as release clearance.

## Summary

Reviewed the Electron shell and native engine ownership, existing-catalog startup, normal Quit and update shutdown, working-file lifecycle and source retirement, retry admission, source-preserving M4B metadata repair, and the complete native-owned packaging/publication graph. The review followed the Brief, standing rules, desktop UX record, build-guard record and accumulated release diff. Shared QuickLaunch/hooks/settings, unrelated chats, live app controls and product implementation are outside this reviewer's ownership.

## Exact working-source inventory

Before final source save the tracked dirty paths were `audio_pipeline.py`, `scripts/check-desktop.mjs`, and `tests/test_web.py`. Untracked final product/test paths were `m4b_preservation.py`, `tests/m4b_native_preservation_fixture.py`, `tests/test_m4b_dispatch.py`, and `tests/test_m4b_preservation.py`; the M4B evidence Doc was also untracked. Independently rechecked the final commit: `0c67862e0bf0a15ff7b7d0506b25f45f3b3adb66..f56739b0911da133cef759fbfa71d6110bbbf941` contains exactly those eight paths, matching the reviewed source inventory. At that point only this documentation-only report was dirty. All final source is now included in the accumulated committed range above.

| Path | Actual SHA256 at review |
|---|---|
| audio_pipeline.py | c8d16b61b1ed3ecb7f522ace082a5dda04603d96ef2168bd24f6f37a37e4a09c |
| m4b_preservation.py | d68a37bbfd851a7fa08f9d23faad75584daa3252ac34e8549452c044c7c09ff2 |
| scripts/check-desktop.mjs | 3cd84c8ecb78991419ed29c8139f75a505ebce5be18fb4af73446d0eeb8f4c8a |
| tests/test_web.py | b4e310eac6a8d472a80b6a97c38320cbe8252c111cc605661afe97c3c85979ae |
| tests/test_m4b_preservation.py | ba06289d4d1eee9444ed93899b0730ef7413b472f356144b8d897e8cd7b87970 |
| tests/test_m4b_dispatch.py | b2a42d1eeab0499f6888eb6aa2cea03b0d1bf89f7068632e5e2ba74046499b46 |
| tests/m4b_native_preservation_fixture.py | a850398f28d9e2880e8b418db0691f5bde6b17356db5430964c368790a0e30b8 |

## Rubric

Severity tags and the always-blocking floor are those in `Team/Docs/ProcessRules.md`, Severity definitions.

### 1. Security

Pass. Renderer sandbox/context isolation and restricted IPC, exact native owner/runtime checks, argument-based process launches, leased Git/GH and credential handling were reviewed; no open Critical or safety-floor finding identified.

### 2. Correctness & Logic

Pass for reviewed source. AAC single-source preservation is separately dispatched; ALAC keeps the existing strict route. Unknown structural layouts are refused. Complete retained-byte reread, source-relative packet/configuration/chapter and PCM checks preserve the 139 chapter-linked MJPG track and f96 HE-AAC clock. Repair admission retains the failed parent and CAS-binds one new child to the unchanged reviewed manifest; it does not reset legacy failure rows.

### 3. Crash / Stability Safety

Pass for reviewed source. Native ownership spans engine startup and lifetime, interrupted-exit recovery distinguishes an ended generation from an unknown owner, Quit drains the current book before releasing ownership, and update failure restores shell retry state without releasing a live engine fence. The old installed app's exit cause remains unestablished.

### 4. Performance

Concerns. [Major, advisory] `working_lifecycle.py:228`: `_references` rescans relevant catalog tables during reconciliation and again before individual deletion (`:411`), so large multipart attempts multiply catalog work by disposable-file count. No new measured user-facing regression is asserted. Preserve the last-moment reference check if optimizing this path; measure representative large attempts before choosing an index/cache strategy.

The preservation route removes the old remux-plus-compatible pair and normalized-WAV path for supported single-source AAC M4Bs. It retains complete verification; this review does not claim the earlier 61–69% pre-encoding cost has been eliminated for other books.

### 5. State & Data Safety

Pass for reviewed source. New lifecycle intent precedes generated writes; only closed, identified, unreferenced generated artifacts are disposed using retained native handles and durable receipts. Publication/source-survival proofs precede retirement of published snapshots. Changed, linked, streamed, unknown or unresolved files remain held. Legacy debt blocks another copy set for that parent. The remaining 77 legacy snapshots and original diagnostic pairs are not declared disposable by this review. A Zone.Identifier-only exception is not inferred from ordinary stream enumeration.

### 6. Input Handling

Pass. Existing-root/catalog validation, canonical paths, held ancestor boundaries, link/stream checks and conservative structural parsing were reviewed. Empty metadata is accepted only as an omitted empty tag; nonempty metadata comparisons and full-byte proof remain strict.

### 7. Maintainability

Pass. The separate preservation module and lifecycle ledger concentrate their invariants; retry admission uses the production plan/manifest contracts. Native guard and release orchestration remain substantial maintenance surfaces, with focused failure-path tests reviewed.

### 8. Doc/Code Drift

Concerns pending release completion. This report distinguishes source review, actual component/real-book evidence, integrated checks, and the still-unbuilt artifact. Historical 137-Python/29-Node declarations are not treated as executed evidence. The current integrated suite declares 354 Python and 29 Node cases plus frontend/syntax checks. Neither this report nor the genuine private whole-product graph claims a canonical protocol-2 handoff receipt. The user's explicit procedural waiver and narrow transport issue are recorded in the operation-review Doc.

### 9. Build & Release Hygiene

Concerns pending actual build and independent QA. Reviewed existing `npm run pack` -> `node scripts/build-step.mjs pack` and existing direct `node scripts/release.mjs` primary publication entry, including complete source/runtime holds, 600-second native deadline, owned descendant closure, UUID staging, payload equality, fixed Git/GH, clean named pushed tag, artifact hashes and keep-four ordering. This is source/operation assessment, not a claimed package or publication run. Final source commit, exact installer manifest, Futaba behavior/identity evidence and final release binding remain outstanding.

## Actual evidence and limits

- Parent reports final native QA06: 36 cases passed, no failures/errors/skips; native PID 88140 exited 0 with zero active descendants. Header05 accepted all three retained source profiles unchanged. These are component scopes, not whole-product or publication claims.
- Independently read the three bundled-runtime real-book native receipts and full proof stdout. All three exited 0, zero active descendants, owned cleanup finalizer completed; one test and 13 codec children per graph. Runtime was the release bundle `n8.1.3-9-g29e619e767`, with all 11 runtime files and archive pinned.
- 07d: 17 chapters; mono PCM 1,697,126,336 frames SHA256 `8e3015d2888a481fb4a254d7dae82825813e4de7d94b1cb9938742381ffe33a4`; native PID 101372, 82.697 seconds.
- 139: 8 chapters; stereo PCM 1,070,323,648 frames SHA256 `0b5dc7c17e628d9da5ec9263dc91b3405ad64287ae87c5657ade71223794886d`; native PID 77084, 75.461 seconds. All original tracks, including chapter-linked MJPG, retained.
- f96: 43 chapters; HE-AAC stereo PCM 1,095,806,976 frames SHA256 `21733f23e62a4641380eed7e5708ff3aed570b45fb872feeb7b32692787a5df7`; native PID 8620, 69.066 seconds. Original decoder/container clock retained.
- All three source native facts and full hashes were unchanged; complete retained bytes/configuration/packets and decoded PCM matched. These graphs wrote only private `checked.m4b` candidates; they did not publish outputs, retry real jobs or retire originals.
- Integrated01 failed before any product test because runtime membership used inconsistent string ordering; exact membership and file hashes were unchanged. Fresh02 corrected ordering, then actually passed 29 Node cases but failed its strict TAP reader because Node26 selected the spec reporter; Python/frontend were not reached. Fresh03 explicitly selects TAP without weakening the zero-fail/skip/cancel assertions. Its actual result is pending.
- Original diagnostic pairs, failed graph evidence and unique recovery records remain preserved. The separately reviewed fixed-hash helper `459928b08635af1bbb1f332f39e0ee07d5bb3cc993fe1875cf105ec7e750000c` was executed once by the parent: exit 0, three new private proof candidates removed, 923,016,616 bytes, final phase `complete_after_native_release`. It accessed no original/source/catalog/app. This is additional QA-generated space, separate from the earlier 59,306,533,081-byte cleanup of user working files.

## Preliminary finding rollup

- Open Critical: 0 identified in reviewed source.
- Open Major: 1 advisory performance finding.
- Open Minor: 0.
- Always-blocking floor: no violation identified in reviewed source.

Final machine-readable verdict is pending final committed source comparison, actual integrated validation and installer evidence. This is an unfinished review document, not release clearance and not a Critical-based release rejection.
