# Code Review — Books Arranger v0.12.1

## Header

Reviewer: Senua. Date: 2026-10-12. Release: v0.12.1.

Commit range: `b569cc1e556726043671f9b329a2f3cb0cf49ea7..0b0101d1b6e631ec2df81cb31da9a9e00a5433bb`. Baseline is released v0.12.0; endpoint is Sully's committed v0.12.1 candidate, tree `09deb6e70a6c3ca5873d5b80e0234396d2c8c60b`. Documentation base `be29dc1a00bf17def33e8962ec6a524eeed5aa8f` is an ancestor of that endpoint. Exact reviewed candidate manifest `8c8381b1b687d769f6cc93b1c620d653d1c7d6278bad94420cb2ecf7e63dce52`, source digest `493ed60cba9883497a624a46742125dcf9a772c4491862ac9ca34b1093a9c020` maps to the committed product/test blobs. Senua independently verified all six Git-normalized blob identities against the pinned candidate, actual tree, changed path list, VERSION 0.12.1 and bounded CHANGELOG delta before publication.

Files changed in the certified commit range: 13, +574 / -13 (including VERSION, CHANGELOG and five authorized documentation files). Product/test delta: 6, +255 / -12. Manual Python/web application, no Electron changes. UI unchanged; no UI design delta. Scope excludes live databases/library, live launch/owner changes, Comics/Comix and Open Library datasets.

## Summary

The patch retries native SQLite BUSY only at four replay-safe database transaction boundaries: automatic progress checkpoint, fetched research-cache persistence, atomic Paused checkpoint/candidate reset, and failure-diagnostic persistence. Retries acquire fresh BEGIN IMMEDIATE, roll back failed attempts, close connections, and are capped at 30 seconds / 60 attempts with short acquisition waits. Stop remains interruptible during worker progress/cache retry; final Paused persistence completes without restarting work. A stale Stop snapshot can no longer overwrite an already committed Paused, Completed or Needs attention state. Network requests, budgets, approvals, conversion, publication and source retirement are never replayed by this helper.

## Rubric

### 1. Security

Pass. No dynamic shell, secret logging, library path or deletion surface added; DB-only callbacks and finite fixed test commands retain ownership boundaries.

### 2. Correctness & Logic

Pass. Real private WAL contention, native error classification, rollback, single cache request/budget debit, atomic pause and stale Stop regression passed. The failure mock now targets the actual retry connection boundary while retaining every refusal assertion.

### 3. Crash / Stability Safety

Concerns. [Major] `automatic_processing.py:182`: Stop persists Stopping before setting stop_event; persistent lock exhaustion can still refuse Stop entry. Other unchanged direct DB operations also have no universal BUSY recovery. This is a bounded transient-contention fix, not uninterrupted-processing assurance. The interrupted worker's former separate candidate-reset failure path is fixed with atomic save and fail-closed diagnostics.

### 4. Performance

Pass. Bounded backoff and short fresh lock acquisition replace immediate failure only in small safe writes. No tight request loop or broad operation replay introduced.

### 5. State & Data Safety

Pass. Failed transactions roll back and close; exhausted persistence retains existing volatile failure preventing Start. Paused is reported only after native work drains and the atomic checkpoint commits. Four private completed-proof records and pending checkpoint survive contention. Existing original verification, native source/publication guards and 24-hour recovery are unchanged.

### 6. Input Handling

Pass. Retry requires a native integer error code whose primary code is SQLITE_BUSY; message-only and non-BUSY errors propagate. No lock owner is assumed from error text.

### 7. Maintainability

Pass. One documented restricted helper; four narrow DB callbacks. No controller-wide retry, request replay or test safety assertion removal.

### 8. Doc/Code Drift

Pass with stated limits. Standing rules remain unchanged. The original live lock owner was not recorded; locating checkpoint/cache failure does not identify that owner. No claim of complete root-cause removal, live application, successful new owner launch or actual completed-book conversion follows from private tests.

### 9. Build & Release Hygiene

Pass for committed candidate and finite proof. VERSION 0.12.1 and CHANGELOG accurately describe the bounded fix and remaining contention limits. Source and test blobs match the reviewed/tested pins after Git line-ending normalization; no seventh product file or interface change appears. Tag/publication and eventual live application remain Sully's procedural work. Candidate native containment/runtime/source hashes were held and reverified by the approved finite route. No interface change needs fresh interface assertions.

## Exact changed source pins

All paths are relative to `scratch/sqlite-busy-2026-10-12/candidate`.

| File | SHA-256 |
| --- | --- |
| automatic_processing.py | fa42f0afebe8bbc3be15cd0715a9ee3e3a2dd0a001992c2fb802ce739402a5eb |
| public_research.py | 491b6e97c30fce13ccca54ddc32a642a0480c468d2241846ddfa9ce5f9dc00f3 |
| scanner.py | eccc12da5a61405dcaa64ad9750e6c8933c792d2ab4c0e8683a9fde1cd1410c8 |
| sqlite_retry.py | 2e840ee9a3b2a4a12ab40ae0ecdfff4b1b70f9b40c0c78fb570a46d3704ba80d |
| tests/test_automatic_processing.py | 53a5d63d42f703fd2d72b676ca3d8fcaf1d91b3ae70ec68b2bac16ac1b407a4d |
| tests/test_sqlite_busy.py | 5ec316393c34e9aaad5833781b2312508fa3550e090d3e97a79ce2574b6669a0 |

## Finite route and actual evidence

**Finite routes: CLEARED.** Producer `run_qa_owned.py` and independent receiver `run_qa_receiver_owned.py` accept no arguments and run only the three fixed suites using pinned C:/Python314/python.exe. Existing audited native kill-on-close Job containment is established on newly created hidden suspended children before resume; assignment failure closes only the owned newly created process. Total 600000 ms deadline, reserved teardown, continuously drained bounded stdout/stderr, descendant closure and output joins are retained. Receipt-only receiver delta was separately reviewed. Runtime/native dependency pins and entire source manifest are checked before/after execution. No service launch, real network request, live library or canonical source mutation occurs in this route.

| Final route | Outer SHA-256 | Inner SHA-256 | Contract SHA-256 |
| --- | --- | --- | --- |
| Producer | 70d05b7f9d5053614e06edbcf8dea5a1eca673b1b17b85fabef3e053b6f0c84e | 1590e984a231a39a15df7e89d0e66d17fc85f1724b46d9335c4a003f5eff96cf | 309a0d6ef93ef26f0d39ddd5d8d5d1b6e184775a92553d07a4a29a4432dd15e7 |
| Receiver | 96ca9e15495c1e04b4abe8e613d2aac9fd52fd41c8a2c1336c5a10f6e52c1ea6 | 9d228c69e1cdd692152740748f80d690ab3b3c03136778d02b3bf4cee488517a | 0a38d7509d82022074ec826834c486b1f29db21957b4fb7b01f6ca8272e07f3d |

Each final invocation passed **78 unique Python tests: 16 BUSY + 52 controller + 10 inventory**. These are the same 78 identities independently verified twice, not 156 distinct tests. Case IDs extracted from actual verbose successful output match the packet, sorted-ID digest `127894b6fbd421f8ece8ad9e9fdab62640341e13f8471a0040e0aae467dcce67`.

Producer outer 45.1228842 s / inner 45.0573019 s; receiver outer 42.1834386 s / inner 42.1212246 s. Both outer exit 0, all three suites exit 0, no error, no truncated streams and complete owned teardown/drains. Senua independently read actual receipts and verified their hashes, success/source/manifest/exit fields; Futaba independently extracted matching unique case identities. Existing mock-HTTP ResourceWarnings remain in proof, not hidden.

| Proof in scratch/sqlite-busy-2026-10-12 | SHA-256 |
| --- | --- |
| producer-check-receipt.json | d4cf97da103f04b0ef90e3887cf73de7b04a8bfc25f9c21b44f8069f59f8ab79 |
| producer-owned-receipt.json | 5efe2f9885fae5a7cf5e649c961909b2fa57fe30f0b85b8ce60f8c3d8e344ee1 |
| receiver-check-receipt.json | e246842b54c8f74291212a3e5eaacb8f5c545d3c6c7627923d1a4cba44de81a9 |
| receiver-owned-receipt.json | 5f99fff819740b272e30b4a9ab6c34baa7159cfbd7b865e2d4c52530b37736fb |

Earlier rejected route and failed producer/receiver evidence remain preserved. Red-team review caught stale outer inner-pinning before execution; producer evidence caught retained fixture connection and obsolete injection target; receiver caught a real stale Stop race. Fixes were reviewed at fresh pins before reruns; no assertion was weakened to obtain pass. Detailed pre-test history: `scratch/sqlite-busy-2026-10-12/Senua_Pretest_Review.md`.

## Verdict

Total Critical: 0. Total Major: 1 (existing persistent Stop-entry contention limit). Total Minor: 0. Safety floor intact.

**Verdict:** RELEASE CLEAR

Clearance certifies `b569cc1e556726043671f9b329a2f3cb0cf49ea7..0b0101d1b6e631ec2df81cb31da9a9e00a5433bb`, with the exact six tested source/test files above and committed v0.12.1 metadata. Sully may carry this reconciled report through a report-only follow-up commit; any additional product/test changes invalidate the endpoint mapping. No new live owner or resume is certified here; those still require normal Windows user launch and protected-state verification.
