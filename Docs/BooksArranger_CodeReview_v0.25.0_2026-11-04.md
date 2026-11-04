# Code Review — Books Arranger v0.25.0

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-11-04
Tool: Books Arranger (Electron desktop with Python backend)
Release: v0.25.0
Commit range: bf4425de09c355d2a0743771ca4209b24c8f0de1..e6912eb7e43cac35bf26a7a662bc9dc95c0e1d2d
Files changed: 412 files, +342101 / -152 lines, including retained documentation/evidence
Product/test/release scope: 39 files, +1673 / -131 lines
Stand-down dimensions: none
Binding: pushed final source and build 3dbcfc92-c326-4d3b-907c-4b1b4e5d8c7a
```

Release source commit: e6912eb7e43cac35bf26a7a662bc9dc95c0e1d2d

## Summary

This range adds verified duplicate-source cleanup using an immutable existing audiobook, identity-bound Tolkien trilogy naming for pending work, a complete names-editor response, PNG chapter-image preservation, precise source-decode diagnostics and old-PNG-failure readmission. Navigation and editor reads avoid unrelated grouping work, and an occupied names-save admission returns a finite busy response while retaining the draft. The previous release review ends at `bf4425d`; all requested product changes are now committed and pushed at the source pin above.

The accumulated review incorporates the validated EditorTrilogy/T1, ConvertedDuplicate implementation, PNGChapter, SourceDecode and FolderResponse slice reports in this directory. The final `7cca37d..e6912eb` consumer/navigation slice was reviewed against its frozen patch and supplied regression receipts. No new open finding remains; the prior cooldown-persistence advisory is carried below. This verdict binds the exact artifact recorded below and does not replace independent behavior QA.

## Rubric

### 1. Security

- Pass. No new Electron, IPC, shell or credential authority. Catalog-derived opaque navigation, configured-root checks and native ancestry protection remain required. Diagnostics are rendered as text; the new PNG parser performs bounded byte/CRC checks without pixel decompression.

### 2. Correctness and Logic

- Concerns: **M2 [Major, carried from 0.24.5] — `public_research.py:507`: a known provider cooldown can be lost to a waiting dispatcher if persisting it fails.** The successful-persistence race was corrected in 0.24.5. A failed cooldown write still releases the family lock without an in-memory hold, allowing a reserved dispatcher to observe the preceding empty record. This unchanged failure path remains advisory missing error handling; no Critical or safety-floor implication was identified. Retain a fail-closed family hold on persistence failure and cover that path next cycle.
- The new paths pass source review: complete ordered source/chapter/work correspondence is required for reuse; parent and child ownership remain separate; typed diagnostic indices bind to the frozen manifest; successful old-PNG admission no longer leaves a future-failure retry/backoff result.

### 3. Crash / Stability Safety

- Pass. Failed startup enrollment now records inert attention without repeating the refused parent proof. Interrupted verification has no publication authority; partial source cleanup retains per-file disposition outcomes. Catalog-only editor scope is thread-local and restored on exit. Busy Save returns HTTP 409 before a blocking refresh.

### 4. Performance

- Pass. Duplicate tasks never start a second codec producer. Existing-source, output and missing-source fallback navigation no longer synchronously regroup the catalog. Names reads bypass grouping locks and shared approval/peer cache entries. PNG reads have separate 8 MiB per-image and 32 MiB aggregate bounds; full media/source verification remains mandatory.

### 5. State & Data Safety

- Pass. Existing publication rows, manifests, outputs and producer ownership remain immutable during duplicate cleanup. The child owns its own verification, source review, backups, retirement, restore and retention receipts. Full held-output/source hashes, reviewed file IDs, backup-first disposal and parent/review/location rechecks inside the destructive write transaction remain required. In-place parents do not grant their rename-retirement shortcut to the child; child staging cleanup cannot prune the parent producer.

### 6. Input Handling

- Pass. Unknown/ambiguous recordings, partial or reordered source sets, different chapter plans, reuse chains, replacement lineage and conflicting explicit choices refuse reuse. PNG signature/chunk framing/CRC/critical order/IHDR and sample extents are bounded; unknown codecs remain unsupported. Source remedies require no output/publication, the source-check stage, current frozen manifest hash and exact index/count/path; ambiguous legacy multi-source failures invent no member identity.

### 7. Maintainability

- Pass. One typed resolver supplies separate publication and cleanup capabilities without relaxing ordinary publication-only contracts. Native source failure classification is centralized; existing readmission/equivalence/CAS and no-replace restore paths remain in use.

### 8. Doc/Code Drift

- Pass. Pending Tolkien replanning retains accepted identity/source correspondence and later explicit names; finished outputs are not migrated. Duplicate activity and Ready counts describe cleanup work without manufacturing another audiobook. Invalid media is distinguished from an unsupported chapter feature, with raw decoder details retained in Technical details.

### 9. Build & Release Hygiene

- Pass for source and the bound guarded package. Package and lock versions are 0.25.0, with unchanged dependency graph except the root version values. The sole build-input change pins the actual lock SHA256 `01d87e0d44a2b4485d5d674121fc1389cfa2092fd1b7a10c6ce7ca846f6c86a5`; the 2,301 seed/tool file pins are unchanged. Root Python collection includes the new modules. No runner graph, canonical deadline or test weight was weakened. Artifact/payload details are bound below; independent full/native QA remains required before publication.

## Closed review findings

| Finding | Closure at the final source |
|---|---|
| T1 [Major], old saved Russian trilogy series overrode the superseding decision | `d9c0da2`: per-field saved provenance and actual decision-commit cutoff distinguish legacy values from later/current explicit choices; old pending replan and future-choice regressions pass. |
| Duplicate ordinary chapter plan omitted [Major] | `87b5681`: exact ordinary `manifest.chapters` equality joins source/part chapter proof; different requested plan is refused in the regression receipt. |
| Duplicate failure reporting could abort startup [Critical] | `87b5681`: blocked verification receipt requires no refused proof and is rejected by the cleanup guard; held-parent startup enrollment regression passes. |
| F1 [Major], output/missing-source navigation still waited on grouping | `e6912eb`: output/fallback uses the same guarded catalog-only identity path; held-lock output/fallback regression passes. |

## Final consumer and readmission checks

`SourceDecodeError` remains a native completed strict-decode failure after the existing finite MP3 tag-repair opportunity. The production pipeline emits `Checking sources` before source work; MergeService maps it to the queue checkpoint, and the real worker records that history stage through `_failure_details`. The added worker bridge drives queue/checkpoint/journal/attention serialization for source 12 of 57, asserting its original filename, unchanged frozen manifest and no output/publication. It is complemented by the separately supplied actual native bad-input helper test; neither claims to reconstruct damaged audio.

The exact old PNG image-entry refusal gains one opportunity through the existing source-preserving M4B retry path. Current native source/profile proof, unchanged review/source/cover/policy equivalence, parent-row CAS, newest-work checks and the one-child ledger remain required. A real ordinary-Start regression records the old parser's refusal/closed attempt, then uses the corrected PNG code to complete a distinct verified child while preserving the old row. Successful admission returns `retryable=False` and `retry_at=None`; refusal retains its existing retry behavior.

The names HTTP read uses only its thread-local stored-generation scope; it neither reads nor populates the shared approval/peer result entries from that scope. Save does not enter it: nonblocking admission is followed by the existing fresh-row, current claim, generation and transactional CAS checks. Held-lock tests cover a timely read, finite busy Save, successful later Save and rejection after the candidate generation advances.

## Evidence and limits

Final consumer summary SHA256: `e9305a418ff46060acf6b03cb89fa3156dbe599c444fb602b967222ccd3446b1`; patch SHA256: `694c0f1f78c6f5b32b1419115ad15e030cbd3d214c893ba5a9610e664debb505`, under `Docs/Evidence/converted-duplicate_2026-11-04/media-consumers-final`. All 12 committed source/test/build-input files match their frozen LF hashes, and all 35 listed evidence files match their exact hashes. Earlier slice source/evidence pins were verified in their reports.

The final 83-case cohort records 82 passing and one existing coauthor/series fixture exceeding the unchanged Windows path limit; the exact unchanged test passes in the separately retained shortened-private-root rerun (7.348 seconds). The actual worker bridge, names read/save and output/fallback regressions pass in that cohort. The separate PNG normal-Start/one-child cohort passes 21/21 in 13.535 seconds. Four existing frontend scripts pass. Earlier evidence includes the duplicate real-publication E2E with converted total one, in-place-parent NFC/NFD cleanup/recovery, 102/102 preservation cases and the native source-decode diagnostic test. Failed initial selectors, fixture mistakes and earlier source/consumer failures remain preserved rather than relabeled as passes. Relevant final receipts show complete owned closure and native zero without force or timeout. These are focused receipts, not a full milestone PASS.

Senua performed read-only source/evidence/hash review and documentation edits only: no test execution, apps, native probes, live library or Z: access, focus action or product edit. The damaged source cases remain held for an intact replacement; no general unsupported-format or damaged-audio bypass is cleared.

The Docs-only 0.25.0 native operator template has the previously reviewed run/preflight/one-use/callback/evidence-consumer body, with candidate/version/path/pin literals pending. Corrected template SHA256 `0758bcaf5b6ea3d59f4545a3fe75a48fa1e831bb48cce1da48f00b27c49f4b1d` contains the exact user authority quotations relayed by Jane; the remaining placeholders prevent admission. After the exact full PASS, final filled operator/self/plan pins and pure admission must be reviewed before the single authorized native run. This static template check grants no preparation or native launch clearance.

## Artifact binding

```text
Release worktree: C:/Antigravity Projects/Worktrees/Books Arranger/0250-release-20261104
Build ID: 3dbcfc92-c326-4d3b-907c-4b1b4e5d8c7a
Product digest: aa6e7c4bf7f0c5c934956e168fc85934b473c77ce4e4b54eb798428c2b53449e
Release artifact manifest SHA256: 068e9ad0a02b2fc16950e5109540c1ed8e77e609845ec914f022b38e8548bc1f
Runtime pointer SHA256: d6386c9f373ebe2f69f03338dac4fda7ec27c21013e9fa2c41ff2a5283b696cd
Payload manifest SHA256: 9619926565735c7d9bb5d32278e90087b8ee119d84e25937cf75fff2498f566d
Installer: Books-Arranger-Setup-0.25.0.exe
Installer size: 174728805 bytes
Installer SHA256: d15fa90bd6d381f68f86ecfbd0071be4c076589a9d455ee42bcc8ee902c59ded
```

The release worktree is clean at the exact source pin. Senua independently verified the artifact-manifest and runtime-pointer hashes, version/source/build/product identity, all three artifact sizes/hashes, packaged shell `package.json` version 0.25.0 and backend `VERSION` 0.25.0. All 20 changed backend/frontend files match their release-source bytes and payload manifest entries, including `publication_reuse.py`, `tolkien_trilogy.py`, the destructive cleanup/resolver modules, media parser/pipeline, job/diagnostic consumers and `web/app.js`. They also correspond to the reviewed immutable Git source after line-ending normalization; the investigated differing blobs contain CRLF/LF conversion only. The raw release lock hash is the accepted `01d87e0d...` pin above.

`Docs/Evidence/converted-duplicate_2026-11-04/pack-0250/pack-owned.json` records the guarded pack finishing in 82.611 seconds with exit 0, complete owned output, native zero, no force and no timeout. This establishes source/artifact identity, not a full QA or native behavior result. No tag/publication is implied.

## Verdict

- Total Critical: 0
- Total Major: 1 (unchanged carried advisory M2)
- Total Minor: 0

**Verdict:** RELEASE CLEAR

This verdict certifies the exact source range, its documentation-only descendants and the exact bound build above. All new review findings are closed and the safety floor is intact. Independent QA and the authorized native check remain necessary before publication.
