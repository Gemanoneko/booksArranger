# Code Review — Books Arranger v0.25.0

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-11-05
Tool: Books Arranger (Electron desktop with Python backend)
Release: v0.25.0
Commit range: bf4425de09c355d2a0743771ca4209b24c8f0de1..90f0368ba7631659a3caafc2fa6125e9075ccf2a
Files changed: 510 files, +436288 / -165 lines, including retained documentation/evidence
Product/test/release scope: 46 files, +1705 / -144 lines
Stand-down dimensions: none
Binding: corrected pushed source and r3 build 9b63e746-2a00-4cd8-a0ba-5b45e6405fc2
```

Release source commit: 90f0368ba7631659a3caafc2fa6125e9075ccf2a

## Summary

This is the updated accumulated source review after the first two 0.25.0 builds' full-check NO-GO results. It incorporates the previously completed review through `e6912eb`, documented in [the November 4 report](BooksArranger_CodeReview_v0.25.0_2026-11-04.md), the nine-file correction through `0ec4971`, and the final one-assertion correction at `90f0368`. The earlier report remains unchanged as historical evidence. Builds `3dbcfc92-c326-4d3b-907c-4b1b4e5d8c7a` and `140014b8-b350-4a3e-a99b-05d24349f139` and their failed full-check results are excluded from this acceptance; no earlier artifact binding is inherited.

The correction changes one product line in `web/app.js`, restoring the established untyped single-MP3 replacement status/hint. Typed `books-media-failure-v1` presentation still takes precedence. Eight existing test files are corrected to use the real constructor/catalog/cleanup entry contracts or the accepted Tolkien naming decision; the changelog records the correction. The final additional test changes only one stale expected status to the committed feature-specific M4B label. No backend SQL, source cleanup, retention, ownership, admission, media validation, build input or runner graph changes in these corrections.

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

- Pass for the corrected source and exact r3 package bound below. Version remains 0.25.0, dependencies/lock/build pins are unchanged, and the exact pushed correction source is pinned above. Both previous build/full NO-GO results and failed baseline receipts remain preserved. The changed Git product digest and generated payload differences are independently explained below. Independent full/native QA remains required; neither an old full result nor an old native plan is reused.

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

### Final Node assertion correction

`0ec4971..90f0368` changes only the expected label in `tests/test_precheck_frontend.js:83`, from the older broad M4B wording to `Can't convert — M4B feature unsupported`. The fixture is the current unsupported-feature group after precheck; the expected label agrees with the committed UX media-addendum table/filter wording and existing runtime copy. No mock, runtime behavior, predicate, safety assertion or test graph is changed.

Verified summary SHA256 `9a1c22e0bae49d2b9ee5fd68a7632e3dc098d23d8c8da2d16d9daf074dd624fd` and patch SHA256 `2d25ce21d44836b487f91db776e3ce559c3fa0ef5f14f4f1abb394a541a76236` under `Docs/Evidence/converted-duplicate_2026-11-05/node-phase-correction`. The committed test's frozen LF hash and all ten listed evidence hashes match. The old assertion failure is reproduced in the preserved baseline receipt.

The actual complete canonical Node-side phase records 11 syntax checks, all 18 declared Node entries/242 cases with zero failures/skips/cancellations, and all 39 sorted DOM scripts: 51 commands, all exit 0, source inputs unchanged. Its owned receipt closes normally in 23.530 seconds with complete output, native zero, no force and no timeout. The fixed phase contract excludes the PA-1 native entry. This Node-side result does not turn the previous r2 full NO-GO into a full pass, combine phases from different source/build identities, or authorize a native launch. A fresh source-bound r3 build/full result remains required.

Senua performed read-only source/evidence/hash inspection and report edits only. No tests, native probes/apps, live library or Z: access, focus action or product edits were performed. The only open construction finding is the carried advisory M2.

## Artifact binding

```text
Release worktree: C:/Antigravity Projects/Worktrees/Books Arranger/0250-release-20261105-r3
Build ID: 9b63e746-2a00-4cd8-a0ba-5b45e6405fc2
Product digest: 21a42959c039c1e80075a5be71e7a86b0b17b09301ff00481857f12047febb16
Release artifact manifest SHA256: 2f58427054176b23f0110dda1a3b51920e8628ecbf571062942a951c292a41a4
Runtime pointer SHA256: da4cfa5c4684ed71706c48536962ba3419c07fac3b8c4281831d59fd4e2fab10
Payload manifest SHA256: cdfe05351609941bdc0d956a7d00a7abfaec0b7fb523d96fbb26d313f0085100
Installer: Books-Arranger-Setup-0.25.0.exe
Installer size: 174729365 bytes
Installer SHA256: a286126ba64d63c61dd307d00bbd230734c967a66114babd7197b9af81921963
```

The r3 release worktree is clean at the exact source pin above. Senua independently verified manifest/pointer/version/source/build/product identity, all three artifact sizes/hashes, actual packaged shell `package.json` and backend `VERSION` at 0.25.0, and unchanged raw lock SHA256 `01d87e0d44a2b4485d5d674121fc1389cfa2092fd1b7a10c6ce7ca846f6c86a5`. All 20 changed runtime backend/frontend files match their release-source bytes and payload records, including both new root modules, media/cleanup/diagnostic consumers and `web/app.js`. No source or release-worktree edit was made.

**Product-digest difference resolved.** `build-manifest.mjs:35` produces Git `{mode, object, name}` records; `release-contract.productTree()` excludes only `Docs/` and `CHANGELOG.md`, sorts by name and hashes their JSON. Tests are included. Independently recomputing both immutable trees yields exactly r2 `3c9a1f5670ac4e0dded9ddc4c658cc70e7c17fda4b80350e80c0d1cf8a69b4cd` and r3 `21a42959c039c1e80075a5be71e7a86b0b17b09301ff00481857f12047febb16`. Each preimage has 427 members; their sole selected-record change is `tests/test_precheck_frontend.js`, mode `100644`, blob `04a9140dd94257fb2ac2aebff81f9f1ec6c211e1` to `a29c9f82c362da1c3224c184907ac22c1610cb63`. The new digest binds the reviewed assertion; it is not evidence of runtime or checkout-EOL drift.

**Payload-manifest difference resolved separately.** Comparing every r2/r3 payload entry finds exactly 95 changed generated backend `.pyc` files, all the same size; every other payload entry is identical, including `app.asar`. The unchanged compiler step uses `compileall --invalidation-mode unchecked-hash` on its private backend path. For every changed bytecode file, Senua replaced only its observed embedded absolute compiler filename prefix: r2 `0250-release-20261105-r2/build-cache/builds/47d1052e-ce23-44c3-b9b1-c9eb9e3768cb/backend/` to r3 `0250-release-20261105-r3/build-cache/builds/37154e4d-beda-45a8-81f1-e42e97c54bc1/backend/`, preserving the same relative filename. All 95 complete binaries then match the r3 recorded SHA256 exactly. Headers and every other byte are identical; no bytecode was executed to establish this. There is no unexplained generated-code drift.

`Docs/Evidence/converted-duplicate_2026-11-05/pack-r3/pack-owned.json` records the guarded pack finishing in 81.805 seconds with exit 0, complete owned output, native zero, no force and no timeout. This accepts r3 source/artifact identity only; independent full/native QA remains necessary. The previous r2 package remains excluded because its full check failed the stale Node assertion. The earlier first-build NO-GO also remains excluded.

## Verdict

- Total Critical: 0
- Total Major: 1 (unchanged carried advisory M2)
- Total Minor: 0

**Verdict:** RELEASE CLEAR

This verdict certifies the exact corrected source range, documentation-only descendants and the exact r3 build bound above. The safety floor is intact. Both superseded builds are excluded; independent QA/native evidence remains required before publication.
