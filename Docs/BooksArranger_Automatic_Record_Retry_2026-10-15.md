# Books Arranger automatic candidate recording and Start eligibility — 2026-10-15

Owner: Ender. Isolated source preparation, not an applied fix or execution verdict. Branch codex/books-automatic-record-retry in scratch/resume-2026-10-15/automatic-busy-worktree. Canonical base ef04a26482895948bad9213e0c64d12b73c49fcf; implementation starts after committed Judy spec at 9ee13c3e10a7a0122ab00b50a8df5e83e56b8cda. Sully owns all Git/version/release operations.

## Observed problem and intended behavior

The installed v0.15.0 owner remained live and continued its audiobook queue while automatic metadata research stopped with a durable SQLITE_BUSY error at 2026-10-15 09:27:07.831216 UTC. The recorded stack points to automatic_processing._work → _record. Which connection held the contending lock was not established. No team Pause/Stop/shutdown was issued to produce this state. The later authenticated observation showed Digital Fortress checking sources, six queued and twelve fully converted, while automatic research separately reported Needs attention.

The existing _record performed a candidate SELECT and subsequent INSERT outside the existing explicit replay-safe transaction helper. Candidate history persistence could therefore fail on writer contention even though fetched research evidence already existed. The fix confines BUSY retries to this local atomic database operation. It does not retry research, provider requests, approval, admission, conversion, publication or source/recovery cleanup.

The existing status can_start omitted the scanner and Running/Pausing audiobook conflicts that Start itself rejected. The UI consequently offered an unavailable action. The correction supplies one authoritative Start-block reason and mirrors the same existing gate on click; it does not allow concurrent automatic research/start while audiobook work is active.

## Source changes

- automatic_processing.py: _record uses unchanged sqlite_retry.transaction. Each BEGIN IMMEDIATE attempt copies supplied result fields, rereads current candidate revision/fingerprint/history, recomputes the bounded twenty-entry history and counter, preserves compatible source_refresh evidence, and writes only the candidate row. Failed attempts roll back before another local attempt. Existing worker Stop cancellation is passed through; nonworker writes keep prior behavior. No SQLITE_LOCKED/corruption/message-string retry was added.
- AutomaticProcessing._start_block_reason is a pure read-only eligibility predicate. status consumes supplied jobs/scanner/server-closing snapshots and does not acquire merge/scanner locks. Missing job telemetry fails closed with unknown availability. BrowserServer supplies its one real jobs snapshot and current scanner/closing flags. start obtains fresh actual job/scanner state under its existing control order, rejects before mutation, and rechecks discovery immediately before admission. The early scanner refusal precedes potentially busy job-status reads. No new lock nesting or concurrency permission was introduced.
- web_server.py: rejected Start returns HTTP 409 with the matching explanation plus acknowledged automatic state. A racing rejection cannot set active_library before acceptance. The generic scan rejection delegates automatic Start to its authoritative gate; other controls retain their existing guard. Closing Start has the matching user-facing reason. Status retains separate actual audiobook and automatic-research lifecycle fields.
- web/app.js and web/index.html follow committed Judy specification BooksArranger_AutomaticStart_Eligibility_UX_2026-10-15.md (SHA-256 bc652df77c67fe24e057f92d078314b9a9dd2c2fb1df9016a93b90d9a55551bf). Start remains natively disabled when unavailable; one visible wrapping explanation matches its tooltip and accessible description. The polite region only changes text when its reason changes. Existing static help gains the approved paused-jobs clarification. Rejected-click feedback consumes the server reason and refreshes actual state without inventing Starting/Running or pausing audio. Draft protection, disconnected/pending controls and independent Stop/Pause/Resume eligibility remain separate. No CSS, layout sizes, colors or theme tokens were changed.

## Prepared meaningful regressions — NOT EXECUTED

New tests/test_automatic_record_retry.py declares fifteen unittest methods, covering real writer contention with a newer committed history, rollback after a partially executed insert, persistent BUSY exhaustion preserving candidate/checkpoint/publication proof, Stop during a worker retry wait, existing nonworker Stop semantics, no retry of native LOCKED/CORRUPT or message-only errors, revision provenance/source_refresh behavior, history bounds, and the actual automatic worker fetching once without readmission while candidate persistence encounters contention. It also covers available/unknown/scanner/audio/lifecycle/failure/closing eligibility and render-to-click gate changes without starting a worker.

Three added tests in tests/test_web.py cover real private HTTP status/Start agreement, available-to-Pausing rejection, and discovery/closing rejection. The extended tests/test_automatic_frontend.js adds five logical assertion groups for the reported combination (research Needs attention while audio Running), exact reasons/clearing, independent conversion status, stable polite text/focus, unavailable telemetry/disconnection/ended status, and an actual asynchronous rejected-click refresh with no extra Start.

Static counting method: count source lines matching four-space def test_ without importing/discovering. New retry module 15; complete web module 20; unchanged sqlite_busy module 16; unchanged automatic_processing module 52: 103 Python method declarations in the proposed focused regression set. The Node frontend file is one asynchronous script with added assertion groups, not five independently discovered Node cases. These numbers are source inventory only. Test discovery, syntax checks, imports, fixtures, tests, DOM/layout/native-input checks and packaging have all run ZERO times for this branch.

Both Python fixture modules and existing regression modules create private fixture parents on import. Therefore discovery/import needs the same separately reviewed owned execution authority as tests. This branch is not covered by the frozen maintenance thirteen-entry graph or forty-file proof snapshot. Do not mutate those inputs or adopt their clearance.

## Exact stable source and test pins

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
| automatic_processing.py | 37159 | 47792fc1b39489e4b716b0d0eb42dc59748f847d98433a8723899518ae392043 |
| web_server.py | 35381 | 324a0ecb3039b1a0c403914c4ad91dc5d7cd6e6798558c99dcd076f2a4dee1b9 |
| web/app.js | 89485 | 7efc277270a6c59f073a0969d9ad61484f2fd87f33ddc7e707b0858b181d06d3 |
| web/index.html | 19063 | 0af8bba153aefb820276eabf62fe093fbee5ff3aa635487dac80526fafce478d |
| tests/test_automatic_record_retry.py | 15177 | cdf52bfdc3df86f5d4a6d8dc0a349e732b0d69faf48dede157ba4f0594e3e9fa |
| tests/test_web.py | 21870 | 56c69da0e80bf5b929ee9f65214c7fcc38e13c29776607b3c93e3bbc4872a652 |
| tests/test_automatic_frontend.js | 39290 | 31be30f97c874055c851bb77205d9f807d3e0f57b8761abd29357d09121f7d89 |

Unchanged safety inputs: sqlite_retry.py b51a30c10bc1795916061defc665438fd61121239c1ca61dc781996d81853314; audio_jobs.py f62954e99ed5b2883133cf883d0d57b746f65bebf3abb33b08de4335ca9b9898; audio_pipeline.py db04496fd2d2efeeb330d820ef0157b7ce362da841223a5958bd1747795f1bb9.

Unchanged regression inputs: tests/test_sqlite_busy.py a04214e6522353355c04cb5d00f1f47e9741920355eddcfb073a2970943205c0; tests/test_automatic_processing.py 3502a1c91172171db198423c2e0e949b3604e1347981e05272cbb389a695a823.

## Validation and next operation

Senua's initial static read found no blocking source issue, but final exact-pinned review remains requested. No runtime clearance is inferred. A fresh branch-specific finite owned graph must bind all source/tests, helper/checker/runtime/dependencies, exact private fixture parents and real discovered test IDs/counts. Long execution needs total timeout 600000 ms with reviewed native ownership and closure; yield is not that deadline. Any command-guard refusal means stop, no changed transport/bypass. After clearance, run the focused set plus relevant regression cases, then independent Futaba behavior/UX coverage including required rendered accessibility/reflow/keyboard evidence. Inspect actual results before any source promotion or version/release claim.

No live app control, source promotion, installation, migration, deletion, ADS exception, shared hooks/config/trust change or maintenance adapter/snapshot edit occurred. The installed app and its ongoing book remain untouched by this isolated preparation. All intentionally prepared source/tests/docs are retained work; no disposable probes/exports/logs or caches were generated. Actual removed files 0; reclaimed bytes 0.

Ender-owned checkpoint paths: automatic_processing.py; web_server.py; web/app.js; web/index.html; tests/test_automatic_record_retry.py; tests/test_web.py; tests/test_automatic_frontend.js; this Docs file. Sully must recheck the branch/index and commit only these explicit files after static review, then push immediately. No merge or deployment is authorized by this checkpoint.
