# Held temporary cleanup — actual-operation review

Reviewer: Senua. Date: 2026-10-12. Books Arranger only. Released v0.12.3: `fbd8cfa0cb7fabd81d00a4edef897a0f56024a38`.

## Construction decision

CONSTRUCTION CLEAR for supported Stop, checkpoint-preserving shutdown and exact application of released source. Final actual invocation cleared after installed physical source/runtime and shutdown proof binding was independently reconciled. Exactly one execution under root coordination is permitted; any partial/failure result requires inspection, not blind repetition.

Frozen contract SHA256 `b4cdf82808e910d8234dfe7066bbc5bfb7f97a0b4d33076ddc6244a0fb4f7b56`; inner SHA256 `b35c19eb0fbb4a8505cc5352a5a35f5904b05986c7c87cdff40c67cef4d97205`; outer SHA256 `5af1606d3c04f4ed9822c1d2bf3ff85e62363c7cdc7508ebbaf4424a14d965ff`. Files reside in `scratch/storage-busy-2026-10-12`. Null physical/shutdown bindings refuse execution; later changes must be data-only and caller hash constants, with no broader operation.

## Authorized narrow operation

Exactly once, existing `StorageCleanup.run('96f89af4-c6ce-46ad-a795-bd792445c6c1', include_recovery=False)`. No MergeService construction, conversion, approval, original retirement, recovery purge, folder cleanup, metadata or automatic processing entry point. Normal audiobook Resume was excluded because it prunes all completed jobs/folders and then resumes pending work. Automatic Start with an empty queue does not retry this cleanup.

The normal reviewed staging disposition/native validation remains authoritative. Frozen inventory contains 29 entries: two directories and 27 files. Expected deletion is exactly 24 verified disposable staging files; ownership marker and two legacy failed-attempt logs remain. Caller must not take conflicting read holds on delete targets; StorageCleanup acquires and owns their disposition handles normally. No manual receipt/state reset or enclosing run replay is cleared.

## Guard construction checked

- Native offline lease protects database parent, final catalog lock, database and WAL/SHM/journal identities before any SQLite read, reserves the normal app port and holds normal catalog admission through all post-verification. Owner record must be absent and old owner dead. Ordinary user launch cannot race the reserved port/catalog lease.
- All installed physical/runtime/task inputs are natively held. Released normalized bytes and physical CRLF bytes are distinct explicit pins. Every canonical root Python module must be represented; verified bytes compile directly and canonical cached bytecode cannot supply executable code.
- Five complete audio rows and full completed records must match the frozen baseline/shutdown proof. Exact checkpoint remains unchanged. All five final M4Bs and original recovery copies are held with native ancestry, single-link facts, size and full SHA256; original source names stay absent under previously completed retirement.
- Target source retirement/recovery rows remain unchanged. Recovery remains retained and the original completion-to-expiry interval is exactly 86400 seconds. `include_recovery=False` prevents recovery-copy disposition.
- Exact staging ownership and full native inventory precede cleanup. Two legacy logs now have retained native ancestry/file holds, full hashes and post-operation fact comparison. Final staging receipts must equal the exact 24-path frozen removal set, all terminal and absent; residual files must equal the three retained paths.
- Reused finite caller has total deadline 600000 ms, literal fixed argv, held executable/source identities, suspended child admission to an owned native Job after bounded drains are installed, exclusive pre-work receipt and required closure. Failures after any disposition are inspection outcomes, never permission for blind retry.

## Evidence and limits

Core source review and private QA covered 45 unique producer passes across two stages and 45 independent receiver cases in one pass. Private containment/native lease fixtures from earlier recovery are reused unchanged; they do not substitute for final actual bindings or outcome proof. No live catalog/library mutation or app control was performed by this reviewer.

Two advisory core findings remain: instance-lifetime per-path receipt cache and shared diagnostic phase labels without all-path serialization. The offline caller's single process/lease and once-only exact operation address this invocation's concurrency boundary without claiming the product has a general mutex.

## Final data-only binding

ACTUAL SINGLE CALL CLEAR. Contract SHA256 `0085df0aeafaad27561938c73a5550666c69028efd633c03130b59147f599e21`; inner SHA256 `ce965b9ab0b8023699d620cbc33973e199bdfb3ecab1ae48148a58bf370475a2`; outer SHA256 `073ae191a139c18a6b621b9046029820b6bce50572a5f58f7e649899e0a397a0`.

Exact caller diffs against preserved construction change only embedded hash constants. Contract changes bind installed physical bytes, explicit line-ending metadata, shutdown proof and the installed source manifest; released semantic source graph and operation remain unchanged. Independently hashed all 85 installed inputs physically and after CRLF normalization: zero mismatch with frozen release hashes. Installed manifest SHA256 `5a823ccb18f2a1195fea78ba27f7444b49d2975d6f39584fc500a5831ba2e6cd`.

Shutdown proof SHA256 `29975cfb8c861aa7a14d68a8561d4d86f67e682fc97cafdbb76bc467ae757190` binds old PID 103408, Paused state, five completed record keys and checkpoint SHA256 `e0ceb38c55cc22af7ab5a06ecb678b546ad37dab1e3acc74f48593b64e94c0bb`. Live owner absence/death, reserved port and catalog/native sidecar guards are rechecked by the reviewed caller immediately before operation, rather than treating this saved proof as a substitute.

Fixed argv: `C:/Python314/python.exe -I -B C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/storage-busy-2026-10-12/run_actual_cleanup_owned.py`, no extra arguments; total deadline 600000 ms, exactly once.

## Actual outcome

The authorized single invocation passed. Independently read immutable `actual-cleanup-owned-receipt.json`, SHA256 `fda575786e5fe278cd72e7d20fd92250e8b04fb64efd8e9951699712155e6ada`: outer 399.437892400019 seconds, exit 0, empty error, no stream truncation, exact cleared inner/contract identities. Parsed native proof reports five protected final M4Bs, completed count five, one retained original recovery copy, unchanged checkpoint SHA256, storage job completed, exactly 24 terminal `removed` receipts and three retained staging files. These are the reviewed caller's actual native/post-SQL checks, not a replayed fixture result.

Independent QA reports launch-safe saved proof passed. New-owner/one-Start guard statically CLEAR: `actual-cleanup/live_control.py` SHA256 `722bb24f63a96b824d51b71e322a81237b7d3d0810a09de92976b9393143bbab`. Only verify-new/start-new/observe modes are reachable. Guard requires immutable actual cleanup receipt/full after-tables, exact five completed rows/checkpoint, fresh v0.12.3 owner and old PID absence, all 85 released source pins, idle Paused saved run/restart state, and a bounded no-proxy/no-redirect server Ready query returning exactly five eligible rows including the recovered book. Native parent protection and exclusive Start marker precede the single API Start; API failure does not permit repetition.

Pending: user's ordinary Windows launch confirmation, actual fresh-owner/Ready-five proof and single Start/observation. This review does not certify media playback or uninterrupted processing.
