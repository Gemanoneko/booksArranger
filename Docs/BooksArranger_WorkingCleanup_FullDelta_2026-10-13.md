# Books Arranger v0.15.0 working cleanup full delta

## Authorized operation completed

Sergei approved A and B directly, then explicitly required cleanup after appropriate actions. A used only the same eight receipt-matched published jobs. The handoff miscounted 120 WAVs; actual exact inventory was136 with the same119317276892 bytes, accepted as a count correction. Independently reviewed urgentcode6bd10c9, sender15/15, matching receiver15/15 and11 independent QA probes passed before the operation. No B stream guard change or source retirement occurred.

Supported verified idle shutdown of v0.14.0 completed;136 files/119317276892 logical bytes were removed. Measured C free bytes:36622192640 before,155916890112 after; actual free-space gain119294697472. Native private ownership supervisor exited0 in271.246s, apply250.292s under the550s child/600s overall bound.148 source snapshot/recovery/ownership files remained held read-only throughout; unchanged protected SQLite projection covers queued90, paused research, completed publications, source cleanup/retirement and24-hour recovery. The app remains stopped. No restart, Start, recovery purge, wrong-original retirement or other library action was performed.

Evidence: scratch/cleanup-delta-2026-10-13. Immutable urgent224-file source digest67570c0e427110030cd47aff814153c2cbdc33b7a5f9e012922037fb8edc7d49; manual contextcbed742afe64ca917cc66446c87a6285f4fb2b7e316f20431fb4282e8fec2a86; historical plan SHAa6305f64b5e2a114f79021a5f7793686d00af4fe600e0a11a6a312a1776214ac. Operation/source/native receipts are retained. The measured free-space difference is distinct from selected logical bytes.

## Full code behavior

- At verified durable publication, remove only the exact published attempt's producer-receipted disposable working files BEFORE attempting original retirement. Preserve source snapshots, ownership, recovery and unknown contents.
- Completed jobs with retirement attention also retry working cleanup on explicit resume. Construction/server startup stay inactive. A read-only working_pending hint recognizes remaining/absent-unproved/recreated paths; it never authorizes deletion or Ready. Already disposed known names avoid repeated large media hashes.
- Working-only success never completes storage_cleanup_jobs, full Ready, folder purge or retirement obligations. Error diagnostics remain durable; completed output is not reset. Full native source/output/correspondence/recovery protections remain unchanged.
- Choose the smallest exact PCM WAV representation by complete streamed canonical double hash/count comparison, testing16-bit,24-bit,32-bit integer and32-bit float; otherwise retain64-bit float. Samples, signed zero, subnormal/low-bit precision, channels and sample counts decide, not a source-format label or prefix/duration. Candidate comparisons produce no WAVs. Exactly one selected WAV is emitted and reverified as canonical full decoded PCM before consumer leases/hash receipts.
- Before large source copies, fully decode held/hash-verified sources for duration/profile admission. Reserve snapshots, worst-case double PCM, both output versions, possible same-disk publication copy and margin. Check destination space at its nearest existing protected parent. Recheck remaining PCM/output obligations before each WAV and output creation.
- ENOSPC is a durable retryable prepublication hold, parks the remaining queue after one attempt and stops automatic processing at its saved checkpoint. It does not create90 successive failures/working directories or auto-resume after restart. Existing source/revision/backoff checks still govern explicit/automatic supported retries.

## Action to cleanup map

Verified publication -> producer-receipted working disposal, independent of retirement. Explicit resume -> retry published pending working receipts. Source retirement completion -> existing full staging/snapshot cleanup, folder obligations and24-hour recovery flow. Precision comparison -> bounded streams, no rejected WAV to accumulate. Clean pre/midstage disk hold -> no further queue attempts/large copies. Unknown/unfinished failed producer files remain preserved; this delta does not invent receipts or broaden to a background sweep.

## Source pin and finite verification graph

Candidate remains unaccepted until committed immutable sender, independent QA and red-team review. Dedicated files: test_working_cleanup.py16 cases; test_working_precision.py16 cases; test_working_lifecycle.py4 real private cases. Focused regressions: test_storage_cleanup.py, test_automatic_media_policy.py, test_automatic_media.py, test_standing_admission.py. All finite routes run under existing native private process ownership with a single600s envelope; if exceeded, stop/report without duplicate. Counts are fully qualified unittest IDs, not assertions/subcases. Prior R3 grouping/spelling evidence is reused only for unchanged matching code.

## Shared boundaries

working_pending/working_files: storage_cleanup -> merge_service explicit completion/resume, cleanup_published_working historicalcaller and native fixtures. on_space_hold: audio_jobs -> MergeService -> existing AutomaticProcessing.stop(force=True); no new control/UI schema. Precision receipts are internal normalizer consumer facts/hash/PCM/codec; durable staging_artifacts attempt/name/hash/size format and native PCM f64 evidence remain compatible. Existing storage_cleanup_jobs remains consumed by Ready, source cleanup status, recovery retention and source-folder obligations without an independent-working completion bypass.

## Release apply prepared

Use Sully's existing documented stopped-app Git fast-forward path; include the tracked.gitattributes. The obsolete sully_apply_release.py copy/normalization route is excluded. Current main/worktree/archive replacement_eye_plan.json all have required raw SHAdb493dbbfa691e1fe6b875a3edacb8ebd318d487c80c9fa4de66639afa35d20f; tracked.gitattributes pins that file to LF. Before/after fast-forward, verify that raw protected plan hash, expected loaded VERSION/source paths, committed tracked file set, unchanged protected SQLite projection and stopped owner/port/catalog condition. Any unexpected raw protected-input or content mismatch blocks launch; do not silently normalize or restore a guessed plan. Harmless existing Python/web CRLF checkout differences must be explicitly reported as in the committed v0.14.0 apply record, never treated as byte-exact matching. No app startup/automatic Start occurs here; Sergei launches the normal entry after final independent clearance/release.
