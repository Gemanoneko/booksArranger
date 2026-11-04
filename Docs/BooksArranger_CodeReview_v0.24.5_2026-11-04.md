# Code Review — Books Arranger v0.24.5

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-11-04
Tool: Books Arranger (Electron desktop with Python backend)
Release: v0.24.5
Commit range: 94be5003b1e66cd4d7a4a50afe1ec2b930b1a6cb..f6553e7b78bf9d7f011b5728b2d219ad48732add
Files changed: 112 files, +9905 / -7 lines
Product/test scope: 7 files, +234 / -7 lines ignoring end-of-line conversion
Stand-down dimensions: none
Binding: final source and build 27b521b3-3d89-40b6-889b-5350d862d08e
```

## Summary

This range retains the preceding release evidence and adds per-provider dispatch spacing, shutdown ownership of detached status computations, and a typed producer-not-closed hold that preserves other queued books. The seven product/test files were reviewed against Ender's frozen worktree; the final two-file correction was reviewed at pushed source `f6553e7b78bf9d7f011b5728b2d219ad48732add`. Local `main` and `origin/main` both named that commit. The preceding review ends at `94be5003b1e66cd4d7a4a50afe1ec2b930b1a6cb`; its findings remain in the November 3 report.

The read-only overnight evidence records a producer-not-closed refusal with 521 pending jobs. The old generic cleanup handler explains how this refusal stopped the queue; the event originally leaving that producer open is not established by the retained diagnostics. The patch does not claim to repair or erase that old producer.

## Rubric

### 1. Security

- Pass. URL allowlisting, transport isolation, shell argument handling and Electron settings are unchanged; the reviewed delta introduces no credential handling or broader file authority.

### 2. Correctness & Logic

- Concerns. **M2 [Major, pre-existing persistence-failure limit] — `public_research.py:507`: a known website pause is lost to waiting dispatchers if saving its cooldown fails.** The final correction holds the family lock through successful response validation and pause commit, then rereads the persisted family pause before another fetch. However, if A receives 429/challenge and its `BEGIN IMMEDIATE`, insert or commit fails once, the `finally` at line 515 still releases that lock with no in-memory family hold. An already-reserved B can read the preceding empty pause record and fetch after the known pause; reads can succeed when a write fails because of a full disk or transient writer contention. Scope: the cooldown persistence failure path already existed before this correction; ordinary successful persistence is fixed and covered by the new regression. Retain a fail-closed family hold when persistence fails and test that failure path in the next cycle. This is advisory missing error handling, with no identified Critical or safety-floor implication. Jane directed it to be recorded for the next cycle.

### 3. Crash / Stability Safety

- Pass. Closing a snapshot refuses new computations and joins all tracked computations, including invalidated flights. Merge close closes its snapshots before closing the catalog monitor; an overlong computation raises instead of silently passing that step.

### 4. Performance

- Pass. Host/family locks leave cached answers and other hosts independent, and the added pacing prevents delayed reservations from compressing starts within the same client.

### 5. State & Data Safety

- Pass. Only `ProducerNotClosed` carries the new job-local hold type. Its old attempt and files remain retained, and no new attempt is admitted for that job. Other cleanup errors retain the global stop and callback; ENOSPC retains its separate global stop. Publication validation and destructive file boundaries are unchanged.

### 6. Input Handling

- Pass. The queue distinguishes the retained-producer condition by exception type rather than matching error text; the changed network path retains existing URL, byte and challenge checks.

### 7. Maintainability

- Pass. The explicit hold type and snapshot thread ownership make the changed lifetime rules visible; no new finding in this range.

### 8. Doc/Code Drift

- Pass. The correction evidence records both the new behavior and its limits, including the unknown original overnight cause and the injected runner used for the independent-book regression.

### 9. Build & Release Hygiene

- Pass. The guarded replacement pack finished with exit 0 in 79.041 seconds, complete owned-process closure and native zero, without timeout or force. Its shell/backend versions are both 0.24.5. The manifest, runtime pointer, three release files and four changed packaged backend modules independently matched their recorded identities. The source worktree remained clean. The preceding c87f0090-7289-4c9b-8eed-eacc948b6d3e build is superseded and excluded from this binding.

## Verification and limits

Read-only review only: no new test, full check, live-library access, application launch or focus-taking operation was run by Senua. Ender's retained receipts under `Docs/Evidence/v0.24.5_2026-11-04/correction-focused/` record an initial 14-case pass, a 91-case affected-module pass, and a final 14-case owner-close/current-producer/startup pass. The strengthened close and producer tests first failed against the preceding product source, then passed against the correction. The earlier module run predates the strengthened close test; the final owner-close/startup receipt covers that exact strengthened test. These receipts are reviewed evidence, not an independent packaged QA verdict.

**M1 closed at f6553e7.** The initial dispatch correction at `616b072` released the family lock before committing a received pause, allowing another reserved URL to fetch afterward. The final correction keeps the lock through raw response/challenge validation and cooldown commit, rereads the current unexpired nonempty host/family pause before dispatch, and propagates `ResearchWait` without reclassifying it. `Docs/Evidence/v0.24.5_2026-11-04/m1-cooldown/` records three deterministic baseline subcase failures (FantLab 429, Wikipedia-to-Wikidata 429, DuckDuckGo 202) and a corrected 14-case `test_gap_fill` pass in 19.537 seconds, with complete owned-process closure and native zero. Its test holds the pause commit while a following URL is already reserved, proves that no following fetch escapes, then proves both readers receive the saved pause. The in-memory failure fallback in M2 remains outside this regression. Senua reviewed the source and these receipts without rerunning them.

**Packaging recovery audited.** `Docs/Evidence/v0.24.5_2026-11-04/pack-recovery/archive-proof.json` records the exact stale 0.24.1 manifest archived through the existing `capture_metadata` / `archive_metadata` native compare-and-swap path. The operator pins its original SHA256 and build ID, requires the missing runtime pointer, verifies the retained candidate and runtime, and checks that unchanged `PriorBuild` accepts the resulting fresh state. The original and archived manifest retain the same native identity, size and bytes. The 680 protected artifact/runtime/pin files have the same before/after inventory SHA256 `5c937b1c04b80daadfbd4f697e3296b78df6098950249774152d8f57d05878f7` and 1,715,444,172 logical bytes. The reviewed operator and proof contain no product or guard change and do not delete the retained artifacts.

`pack-recovery/lock-byte-restoration.json` records a CRLF-only checkout conversion of `package-lock.json`; dependency JSON was unchanged. Senua independently read the immutable `f6553e7:package-lock.json` blob and verified the release worktree's 129,812-byte file is exactly equal, SHA256 `48ff09fc1d00712e3e87aa79e746a15d2755ae34615b925956a15d18f5684f55`. No dependency change or unique source change was discarded. Sully's owned `npm ci` receipt reports 18 transitive audit findings (16 moderate, 2 high) without package/advisory details. This review does not claim a clean dependency audit or assign a construction severity from those aggregate labels; dependency versions are unchanged in the certified range. No extra audit command was run.

No disposable output was created for this review. Existing recovery and QA evidence, unrelated changes and other owners' files were preserved.

## Final candidate binding

```text
Source worktree: C:/Antigravity Projects/Worktrees/Books Arranger/0245-release-20261104
Release source commit: f6553e7b78bf9d7f011b5728b2d219ad48732add
Build ID: 27b521b3-3d89-40b6-889b-5350d862d08e
Product digest: 3a2b60eb20f3c411fe1bd8c9a1b375bf652e5d2469c4e05840fa351b64254f96
Manifest: dist/release-artifacts.json
Release artifact manifest SHA256: a44358f11c9fb7284ec07d1351867808f262edf5c7ab1d87494fbd4f6070c657
Runtime pointer: build-cache/runtime-pointer.json
Runtime pointer SHA256: 58a6e6a326194d8712afdf34e98a70f99909bfec93a4d1edabbc9853333b58e9
Lockfile SHA256: 48ff09fc1d00712e3e87aa79e746a15d2755ae34615b925956a15d18f5684f55
```

The active manifest and runtime pointer both name this build. Senua independently checked the following artifact sizes and SHA256 values against the manifest:

| Artifact under `dist/builds/27b521b3-3d89-40b6-889b-5350d862d08e/` | Bytes | SHA256 |
|---|---:|---|
| Books-Arranger-Setup-0.24.5.exe | 174681044 | `6b3a6f87a962b85798a6a3ed11aabdae7fb8258de82c38387eb49dc189e0a280` |
| Books-Arranger-Setup-0.24.5.exe.blockmap | 182057 | `60e3601c9f0ea334d7e5b0ae6cf1bfc00618f96f2cd56262b68c3c66d90cc43c` |
| latest.yml | 360 | `2782af87ec064ed265b21501634ffbe5e0ffac1fd96800873644b3eab54d0aa3` |

The packaged `audio_jobs.py`, `merge_service.py`, `public_research.py` and `working_lifecycle.py` each match both the reviewed source bytes and the payload manifest. Pack evidence: `Docs/Evidence/v0.24.5_2026-11-04/pack-f6553e7/owned.json`. This binding establishes source/artifact identity; Futaba's full check and the separately approved hidden check are pending and are not granted by this review.

## Verdict

- Total Critical: 0
- Total Major: 1
- Total Minor: 0

**Verdict:** RELEASE CLEAR

This verdict certifies the source range above, documentation-only descendants, and the exact replacement build bound above. M1 is closed; M2 remains advisory for the next cycle under ProcessRules. The earlier November 3 artifact binding does not transfer to this correction. Independent QA remains required before publication.
