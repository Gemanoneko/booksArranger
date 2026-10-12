# Books Arranger — bounded SQLite checkpoint/cache retry candidate

2026-10-12. **Final status: producer and independent receiver each 78/78 PASS; Futaba GO and Senua RELEASE CLEAR. Published v0.12.1 at a36d3fe9e61d5b6663dddba9322031ef9d9b194c, safely applied and verified through normal Windows launch, then resumed once. Historical investigation stages and failed receipts below remain retained; bounded recovery and persistent Stop-entry limits remain.** Baseline is released v0.12.0 commit `b569cc1e556726043671f9b329a2f3cb0cf49ea7`, extracted with read-only Git archive into `scratch/sqlite-busy-2026-10-12/candidate`. No canonical product source, runtime, Git index, Comics, Open Library or real-library content was modified for this investigation.

## Demonstrated failure and limits

The retained `scratch/source-fallback-2026-10-11/live-old-runtime-resume-2026-10-12.json` records old loaded v0.11.1 failure `ece3d07c-9653-4d53-a583-5f2e84ed1c16` at automatic_processing._work line263 -> _update line89: native SQLITE_BUSY during the single checkpoint UPDATE. One guarded supported Start subsequently continued the same run.

Current read-only live proof, `scratch/live-update-2026-10-12/failure-preservation.json`, records a later failure `12db22fa-1dd9-4605-96d9-0d99a06e76e6`, 2026-10-11T21:27:00.067346+00:00, _work267 -> lookup371 -> json302 -> read299. Mapping against `git show v0.11.1:public_research.py` identifies the successful-response cache INSERT. Diagnostic persistence also failed with OperationalError; the volatile failure correctly blocks Start. Four completed outputs and their native verification evidence remain preserved. No active converter, discovery or cleanup was observed by the separate live-update owner.

The demonstrated cause is a SQLite write-contention exception escaping replay-safe checkpoint/cache writes and then the failure-save transaction. **The competing lock owner, exact lock lifetime and whether an underlying external connection leaked are unknown.** Existing connect() could leave an opened connection unclosed if its initialization raised; this candidate closes that path, without claiming it caused either actual incident. We cannot promise uninterrupted processing: other database boundaries and persistent contention still fail closed.

## Exact producer/consumer boundaries

- `scanner.connect(database, timeout=10)`: unchanged default 10-second connection behavior; optional shorter acquisition wait for scoped retries; close opened connection on any initialization failure. All existing scanner/inventory/review/media callers retain their original default behavior.
- New `sqlite_retry.transaction`: fresh connection + BEGIN IMMEDIATE + callback + commit; rollback/close before retry. Only native integer SQLITE_BUSY primary/extended codes retry. No exception-message matching, SQLITE_LOCKED/corruption/unknown-error replay. Maximum 30-second budget, 60 attempts, at most .25-second SQLite acquisition wait, .1/.2/.4/.8/1-second capped backoff; Stop interruptible when supplied. Callbacks must contain only replay-safe DB writes.
- `AutomaticProcessing._update`: retry the same checkpoint fields only. Worker interruption reaches existing Paused checkpoint handling. Writing Paused itself must survive an already-set Stop event. Existing Start/Stop sequencing and restart-paused behavior are preserved; this does not replay research, approvals, immutable queue enrollment or media work.
- `AutomaticProcessing._failure`: retry only one diagnostic/candidate/run transaction. Failed commits roll back; the same diagnostic ID is retried. Exhaustion retains the existing nondurable volatile failure and Start refusal. No automatic controller restart or false saved-checkpoint claim.
- `PublicClient.read`: retry only successful-response cache INSERT/retention DELETE. The already-fetched bytes remain local; network request, host reservation, request-budget decrement and source cooldown are outside the callback and never repeated. Cache Stop raises InterruptedError; no uncached evidence receipt is fabricated.

Publication, proof gates, source refresh protections, native media/collision/cleanup behavior and 24-hour recovery remain unchanged. No UI change.

## Private fault coverage prepared

`tests/test_sqlite_busy.py` declares **13 cases**, measured with `rg -c '^    def test_'` (not a passing-test count): real WAL contention recovery; worker Stop interruption; Paused save with Stop set; restart remains Paused; bounded persistent BUSY; transaction rollback before one retry; message-only and native non-BUSY refusal; failed initialization closure; fetched-cache retry without duplicate request/budget spending; cache Stop without fabricated receipt; durable failure-save recovery without restart; exhausted failure-save remains volatile and blocks Start. Protected-output fixtures assert four immutable proof rows survive. Tests use private scratch databases only; no real library or Internet access.

The amended finite route additionally selects existing `test_automatic_processing.py` and `test_inventory.py`; actual executed names/counts/results will be reported from receipts, not inferred from source declarations. v0.12.0's prior 181 unique Python plus four reused UI checks remain historical evidence, not a new patch result.

## Finite route and reviewer gate

`scratch/sqlite-busy-2026-10-12/manual-contract.json` adapts the retained audited `automatic-failure-2026-10-11/qa_checks_v2.py` and `run_qa_v2_owned.py` route. Same fixed trusted native/runtime pins, hidden suspended child assignment to OwnedProcessJob, bounded drains, common 600000ms deadline and owned teardown. Changes are isolated paths/source hashes/version labels, three fixed suite commands and disabled bytecode. No arbitrary paths/commands accepted. Execution is pending Senua's explicit clearance.

Initial route inspection caught a preparation defect: generator missed INNER_SHA on a combined declaration line, so the outer retained the prior inner pin and would have refused execution. No tests ran. Generator was corrected and manifest regeneration excludes its own prior output/runtime scratch. Current pinned candidate: 164 archive-source files including docs/config and the new module/test (measured by manifest files array); source digest `e4941812297296aea19fce81eaad40c9a0384d60033f6c1cdcda9d0160af8bdd`.

| Input | SHA256 |
| --- | --- |
| candidate/manifest.json | 7a193582a6ad998fab0acca55f1c9d3b09783ae4172c6d51ebb3a559b4ed7a38 |
| qa_checks_owned.py | 984c2293602fd7497a612d799294e2a2e16710cf183475c3abc4ea2524d405c9 |
| run_qa_owned.py | f86f4e2a0fd804119d60fac114c34d70711703c58082352bd6cd93ba71c5e6c3 |

Remaining: source/route review, authorized producer execution, independent Futaba fault verification, Senua release clearance, then Sully Git/version/release. Live v0.12.0 application remains separately coordinated. Own unique candidate and diagnostic/review proofs retained; no disposable test output exists yet.

## First actual execution and focused amendment

Senua cleared the corrected initial finite route. One producer invocation reached **13 cases: 10 PASS, 3 ERROR**, exit1, 8.801s outer/8.749s inner. Existing controller/inventory suites were unrun because fail-fast stopped after the first suite. Three ERRORs were teardown WinError32: the fixture's native-BUSY generator used a raw sqlite3 connection context manager, which commits/rolls back but does not close; the returned exception traceback retained that fixture handle. Product assertions reached, but the errored cases are not claimed PASS. The fixture now explicitly closes the connection. Initial failing source/test/manifest/contract/both route scripts/receipts remain in `scratch/sqlite-busy-2026-10-12/failed-v1/`; private residual fixture databases remain preserved as failed evidence. No failure-output deletion occurred.

Senua/Futaba identified the existing Stop handler's direct candidate reset as another BUSY-sensitive persistence boundary. Root authorized a focused amendment: `_paused_checkpoint` atomically resets Researching candidates and saves Paused/run checkpoint through the same noncancellable bounded transaction. Existing scan/converter draining still precedes persistence. If this save exhausts, the worker records the existing `_failure` path with phase pause; it never claims saved Paused or resumes processing. Other SQLite readers/writers remain outside recovery, including metadata/host reservation, candidate-record writes, approval/queue, scan/media/cleanup and pre-save drain status reads. Persistent contention remains capable of requiring attention/restart. No uninterrupted-processing guarantee.

Two additional fault fixtures bring **prepared cases to 15**, counted by distinct declared `def test_` methods: supported controller Start/Stop under real WAL contention injected after Stopping, saved checkpoint/four proofs/restart Paused; and exhausted atomic pause preserving both prior checkpoint and Researching state without a false Paused claim. Actual results await the amended route review.

Current amended manifest still pins 164 source files. Source digest `cf92c1e485bee07ab58c6f4ee0ff79ae8b62ed923b64a9a73790e064118b788d`; manifest SHA `170d50656bf2cc74d1b8fa04713e57863146b6b71426105cde944055c980a6e9`; producer inner `da652eb8319083d10c1deb1795e8ff86c3b1db2a59b0508e49400866baa026f1`; producer outer `a6ced7494b78ec4f4675a990ae94aa9e481f352929feadda18a602131ebad1bc`. Independent receiver changes only its inner/receipt paths and holds the same source: receiver inner `65b33a1d55ddbd8d68a79ed2f54c9d92aba901f57a35b8f458c5bccd3b59045c`; receiver outer `e7bf25c06bbb0ded4e2cd15a3ac3f9c486519d675cb8409ad299740698be1e47`. Both require explicit Senua clearance before execution.

## Actual independent Stop race and correction

Second producer attempt: 15 fault PASS, 51 controller PASS, one controller FAIL; inventory unrun, 40.856s outer. The one failure was an obsolete mock target in the failure-refusal fixture: `_failure` now uses sqlite_retry.connect rather than automatic_processing.connect. Only that target changed, all assertions stayed. A cleared focused continuation passed that one case plus ten previously unrun inventory cases in 5.868s outer. The applicable then-current producer union was 77 distinct cases across two stages, not one combined receipt; both stages remain retained.

Independent receiver then reached 15 fault PASS and 51 controller PASS, but earliest-wake controller asserted **Stopping rather than Paused** after its worker ended. This was a product race, not a fixture deadline: supported Stop reads Running; worker can separately observe Stop and commit atomic Paused; caller then blindly writes Stopping from its stale snapshot. The deterministic final transition can survive after the thread ends. Receiver evidence and exact affected source are preserved in `failed-receiver-v3`.

Focused correction: `_update` appends `AND state='Running'` only when writing Stopping. Its existing BEGIN IMMEDIATE transaction performs this conditional transition atomically; stale Stop cannot overwrite committed Paused, Completed or Needs attention. No work, approval or request is replayed. New deterministic supported-Stop stale-snapshot fixture preserves Paused/checkpoint/four proof rows while setting Stop and invoking scanner/merge pause. Original earliest-wake, exact wake and attempt-count assertions remain unchanged. Prepared fault count is now 16, with 52 controller and ten inventory cases selected in both final producer and independent receiver because production changed.

Remaining limit: initiating Stop still persists Stopping before setting the Stop event; a persistent lock may delay/refuse that entry. Later status/drain/other DB operations remain outside retry. No durable Paused claim if save fails, no universal SQLite recovery, and no uninterrupted-processing guarantee.

Final pending-review source digest `493ed60cba9883497a624a46742125dcf9a772c4491862ac9ca34b1093a9c020`; manifest `8c8381b1b687d769f6cc93b1c620d653d1c7d6278bad94420cb2ecf7e63dce52`; producer inner `1590e984a231a39a15df7e89d0e66d17fc85f1724b46d9335c4a003f5eff96cf`; producer outer `70d05b7f9d5053614e06edbcf8dea5a1eca673b1b17b85fabef3e053b6f0c84e`; receiver inner `9d228c69e1cdd692152740748f80d690ab3b3c03136778d02b3bf4cee488517a`; receiver outer `96ca9e15495c1e04b4abe8e613d2aac9fd52fd41c8a2c1336c5a10f6e52c1ea6`. No post-race run yet.

## Final producer evidence and handoff

Senua explicitly cleared the final full fixed producer route and its conditional-transition mechanism. **Actual final producer: 78/78 PASS in one invocation**, 16 new SQLite/Stop fault cases, 52 existing controller cases and ten existing inventory cases. All three suite exits0. Outer45.122884s / inner45.057302s, empty outer stderr, no output truncation/containment error. Owned descendants and drains closed. Six inherited mock HTTPError ResourceWarnings were emitted within the passing controller suite; these are not described as a warning-free run and no production transport change was made to hide them.

Actual case count was reconciled from the three verbose unittest suite outputs: distinct full case IDs ending in successful `ok`, including successes whose warning text appears between the case header and final `ok`. The list has 78 names with no duplicate; sorted newline-delimited case-ID digest is `127894b6fbd421f8ece8ad9e9fdab62640341e13f8471a0040e0aae467dcce67`. Historical partial/failed stages are not added to this final 78 count. Prior v0.12.0's 181 plus four UI results remain separate historical evidence.

| Final producer proof | SHA256 |
| --- | --- |
| producer-check-receipt.json | d4cf97da103f04b0ef90e3887cf73de7b04a8bfc25f9c21b44f8069f59f8ab79 |
| producer-owned-receipt.json | 5efe2f9885fae5a7cf5e649c961909b2fa57fe30f0b85b8ce60f8c3d8e344ee1 |
| manual-contract.json | 309a0d6ef93ef26f0d39ddd5d8d5d1b6e184775a92553d07a4a29a4432dd15e7 |

`scratch/sqlite-busy-2026-10-12/application-packet.json` pins the six files eligible for later owner-managed application; each is relative to the released baseline, with the candidate absolute path, byte size and SHA256. Four production files (`automatic_processing.py`, `public_research.py`, `scanner.py`, new `sqlite_retry.py`) plus existing test mock-target correction (`tests/test_automatic_processing.py`) and new `tests/test_sqlite_busy.py`. No UI, media/approval/cleanup/source gates or release version file is included. The durable candidate report is separate documentation, not a seventh product source. Sully owns eventual version/commit/publication; root/authorized live-update Ender owns any later application boundary, not this investigation worker.

Futaba receives the independently pinned full 78-case receiver route with separate receipts. Exact final candidate source stays immutable. Release clearance and real-runtime application remain pending independent verdicts and orchestration; no new normal Windows launch is performed by this worker. Unique source/failed/passing receipts, residual failed fixture databases and review evidence are retained. Tests cleaned their own successful private temporary directories; task bytecode was disabled. No verified disposable cache/export remains to remove.

Root-cause commit guidance for Sully: **Handle SQLite write contention at replay-safe checkpoints/cache/pause saves; prevent stale Stop snapshots overwriting a committed Paused checkpoint.** The competing live lock owner's identity remains unknown; this patch does not claim otherwise or provide universal SQLite/controller recovery.
