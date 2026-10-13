# Books Arranger working cleanup — urgent subset, 2026-10-13

Root cause: published jobs retained large normalized PCM WAVs because both service ordering and full staging cleanup depended on successful source retirement. The new StorageCleanup.working_files path independently validates published output ancestry/bytes and exact attempt/name/hash/size receipts, holds native identities before disposition, journals per file and excludes snapshots/recovery/unknown content. It never completes storage_cleanup_jobs or the full Ready/retirement obligation.

Sergei directly answered A Yes (receipt-matched leftover working WAVs, originals/recovery untouched), B Yes to read-only original stream listing and normal retirement only if streams are solely Zone.Identifier. B/native stream guards remain unchanged in this delta. His later instruction requires cleanup after every appropriate action; publication invokes working cleanup before retirement in the full pending delta. Adaptive-format decisions will be proved before generating WAVs, avoiding rejected precision copies. Failed/unverified intermediates remain held rather than blindly deleted.

A's handoff count was incorrect: one SQLite backup-API copy and exact C-only producer-receipt-name inventory show **136 existing WAVs**, not 120, with exactly the approved **119317276892 bytes** across the same eight jobs. This is a count correction, not extra bytes or jobs. No live DB writes, deletion, Z/Y reads, app POST/shutdown/start or original retirement occurred during preparation.

## Urgent operational subset

Files: storage_cleanup.py, cleanup_published_working.py, tests/test_working_cleanup.py, this document. No audio_pipeline/merge_service delta is included in that subset commit. Version unchanged. Runtime/dependency graph is existing Python/native boundary and catalog lock; no UI/control/API schema changes.

Historical caller is deliberately bounded to the eight exact UUIDs, 136 files and 119317276892 bytes. It accepts only normalizedNNNNN.wav producer receipts. Its plan runs against a caller-provided one-time SQLite backup outside live data; native output protection necessarily reads only the eight published destination M4Bs. Unknown attempts/files, snapshots and recovery remain untouched. Plan includes held file identity, hash and size; apply requires the reviewed plan SHA-256, exact current catalog/publication records, identical full native plan, and per-job identity equality before disposition.

Apply holds the app's existing exclusive catalog lock. A Paused app still holds this lock, so approved supported idle shutdown is required first; caller never sends POST, kills/starts a process or bypasses ownership. Jane must verify identity/idle via bounded read-only GET, use normal token-guarded idle shutdown, verify exact PID exit/instance record removal/port release, then authorize this reviewed caller. The normal app must not purge incidental expired recovery during this procedure. Catalog manifests/output records are protected before/after. Original/snapshot/recovery names are never selected.

Commands after independent subset QA GO and review CLEAR (absolute pinned interpreter; no arguments invented):

    python -I -B cleanup_published_working.py plan --data-root <live data> --catalog-copy <one backup copy> --plan <new evidence plan>
    python -I -B cleanup_published_working.py apply --data-root <live data> --catalog-copy <same copy> --plan <same plan> --plan-sha256 <reviewed SHA-256>

The plan/apply commands are operational permission boundaries, not a QA handoff receipt. Abrupt partial disposition retains per-file journal evidence. The same frozen plan resumes by proving the union of remaining native identities and absent names backed by exact durable removal-intent/completion receipts. Unknown absence, native replacements or mismatching provenance still block. No wider sweep or new approval scope is used.

## Private verification contract

Use a committed git-archive immutable copy excluding data/scratch; exact source, runtime and runner hashes must be independently derived. Dedicated test_working_cleanup.py covers pending retirement, snapshot/source preservation, historical normalized-only selection, no full completion, wrong output/bytes, native hardlinks/ADS, absent without intent, terminal path replacement, crash reconciliation, wrong marker, wrong dry-run identity and other-attempt preservation. Sender/receiver execute the same bounded Python Windows Job-owned manual route; qa-handoff applies as separately reviewed nonpackage contract, never n/a or an automated package receipt.

Cross-boundary consumers: working_files -> cleanup_published_working.py, new tests, pending MergeService._after_completed; existing full storage_cleanup_jobs -> source_cleanup status/Ready/recovery_retention/folder obligations remains unchanged. No shared schema/report field changes.
