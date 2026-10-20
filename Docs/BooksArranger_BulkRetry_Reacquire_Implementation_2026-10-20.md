# Bulk Retry and Need to reacquire — frozen implementation candidate

This is SOURCE-only review input, not QA/release/activation clearance. No live catalog/library/API control, queue replay, source deletion or provider request was performed. The actual v0.19 trace at 17:24 UTC found 69 durable queued readmission requests and zero child jobs; it did not establish their original swallowed exception. See RetryAll69_Diagnosis and its 2fdd67a9… receipt.

## Bulk behavior and control boundary

Retry All and selected Retry/Repair submit one correlated server run. Accepted requests are counted separately from actual child jobs. Pending requests leave Can retry, appear under Retry checks, and stale requests refuse duplicate admission. Each target's current state is joined in one short catalog read as waiting/checking/queued/running/completed/stopped. The latest all/selected receipt replaces older banners. Routine counts sit outside the live announcement region; meaningful phase/failure/unavailable changes stay in the existing live status. Prior startup errors cease to describe current blockage once actual checking/child activity appears. Explicit Start is usable when saved requests exist and real queue=0. The legacy run.queued field remains an accepted-request compatibility alias; new UI uses accepted and progress. has_unfinished includes pending requests but has no current production caller and is NOT claimed as the historical cause.

Start and worker failures retain real reasons rather than disappearing. Bulk submission receipts are additive retry_bulk_runs data, not admission authority; exact existing request/manifest/source/review/native gates still decide child creation. A later successful receipt save clears obsolete persistence errors. Selected HTTP requests require exact fields, UUIDs, supported kind, revision and unique job IDs; each item is rechecked before enrollment.

Pause follows the independently reviewed completion semantics (v2 design9cea1449… / reviewc4818da1…): generation invalidation precedes both existing queue-stop lock boundaries; older admission already holding a queue lock may finish before Pause returns, but cannot undo completed Pause. New Start during incomplete Pause is explicitly busy. Merge no longer clears the audio stop event before long pruning; only guarded queue admission can clear it. Manual generation is captured before operation_lock; async and bulk capture at scheduling. Old pending-owner/checker conflicts return retryable busy/stale, not false started. Closing is permanent before joins, and draining invalidates old generations. The cleanup-to-audio callback is stored per individual worker with the same captured generation. It acquires no Merge lock under a queue lock.

Two existing independent cleanup actions retain optional default calls and MUST remain visible in review: start_historical_cleanup is an explicit finite follow_audio=False action; _finish_held_cleanups is an automatic metadata-held follow_audio=False action. Neither is a bulk/Start handoff. Their own admission intent/Pause interaction is not claimed proven by this patch. No scheduler or physical-cleanup authority was broadened.

## Reacquire boundary and explicit producer limitation

Only a fixed trusted in-process typed source-damage assessment can enroll a current marker after exact closed-attempt/source/full-SHA/current-job CAS checks. English decoder errors, arbitrary JSON/scratch proofs, callback invocation alone and missing/uncertain closure never enroll a marker. Admission barriers cover Retry/Repair/start-over/create/bulk/automatic/before-attempt. Marked source reconciliation requires a complete accessible error-free original-source scan, exact frozen members, fresh native/full-SHA checks and a final absent-member recheck. Offline/partial/error scans, same old bytes at a new native ID, changed marker/review/intent/dependency/publication or overlapping ownership hold. Shared anthology parents are never book ownership.

All old members must be absent or proved displaced by different content before the active old incarnation is archived; history/dependencies/jobs remain. Same-path replacement inventory is preserved/refreshed, stat-identical changed content cannot reuse old SHA/approval, and the newly discovered incarnation gets fresh ID/research/review. No physical file is deleted by reconciliation. Scanner/source-status contention changes are separately owned and reviewed.

IMPORTANT: the current bounded Audio fix has NO supported positive serious-damage producer. Partial PCM plus FFmpeg nonzero was rejected as insufficient and removed. The typed bridge/category is therefore dormant/fail-closed until independently proved source-specific damage support exists; no live reacquire marker was seeded. Iron Inferno was proved to have a harmless 128-byte ID3 trailer with zero audio loss and is NOT reacquire. Its separate safe staged repair preserves originals and is not a general damage classifier.

## Checks and graph

ACTUAL: 23 assertions in the new real-app DOM harness executed in-process, no child/native/RNG; full app.js syntax passed. They cover one selected server request/no duplicate, exact selection fields, accepted versus waiting/real queue, explicit Start for request-only work, stale-row exclusion, newer shared result, real blocked reason, missing-progress honesty, recovery from prior blockage, same-phase numeric updates outside aria-live, network uncertainty/no resubmit. Earlier intermediate failures were test-harness/context mistakes and a remaining live-status call; corrected before this receipt. No formal QA gate claimed.

UNRUN: 19 reacquire Python cases; 10 bulk receipt Python cases; 16 deterministic real-start-method/fake-worker Python race cases; two added HTTP cases inside the existing attention suite; updated existing selected/attention frontend suites; separate 17 DB-contention cases and revised 12 Audio tests. There is no admitted Books Python test route here. Normal real-media diagnostics did not authorize unit-test wrappers. No skipped or unreachable test was reported passed.

The declaration-only check graph includes test_reacquire_sources.py, test_mp3_tag_repair.py, test_bulk_retry_receipts.py, test_retry_start_fence.py and test_catalog_contention.py. Frontend files are discovered by the existing test_*.js rule. No harness/protocol/admission execution change. All old QA preparation packets whose source hashes predate these changes are stale.

## Parallel preservation and exact source ledger

Scanner SHA ebdcec3cd151cf43720dbbda114ce6fd2b2544d946b080db5e97d226a1f564bf unchanged from Sources' frozen candidate. Merge progress_books region7491 bytes remains e61df445787ac21e9886ca2e2a8de47bb610d1d45d47a48aeeea391470bd112e. Audio source files are included as read-only dependency pins, not edited here. Physical publication/source cleanup/native/recovery floors remain.

Producer/caller map: m4b_readmission.{request,next_job,record_waiting,target_progress,save_bulk/latest_bulk}; AudioJobs.{attention_summary,status,report_priority,resume,_work,has_unfinished,StartRefused}; MergeService.{state,_resume_later,_record_start_failure,retry_all,_retry_all_work,_bulk_retry_view,_retry_one,_capture_start_generation,_start_allowed,resume/_resume_guarded,pause,drain,close}; CleanupJobs.{resume,pause,_work per-worker handoff}; web_server existing retry-all route; web app shared formatter/all+selected handlers/readmission projection; review_backend checking/reacquire filtering. ReacquireSources consumers are scanner/groups, AudioJobs admission/failure handling, Merge admission and category projection, review_backend archived writes, and renderer. Actual SourceDamageAssessment producer is unsupported as stated above.

The companion JSON packet records exact current hashes, source declarations, code-boundary audit and these limits. No further source edits are planned pending independent review.

| File | SHA256 |
|---|---|
| reacquire_sources.py | a798b1fc12af460eb627e695da2a8f6e9aab55894aa2afdf90f74026742dc1d5 |
| scanner.py | ebdcec3cd151cf43720dbbda114ce6fd2b2544d946b080db5e97d226a1f564bf |
| groups.py | b28826c07cfe8c8a5b2cffb157b815c6a967a8e9cc0cd736b2e75312d345760f |
| audio_jobs.py | c3af1f9805b0ba49fa485830502905fd0126bbad39df52870bba370186f03a0b |
| m4b_readmission.py | 24cb3517dcd2042be2070dad88109dba7984de3c555afe7f0008b66b73fd4ec1 |
| merge_service.py | b242440be7a6495bdc26a8e3280d2796f02062b1d92b75ce8e46bf62410207e2 |
| source_cleanup.py | 8e08e2824dc56d0bf38a498ad1201b9b1d0c80826a807985cc1b761e16aade37 |
| review_backend.py | cf01318ed052cffa00d9fea37bf1475ce4a3d54b6d7db3537b5824a8a3c8e332 |
| web_server.py | 71980f3e9aad25c81e5be7f10137919154811a7cdf032b131d2b7738ebdb692a |
| web/app.js | f5e44af8983b1d11b877d09bd9ceb7a648a644921e81c4b4018d0b0125c33ce4 |
| web/index.html | bc669770205f2df57225cd17f942c1a7ed3acaec2f48aefe45944826554788e3 |
| catalog_contention.py | 70cf0a3eeefab4b670fe9a1f35590e85b3c0188028c6a2899706344e43fc174b |
| mp3_tag_repair.py | 2daef1a8752475b16e9956311195fdee48efb9e8588e9195c761ce0c3298f11d |
| audio_pipeline.py | f6ef578485148efd810ae6c301fb1801a66c9582eff43b581323a757ff931150 |
| tests/test_reacquire_sources.py | 715c15b078c2a08b408049136a0bce57c3c6c5debc237856cba4266d955e0c27 |
| tests/test_bulk_retry_receipts.py | d2af068fc1f758b9b43184bcc8924f748fca363b0e5c37108319b7c636c51e36 |
| tests/test_retry_start_fence.py | e999b1dd5aa4a8d3bd8dea4c692a983c1552f91f4912a529279a3c0d1380b509 |
| tests/test_bulk_retry_receipts_frontend.js | d9daeb05d5868541aca0d20277cd9e92f535305ee176a65f99f82ea9992e8ea0 |
| tests/test_attention_frontend.js | e0935c6e02ba3f930e59a7974a4c340100c0e5fe8e791fc16197aeb205369977 |
| tests/test_retry_selected_frontend.js | c5327108b9dd53d6c78a751c5a642a66ecc67fe3c97ffa02bfac90d4b2801418 |
| tests/test_attention_repair.py | 25b60b4990ecadc87a885902ec4f03e73bd93cd47f4b0cd23d06ccc5d5491ca6 |
| tests/test_catalog_contention.py | 5ff724fe0581594f1ddc62d3bf18952bd37915a3f507bb87c62d474914e018e7 |
| tests/test_mp3_tag_repair.py | 4dd4c116c7a93250eaa14d1fa947e5926549e0d39d1aee4c917707bd29e1c6eb |
| scripts/check-desktop.mjs | 762940e9ae762ead36875680e9ce1cc0ec1bba1b9129b1a88fdc64d9c2e2362c |
| native_io.py | e5e6aef41da64308215d10b636d6e583635b7e2476c7d90a7158d8ad4525dc14 |
| working_lifecycle.py | 409280ddf0adb151b85138538451da609cac9c33a406bbf28308c0713328407f |
| producer_recovery.py | 2c712278a4fed89d329fd5b5722a4c5ec5a0efc30cc9fdab68517f187f596628 |
| retry_intent.py | b8de3686baa1d3d2d7226444f93f5065eee8515cfbf3613c0d84db6ef7c2b3d1 |
| destination_admission.py | 9f4ead6a2c7955270b06fe2ac40467dd8417d4c2af5b5e2526455296ea5d8371 |
| manifest_compatibility.py | 9d70158c6f8a247fffc6993ded82d66b308537bbb6addb919b359dbadc9efb58 |
| failed_m4b_retry.py | 24f45434afcbcd94d3bce691190c69949ce3b6863f680a8dd006527f36c02e3d |
| m4b_repair.py | ee7b9f06a279f74327948ce41c359ef7aee5bff7b383afe92fa19e689507a9fd |
| conversion_progress.py | b62caf9d606c07371c97942607f65e32dafd2cd0a4f2216324d1c146193d3816 |
| organization.py | 329bbd1fdf5ec05fb92fe16332d2bbbff9758713c62d6738c58b1a1d3a919401 |
| metadata.py | 3458c54cbde8d91902b09aa75de07539ef5cd0d1919f7659bf1fa01d2233db2e |
| tests/test_retry_frontend.js | e72986825bea25e61183d283bf853dd15ed4154ee4fa4d714c53351a3b822029 |
| package.json | d46c50fb8a5d3d3ff0ebddf00d368c98e468004e9fa90130aafbc1e08f290ae8 |
| scripts/qa-runtime.json | e8e01fec2a6a93f2ec313d70bdf7cab60678bbc3b77aaaf0e0265d2c8ed2ff45 |
