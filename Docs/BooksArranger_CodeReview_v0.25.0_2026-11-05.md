# Code Review — Books Arranger v0.25.0

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-11-05
Tool: Books Arranger (Electron desktop with Python backend)
Release: v0.25.0
Commit range: bf4425de09c355d2a0743771ca4209b24c8f0de1..0ec4971169a70d57a407ae1a9ef6bf96227724d4
Files changed: 456 files, +343997 / -164 lines, including retained documentation/evidence
Product/test/release scope: 45 files, +1704 / -143 lines
Stand-down dimensions: none
Binding: corrected pushed source and build 140014b8-b350-4a3e-a99b-05d24349f139
```

Release source commit: 0ec4971169a70d57a407ae1a9ef6bf96227724d4

## Summary

This is the updated accumulated source review after the first 0.25.0 build's full-check NO-GO. It incorporates the previously completed review through `e6912eb`, documented in [the November 4 report](BooksArranger_CodeReview_v0.25.0_2026-11-04.md), and reviews the exact correction through `0ec4971`. The earlier report remains unchanged as historical evidence. Build `3dbcfc92-c326-4d3b-907c-4b1b4e5d8c7a` and its failed full-check result are excluded from this acceptance; no earlier artifact binding is inherited.

The correction changes one product line in `web/app.js`, restoring the established untyped single-MP3 replacement status/hint. Typed `books-media-failure-v1` presentation still takes precedence. Eight existing test files are corrected to use the real constructor/catalog/cleanup entry contracts or the accepted Tolkien naming decision; the changelog records the correction. No backend SQL, source cleanup, retention, ownership, admission, media validation, build input or runner graph changes in this correction.

## Rubric

### 1. Security

- Pass. The correction grants no new execution, IPC, filesystem or credential authority. The earlier opaque navigation, native path protection, bounded PNG parsing and renderer text-handling review remains applicable.

### 2. Correctness and Logic

- Concerns: **M2 [Major, unchanged carried advisory] — `public_research.py:507`: a known provider cooldown can be lost to a waiting dispatcher if saving it fails.** The successful-persistence race was fixed in 0.24.5; a failed cooldown write still releases the family lock without an in-memory hold. Retain a fail-closed family hold on persistence failure and cover that path next cycle. This existing missing-error-handling limit has no identified Critical or safety-floor implication.
- The correction restores the prior legacy MP3 presentation without changing typed diagnostic/source binding, generic classification, readmission eligibility or conversion behavior. The accepted Tolkien assertions now distinguish canonical names from retained source/catalog facts.

### 3. Crash / Stability Safety

- Pass. The real constructor uses the RLocks and thread-local state now supplied by the corrected minimal doubles. Real `groups.setup()` supplies the catalog columns required by navigation. No product exception is hidden by an optional/no-op fallback.

### 4. Performance

- Pass. The catalog-only navigation and thread-local names-read fixes remain unchanged; the actual Inventory held-lock HTTP/read/save/fallback regressions pass in the affected cohort. No deadline was increased.

### 5. State & Data Safety

- Pass. Destructive cleanup code is unchanged. The updated interruption test patches the actual production guard, proves unchanged library bytes and no sweep marker/prior-state change, then checks successful retry. Native output/source/recovery protection and transaction guards remain required.

### 6. Input Handling

- Pass. Complete candidate evidence, root/superseded state and actual frozen manifests are now supplied to the affected fixture consumers. Source diagnostics still require the exact manifest hash, source-check stage, index/count/path and no output/publication; ambiguous legacy multi-source failures remain unknown.

### 7. Maintainability

- Pass. Fixtures now use `groups.setup()` and actual consumer methods rather than maintaining a rootless substitute schema or patching an unused owner wrapper. No safety contract was relaxed to accommodate the fixtures.

### 8. Doc/Code Drift

- Pass. Tolkien accepted review/path/world-authority assertions reflect the committed decision while preserving Russian raw clues and the existing identity negatives. Legacy MP3 copy matches the preexisting remedy; typed filename-aware copy is unchanged.

### 9. Build & Release Hygiene

- Pass for the corrected source and exact replacement package bound below. Version remains 0.25.0, dependencies/lock/build pins are unchanged, and the exact pushed correction source is pinned above. The previous build/full NO-GO and failed baseline receipts remain preserved. Independent full/native QA remains required; neither an old full result nor an old native plan is reused.

## Correction review and safety trace

The navigation `_source_directories()` helper is consumed only by inspection and source/output folder navigation. It is not part of source cleanup, storage cleanup or retention. The replacement fixture had created `book_groups(id,revision,review)` by hand; the actual `groups.setup()` schema has `root`, `evidence` and `superseded`. Using the real setup and persisted candidate evidence corrects the fixture without weakening the production query.

`StorageCleanup.run_folders()` uses `protected_cleanup()`, not the old publication-only wrapper the failed test patched. It calls the real guard before work, through protected-output reads and around capture/disposition. The corrected `test_interrupted_sweep_retains_its_selection_and_retries` injects `InterruptedError` into that guard, requires propagation, compares all library file bytes, preserves the prior outcome and absence of a sweep marker, and completes a later safe retry. Existing native ancestry, source-retirement, current-publication and transactional disposition code remains unchanged. This is not a navigation timeout substituted for a cleanup safety test.

The corrected names-save integration fixture supplies all three real RLocks; shared-peer fixtures supply the real thread-local interface. Current-publication inputs carry their frozen manifests, and the navigation double uses the actual catalog-derived method. Stale generation, rollback, source immutability, moved/native-bound and renamed-waiting target assertions remain in place.

The Tolkien-only delta changes five outdated accepted-layer subcase expectations across two methods. It additionally asserts retained Russian work/catalog facts and input immutability, strengthens the destination from a suffix check to the exact author/world/English-series/number/title path, and binds the current user-authority ID/evidence. Existing wrong work/title/author/ordinal/cycle/member/universe and unrelated-family negative cases are retained.

## Evidence checked

- Primary correction summary SHA256 `c0279204fb51aa4aaf013a878d7a931f1ab4c2d9ed811c7d4bc88cb3a8c91a83`, patch SHA256 `322c0416b22556eb966c34d1bf4e5a8568fd714f2a5d177583d8103f4b8c78ea`, under `Docs/Evidence/converted-duplicate_2026-11-05/full-entry-corrections`. All eight source/test frozen LF hashes and all 21 listed evidence hashes match.
- Tolkien correction summary SHA256 `cce29cba6bef88f20fb34853ac6f1066f2a92e2e590561c09c76380f1d1737c2`, patch SHA256 `9ec4e021dcad704875d0768a3b47a708e2523c0d8139e800f1f162766bfb1f5c`, under `Docs/Evidence/converted-duplicate_2026-11-05/tolkien-fixture-correction`. The exact test file and all listed evidence hashes match.

The primary baseline reproduces the own affected failure categories in ten methods, with two failures/ten errors including subcases. The corrected same ten methods pass, and the full affected-module cohort passes 172/172 in 46.636 seconds, including the real Inventory navigation/names concurrency tests. Four existing frontend scripts pass. The Tolkien module's 21/21 methods pass after its five expected-layer corrections. Read owned receipts report complete output, normal closure, native zero, no force and no timeout. These are focused correction receipts; the first build's full NO-GO is not relabeled as a pass.

All earlier source findings remain closed as documented in the November 4 review: saved-series T1, duplicate chapter-plan correspondence, startup failure reporting and output/fallback navigation F1. The typed child/publication ownership, backup-first cleanup, immutable parent, current destructive-transaction guards, strict PNG/audio preservation, names CAS and honest damaged-source holds are unchanged by this correction.

Senua performed read-only source/evidence/hash inspection and report edits only. No tests, native probes/apps, live library or Z: access, focus action or product edits were performed. The only open construction finding is the carried advisory M2.

## Artifact binding

```text
Release worktree: C:/Antigravity Projects/Worktrees/Books Arranger/0250-release-20261105-r2
Build ID: 140014b8-b350-4a3e-a99b-05d24349f139
Product digest: 3c9a1f5670ac4e0dded9ddc4c658cc70e7c17fda4b80350e80c0d1cf8a69b4cd
Release artifact manifest SHA256: 8f055521103f91f9417331091b971c423f7da483980364ee7a020016c99a9ca9
Runtime pointer SHA256: fe2e42723bbf6c5f7bfec0ad7d77b84255907a363ecf4d2c612ce432e61ec130
Payload manifest SHA256: 960972d791d3b4dd8b471775e2c6edaeaa727a08bb701b2008c9c854b3eae270
Installer: Books-Arranger-Setup-0.25.0.exe
Installer size: 174729156 bytes
Installer SHA256: 695e52cb8b4788d7c010ee11edc3e87b5d9cbad8fc7ab19c71f835721d7d00e3
```

The replacement release worktree is clean at the exact corrected source pin. Senua independently verified the artifact-manifest/runtime-pointer hashes and version/source/build/product identity; all three artifact sizes and hashes; actual packaged shell `package.json` and backend `VERSION` at 0.25.0; and the unchanged raw lock SHA256 `01d87e0d44a2b4485d5d674121fc1389cfa2092fd1b7a10c6ce7ca846f6c86a5`.

All 20 changed backend/frontend files match the release-source bytes and payload entries, including both new root modules `publication_reuse.py` and `tolkien_trilogy.py`, the cleanup/resolver and media/diagnostic modules, and corrected `web/app.js`. Independent binary Git-blob reads confirm every file matches the accepted `0ec4971` source after CRLF/LF normalization. No source or release-worktree edit was made.

`Docs/Evidence/converted-duplicate_2026-11-05/pack-r2/pack-owned.json` records the guarded replacement pack finishing in 83.224 seconds with exit 0, complete owned output, native zero, no force and no timeout. This establishes source/artifact identity, not independent full/native QA clearance. The excluded first build and its full-check NO-GO remain historical evidence; no tag/publication is implied.

## Verdict

- Total Critical: 0
- Total Major: 1 (unchanged carried advisory M2)
- Total Minor: 0

**Verdict:** RELEASE CLEAR

This verdict certifies the exact corrected source range, documentation-only descendants and the exact replacement build bound above. The safety floor is intact. It excludes the superseded build; independent QA/native evidence remains required before publication.
