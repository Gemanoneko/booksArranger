# Books Arranger storage BUSY QA — v0.12.3 candidate — 2026-10-12

**Verdict: GO for the exact isolated candidate.** Independent receiver passed **45 unique Python cases in one invocation: 15 targeted + 18 storage cleanup + 12 recovery retention**. No live cleanup, app control, Ready-count reconciliation, release or actual deletion was performed by QA. The real fifth-book temporary cleanup remains unresolved until separately reviewed stable application and guarded actual cleanup.

## Identity, handoff and execution

Source HEAD `315aec2699d6d57dda5944a2e93fdf3e2a53172b`, released code baseline `0a238ba370edadd2adf809fc22efaae07977be8e`, source version 0.12.2, target 0.12.3-candidate, dirty=true. Snapshot `scratch/storage-busy-2026-10-12/candidate`; source digest `4727d99e7d81cd4ac90471c2977d8feb98b1feaa988375e933ad5a2065e14edd`; manifest `fe719c9e60ec9b1c902bfa3661ac226874963a5a2b3eac4159530340fd2e53e3`. Production storage module digest remains `c79a3fb2e875ff765509739ff0761742449f410839237dbd2690d982eb5ef4ed` across the producer fixture correction; this is snapshot verification, not a fix commit.

Applied qa-handoff's separately reviewed nonpackage manual contract, not a package checker or stale broad suite. Senua explicitly cleared the exact receiver route contingent on actual producer continuation pass; Futaba read that pass and independently matched receiver outer/inner/manifest before executing once. Outer `9f64aca2025dccc9fdf95aabfadbd69dbf4394fd095403304a078fcd8650de78`; inner `0137413285fb6b8b339132244698cc082abd91aab56a03c08430b66e7b0c0046`. Fixed command: `C:/Python314/python.exe -I -B` followed by `C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/storage-busy-2026-10-12/run_qa_receiver_owned.py`, no arguments.

Producer actual history: **44 PASS/1 ERROR**, then fixture-only correction to fake BrowserServer's missing released `recovery_operations=0`, focused failed-ID continuation **1 PASS**. Applicable producer unique passes: **45 across two stages**, not one passing full producer invocation. Failure receipts remain preserved. Imported-TestCase discovery was corrected before execution; receiver counts do not include duplicate imported RetentionTests runs.

Receiver outer elapsed **24.7497679s**, inner **24.7150678s**, hard deadline **600000ms**, exit 0. Suites: 15/5.150s, 18/8.192s, 12/8.914s; all exit 0. No runtime errors, warnings or retained-stream truncation. Held source/runtime pins, `.pyc` refusal, suspended children into owned kill-on-close Jobs, bounded drains, exclusive owned receipt paths, pre/post input verification and awaited child closure passed. No owned persistent process remains.

Evidence in the same scratch area: `receiver-check-receipt.json` SHA256 `cccf7e8c7279c9e1b9ba263ae5b4173b1b3058e25b1fc628091ff2e78d31ddb2`; `receiver-owned-receipt.json` SHA256 `f402a921b3fdc55b5bce3c4ed04f9a7bfed2a869eaeb5cbb76c3091fbc52371d`. Futaba independently extracted fully qualified verbose IDs ending `... ok`, deduplicated, and checked all three `Ran N tests`/`OK` records: **45 distinct executed and passed**, no assertion/subtest or historical interface/core count added.

Actual receipt identity/result matches producer continuation exactly:

```text
BOOKS_MANUAL_QA|tool=Books Arranger|target=0.12.3-candidate|source=0.12.2|HEAD=315aec2699d6d57dda5944a2e93fdf3e2a53172b|dirty=true|source_digest=4727d99e7d81cd4ac90471c2977d8feb98b1feaa988375e933ad5a2065e14edd|manifest_sha256=fe719c9e60ec9b1c902bfa3661ac226874963a5a2b3eac4159530340fd2e53e3|python=pass|node=n/a(unchanged interface)|package=n/a(reviewed nonpackage manual contract)
```

## Behavioral evidence and limits

Private real writer-lock contention recovers short DB-only receipt writes with actual repeated connection attempts and exactly one native disposition. Exhaustion before intent preserves the file. BUSY after disposition preserves removal intent and does not replay native deletion. Full receipt provenance and allowed transitions refuse changed or regressive receipts; same-state success still revalidates provenance. Completed job state cannot regress to stale attention, removing crash resume revalidates native intents without regressing job state. Native SQLITE_LOCKED and untyped message-only database-is-locked are not retried. Original boundary failure remains the raised exception when diagnostic persistence also fails, with secondary errors retained. Existing catalogs gain the diagnostic table additively without changing queue status.

Completed output bytes remain protected; failure preserves source recovery and the exact 86400-second retention deadline. Existing fixtures exercise real native file removal/collision/replacement/hardlink/unknown-content boundaries, interrupted intent reconciliation, age/restart/manual retention and shutdown admission. These are actual private SQLite/native-path tests, not live-library cleanup acceptance. The historical real cleanup lock has no known native code/exact statement/lock owner; candidate coverage does not retroactively prove its specific cause. File operations/whole cleanup runs are not replayed inside SQLite retry.

No UI code/source policy/24-hour policy changed in this pass. Ready count 5 is not claimed until an independently reviewed stable offline operation safely reconciles the real fifth job's cleanup and refreshed Ready state. QA issued no Start/Stop, launch, helper, live cleanup, Git or release operations and touched no Comics/Comix or Open Library data. Unique failure/source/receipt evidence remains preserved. No open candidate QA defect or new pattern alert; real cleanup remains an existing Major issue pending actual verification.

## Actual fully qualified case IDs

```text
test_storage_busy.StorageBusyTests.test_additive_diagnostic_catalog_compatibility
test_storage_busy.StorageBusyTests.test_busy_after_dispose_preserves_intent_and_never_replays_disposal
test_storage_busy.StorageBusyTests.test_busy_exhaustion_before_intent_retains_file
test_storage_busy.StorageBusyTests.test_exact_same_file_state_revalidates_database_provenance
test_storage_busy.StorageBusyTests.test_failure_preserves_completed_recovery_and_exact_24_hour_expiry
test_storage_busy.StorageBusyTests.test_full_file_provenance_cas_refuses_changed_receipt
test_storage_busy.StorageBusyTests.test_job_completed_not_overwritten_by_stale_attention
test_storage_busy.StorageBusyTests.test_native_locked_is_not_retried
test_storage_busy.StorageBusyTests.test_real_busy_release_commits_one_receipt_and_disposes_once
test_storage_busy.StorageBusyTests.test_removing_crash_resume_revalidates_without_regression
test_storage_busy.StorageBusyTests.test_secondary_diagnostic_failures_do_not_mask_original
test_storage_busy.StorageBusyTests.test_terminal_file_receipt_never_regresses
test_storage_busy.StorageBusyTests.test_unknown_message_busy_is_not_retried
test_storage_busy.StorageBusyTests.test_unknown_output_provenance_cannot_overwrite_job
test_storage_busy.StorageBusyTests.test_unproven_preoutput_failure_upgrades_only_after_verified_output
test_storage_cleanup.RetentionTests.test_changed_retained_source_preserves_staging
test_storage_cleanup.RetentionTests.test_completed_retirement_discards_exact_recovery_and_correct_status
test_storage_cleanup.RetentionTests.test_crash_after_disposition_reconciles_only_durable_intent
test_storage_cleanup.RetentionTests.test_crash_before_disposition_preserves_changed_replacement
test_storage_cleanup.RetentionTests.test_enrolled_policy_without_retirement_is_preserved
test_storage_cleanup.RetentionTests.test_hardlinked_copy_is_not_discarded
test_storage_cleanup.RetentionTests.test_invalid_output_preserves_copies
test_storage_cleanup.RetentionTests.test_known_name_substitutions_are_preserved
test_storage_cleanup.RetentionTests.test_metadata_substitution_after_source_retirement_keeps_recovery
test_storage_cleanup.RetentionTests.test_nested_git_is_not_touched
test_storage_cleanup.RetentionTests.test_paused_source_removal_preserves_recovery_and_staging
test_storage_cleanup.RetentionTests.test_pending_or_failed_audio_cannot_discard
test_storage_cleanup.RetentionTests.test_preflight_failure_keeps_complete_recovery_restorable
test_storage_cleanup.RetentionTests.test_success_discards_staging_preserves_originals_and_output
test_storage_cleanup.RetentionTests.test_unknown_recovery_content_blocks_before_any_disposition
test_storage_cleanup.RetentionTests.test_unknown_staging_content_blocks_before_any_disposition
test_storage_cleanup.RetentionTests.test_unregistered_named_output_is_never_adopted
test_storage_cleanup.RetentionTests.test_verified_only_receipt_cannot_turn_unknown_absence_into_success
test_recovery_retention.AdmissionTests.test_idle_startup_worker_and_shutdown_and_scan_admission
test_recovery_retention.AdmissionTests.test_manual_duplicate_stale_and_busy_no_action
test_recovery_retention.RecoveryTests.test_24h_boundary_restart_and_stage_independence
test_recovery_retention.RecoveryTests.test_changed_output_and_incomplete_retirement_preserve
test_recovery_retention.RecoveryTests.test_cooperative_shutdown_resumes_partial_exact_purge
test_recovery_retention.RecoveryTests.test_crash_reconciles_exact_intent_and_unknown_absence_does_not
test_recovery_retention.RecoveryTests.test_incomplete_source_retirement_blocks_all_copies
test_recovery_retention.RecoveryTests.test_manual_scope_and_foreign_identity_are_preserved
test_recovery_retention.RecoveryTests.test_manual_success_before_expiry
test_recovery_retention.RecoveryTests.test_mutable_completion_status_cannot_reset_deadline
test_recovery_retention.RecoveryTests.test_unknown_absence_and_uncertain_legacy_age_preserve
test_recovery_retention.RecoveryTests.test_unknown_content_and_changed_output_block_before_deletion
```
