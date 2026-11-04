# Code Review — Books Arranger v0.24.5

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-11-04
Tool: Books Arranger (Electron desktop with Python backend)
Release: v0.24.5
Commit range: 94be5003b1e66cd4d7a4a50afe1ec2b930b1a6cb..bf4425de09c355d2a0743771ca4209b24c8f0de1
Files changed: 140 files, +12124 / -30 lines
Product/test scope: 10 files, +527 / -30 lines ignoring end-of-line conversion
Stand-down dimensions: none
Binding: final source and build c2d002ed-118f-47c1-8364-39a8f6d91352
```

## Summary

This range retains the preceding release evidence and adds per-provider dispatch spacing, shutdown ownership of detached status computations and startup workers, a typed producer-not-closed hold that preserves other queued books, and process-local primary-thread recovery before owned media launches. The first corrections were reviewed through `cc5ea7f`; the subsequent two-file native correction was reviewed at pushed source `bf4425de09c355d2a0743771ca4209b24c8f0de1`. Its two files match Ender's frozen hashes, and local `main` and `origin/main` both named that commit. The preceding review ends at `94be5003b1e66cd4d7a4a50afe1ec2b930b1a6cb`; its findings remain in the November 3 report.

The read-only overnight evidence records a producer-not-closed refusal with 521 pending jobs. The old generic cleanup handler explains how this refusal stopped the queue; the event originally leaving that producer open is not established by the retained diagnostics. The patch does not claim to repair or erase that old producer.

## Rubric

### 1. Security

- Pass. The retained child-process handle is checked before process-local thread capture; Job assignment still precedes resume, which requires exactly one owned suspended thread. Capture, enumeration and cleanup errors refuse the launch. URL allowlisting, shell arguments, Electron settings and file authority are unchanged.

### 2. Correctness & Logic

- Concerns. **M2 [Major, pre-existing persistence-failure limit] — `public_research.py:507`: a known website pause is lost to waiting dispatchers if saving its cooldown fails.** The final correction holds the family lock through successful response validation and pause commit, then rereads the persisted family pause before another fetch. However, if A receives 429/challenge and its `BEGIN IMMEDIATE`, insert or commit fails once, the `finally` at line 515 still releases that lock with no in-memory family hold. An already-reserved B can read the preceding empty pause record and fetch after the known pause; reads can succeed when a write fails because of a full disk or transient writer contention. Scope: the cooldown persistence failure path already existed before this correction; ordinary successful persistence is fixed and covered by the new regression. Retain a fail-closed family hold when persistence fails and test that failure path in the next cycle. This is advisory missing error handling, with no identified Critical or safety-floor implication. Jane directed it to be recorded for the next cycle.

### 3. Crash / Stability Safety

- Pass. Closing a snapshot refuses new computations and joins all tracked computations, including invalidated flights. Startup regroup admission and the closing flag share `_BULK_LOCK`; its retained thread is joined outside that lock before dependent resources close. Published verification now honors its supplied close timeout and raises while still alive. Timeout paths retain the service/queue for retry instead of claiming completed closure.

### 4. Performance

- Pass. Host/family locks preserve independent cached reads. Production primary-thread recovery now captures only the retained child process rather than enumerating machine threads; the measured saving and remaining end-to-end variance are recorded below.

### 5. State & Data Safety

- Pass. Only `ProducerNotClosed` carries the new job-local hold type. Its old attempt and files remain retained, and no new attempt is admitted for that job. Other cleanup errors retain the global stop and callback; ENOSPC retains its separate global stop. Publication validation and destructive file boundaries are unchanged.

### 6. Input Handling

- Pass. The queue distinguishes the retained-producer condition by exception type rather than matching error text; the changed network path retains existing URL, byte and challenge checks.

### 7. Maintainability

- Pass. The explicit hold type and snapshot thread ownership make the changed lifetime rules visible; no new finding in this range.

### 8. Doc/Code Drift

- Pass. The correction evidence records both the new behavior and its limits, including the unknown original overnight cause and the injected runner used for the independent-book regression.

### 9. Build & Release Hygiene

- Pass. The guarded replacement pack for `bf4425d` finished with exit 0 in 87.254 seconds, complete owned-process closure and native zero, without timeout or force. The shell/backend versions are both 0.24.5. The manifest, runtime pointer, three release files and five changed packaged backend modules independently matched their recorded identities; the source worktree remained clean. Package/dependency/build inputs and the 60-second job wait are unchanged. Earlier builds c87f0090-7289-4c9b-8eed-eacc948b6d3e, 27b521b3-3d89-40b6-889b-5350d862d08e and 3369d944-a8e3-4513-a758-5e006309cf9b are superseded and excluded from this binding.

## Verification and limits

Read-only review only: no new test, full check, live-library access, application launch or focus-taking operation was run by Senua. Ender's retained receipts under `Docs/Evidence/v0.24.5_2026-11-04/correction-focused/` record an initial 14-case pass, a 91-case affected-module pass, and a final 14-case owner-close/current-producer/startup pass. The strengthened close and producer tests first failed against the preceding product source, then passed against the correction. The earlier module run predates the strengthened close test; the final owner-close/startup receipt covers that exact strengthened test. These receipts are reviewed evidence, not an independent packaged QA verdict.

**M1 closed at f6553e7.** The initial dispatch correction at `616b072` released the family lock before committing a received pause, allowing another reserved URL to fetch afterward. The final correction keeps the lock through raw response/challenge validation and cooldown commit, rereads the current unexpired nonempty host/family pause before dispatch, and propagates `ResearchWait` without reclassifying it. `Docs/Evidence/v0.24.5_2026-11-04/m1-cooldown/` records three deterministic baseline subcase failures (FantLab 429, Wikipedia-to-Wikidata 429, DuckDuckGo 202) and a corrected 14-case `test_gap_fill` pass in 19.537 seconds, with complete owned-process closure and native zero. Its test holds the pause commit while a following URL is already reserved, proves that no following fetch escapes, then proves both readers receive the saved pause. The in-memory failure fallback in M2 remains outside this regression. Senua reviewed the source and these receipts without rerunning them.

**Startup lifetime correction reviewed at cc5ea7f.** The full check on the superseded `f6553e7` build ran 2,349 Python cases with one teardown error in the strict-port/owner-lock case: WinError 32 removing its private SQLite file. Node passed 242/242. The original handle was unavailable after gate cleanup, so direct attribution of that historical handle remains unproved. An event-controlled baseline then demonstrated two actual lifetime defects on that same source: server close returned while the untracked `books-folder-regroup` daemon held a real catalog connection, and the published verifier silently survived an explicit close timeout.

`Docs/Evidence/v0.24.5_2026-11-04/sqlite-lifetime-correction/` records those two expected baseline failures, then 71/71 corrected focused cases in 20.336 seconds with complete owned closure and native zero. The real regroup connection and thread must exit before server close completes, and the catalog then admits native DELETE access. Repeat startup retains one live regroup worker; startup after close admits none. A simulated live regroup worker makes close raise without closing dependent jobs/cleanup, and a later close succeeds after it exits. The real verifier connection likewise makes its explicit timeout raise until closure. Final patch SHA256 `164ba429a5f62c2ad8d1f5417d6787826b149cfbc1d35d7b4c70b336facb2e89` and all four frozen source hashes matched the committed correction. No new finding arose from its admission, join ordering or failure paths. The later full run passed the SQLite closure cases; its separate R56 failure is recorded below.

**Native process snapshot correction reviewed at bf4425d.** The full check on superseded `cc5ea7f` ran 2,352 Python cases with only R56's private Approve job exceeding its unchanged 60-second wait; Node passed 242/242. That NO-GO is retained under `new-build-r2-full-entry-failure/`. The correction replaces production Toolhelp enumeration with `PssCaptureSnapshot` on the already-retained child handle and uses `PSS_CAPTURE_THREADS` only, without an address-space clone. The static `PSS_THREAD_ENTRY` definition matches SDK `processsnapshot.h` lines 323–349: x64 size 120, PID/TID offsets 16/20 and flags/suspend offsets 104/108. Senua checked the field declaration and capture contract against [Microsoft's structure](https://learn.microsoft.com/en-us/windows/win32/api/processsnapshot/ns-processsnapshot-pss_thread_entry) and [capture flags](https://learn.microsoft.com/en-us/windows/win32/api/processsnapshot/ne-processsnapshot-pss_capture_flags).

The helper checks process-handle identity, one nonterminated entry with suspend count 1, and a second walk returning the documented end status. It retains the thread handle before freeing marker/snapshot, frees the locally owned snapshot through `GetCurrentProcess`, then verifies native thread ownership and requires `ResumeThread`'s previous count to equal 1. Nested cleanup attempts snapshot release even if marker release fails; a failed cleanup prevents resume and the caller tears down its owned Job. The API bindings use documented DWORD status returns and one shared ctypes structure. The ownership and enumeration rules were checked against [PssFreeSnapshot](https://learn.microsoft.com/en-us/windows/win32/api/processsnapshot/nf-processsnapshot-pssfreesnapshot) and [PssWalkSnapshot](https://learn.microsoft.com/en-us/windows/win32/api/processsnapshot/nf-processsnapshot-psswalksnapshot); no fallback weakens a refused launch.

`r56-primary-performance/` records 37/37 safety cases in 14.478 seconds, including real Job assignment before resume, refusal teardown, parallel children and API/cleanup failures. The matched comparison used 12 peer processes per arm, with all 26 children exiting 0 and complete owned closure/native zero. Across 45 launches, primary-thread recovery fell from 14.1368 to 0.0112 seconds; machine thread snapshots fell from 45 to zero; 24 codec operations fell from 14.8849 to 7.2981 seconds. Whole-case times were 62.938 and 58.068 seconds, including fixture preparation, and both original wait deadlines passed. This did not reproduce the full-run timeout or establish a timing guarantee: post-completion work rose from 22.686 to 28.232 seconds, status reads remained around 39–40 seconds, and the same outer owner retained earlier handles into the corrected arm. Patch SHA256 `6ff570e5a7b338d3ec43d739a8ba2ad14b568069efe5b01161ab077563329b41` and both frozen file hashes matched committed source. No full or hidden check was run by Senua or asserted by this focused evidence.

**Packaging recovery audited.** `Docs/Evidence/v0.24.5_2026-11-04/pack-recovery/archive-proof.json` records the exact stale 0.24.1 manifest archived through the existing `capture_metadata` / `archive_metadata` native compare-and-swap path. The operator pins its original SHA256 and build ID, requires the missing runtime pointer, verifies the retained candidate and runtime, and checks that unchanged `PriorBuild` accepts the resulting fresh state. The original and archived manifest retain the same native identity, size and bytes. The 680 protected artifact/runtime/pin files have the same before/after inventory SHA256 `5c937b1c04b80daadfbd4f697e3296b78df6098950249774152d8f57d05878f7` and 1,715,444,172 logical bytes. The reviewed operator and proof contain no product or guard change and do not delete the retained artifacts.

`pack-recovery/lock-byte-restoration.json` records a CRLF-only checkout conversion of `package-lock.json`; dependency JSON was unchanged. Senua independently read the immutable `f6553e7:package-lock.json` blob and verified the release worktree's 129,812-byte file is exactly equal, SHA256 `48ff09fc1d00712e3e87aa79e746a15d2755ae34615b925956a15d18f5684f55`. No dependency change or unique source change was discarded. Sully's owned `npm ci` receipt reports 18 transitive audit findings (16 moderate, 2 high) without package/advisory details. This review does not claim a clean dependency audit or assign a construction severity from those aggregate labels; dependency versions are unchanged in the certified range. No extra audit command was run.

No disposable output was created for this review. Existing recovery and QA evidence, unrelated changes and other owners' files were preserved.

## Final candidate binding

```text
Source worktree: C:/Antigravity Projects/Worktrees/Books Arranger/0245-release-20261104-r3
Release source commit: bf4425de09c355d2a0743771ca4209b24c8f0de1
Build ID: c2d002ed-118f-47c1-8364-39a8f6d91352
Product digest: 509fcca6bf4c909827bd815cd6c6b3bcce4aa111e085f9eec0186e4bb6c7b156
Manifest: dist/release-artifacts.json
Release artifact manifest SHA256: 0c01cb73b9ed7b4adc7e6eeccdbb30b1c933a99ccf554af5fbf0aca4b0a09133
Runtime pointer: build-cache/runtime-pointer.json
Runtime pointer SHA256: 0f66ee569f9d6c5e4deca41098f11ed8aa2495e7a93b38da41f6678daf81b997
Lockfile SHA256: 48ff09fc1d00712e3e87aa79e746a15d2755ae34615b925956a15d18f5684f55
```

The active manifest and runtime pointer both name this build. Senua independently checked the following artifact sizes and SHA256 values against the manifest:

| Artifact under `dist/builds/c2d002ed-118f-47c1-8364-39a8f6d91352/` | Bytes | SHA256 |
|---|---:|---|
| Books-Arranger-Setup-0.24.5.exe | 174683299 | `3a6e22a63cdd7f04c55dfe282bfdb3d221e77709a69e1cafc67ad479e6ad22f5` |
| Books-Arranger-Setup-0.24.5.exe.blockmap | 182063 | `fe9207b74c95a828e2b23e742af607ddb4932e0f123d1e6038ef0ce853d94127` |
| latest.yml | 360 | `8d9bc2ce801a314b3c38ed0a559668ac855cd6fc1356b915a791c07cba9c92c4` |

The packaged `audio_jobs.py`, `merge_service.py`, `public_research.py`, `working_lifecycle.py` and `native_io.py` each match the release worktree's source bytes and payload manifest. All five also match the immutable reviewed `bf4425d` Git blobs after CRLF-to-LF normalization; checkout line-ending conversion is the only difference where raw hashes vary. Pack evidence is under `Docs/Evidence/v0.24.5_2026-11-04/pack-bf4425d/`. This binding establishes source/artifact identity. At this handoff focused/full QA and the separately approved hidden check remain pending; this review does not grant behavior clearance. Superseded build `3369d944` and its full-check NO-GO remain recorded under `new-build-r2-full-entry-failure/`.

## Verdict

- Total Critical: 0
- Total Major: 1
- Total Minor: 0

**Verdict:** RELEASE CLEAR

This verdict certifies the source range above, documentation-only descendants, and the exact replacement build bound above. M1 is closed; M2 remains advisory for the next cycle under ProcessRules. Independent QA remains required before publication.
