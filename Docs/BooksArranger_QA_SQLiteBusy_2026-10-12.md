# Books Arranger SQLITE_BUSY candidate QA — 2026-10-12

**Verdict: GO for the final isolated candidate.** Independent final receiver passed **78 unique Python cases in one invocation: 16 BUSY + 52 controller + 10 inventory**. No candidate was applied or launched; live v0.12.0 is outside this pass. This is candidate QA clearance, not a claim of uninterrupted real processing or release/application approval.

## Final verified candidate and regression

Final source digest `493ed60cba9883497a624a46742125dcf9a772c4491862ac9ca34b1093a9c020`, manifest `8c8381b1b687d769f6cc93b1c620d653d1c7d6278bad94420cb2ecf7e63dce52`; same released b569 baseline/source version 0.12.0, target 0.12.1-candidate, dirty=true. Final receiver contract `0a38d7509d82022074ec826834c486b1f29db21957b4fb7b01f6ca8272e07f3d`, outer `96ca9e15495c1e04b4abe8e613d2aac9fd52fd41c8a2c1336c5a10f6e52c1ea6`, inner `9d228c69e1cdd692152740748f80d690ab3b3c03136778d02b3bf4cee488517a`. Independently matched all four current pins before executing the exact fixed no-argument receiver command below, after Senua's explicit latest-route clearance and Ender's one-invocation 78/78 producer pass.

Final outer elapsed **42.1834386s**, inner **42.1212246s**, exit 0; three suites exit 0, all 600000ms owned-deadline requirements retained. Suite times: 6.158s, 29.095s, 0.558s. Pre/post snapshot verification passed; owned children exited and output drained without runtime error or retained-stream truncation. Actual receipts: `receiver-check-receipt.json` SHA256 `e246842b54c8f74291212a3e5eaacb8f5c545d3c6c7627923d1a4cba44de81a9`; `receiver-owned-receipt.json` SHA256 `5f99fff819740b272e30b4a9ab6c34baa7159cfbd7b865e2d4c52530b37736fb`, both in scratch/sqlite-busy-2026-10-12.

Futaba independently extracted fully qualified verbose unittest case IDs from the final receiver outputs, including IDs whose success output spans intervening inherited mock-HTTP ResourceWarnings. **78 distinct IDs**, all three `Ran N tests`/`OK` records and exit 0; the sorted IDs exactly match the complete 78-ID list in `application-packet.json`. Case-list digest `127894b6fbd421f8ece8ad9e9fdab62640341e13f8471a0040e0aae467dcce67`. This manifest/list and retained verbose receiver receipt provide every actual case ID; no assertions, subtests, historical producer passes, or interface checks increase the count. The warnings concern fixture HTTPError cleanup (403/429/500/503); they are retained and are not claimed absent.

Ender fixed the observed stale Stop race with an atomic Stopping update conditioned on durable state still being Running. The new 16th focused case `test_sqlite_busy.BusyTests.test_supported_stale_stop_cannot_overwrite_committed_paused_checkpoint` deterministically supplies a stale run snapshot after Paused is committed. It passed, as did the previously failing `test_automatic_processing.AutoTests.test_waiting_uses_earliest_candidate_and_does_not_revisit_later_source_early`. **Prior Major regression status: VERIFIED FIXED against this exact snapshot, not yet a fix commit.** Previous 67-case NO-GO/source/receipts remain under `failed-receiver-v3`; the historical record below remains intentionally preserved.

Actual manual receipt (matches final producer identity/result receipt):

```text
BOOKS_MANUAL_QA|tool=Books Arranger|target=0.12.1-candidate|source=0.12.0|HEAD=b569cc1e556726043671f9b329a2f3cb0cf49ea7|dirty=true|source_digest=493ed60cba9883497a624a46742125dcf9a772c4491862ac9ca34b1093a9c020|manifest_sha256=8c8381b1b687d769f6cc93b1c620d653d1c7d6278bad94420cb2ecf7e63dce52|python=pass|node=n/a(unchanged frontend; released v0.12.0 baseline)|package=n/a(manual nonpackage contract)
```

Remaining Stop-initiation, native-media/live acceptance, 24-hour retention and verified-original deletion limits below still apply. No new pattern alert. Historical failure disposition: fix implemented by Ender and independently verified; HTTPError fixture cleanup warnings remain recorded for Ender, with no product behavior failure observed in this bounded pass. No further test repetition is warranted absent new source or findings.

## Historical failed receiver — retained evidence

The following refers to the prior snapshot and does not describe the final cleared candidate.

Futaba tested the isolated `scratch/sqlite-busy-2026-10-12/candidate` snapshot based on released `b569cc1e556726043671f9b329a2f3cb0cf49ea7`, source version 0.12.0, target label 0.12.1-candidate, dirty=true. The label is not a released version or fix commit. Source digest: `fbad338b1cfca6c2cb0bacbc607ba422c69f0835e11a3aebd1614e67618f3dc3` (164 source entries). Manifest SHA256: `e77c064c3b55074476eb5e334514340312a566bb7b8aa1cf5b7ebc2b54234150`.

## Execution and identity

Read qa-handoff in full. Books Arranger is a nonpackage/manual tool; used its separately reviewed existing finite owned route amendment, not the package checker or stale 86-case receiver route. Senua explicitly cleared the exact amended receiver route after the producer proof. Producer obtained 77 unique passes across two applicable stages (66 retained plus 11 continuation), not one 77-case passing invocation.

Fixed receiver command, no arguments: `C:/Python314/python.exe` followed by `C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/sqlite-busy-2026-10-12/run_qa_receiver_owned.py`. Receiver contract hash `ff56ddddf072adb6a9dbbbd8ba0e80456614f0e035860787e8b1882a5bc7872d`; outer hash `b2cc287c40bf64d32171aef1ab89391c1a5f4979ffee5394ff72e65f5fa5e454`; inner hash `cd6ecda275d8ca0402d2b1798ad4318a0ef56f03e09148157185ccfbc7d6baae`. Futaba independently re-derived those four pins before execution.

The route retains the 600000ms total deadline, pinned Python/native ownership module/runtimes, suspended child launch into private kill-on-close Windows Job ownership, bounded drains, awaited child exit, and pre/post source verification. Outer elapsed 38.413692 seconds, inner 38.359947 seconds, exit 1. No harness error or retained-stream truncation. The shell output display was truncated; the actual retained receipts are complete.

Historical evidence: the prior receiver receipts/source are preserved under `scratch/sqlite-busy-2026-10-12/failed-receiver-v3`. Current root-level receiver receipts are the final 78-case PASS described above. The previous failed-v1/v2 producer evidence remains preserved.

## Historical failed-pass counts and cases

Unittest verbose terminal case IDs and `Ran N tests` records in the retained receiver receipt are the count source. Counts are distinct fully qualified test IDs, not assertions/subtests or producer reruns. Focused `test_sqlite_busy.BusyTests`: **15/15 PASS**. Controller `test_automatic_processing.AutoTests`: **51/52 PASS**. Total: **67 unique executed, 66 PASS, 1 FAIL**. `test_inventory.py` did not execute because the route stops on failure; do not count its producer coverage as independent receiver QA.

The 15 focused case suffixes are:

- `test_atomic_pause_exhaustion_never_claims_saved_or_resets_candidate`
- `test_cache_retry_never_repeats_request_or_spends_budget_twice`
- `test_cache_stop_does_not_refetch_or_claim_evidence_receipt`
- `test_checkpoint_recovers_real_writer_lock_preserves_four_completed`
- `test_checkpoint_stop_interrupts_wait_without_advancing`
- `test_failed_connection_initialization_is_closed`
- `test_failure_persistence_exhaustion_stays_volatile_and_blocks_start`
- `test_failure_persistence_recovers_once_without_restarting`
- `test_nonbusy_and_message_only_errors_never_retry`
- `test_nonbusy_native_operational_error_never_retry`
- `test_partial_transaction_rolls_back_before_one_successful_replay`
- `test_paused_checkpoint_still_persists_with_stop_set`
- `test_persistent_busy_bounded_and_checkpoint_unchanged`
- `test_restart_keeps_saved_progress_paused_never_starts_worker`
- `test_supported_stop_recovers_busy_atomic_pause_and_restart_remains_paused`

## Historical regression — now closed

**Major — originally OPEN and NO-GO on the historical 67-case pass; current status VERIFIED FIXED/CLOSED for the final pinned candidate.** `test_automatic_processing.AutoTests.test_waiting_uses_earliest_candidate_and_does_not_revisit_later_source_early` failed at the earlier candidate `tests/test_automatic_processing.py:279`: expected `Paused`, observed `Stopping`. Earlier assertions for wakes `[100005,100020]` and two visits per candidate passed. Ender and Jane were notified immediately. Ender's conditional Stopping save prevents a stale Stop snapshot from overwriting committed Paused; the final independent 78-case run passed both this case and the new deterministic stale-Stop regression. The earlier 66 PASS/1 FAIL counts and evidence remain intact; this was verified after a source fix, not erased by repeating the failed snapshot.

## Practical limits and policy checks

The focused cases exercise real private SQLite WAL writer contention, rollback before safe transaction replay, native BUSY-only classification, nonBUSY refusal, bounded exhaustion, interrupted checkpoint retries, cache fetch/budget exactly once, no evidence receipt after cancellation, failure persistence, and atomic candidate-reset/Paused save. Four private completion proofs and saved progress remain unchanged. Supported Stop coverage introduces contention after Stopping is durably saved; it does not establish prompt Stop initiation when the earlier direct `_run_row`/Stopping boundary is already contended. No universal cancellation or uninterrupted-processing guarantee is made.

No real library, originals, media publication/retirement, network requests, approval replay, UI/app/native persistent launch, canonical checkout, Comics/Comix, or Open Library data was operated by this QA pass. Existing 24-hour recovery and verification-before-deletion policies remain required; this narrow fixture pass does not re-certify actual media/native deletion safeguards or live outputs. The unchanged frontend's released v0.12.0 checks are baseline evidence only, not new interface checks.

Pattern alert: none newly established. Historical regression disposition: fixed by Ender and independently verified against the final snapshot in the 78/78 PASS run. Owned finite processes exited; no unique evidence or recovery artifacts were removed. **Current candidate verdict: GO**, with the practical limits above unchanged.
