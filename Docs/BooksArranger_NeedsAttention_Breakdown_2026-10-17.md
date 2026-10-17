# Books Arranger - Output needs attention breakdown (2026-10-17)

Method: copied inventory.sqlite3 + -wal + -shm into scratchpad/shared/attention/ and queried the copy (data folder untouched). The UI state comes from review_backend.page(): for each candidate the latest audio_jobs row (ORDER BY created) maps state "needs attention" to "Output needs attention". Reasons are audio_jobs.reason with numbers/paths stripped. Cleanup state from source_cleanup, source_folder_cleanup_jobs, storage_cleanup_jobs, recovery_retention.

audio_jobs by state: completed 78, needs attention 125 (all with output NULL), pending 276, running 1. 125 candidates = 125 jobs (one job each).

All 125 have output IS NULL and no source_cleanup row, so originals are untouched (no cleanup ever started; no publication).

| # | Normalized reason | Stage | Example titles | Cause class |
|---|---|---|---|---|
| 51 | Remux changed the decoder configuration or relative audio packet timing (raw: Remux changed the decoder configuration or relative audio packet timing) | checking | Алкоголь, Альтернативная история, Альфред Хичкок представляет | Needs a code change / investigation (verifier may be too strict or remux path lossy for these Russian-title books) |
| 35 | M4B leading gaps or edit presentation require a verified preservation plan (raw: M4B leading gaps or edit presentation require a verified preservation plan) | checking | The Talon of Horus, Black Legion, False Gods | Needs a code change (preservation plan for edit lists/leading gaps not implemented); until then a safe refusal |
| 24 | M4B preservation requires review: Unsupported/ambiguous brand (raw: M4B preservation requires review: Unsupported/ambiguous brand) | checking sources | Город теней, Закон фронтира, Симбионты | Safe permanent refusal today; code change only if brand support is wanted; else human decision per file |
| 6 | M4B preservation requires review: Unsupported structural box (raw: M4B preservation requires review: Unsupported structural box) | checking sources | Гурман, Выбраковка, Mass Effect: Revelation | Safe permanent refusal; code change only if those boxes should be supported |
| 5 | Preservation changed decoder, packets or presentation (raw: Preservation changed decoder, packets or presentation) | checking | Сборник рассказов, Культ, Мухи | Needs a code change / investigation (same family as Remux changed...) |
| 1 | database is locked (raw: database is locked) | checking sources | Horus Rising | Transient / retryable now (SQLite OperationalError) |
| 1 | M4B presentation bounds cannot be verified (raw: M4B presentation bounds cannot be verified) | checking | Bird Box | Safe refusal; possible code change (verifier cannot prove presentation bounds) |
| 1 | [Errno N] Insufficient working space; need N bytes before snapshotting; originals retained (raw: [Errno 28] Insufficient working space; need 62699883954 bytes before snapshotting; originals retained) | checking sources | The Lost Symbol | Transient / retryable (retryable=true) - needs free working space (human) |
| 1 | M4B preservation requires review: Top-level extent invalid (raw: M4B preservation requires review: Top-level extent invalid) | checking sources | Призраки белых ночей | Safe permanent refusal (file looks malformed); human decision: replace source |

## Cleanup held / needs attention (separate table)

| Table | State | Reason | Count |
|---|---|---|---|
| source_cleanup | needs_attention | Download marker native identity differs | 2 |
| source_folder_cleanup_jobs | needs_attention | Source-folder ancestor is missing without verified removal intent | 1 |
| source_folder_cleanup_jobs | unsupported | Empty source folder retained: NTFS supports named data streams; arriving directory stream data cannot be protected atomically | 23 |

source_cleanup needs_attention rows belong to jobs: [["19c56029", "completed"], ["03e6fbfa", "completed"]] - these are COMPLETED audiobooks (originals cleanup), not among the 125.

Held candidates (automatic Held) are a separate status and not counted here.