# Books Arranger v0.12.3 application and staging cleanup QA — 2026-10-12

**Current verdict: GO for normal user launch.** The exact released v0.12.3 source and one-time offline staging cleanup are independently verified from saved immutable evidence. New loaded owner, server Ready count 5 and one supported Start remain pending normal Windows launch. No live cleanup, controls, query, launch or mutation was performed by Futaba.

## Exact installation and operation

Installed release `fbd8cfa0cb7fabd81d00a4edef897a0f56024a38`, version 0.12.3. `scratch/storage-busy-2026-10-12/installed-source-manifest.json` SHA256 `5a823ccb18f2a1195fea78ba27f7444b49d2975d6f39584fc500a5831ba2e6cd` names 85 files, with physical hashes and released blob hashes/line endings separately recorded. Futaba independently matched **all 85 entries** to actual caller held native physical proof, including size, physical hash and released hash. This reconciles CRLF physical bytes without pretending their hashes equal normalized Git blobs.

Actual receipt `actual-cleanup-owned-receipt.json` in the same scratch area SHA256 `fda575786e5fe278cd72e7d20fd92250e8b04fb64efd8e9951699712155e6ada` independently matched. Final JSONL record: passed=true, exit 0, empty error, outer **399.4378924s**, inner **399.3746118s**, hard deadline 600000ms; complete bounded stdout drain and zero stderr, no truncation. Native owned child/lease/source boundaries closed cleanly. Contract `0085df0aeafaad27561938c73a5550666c69028efd633c03130b59147f599e21`, inner `ce965b9ab0b8023699d620cbc33973e199bdfb3ecab1ae48148a58bf370475a2` bind the reviewed operation.

Ender ran exactly one `StorageCleanup.run` for job `96f89af4-c6ce-46ad-a795-bd792445c6c1`, **include_recovery=False**, while the supported app was safely offline under retained normal catalog lease/port/owner protections. No conversion/source-retirement/recovery-retention/folder cleanup entrypoint was invoked. No QA repeat operation or extra tests were run.

## Independent postconditions

Futaba compared the actual result with `actual-cleanup/shutdown-proof.json` SHA256 `29975cfb8c861aa7a14d68a8561d4d86f67e682fc97cafdbb76bc467ae757190`: **all five full completed records exactly match**, and saved checkpoint SHA256 **e0ceb38c55cc22af7ab5a06ecb678b546ad37dab1e3acc74f48593b64e94c0bb** matches. All five protected final M4Bs have native single-link identities and full hash/size matching their completed output records. The recovered fifth output remains 67,166,777 bytes, SHA256 `9df939451e7ec43aafbf2f59d2d259fc05ba49cf0ab06cf272a1ecf3b92d698a`.

Target storage cleanup now has state **completed**, empty reason, unchanged output hash. There are **24 terminal removed receipts**, all kind staging. Their path set exactly equals the contract's 24 approved paths; each saved native receipt size equals its receipt size with one link. Receipt sizes sum **2,146,960,451 bytes**. These are owned-copy disposition receipts, not unique Python cases or a measure of original library deletion.

Residual files exactly equal the contract's **three preserved paths**: ownership marker plus two old failed-attempt logs. Both legacy log hashes remain unchanged (empty-file SHA256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`), with durable preserved reasons stating legacy evidence lacks exact producer bytes. No invented receipt or unverified legacy disposal is claimed.

Source cleanup, source retirement, recovery completion and recovery retention table snapshots are **exactly equal before/after**. Original retained recovery MP3 remains 66,235,353 bytes with native single-link identity and full SHA256 `f2a0a75072328c0f5280b17da2cc7f8c6af61dec2acc1ebc2a07ae2e9567a11e`, matching the original source retirement proof. Retention expires **2026-10-13 13:57:52 Israel time**, unchanged; state retained and deleted_at empty. Cleanup authorizations remain empty. The four earlier books and completed fifth publication were untouched.

## Remaining checks and scope

The historical temporary-cleanup Major issue is verified resolved for this exact offline operation at the durable/native receipt boundary. Server Ready count and normal launch/resume still need new loaded-owner evidence; this report does not infer a UI count from a cleanup row. Metadata research uninterruptedness is not promised. Senua's two Minor candidate notes (lifetime path-receipt cache and shared diagnostic phase/disposition under possible concurrent callers) remain advisory and are not evidence of general serialization.

The independent private candidate QA report remains **45 unique cases**, distinct from this actual-operation proof; no 45-case rerun or count inflation. Comics/Comix, Open Library, source policy, metadata decisions and unrelated work were untouched. Unique source/receipt/failed-attempt evidence is preserved. No live actions are pending for Futaba before normal-launch proofs arrive.
