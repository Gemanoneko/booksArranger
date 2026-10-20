# Producer recovery and explicit retry intent — 2026-10-20

Developer checkpoint only. No production origin record, checkpoint, isolation, retry, settings change or media move was performed. The user has now supplied the historical fact “Yes, this machine; folders unchanged”. It has not been persisted to the live catalog. Actual Сказка remains held until supported exact-bound recording, Prepare and later native startup evidence plus normal checks.

## Contracts

ProducerRecovery records an explicit historical fact only through record_origin; Prepare never invents that fact. Missing origin reports origin_unproved and cannot enroll. The trusted measurement binds Windows MachineGuid, computer, installation path and system volume serial plus unsigned GetTickCount64. Strictly lower uptime is supporting closure evidence only under the accepted unchanged local installation/no clone/restore/memory rollback historical fact. Current registered job+attempt refuses. Catalog/staging must be local fixed volumes and retain their native ancestry, catalog identity, immutable ownership marker and every exactly listed member.

Prepare captures full bytes under held native file fences and writes only a FULL-synchronous catalog checkpoint. Same startup cannot isolate. A later accepted startup must match every full byte/native fence and exact job/attempt/file/candidate scope in one CAS transaction. Isolation changes only working_attempts producer/state/reason/updated plus its own proof ledger. Old audio_jobs, working_files creation intents, marker and file bytes stay unchanged. No creation intent becomes ownership. isolate emits isolated_retained; no cleanup or queue starts automatically.

Every recovery Retry freshly fences/hashes the retained namespace through child admission. Unknown members, changed bytes, history drift or missing originals refuse. A fresh job and later fresh attempt have distinct UUIDs; the parent row stays exact. Normal current review/source/order/cover checks rebuild the manifest. An explicit retry_intent allows only output_root/destination to follow the configured v2 hierarchy; canonical metadata, source root/order/hashes, cover, evidence/profile/cleanup policy compare exactly. Retained recovery additionally disables original-source/empty-folder removal, explicitly bound to the verified checkpoint. Normal child cleanup remains unchanged.

Source-cleanup guard refuses retained dependencies. Storage/retention preparation and folder removal refuse retained paths/dependencies. WorkingLifecycle refuses Clear on isolated_retained. Candidate producer_recovery_retained persists the old path/job/attempt warning after a new representative appears. Source retention is truthful: the new published output can be Ready after normal temporary cleanup while originals and forensic old files remain retained; no source-deletion receipt is fabricated.

Retry child admission binds exact parent manifest/journal, current group revision/fingerprint and complete candidate-context bytes in one transaction with a one-parent/one-child relation. The job guard recomputes the exact current policy and checks its durable relation. Ready accepts only that verified relation and exact canonical/source/cover scope. Legacy missing output_root separately defaults to the frozen root; it cannot authorize a changed path or explicit null.

The active producer is tracked by the currently executing job/attempt tuple around the existing media runner; no PID-absence or thread-absence closure proof is used.

## Native developer evidence

- 10 recovery core/negative cases PASS, 0.791s: missing historical fact, same startup, current producer, changed machine, old bytes, unknown member, post-isolation drift, ledger drift, normal storage refusal, unchanged old job/file ledger and retained bytes. All private Job members closed/signaled (active0, unsignaled0).
- Genuine pre-v2 stored review and parent missing output_root, supported fresh service with TWO sources plus Sorted output: distinct child -> actual conversion and normal cleanup -> Ready1 and current view verified. PASS 7.995s; active0/unsignaled0. Parent row unchanged.
- Synthetic explicit historical fact/later-startup fixture -> isolation -> actual fresh conversion -> Ready1/verified while old namespace, parent/file ledger and original sources remain intact; stale Clear refuses. PASS 7.585s, active0/unsignaled0. This is fixture input, not the missing production fact.
- Explicit candidate/fingerprint/review-bound user Universe decision -> actual plan/operator native move from Author/Cycle to Universe/Cycle -> fresh configured service + normal published startup check -> verified current path and Ready/filter1; immutable original job/receipt unchanged. PASS 9.377s, active0/unsignaled0.
- Two exact identity/destination/cleanup-policy negative tests PASS 2.244s.
- Shared absent-output-root helper/bind checks: audio Ender reports31 focused cases PASS, separate checkpoint.

A prior combined3-case command stopped with Native job membership list is incomplete, forced=true/closed=true/active0/unsignaled0 at6.813s, with NO Python result. It remains NO RESULT, not a pass. Later individual meaningful native cases used the same unchanged owner; no supervisor relaxation. No canonical sender/receiver receipt, independent QA, release or production-delete clearance exists.

## Review scope and limits

Freeze the source files below for Senua. ProducerRecovery positive core and service/UI boundary exist; real human fact is absent. No API lets browser supply a closure boolean or origin attestation. The separate prepare HTTP/UI tests are mocked-service evidence; full positive core tests exercise the actual service/queue/media/cleanup path. The first Universe fixture correctly reported verifying after relocation invalidated caches; the final case uses the normal startup publication verifier before asserting verified.

The new operator live-owner interrupted-delete recovery bridge is still a separate reviewed design, not implemented/admitted. Lost original owner capability keeps interrupted removal held. Formal QA/deployment remains blocked by its separate native bootstrap/admission work. Open Library importer integration remains approved separate backlog.

Canonical declared graph now includes manifest_compatibility, producer_recovery, producer_recovery_http, retry_intent and existing merge_http; frontend recovery handler script is picked up by its existing exact test_*.js discovery. This statement does not claim execution of that whole graph.

## Frozen source hashes

| File | SHA256 |
|---|---|
| producer_recovery.py | 2c712278a4fed89d329fd5b5722a4c5ec5a0efc30cc9fdab68517f187f596628 |
| retry_intent.py | b7c9f832a4e033621e0b33a1afc7aa1d9db692750a6629862ac7d2087619dea1 |
| audio_jobs.py | 881e748d43c9cb82d7d7dfa3afe53aef39ea893c458c0215faae91df455fc0ec |
| merge_service.py | a0157d8d97a288f78098e1d68d314c29869ba01d4dc167218836298bed03dbed |
| working_lifecycle.py | 409280ddf0adb151b85138538451da609cac9c33a406bbf28308c0713328407f |
| storage_cleanup.py | 9f5bc97ab91b3d2e0684ff976cb5a75c4586ded92c851bedae5eaad87beb92da |
| review_backend.py | ff723a7afdfb6f1274d9c39d9f54b3e731f8b96dc4ca981e8ce393606975967c |
| conversion_progress.py | 0d191a65b7079db82b35ea58d31c665070df29bba9d9941a13fb3619467ad04c |
| manifest_compatibility.py | 9d70158c6f8a247fffc6993ded82d66b308537bbb6addb919b359dbadc9efb58 |
| failed_m4b_retry.py | 24f45434afcbcd94d3bce691190c69949ce3b6863f680a8dd006527f36c02e3d |
| m4b_repair.py | ee7b9f06a279f74327948ce41c359ef7aee5bff7b383afe92fa19e689507a9fd |
| tests/test_producer_recovery.py | 023944cc140a0b0d224bf2a8b1f1dc72f786bc0c128a4a01cc9242d098964810 |
| tests/test_retry_intent.py | d5063339377860c6472bd1ad7d463e89480cb2796bcc62c523aa109c53b01376 |
| scripts/check-desktop.mjs | 72c1bc08c2ef4d5dca95e7442b8298e93be6d14b9c55bb0a38c83031ce270eb8 |

## Review corrections after pinned498e22c

All3 findings addressed in source; independent re-review pending.

1. AudioJobs now runs exactly its prior single-attempt body inside an optional attempt_boundary capability. MergeService supplies the parent's fresh native/fullhash retained fence for isolation retry children. The fence is acquired before before_attempt/attempt creation and held through the actual media runner, producer closure and postprocessing. Enqueue proof alone is insufficient. A later old-file byte/member/stream drift refuses before a fresh child attempt id or staging path exists. Normal queue behavior uses a null boundary. No mutable file deletion ownership is granted.
2. prepare/isolate re-read the latest exact checkpoint and origin within BEGIN IMMEDIATE; superseded rows/origin refuse. Isolation's conditional checkpoint UPDATE must affect exactly1row, and all attempt changes roll back if it does not. The saved historical evidence actor/claim/content is semantically revalidated, not inferred from an origin table row existing.
3. Marker and every legacy artifact require single_stream while their same native read/no-delete fence is held. Extra ADS are refused before preparation, isolation and actual retry. No stream is removed or ignored.

Corrected evidence:15native core tests PASS1.400s, including deterministic prepare superseding a checkpoint during isolate's hash, ADS on marker/artifact beforePrepare/aftercheckpoint/afterisolation. Actual enqueue→external oldfile drift→worker admission PASS1.683s: child remains needs-attention with no attempt id/path, oldhistory/source bytes preserved. Actual positive retained-isolation child conversion PASS9.104s with an attempted oldfile write DURING the actual runner denied by the held native handle, then Ready1/currentverified; old files/originals unchanged. Existing Retry/Quit/failure queue regression50tests PASS4.763s. Every owner closed with active0/unsignaled0. These are developer evidence, not canonical QA.

Human historical-origin answer arrived during review: “Yes, this machine; folders unchanged”, with direct user provenance relayed by Jane. No production record or restart is inferred. The reviewed supported flow may record only this historical fact after its safe deployment/admission; later-boot closure remains separate.

Canonical fixture hygiene: recovery core now honors BOOKS_QA_FIXTURE_ROOT (session/shared remains developer default);15cases PASS1.456s under unchanged owner after that test-only adjustment, active0/unsignaled0. Product hashes unchanged.
