# Books Arranger storage receipt retry candidate v0.12.3 — 2026-10-12

The current stable v0.12.2 successfully completed «Дельфин в пустыне», but a separate postpublication temporary-storage receipt encountered `database is locked`. Ready still shows four because successful storage cleanup is a server eligibility requirement; existing candidate auto-refresh already polls the server. This candidate fixes the receipt boundary without changing Ready/UI semantics or source/recovery policy. The historical failing SQL/native code/lock owner was not recorded and is not asserted.

## Candidate and safety scope

The frozen isolated graph is `scratch/storage-busy-2026-10-12/candidate`, manifest SHA256 `fe719c9e60ec9b1c902bfa3661ac226874963a5a2b3eac4159530340fd2e53e3`, source digest `4727d99e7d81cd4ac90471c2977d8feb98b1feaa988375e933ad5a2065e14edd`. Baseline source v0.12.2, document-child HEAD `315aec2699d6d57dda5944a2e93fdf3e2a53172b`, released baseline `0a238ba370edadd2adf809fc22efaae07977be8e`.

Only storage_cleanup.py, new tests/test_storage_busy.py and one legacy private fake initialization in tests/test_recovery_retention.py are proposed for source publication. VERSION/CHANGELOG and all Git/release operations belong to Sully. The release-packet.json binds exact candidate/baseline physical and normalized hashes. No live app code, library records, controls or cleanup actions were changed.

Short database-only receipt callbacks reuse the existing bounded native SQLITE_BUSY transaction helper. Full-row CAS preserves exact output/file provenance and monotonic transitions. Completed job receipts never regress; removing crash receipts are retained while normal output/source revalidation reconciles existing intents. Unknown pre-output hash may upgrade only after fresh verified output; a known hash cannot downgrade or change. Native disposal, publication and whole cleanup runs are never replayed by retry callbacks.

An additive append-only storage_cleanup_errors table records typed SQLite codes/names, bounded application frames and logical pre/post disposition phase. Original error remains in bounded internal evidence even when diagnostic/state persistence separately fails; the primary exception is re-raised. Existing schema rows/API/status/Ready/retention consumers remain compatible. Initialization/folder SQL, non-BUSY/LOCKED/unknown errors and broad automatic cleanup recovery are outside this patch.

## Actual verification and handoff

Producer verification passed 45 unique Python test cases across two stages: 44 initial passes plus one corrected fixture continuation. The first stage's sole error was a private BrowserServer.__new__ fake missing the released recovery_operations field; only that initialization was corrected, the original failure preserved, and only its failed ID rerun. The product candidate was unchanged by this correction. Independent receiver passed all 45 unique cases in one full owned invocation. These are reused same cases, not 90 unique tests.

The graph includes 15 targeted cases, 18 existing storage cases and 12 recovery-retention cases. Real SQLite contention proves receipt retry and exactly one native owned-file disposition; exhaustion before/after disposition, full provenance CAS, terminal/stale/crash-removing behavior, typed error refusal, original/secondary diagnostic failure and additive catalog/24-hour recovery compatibility are covered. Both finite routes retain exact held inputs, bounded drains, suspended private Job admission, exclusive no-repeat receipts and proven closure under one 600000ms deadline. Formal entry uses the separately reviewed nonpackage manual contract; the identical actual Ender/Futaba identity line follows.

```text
BOOKS_MANUAL_QA|tool=Books Arranger|target=0.12.3-candidate|source=0.12.2|HEAD=315aec2699d6d57dda5944a2e93fdf3e2a53172b|dirty=true|source_digest=4727d99e7d81cd4ac90471c2977d8feb98b1feaa988375e933ad5a2065e14edd|manifest_sha256=fe719c9e60ec9b1c902bfa3661ac226874963a5a2b3eac4159530340fd2e53e3|python=pass|node=n/a(unchanged interface)|package=n/a(reviewed nonpackage manual contract)
```

Proofs and exact hashes are in release-packet.json and ender-producer-summary.json, with all original producer/continuation/receiver receipts retained. Senua's release verdict and Futaba's QA report are separate owner-authored artifacts. No release or latest-stable application is claimed by this report. Any later real cleanup retry requires the verified new stable owner and exact completed output/source/recovery/receipt guards; no live retry has occurred.

## Known advisory limits

StorageCleanup is a MergeService-lifetime instance; its run/callback paths lack a dedicated all-path mutex. Instance-shared phase/disposition labels can mix under a concurrent run, and exact per-path receipt snapshots remain cached for the instance lifetime. Full-row SQL CAS and native gates refuse provenance drift; diagnostic labels and memory lifetime remain advisory review items. No unreviewed concurrency framework or cache change was added.

The original recovery copy remains protected by the approved 24-hour policy. The four earlier completed books and verified fifth output/recovery evidence are preserved. Comics/Comix, Open Library dumps, provider prototypes and unrelated studio edits remain outside scope.
