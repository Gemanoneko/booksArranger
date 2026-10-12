# Code Review — Books Arranger v0.12.3

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-12
Tool: Books Arranger
Release: v0.12.3
Commit range: 315aec2699d6d57dda5944a2e93fdf3e2a53172b..93c5c385e8962ae2c12b9469a0e8b37154096f24
Released product baseline: v0.12.2, 0a238ba370edadd2adf809fc22efaae07977be8e
Files changed: 8 files, +462/-11; 3 code/test files, VERSION, CHANGELOG and 3 authorized reports
Stand-down dimensions: none; UI/browser/media subprocess implementations unchanged
```

Committed endpoint independently reconciled: tree `8da389e2df1505e7d362f1fb9782ca96865917b5`, exactly the eight declared paths. All three committed Git blobs match the reviewed candidate after CRLF normalization, with SHA256 respectively `205e246d8da71d4c22a3404e1b08365068a6ce88093718f29c7e50ea97f81ea4`, `0d01d0ecf2b139ed3976bb5f3b3b1fc6e7659c5a97b216b3695e1562c93b5015`, and `ad041ffd3de9acd864d449432e943ae42e7e4364c2148321fed6739bb034d579`. VERSION is 0.12.3 and CHANGELOG accurately scopes the patch. The ensuing report-only child may carry this reconciliation without changing certified product/test bytes.

## Summary

Storage cleanup retries bounded, typed native SQLITE_BUSY failures only inside short database transactions. Receipt writes now compare full rows and preserve terminal states and output/file provenance. Native file disposition stays outside every retry callback. An additive error table records bounded original diagnostics; secondary persistence failures are retained separately without replacing the original exception. Reviewed changes preserve existing verified audiobook publication, native ancestry/file guards, source-retirement verification and the 24-hour recovery policy. The old live `database is locked` report has no retained native error code, exact statement, stack or lock-owner identity, so this review does not assign an unsupported historical cause.

## Candidate identity and evidence

Final manifest: `fe719c9e60ec9b1c902bfa3661ac226874963a5a2b3eac4159530340fd2e53e3`.

Source graph: `4727d99e7d81cd4ac90471c2977d8feb98b1feaa988375e933ad5a2065e14edd`.

| Candidate path | Physical SHA256 |
|---|---|
| storage_cleanup.py | c79a3fb2e875ff765509739ff0761742449f410839237dbd2690d982eb5ef4ed |
| tests/test_storage_busy.py | 374e077981be500cf5544ca839683cdcd79d5ed7f391154a849305bc2478e138 |
| tests/test_recovery_retention.py | 9d89afaa9da39d2161234df7d81e330266708e7b3af2e59f00f8d8dccd6cf208 |

Producer: 45 distinct passing cases across two stages, 44 retained passes plus one corrected admission fixture continuation. The first invocation had one AttributeError from a fake BrowserServer missing released-required `recovery_operations`; it was not an all-pass invocation. Only that initialization changed, with all assertions preserved. Product bytes remained unchanged.

Independent receiver: 45 distinct cases passed in one invocation: 15 contention/CAS/diagnostic cases, 18 existing storage cleanup cases, 12 recovery-retention/admission cases. Independently read receipts and extracted 45 unique verbose case IDs. Outer 24.749767900008 seconds, inner 24.715067800018 seconds; all three suite exits and outer exit 0, no errors or stream truncation. Focused continuation outer 1.49494709999999 seconds, inner 1.46024680000846 seconds, exit 0.

| Evidence | SHA256 |
|---|---|
| producer-check-receipt.json | 245f88b0e10e9f0b3119aa2bc2a988ba077fc48d00da0b034a2fb0ab516c8bd8 |
| producer-owned-receipt.json | 31016d9327c6783eef88c7f3d53180028896660ce6c4038b45dbb8cdc8e81b65 |
| continuation-check-receipt.json | 822733bfcfdc7cde38c9f1c8381c5009f0f229a4e239d6dae8da86f3662ca4de |
| continuation-owned-receipt.json | 76cf0170bd85db4b03b74da70b06fd7044c87dcc8af9df5a0d763d5cfeff540f |
| receiver-check-receipt.json | cccf7e8c7279c9e1b9ba263ae5b4173b1b3058e25b1fc628091ff2e78d31ddb2 |
| receiver-owned-receipt.json | f402a921b3fdc55b5bce3c4ed04f9a7bfed2a869eaeb5cbb76c3091fbc52371d |

Evidence resides under `scratch/storage-busy-2026-10-12`. Private suites use synthetic media and native ordinary files; they certify neither live cleanup completion nor actual media playback. No live app/catalog/library actions were performed by this review.

## Rubric

### 1. Security

Pass — SQL identifiers come from internal fixed receipt schemas; data remain parameterized. No new shell, network, credential or media process routes. Existing native file/ancestry boundaries precede disposition.

### 2. Correctness & Logic

Pass — database callbacks freeze intended values and enforce full-row provenance, allowed transitions and idempotent same-target acceptance. Only previously empty failed output provenance may upgrade after normal freshly verified output; known hashes cannot change or disappear.

### 3. Crash / Stability Safety

Pass — existing helper uses bounded BUSY-only retries with fresh transactions, rollback and closure. Native LOCKED and message-only unknown errors fail closed. Tests cover real writer release, exhausted receipt writes before/after disposition, durable intent reconciliation and original-error preservation when secondary writes fail. Reads and schema initialization can still fail; this is not universal SQLite recovery or uninterrupted-processing certification.

### 4. Performance

Concerns — [Minor] `storage_cleanup.py:27`: `_receipts` retains per-path snapshots for the MergeService instance lifetime. Prune safely completed snapshots in a later cycle; no measured current bottleneck is claimed.

### 5. State & Data Safety

Pass — native `dispose()` occurs exactly once outside database retries; intent commits first. Completion and terminal file receipts cannot regress. Full-row CAS rejects changed size, native facts, job/output association and same-state drift. Existing completed output/original preservation and 86400-second recovery snapshots are asserted. The new append-only diagnostic table leaves old tables/consumer fields intact, with private existing-catalog compatibility proof.

### 6. Input Handling

Pass — retry classification requires native SQLite codes, not text matching. Fixed receipt identity/provenance rejects unexpected changes; existing source/publication/native validation remains authoritative.

### 7. Maintainability

Concerns — [Minor] `storage_cleanup.py:29`: `_phase`/`_disposition` are shared instance fields and may mislabel concurrent failures. Entry admissions do not prove all-path serialization; make diagnostic context per run in a later cycle. CAS/native guards remain authoritative rather than these labels.

### 8. Doc/Code Drift

Pass — frozen design and reports distinguish bounded receipt-write recovery from filesystem replay, unknown historical lock cause, and private fixture coverage. No UI/filter/provider changes are included; existing completed-filter behavior continues to depend on durable cleanup completion.

### 9. Build & Release Hygiene

Pass — reviewed finite routes hold manifest/source/runtime pins, refuse candidate cached bytecode, install bounded drains before suspended Job admission, require descendant/drain closure and use exclusive separate receipts. Total deadline 600000 ms. Final receiver outer SHA `9f64aca2025dccc9fdf95aabfadbd69dbf4394fd095403304a078fcd8650de78`, inner SHA `0137413285fb6b8b339132244698cc082abd91aab56a03c08430b66e7b0c0046`. Independently verified final committed range, allowed paths, normalized code/test pins, VERSION and CHANGELOG. Git/release operations remain Sully's responsibility.

## Verdict

- Total Critical: 0
- Total Major: 0
- Total Minor: 2

**Verdict:** RELEASE CLEAR

Safety floor intact for the exact candidate. Clearance does not authorize live cleanup replay, remove existing approval/source checks, promise uninterrupted processing, or certify unrelated browser/helper/UI changes.
