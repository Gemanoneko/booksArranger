# Code Review — Books Arranger v0.27.0

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-11-11
Tool: Books Arranger (Electron desktop and Python backend)
Release: v0.27.0
Commit range: 3932155e9f3ceac00632d2d82a4e91315f7c832f..d11302ab70a2831e2096ec4a6a4629f33fc0f9c9
Files changed: 194 files, +462674 / -104 lines including retained documentation and evidence
Product, tests, changelog and release inputs: 26 files, +2279 / -74 lines
Stand-down dimensions: none
```

Release source commit: d11302ab70a2831e2096ec4a6a4629f33fc0f9c9

Release artifact manifest SHA256: 8825b291e3d55abc45bc0ba488d98c2d5a32d32c29d17a64dd5de4c7639a66b7

## Summary

The release adds persistent manual source selection, metadata and track order, exact M4B export, and source retirement through the shared audiobook worker. I traced the authenticated renderer and Electron pickers through draft identity, queue admission, source verification, no-replace publication, original disposal and Converted projection. The initial blocked review on `3f636e1` found that a changed file could be admitted through an edited track list. Its original report is retained in the review scratch area with SHA-256 `df9cd5d1cef15e6a87f4ba6a3bd6b18485d0d488593c4a319eed479be45d8f57`.

## Rubric

### 1. Security

- Pass. Manual routes use the existing local Host, Origin and token checks. The native pickers require a trusted app sender and expose narrow IPC methods. Renderer paths and metadata are rendered as text. Inspection proof uses a process-local secret and binds normalized path, size, modified time and native file identity.

### 2. Correctness & Logic

- Pass. The renderer checks the returned job and candidate binding, revision and exact submitted plan before settling a direct or recovered queue response (`web/app.js:5369`, `web/app.js:5573`). Unchanged saved drafts can now recover an accepted response at the same revision. The renderer regression exercised both a mismatched plan and a matching same-revision plan. The prior M1 finding is closed.
- The final two-file QA witness change keeps the SDK IPv4 listener-only class, exact loopback/port, positive unique PID, retained private process and repeated liveness checks. It accepts the observed raw state 6 only with both remote fields zero and leaves it as a diagnostic. The active health and CDP challenges are unchanged. The old failed PA-1 and its exact own-leaf cleanup remain separate evidence.

### 3. Crash / Stability Safety

- Pass. Draft and job writes share one admission transaction. Reopen and retry refuse jobs with published or retained work. The compatibility correction restores legacy catalog and lightweight service behavior. Unchanged saved source facts can be queued after restart without reusing transient inspection proofs.

### 4. Performance

- Concerns. **M2 [Major] — `manual_conversion.py:350` and `manual_conversion.py:360`: manual polling and admission scale with retained history.** A Manual tab poll queries every completed draft and job before the renderer discards completed list entries. Save and Queue hold the job lock while scanning current job manifests and owned artifacts. Project pending and requested completed rows directly and index shared ownership.

### 5. State & Data Safety

- The prior C1 finding is closed by `manual_conversion.py:248`, `manual_conversion.py:517` and `manual_conversion.py:544`. New or changed source facts require current proof from explicit inspection, including first Save or Queue. Saved facts are compared by path independently of track order and membership. An excluded track preserves its facts, and admission repeats the check inside the write transaction. The frozen queue still performs full source byte and identity checks. Native disposal remains limited to originals with verified recovery copies and complete verified output receipts. Manual publication uses the copy-based no-replace route and skips folder removal.
- Concerns. **M3 [Major] — `manual_conversion.py:31`, `manual_conversion.py:77` and `manual_conversion.py:360`: reservation and overlap compare lexical paths.** Different ordinary Windows names for the same file can bypass a path-only reservation where both names resolve. The review did not reproduce this on a live share. Native source verification, the serial worker and exact-handle disposition still protect actual deletion. Compare native file identity as well as path where available and cover a private alias fixture. Lexical source and export containment has the same alias limitation.

### 6. Input Handling

- Concerns. **m1 [Minor] — `manual_conversion.py:294`: series ordinal suggestions only read `series_number`.** The existing reader recognizes `series-part` and `series_part` at `metadata.py:81`. Use the same normalized aliases for Manual prefills.

### 7. Maintainability

- Pass. The manual plan and cleanup binding are distinct from automatic planning. Existing queue, source proof, conversion, publication and cleanup primitives remain shared.

### 8. Doc/Code Drift

- Concerns. **m2 [Minor] — `Docs/BooksArranger_ManualConversion_UX.md:8`: the spec refers to regular job controls and status.** The Manual tab links to the Library for cleanup actions. Describe this handoff explicitly so those controls can be located.

### 9. Build & Release Hygiene

- Pass. Package, lockfile, changelog and guarded input pin agree on 0.27.0. Existing guarded publisher and credential paths are unchanged. I independently verified the corrected source digest, guarded build `0245e25b-e185-4357-b48c-8f1cb4b242c0`, all 334 payload files, the three exact artifacts and the build's native-zero receipt. Canonical entry and native release QA supply their own candidate-bound results.

## Verification

- I independently ran the renderer regression and eight source-evidence assertions against the frozen correction. The assertions covered no proof on initial admission, stale initial proof, reordered and reduced saved selections, an excluded baseline, wrong-file proof, unchanged reorder and a current proof accepted for the replacement. Both checks passed.
- Ender reported 11 passing focused Windows/FFmpeg backend cases and renderer success, with closed process ownership. The corrective regression was also tested against the preceding bytes to establish that both initial Save and initial Queue had admitted a replacement. I performed no full-suite rerun or native application launch.
- I ran the three listener decoder tests and replayed the actual raw capture through the revised decoder. It accepted all 240 observed loopback listener rows and returned no endpoint for 60 closed samples. It refused the all-rows table and refused an actual state-6 row with nonzero remote data even when the test supplied it under class 3. The 60 observed connection controls all had separate nonzero-remote rows in the all-rows table. The owned diagnostic closed with native zero. [Microsoft TCP table class contract](https://learn.microsoft.com/en-us/windows/desktop/api/iprtrmib/ne-iprtrmib-tcp_table_class).

## Verdict

- Total Critical: 0
- Total Major: 2
- Total Minor: 2

**Verdict:** RELEASE CLEAR
