# Code Review — Books Arranger v0.12.2

## Header

Reviewer: Senua. Date: 2026-10-12. Target release: v0.12.2.

Commit-range baseline: `a45566237eeeb8b79a15a16f7a046dcdab14ec3c` (documentation child of physical stable v0.12.1 `a36d3fe`). Reviewed endpoint is the exact uncommitted native candidate manifest `77c5145ac68837ca65d91a26174dce8e4fbf3bab4e64e124bf70fe36853241e2`, source digest `83cb44b8b5f079358cc6e70815c044015c00f3a74a11b1a1327ab9de5603d4fa`. Actual release commit does not yet exist; Sully must supply the committed endpoint for reconciliation before tag/publication.

Scope: native_io.py and tests/test_native_thread_check.py only; 2 files, +108 / -7. Python/native Windows utility, no Electron/browser/UI changes. Failed-job recovery helper, existing failed-job state, actual library actions and browser prototype are explicitly excluded from this clearance.

## Summary

The actual source-check failure matches a race in resume_owned_primary: overlapping calls recreate identically named but distinct ctypes ThreadEntry classes and replace shared DLL function pointer argtypes before another caller passes its entry pointer. The patch defines one 28-byte Windows ThreadEntry identity and binds snapshot/enumeration/open/resume signatures once at module initialization. Real typed pointers and native calls remain; there is no cast/alias workaround. Both producer and independent QA deterministically reproduced the exact baseline ArgumentError and verified the candidate preserves ABI identity while actual owned child/media-source operations advance safely.

## Rubric

### 1. Security

Pass. No ownership/path/process-creation permission is broadened. Native Job assignment before resume, exact primary-thread cardinality, PID revalidation and suspend-count requirement remain.

### 2. Correctness & Logic

Pass. Deterministic barrier-controlled actual native enumeration reproduces the old expected-LP_ThreadEntry/pointer-to-ThreadEntry mismatch; candidate instead returns the expected no-owned-primary refusal with no open/resume. ABI size, offsets, pointer identity and BOOL results pass. Two actual private children finish; private source probing/PCM validation advances to the deliberate invalid-cover hold.

### 3. Crash / Stability Safety

Pass for changed boundary. Per-call shared signature mutation is removed. Snapshot/thread handles still close. Native private concurrency and early-descendant cancellation pass. No claim of universal recovery or uninterrupted processing follows.

### 4. Performance

Pass. Initialization is performed once; no new loop, retry, process or scan is added to product behavior.

### 5. State & Data Safety

Pass. Publication, retirement, recovery retention and queue state are untouched. Native private audio fixture retains source hashes, no output and no publication intent after an intentionally invalid cover. Existing collision/reparse safety fixtures pass. Protected-source verification and 24-hour recovery remain unchanged.

### 6. Input Handling

Pass. Matching exactly one thread of the exact owned PID remains mandatory; GetProcessIdOfThread and ResumeThread==1 guards remain. The new unmatched-PID fixture uses -1, impossible for DWORD process IDs, with OpenThread/ResumeThread fail-if-called assertions.

### 7. Maintainability

Pass. One module-level ABI type and explicit native signatures remove the race without adding locking, permissive casting or architecture.

### 8. Doc/Code Drift

Pass with scope limits. Evidence identifies this exact native argument mismatch; it does not make every ArgumentError recoverable. Existing failed jobs require a separate guarded proposal. Browser default remains unchanged; its failed search prototype is outside this patch.

### 9. Build & Release Hygiene

Pass for exact source candidate and finite proof. Actual version bump/commit/tag and final commit mapping remain Sully's subsequent procedural work. Input/manifest/runtime pins match before/after finite execution. No unrelated broad regression suite was rerun.

## Exact source and finite-route pins

Paths below are relative to scratch/native-thread-check-2026-10-12.

| Input | SHA-256 |
| --- | --- |
| candidate/native_io.py | 6509963b1ff3aa414441a7ec4728874ee41ebfbc6c2d13c76a17c04193f65e80 |
| candidate/tests/test_native_thread_check.py | 2cce2e4689b5c3d1ce9a48aba8d5bfac7005d9d1e98c17db60fd470eb6939bf2 |
| candidate/manifest.json | 77c5145ac68837ca65d91a26174dce8e4fbf3bab4e64e124bf70fe36853241e2 |
| baseline_native_io.py | 5bc7bfaf137e6eea29a5c4e829f6ae1fd604b2152fe8fdd61f139ab84215855e |
| producer inner qa_checks_receiver_owned.py | 835d40776d48e525b9ddc7bcc20c804566b015c1393e7afad7c3347d4f7cdc9d |
| producer outer run_qa_receiver_owned.py | cf1fc2bfc06d53a1122f963dc3d72bc91faacd3988b4bba5dafd050faea62157 |
| receiver inner qa_checks_independent_receiver_owned.py | 59b477cc618134608e8f2d29e80db2f0c13d5ff3968dcb54aefb9d8403a6dbb7 |
| receiver outer run_qa_independent_receiver_owned.py | bd9604a962ebdc9e4747293a49b6156f335c47638434be182f78a31aa0c228e6 |
| receiver-contract.json | d04397b22ac2599b009df375289873a32053cec018ca75521a99ea59318a0d1b |

**Finite producer and receiver routes: CLEARED**, each fixed Python314/python.exe plus its outer script above, no arguments. They retain the previously audited containment native `9939de63b3448e02f0c664d43242fe46e728a2f4f77ad21ed62f0bf98c7fad44`, Python `434b361fe0c5960d404974feed493db47f2603a1ace2574312104fbed0182c6f`, ffmpeg/ffprobe/runtime/source holds, suspended owned child assignment before resume, total 600000 ms deadline/reserved teardown, capped continuous drains and verified descendant/output closure. Receiver diff only changes its independently owned receipt paths and inner pin.

Initial pre-review fixture used PID 0, which does not guarantee no system idle thread. Senua rejected that route before execution; Ender changed it to impossible DWORD PID -1 and fail-if-called native open/resume mocks. Baseline reproduction still invokes actual First/Next and preserves the exact ctypes error. Previous route bytes were retained; no unsafe test was run. Review history: scratch/native-thread-check-2026-10-12/Senua_Native_Preexecution_Review.md.

## Actual validation evidence

Producer and independent receiver each passed the same **12 distinct fully qualified Python test IDs**, 6 native/concurrency/private-audio cases and 6 native safety boundary cases. This is 12 unique cases independently verified twice, not 24. Senua independently read actual verbose receipts, source/manifest pins, all suite exits and outer closure fields.

Producer outer 10.0184762 s / inner 9.9734818 s; receiver outer 10.6453752 s / inner 10.5979994 s. Outer exit 0, both suites exit 0, no errors/warnings/truncated streams, complete owned closure/drains. Futaba independently issued GO for these two source/test files; no recovery-helper or real library action was tested.

| Actual proof | SHA-256 |
| --- | --- |
| producer-check-receipt.json | ee09f93bf6ff90778518cb3de59b0269fa21a882699cab71b514699885d3a1a0 |
| producer-owned-receipt.json | db187f57f9701220d7b51496a1d17f5df823a66055032c31f8b17b6c01160185 |
| receiver-check-receipt.json | ab97202383ca00ca5dbe2b0cbfdc31bf5f13797a08fd1497bb09bb3ca7d75be2 |
| receiver-owned-receipt.json | 75b08dc8dc491b0295491d9b2a49a19aacdddc058a4d4dccced2a84131868c79 |

## Verdict

Total Critical: 0. Total Major: 0. Total Minor: 0. Safety floor intact.

**Verdict:** RELEASE CLEAR

This clears the exact two-file ABI candidate against baseline a45566237eeeb8b79a15a16f7a046dcdab14ec3c. Sully must map the source/test blobs and v0.12.2 metadata to the actual release commit before publication. It does not reclassify or retry the existing failed job, authorize a one-off recovery helper, alter source protection or certify live application/new loaded owner. Those are separate guarded work.
