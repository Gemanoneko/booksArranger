# Code Review — Books Arranger v0.24.5

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-11-04
Tool: Books Arranger (Electron desktop with Python backend)
Release: v0.24.5
Commit range: 94be5003b1e66cd4d7a4a50afe1ec2b930b1a6cb..cc5ea7f9deb3b2843cb75b1392e24314532a0f2a
Files changed: 125 files, +10744 / -13 lines
Product/test scope: 9 files, +350 / -13 lines ignoring end-of-line conversion
Stand-down dimensions: none
Binding: final source and build 3369d944-a8e3-4513-a758-5e006309cf9b
```

## Summary

This range retains the preceding release evidence and adds per-provider dispatch spacing, shutdown ownership of detached status computations and startup workers, and a typed producer-not-closed hold that preserves other queued books. The first seven-file correction and the two-file cooldown follow-up were reviewed through `f6553e7`; the subsequent four-file shutdown correction was reviewed at pushed source `cc5ea7f9deb3b2843cb75b1392e24314532a0f2a`. Its four files match Ender's frozen hashes, and local `main` and `origin/main` both named that commit. The preceding review ends at `94be5003b1e66cd4d7a4a50afe1ec2b930b1a6cb`; its findings remain in the November 3 report.

The read-only overnight evidence records a producer-not-closed refusal with 521 pending jobs. The old generic cleanup handler explains how this refusal stopped the queue; the event originally leaving that producer open is not established by the retained diagnostics. The patch does not claim to repair or erase that old producer.

## Rubric

### 1. Security

- Pass. URL allowlisting, transport isolation, shell argument handling and Electron settings are unchanged; the reviewed delta introduces no credential handling or broader file authority.

### 2. Correctness & Logic

- Concerns. **M2 [Major, pre-existing persistence-failure limit] — `public_research.py:507`: a known website pause is lost to waiting dispatchers if saving its cooldown fails.** The final correction holds the family lock through successful response validation and pause commit, then rereads the persisted family pause before another fetch. However, if A receives 429/challenge and its `BEGIN IMMEDIATE`, insert or commit fails once, the `finally` at line 515 still releases that lock with no in-memory family hold. An already-reserved B can read the preceding empty pause record and fetch after the known pause; reads can succeed when a write fails because of a full disk or transient writer contention. Scope: the cooldown persistence failure path already existed before this correction; ordinary successful persistence is fixed and covered by the new regression. Retain a fail-closed family hold when persistence fails and test that failure path in the next cycle. This is advisory missing error handling, with no identified Critical or safety-floor implication. Jane directed it to be recorded for the next cycle.

### 3. Crash / Stability Safety

- Pass. Closing a snapshot refuses new computations and joins all tracked computations, including invalidated flights. Startup regroup admission and the closing flag share `_BULK_LOCK`; its retained thread is joined outside that lock before dependent resources close. Published verification now honors its supplied close timeout and raises while still alive. Timeout paths retain the service/queue for retry instead of claiming completed closure.

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

- Pass. The guarded replacement pack for `cc5ea7f` finished with exit 0 in 125.581 seconds, complete owned-process closure and native zero, without timeout or force. The shell/backend versions are both 0.24.5. The manifest, runtime pointer, three release files and four changed packaged backend modules independently matched their recorded identities; the source worktree remained clean. Earlier builds c87f0090-7289-4c9b-8eed-eacc948b6d3e and 27b521b3-3d89-40b6-889b-5350d862d08e are superseded and excluded from this binding.

## Verification and limits

Read-only review only: no new test, full check, live-library access, application launch or focus-taking operation was run by Senua. Ender's retained receipts under `Docs/Evidence/v0.24.5_2026-11-04/correction-focused/` record an initial 14-case pass, a 91-case affected-module pass, and a final 14-case owner-close/current-producer/startup pass. The strengthened close and producer tests first failed against the preceding product source, then passed against the correction. The earlier module run predates the strengthened close test; the final owner-close/startup receipt covers that exact strengthened test. These receipts are reviewed evidence, not an independent packaged QA verdict.

**M1 closed at f6553e7.** The initial dispatch correction at `616b072` released the family lock before committing a received pause, allowing another reserved URL to fetch afterward. The final correction keeps the lock through raw response/challenge validation and cooldown commit, rereads the current unexpired nonempty host/family pause before dispatch, and propagates `ResearchWait` without reclassifying it. `Docs/Evidence/v0.24.5_2026-11-04/m1-cooldown/` records three deterministic baseline subcase failures (FantLab 429, Wikipedia-to-Wikidata 429, DuckDuckGo 202) and a corrected 14-case `test_gap_fill` pass in 19.537 seconds, with complete owned-process closure and native zero. Its test holds the pause commit while a following URL is already reserved, proves that no following fetch escapes, then proves both readers receive the saved pause. The in-memory failure fallback in M2 remains outside this regression. Senua reviewed the source and these receipts without rerunning them.

**Startup lifetime correction reviewed at cc5ea7f.** The full check on the superseded `f6553e7` build ran 2,349 Python cases with one teardown error in the strict-port/owner-lock case: WinError 32 removing its private SQLite file. Node passed 242/242. The original handle was unavailable after gate cleanup, so direct attribution of that historical handle remains unproved. An event-controlled baseline then demonstrated two actual lifetime defects on that same source: server close returned while the untracked `books-folder-regroup` daemon held a real catalog connection, and the published verifier silently survived an explicit close timeout.

`Docs/Evidence/v0.24.5_2026-11-04/sqlite-lifetime-correction/` records those two expected baseline failures, then 71/71 corrected focused cases in 20.336 seconds with complete owned closure and native zero. The real regroup connection and thread must exit before server close completes, and the catalog then admits native DELETE access. Repeat startup retains one live regroup worker; startup after close admits none. A simulated live regroup worker makes close raise without closing dependent jobs/cleanup, and a later close succeeds after it exits. The real verifier connection likewise makes its explicit timeout raise until closure. Final patch SHA256 `164ba429a5f62c2ad8d1f5417d6787826b149cfbc1d35d7b4c70b336facb2e89` and all four frozen source hashes matched the committed correction. No new finding arose from its admission, join ordering or failure paths. The pending full check remains the broader behavior gate.

**Packaging recovery audited.** `Docs/Evidence/v0.24.5_2026-11-04/pack-recovery/archive-proof.json` records the exact stale 0.24.1 manifest archived through the existing `capture_metadata` / `archive_metadata` native compare-and-swap path. The operator pins its original SHA256 and build ID, requires the missing runtime pointer, verifies the retained candidate and runtime, and checks that unchanged `PriorBuild` accepts the resulting fresh state. The original and archived manifest retain the same native identity, size and bytes. The 680 protected artifact/runtime/pin files have the same before/after inventory SHA256 `5c937b1c04b80daadfbd4f697e3296b78df6098950249774152d8f57d05878f7` and 1,715,444,172 logical bytes. The reviewed operator and proof contain no product or guard change and do not delete the retained artifacts.

`pack-recovery/lock-byte-restoration.json` records a CRLF-only checkout conversion of `package-lock.json`; dependency JSON was unchanged. Senua independently read the immutable `f6553e7:package-lock.json` blob and verified the release worktree's 129,812-byte file is exactly equal, SHA256 `48ff09fc1d00712e3e87aa79e746a15d2755ae34615b925956a15d18f5684f55`. No dependency change or unique source change was discarded. Sully's owned `npm ci` receipt reports 18 transitive audit findings (16 moderate, 2 high) without package/advisory details. This review does not claim a clean dependency audit or assign a construction severity from those aggregate labels; dependency versions are unchanged in the certified range. No extra audit command was run.

No disposable output was created for this review. Existing recovery and QA evidence, unrelated changes and other owners' files were preserved.

## Final candidate binding

```text
Source worktree: C:/Antigravity Projects/Worktrees/Books Arranger/0245-release-20261104-r2
Release source commit: cc5ea7f9deb3b2843cb75b1392e24314532a0f2a
Build ID: 3369d944-a8e3-4513-a758-5e006309cf9b
Product digest: 749eee7ece79f60b4236cdfc6481bcf5d16595b0a88009fb5df596321cc0380f
Manifest: dist/release-artifacts.json
Release artifact manifest SHA256: 233f2a17919e596a63a16a7661df7ce2c5972b65a84f8c1823aeaacee9a8c1dc
Runtime pointer: build-cache/runtime-pointer.json
Runtime pointer SHA256: f93162afd9dcfaacdfc7cd68c2267028c713b441ac97ea91c8419e0cc9b8a20a
Lockfile SHA256: 48ff09fc1d00712e3e87aa79e746a15d2755ae34615b925956a15d18f5684f55
```

The active manifest and runtime pointer both name this build. Senua independently checked the following artifact sizes and SHA256 values against the manifest:

| Artifact under `dist/builds/3369d944-a8e3-4513-a758-5e006309cf9b/` | Bytes | SHA256 |
|---|---:|---|
| Books-Arranger-Setup-0.24.5.exe | 174681700 | `e49e1716747f2d1cb82955c3cf66b0f970a4e6eedac080c12d0a785f9c16421d` |
| Books-Arranger-Setup-0.24.5.exe.blockmap | 182052 | `ce536995c0bf6fc77c623ffb1bad769aba61bc7f4dd660f8fcd894473bcb796e` |
| latest.yml | 360 | `e19fe0e3bfb36117af629de0efd78a7c8ed8deeb25c5de374372c747f8d34f7d` |

The packaged `audio_jobs.py`, `merge_service.py`, `public_research.py` and `working_lifecycle.py` each match both the reviewed source bytes and the payload manifest. Pack evidence is under `Docs/Evidence/v0.24.5_2026-11-04/pack-cc5ea7f/`. This binding establishes source/artifact identity. At this handoff the full check and separately approved hidden check remain pending; this review does not grant either behavior clearance. Superseded build `27b521b3` and its full-check NO-GO remain recorded under `new-build-full-entry-failure/`.

## Verdict

- Total Critical: 0
- Total Major: 1
- Total Minor: 0

**Verdict:** RELEASE CLEAR

This verdict certifies the source range above, documentation-only descendants, and the exact replacement build bound above. M1 is closed; M2 remains advisory for the next cycle under ProcessRules. Independent QA remains required before publication.
