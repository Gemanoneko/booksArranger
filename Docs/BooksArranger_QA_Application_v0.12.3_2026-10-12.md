# Books Arranger v0.12.3 application and staging cleanup QA — 2026-10-12

**Current verdict: GO — v0.12.3 applied, exact staging cleanup completed, server Audiobook Ready contains five books, and automatic research resumed.** The new normal-launch owner, all 85 released physical pins, protected records/checkpoint, one supported Start and bounded progress are independently verified from saved evidence. No live cleanup, controls, query, launch or mutation was performed by Futaba. No uninterrupted-processing guarantee is made.

## Normal launch, Ready count and resume — final verification

`actual-cleanup/new-owner-proof.json` SHA256 `101fff4be63ce8adbc52c2ff838815648207d448e9c54805c31629922236f67e` identifies **v0.12.3 Pythonw PID 84036**, instance **8da5ee732c2b31081f1b57109e114c9e**, port 5210, old PID absent. Futaba independently matched its **85 physical pins** to the installed source manifest, all five full completed records and saved checkpoint `e0ceb38c…` to the actual cleanup receipt, and every cleanup/retirement/retention after-table snapshot exactly. Before Start automatic processing was Paused.

The saved HTTP server Ready response has **total 5, five rows, all audiobook_ready=true**. It includes exact recovered candidate `137b5e43-8f6f-44d9-887f-b2b094f233ab`, job `96f89af4-c6ce-46ad-a795-bd792445c6c1`, temporary_cleanup completed, preserved_evidence_count 2, and original recovery retained through the unchanged 24-hour expiry. This verifies the Ready filter's server result; QA did not operate or screenshot the browser.

The first verify-new guard refused because the numeric old PID was reported alive; its process identity at that instant is unknown. No complete new-owner proof or Start marker existed then. A subsequent scoped identity-only proof found that PID absent; root/Senua authorized a renewed **unchanged** read-only guard, which passed all predicates. No ownership guard bypass or repeated Start was used.

`actual-cleanup/start-issued.json` SHA256 `7cff7077f4a43c2f0ab70f26d002aea30eed1d79045cfd3a81413c415eb7ed6b` records **one Start** bound to the new owner and saved run `96cbe916-3b2b-4858-b386-89d493cb4f24`. `start-reply.json` SHA256 `56827e686b7fe6247cfa3d57c49192e379dbf64663842dbb49b20ea0ef1bae82` confirms accepted Running/research. Matching reply bytes to an earlier reply are not counted as an additional call; the owner-bound issuance marker is authoritative for this launch.

Bounded `actual-cleanup/observation-120733.json` SHA256 `d0df59cdead8eeca99bf3e52d7c345903314263a502e43e39030f5a1f9288161`, observed **15:07:33 Israel time**, identifies the same owner, automatic **Running/research**, current **Small Gods / Wikipedia / Finding article reference leads**. Audiobook jobs: Completed, **completed 5 / converted 5 / approved 5 / failed 0 / queued 0**, no active encoding or cleanup. All five full completed records remain exactly equal to the actual cleanup receipt, digest `3c299753f7024677f30510c0659b584dd8dbb9fbad07916a2a8282c1fa4b4112`. Checkpoint legitimately advanced to `cfa57feb0a3120c62b1ad2cb98f283f4823e4da510d378adc2f64945f59c568b` after resume; it was preserved exactly before Start. No new fault was observed in this bounded sample.

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

The historical temporary-cleanup Major issue is verified resolved for this exact offline operation at the durable/native receipt boundary. Normal owner/resume and actual server Ready count 5 are verified above; the count was not inferred from a cleanup row. Metadata research uninterruptedness is not promised. Senua's two Minor candidate notes (lifetime path-receipt cache and shared diagnostic phase/disposition under possible concurrent callers) remain advisory and are not evidence of general serialization.

The independent private candidate QA report remains **45 unique cases**, distinct from this runtime/application evidence; no 45-case rerun or count inflation. Comics/Comix, Open Library, source policy, metadata decisions and unrelated work were untouched. Unique source/receipt/failed-attempt evidence is preserved. **No QA tests, live actions or documentation writes remain pending for this application handoff.**
