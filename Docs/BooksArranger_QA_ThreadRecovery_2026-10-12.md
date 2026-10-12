# Books Arranger offline ThreadEntry recovery helper QA — 2026-10-12

**Current verdict: GO — recovered book converted, published and physically verified; temporary staging cleanup remains a Major open issue (`database is locked`).** The final M4B and retained original copy have matching full native hash/size proof. This is not uninterrupted-processing or cleanup clearance. QA issued no controls or retry. Private **17-case** helper proof and core **12-case** ABI proof remain separate counts.

## New postpublication cleanup issue — current state

At **13:58:37 Israel time**, saved observation SHA256 `e2480d7f95bcad81adced9fd5cabed9e53993e39a72f4f5fd7bddda86574d805` reports Needs attention / temporary / database is locked, completed 5, failed 1, converted_total 4; automatic metadata research remains Running. This is a technical database failure, not a request for user approval.

Futaba independently read raw durable proof `actual-recovery/new-database-lock-failure-proof.json` SHA256 `963fc7684f1da764a91258802a5fdf1406f51d26257e5a84d709c2844debc574`: the audio job itself is **completed/completed**, new attempt `c8c12e8a-1369-4c23-a3c3-efed4c311972`, output validation passed, M4B size **67,166,777**, SHA256 `9df939451e7ec43aafbf2f59d2d259fc05ba49cf0ab06cf272a1ecf3b92d698a`. All four original full completed records remain exactly unchanged. `storage_cleanup_jobs` is needs_attention with database is locked after publication; source cleanup is completed, exact source retirement is recorded removed, recovery retention is retained until **2026-10-13 13:57:52 Israel time** (24 hours after completion), deleted_at empty. This explains completed 5 with UI converted_total still 4 without classifying the successful conversion as failed. No re-encoding, publication replay, cleanup deletion or helper rerun is authorized by this evidence.

Futaba independently compared saved native physical proof `actual-recovery/publication-and-recovery-physical-proof.json` SHA256 `54c1947afde9caca541abf35ee43dd6d6a3107c18f2644ae2a53179c4fe4b7e4`, observed at **14:00:29 Israel time**. Final `Z:\\Audiobooks\\Shimada Masahiko\\Дельфин в пустыне - Shimada Masahiko.m4b` native size/hash exactly match the completed output above, with one link and held identity. Original recovery `data/source-recovery/b4e40f30-dc00-4ad0-ac96-cbe9bd1789ab/00000.mp3` native size **66,235,353** and SHA256 `f2a0a75072328c0f5280b17da2cc7f8c6af61dec2acc1ebc2a07ae2e9567a11e` exactly match the frozen source and actual recovery transaction archive, with one link. Original source absence is recorded only after verified retirement; recovery retained/deleted_at-empty and cleanup needs_attention match durable table evidence. Thus book conversion/publication is accepted, while staging cleanup is unresolved. Saved native proof is Ender's guarded read-only physical verification, independently checked by QA; QA did not duplicate the real-file/native operation.

## Normal launch and one Start — independently verified

`actual-recovery/new-owner-proof.json` SHA256 `ca9524b16e78d99095fc06a1bfc29fd92f43a644de5e86f8c55d961091e4e876` identifies latest stable **v0.12.2**, Pythonw **PID 103408**, instance **6390b07798178c2077f7d6bb4d509147**, port 5210, old PID absent, and 84 release physical pins. Before Start the saved automatic run was Paused. Futaba compared its four full completed records, checkpoint digest `623db0ce…`, repaired pending/queued row and full original failure archive exactly with the actual-operation result; all matched.

`actual-recovery/start-issued.json` SHA256 `263e34865a94cfd8756c93bd627018c51e3e1267ae78fc2915729d1153f96349` records one Start for run `96cbe916-3b2b-4858-b386-89d493cb4f24`; `start-reply.json` SHA256 `56827e686b7fe6247cfa3d57c49192e379dbf64663842dbb49b20ea0ef1bae82` records accepted Running/research. Console cp1251 output failures happened after durable proofs/reply were saved, per Ender; no repeated Start or repair was issued to compensate. The retained historical SQLITE_BUSY failure in the reply is not treated as a new active failure.

Two bounded saved observations used the same owner. At **13:55:48 Israel time**, the repaired job was queued, completed 4, failed 0. At **13:56:08 Israel time**, `actual-recovery/observation-105608.json` SHA256 `4e2341eaaa2a47ea8ad190cb17539721c049382c8e8e7cc34534cc52bc46ffa1` shows intended job `96f89af4-c6ce-46ad-a795-bd792445c6c1`, title **Дельфин в пустыне**, **Running / checking sources**, new attempt **c8c12e8a-1369-4c23-a3c3-efed4c311972**, queue 0, failed 0, completed 4. All four full previously completed records still exactly match the actual-operation proof. Automatic metadata research remained Running/research; checkpoint counts moved pending 2392→2190 and deferred 0→202, with historical done 2431 retained. These are progress observations, not new completed-book counts.

Further bounded durable proof `actual-recovery/resumed-job-proof.json` SHA256 `af1e0ddc77ad050671af3bf83af1284a7520526e7f540823bba8672c8882e307` confirms checking sources at 13:55:52→creating at 13:56:22, with new attempt journal, source PCM 121,705,344 frames at 44,100Hz and duration 2759.758367s; output remains null. Its full original archive and four completed records exactly match the actual repair proof. `observation-105655.json` SHA256 `920a11dedfad5dc7488163e78efffbbfe9745e64535e362921428cee6f17cd75` at **13:56:55 Israel time** identifies the same owner/job/new attempt at **encoding 1225.920703 / 2759.758367 seconds (~44.4%)**, failed 0, completed 4, full original four records unchanged. This observed passage beyond the old native failure is meaningful actual recovery evidence.

At the earlier partial-encoding observation, no completion/publication/retirement was claimed. Subsequent durable and native physical proof above establishes completed output and retained original recovery; the 24-hour policy is unchanged. The earlier original failure remains archived. No further QA tests or live actions are pending for this book-recovery handoff; the newly observed cleanup defect requires separate agent diagnosis and regression proof before cleanup clearance.

## Actual recovery — independent saved-proof verification

Actual receipt `scratch/native-thread-check-2026-10-12/actual-operation-owned-receipt.json` SHA256 `54adde30659fda2a04b23c068f7771c2950a3e49e63f08e78cfc9c55daa4ef39` matched independently. Its final JSONL result reports passed=true, exit 0, empty error, outer **6.4506625s**, inner **6.3671117s**, total deadline 600000ms, complete drained stdout and zero stderr, no truncation. The reviewed fixed caller contract hash is `97cae720a35129e480017206aa8a4b5c9e8f0e57fa0fc8edaa82e62a5e92a077`, inner `b080a5fc108780104adcd484a4f4aae6e2d70c1f1410fd8382658ab997f6611a`. The two receipt lines represent ownership/run recording and final result, not two repair operations. No repeat operation was invoked by QA.

Futaba parsed the original archive and confirmed its full original row exactly equals `recovery-baseline.json` (SHA256 `10dae49946e3ff8e8e623dcdb2e87968e7f50ee78678fca90acf97b111214f1e`), including the exact ArgumentError provenance, manifest, original journal and attempt. The archive row SHA256 re-derived correctly. Result job `96f89af4-c6ce-46ad-a795-bd792445c6c1` is **pending/queued**, retains attempt `0e6812bc-41a7-47a3-85d9-a1c65f791c95`, exact original journal/manifest/manifest_hash/output/created; only state, stage, reason and updated changed. The helper's conditional compare-and-swap targets this one exact full row; no generic reset was used. A new processing attempt has not yet been observed.

The four full completed records in the actual result exactly equal `actual-recovery/shutdown-proof.json` (SHA256 `396ade432030752de508cf9ae6c8e591037e286e22f4807e38cb9f9c5ed44e07`), not only their count. Completed digest remains `dba3bd841c2ae9f2d98cfeff4e694a936f38d8c930a25243595f20758b28c22e`; saved checkpoint digest remains `623db0ce10a272f757347af308c698dfff2aa2f66048547cf72d1f63cd2bcb40`. The reviewed actual caller checked checkpoint bytes before and after, completed records before and after, offline owner record absence and held lease/port protections; success result means these postconditions passed.

Fresh actual source proof inside the transaction archives one **66,235,353-byte** protected MP3 with SHA256 `f2a0a75072328c0f5280b17da2cc7f8c6af61dec2acc1ebc2a07ae2e9567a11e`, matching the frozen manifest hash/size. Native proof reports one link, unchanged protected identity, and BY_HANDLE_FILE_INFORMATION64 fallback identity (FileIdInfo128 API error 87 was recorded rather than hidden). Source proof in operation and archive matches. The caller also held and verified **91 actual physical inputs**, explicitly distinguishing release normalization from physical bytes; this actual fresh proof supersedes the earlier read-only preflight. It is not an output/media-conversion or original-retirement acceptance claim.

No failed book output was claimed completed at the actual-operation point; the app was offline then. The subsequent normal user launch/new owner/one Start and source-checking progress are verified above. QA did not access the live catalog or run the helper, launch, Start or Stop. The 24-hour recovery/original-verification requirements remain unchanged.

## Historical private-only clearance

The sections below record the prior private-fixture verification and its then-applicable actual-operation restrictions. Actual execution was separately authorized/reviewed later as recorded above; those historical NOT GO statements do not invalidate the verified one-time operation.

**Historical private verdict: GO for the exact private-fixture helper candidate only; actual catalog operation was not authorized or executed at that time.** Independent receiver passed **17 unique Python cases in one invocation**.

## Scope and pins

The helper is one offline repair for the pinned legacy prepublication ThreadEntry failure, not a generic ArgumentError retry or a shipped automatic recovery feature. Actual failed job `96f89af4-c6ce-46ad-a795-bd792445c6c1`, attempt `0e6812bc-41a7-47a3-85d9-a1c65f791c95`, baseline snapshot SHA256 `10dae49946e3ff8e8e623dcdb2e87968e7f50ee78678fca90acf97b111214f1e` are identity constraints, not proof of a repair performed. Actual failed row/originals remain preserved.

Frozen private graph under `scratch/native-thread-check-2026-10-12`: core baseline `a45566237eeeb8b79a15a16f7a046dcdab14ec3c`, core source version 0.12.1, target label `0.12.2-offline-recovery`, dirty=true. Core manifest `77c5145ac68837ca65d91a26174dce8e4fbf3bab4e64e124bf70fe36853241e2`; helper-graph digest `f5082f64cf7fe2eb9e90ad87c37e6e5e075ebb2943240f94cd66c0cf5d34098b`. Helper `recover_failed_thread_job.py` hash `716e5db0ddd3e6dc0d22efa21ad9a0bf28e1536117a370297ff2dbca07ced889`; fixture hash `4adf903c8aae46fc692633879048cbe45215cd558d159cc99f87e2b3bd8d0bf9`.

Receiver contract `7c1be6829a9d4ddc92eea1cd4deaacf69718f59f864fa9da9b1197c421e63297`; outer `921fc388757dea0a3af7ffa0a2b71d29efd4c6c1670f4bff2ebe555a10257ec1`; inner `5082bc82a8fee72bd8a49d1ed18d90fac89afdefec35e3738f549b84b8cce812`. Futaba re-derived these pins before execution and received Senua's explicit exact receiver route clearance. Used qa-handoff's separately reviewed manual nonpackage contract, not a package checker/stale route. Old 11-case and intermediate 17-case packets were not run by QA.

Producer evidence is **17 unique applicable passes across two stages**, not one full passing invocation: first full stage 16 PASS/1 FAIL (junction command syntax fixture), then corrected literal Windows cmd path targeted case 1 PASS. Original failing producer evidence is preserved under `failed-repair-producer-v1`, with `repair-continuation-check-receipt.json` and owned continuation proof. Receiver independently ran all 17 on the final fixture; no producer output was substituted.

## Actual invocation, counts and closure

Fixed no-argument command: `C:/Python314/python.exe` followed by `C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/native-thread-check-2026-10-12/run_repair_checks_independent_receiver_owned.py`. Total owned deadline **600000ms**; elapsed outer **7.3950701s**, inner **7.3528237s**, unittest **3.634s**. Outer and sole suite exit 0; no runtime error, warnings or retained-stream truncation. Pinned native/runtime ownership, suspended-child admission into private kill-on-close Windows Job, pre/post source verification, bounded drains and awaited closure passed. No own persistent process remains.

Evidence: `repair-receiver-check-receipt.json` SHA256 `536eb466968dfb34d6d31225f012928c038e777b954e4ae645995858a710e54f`; `repair-receiver-owned-receipt.json` SHA256 `32109bbfa7a0ae0d0a0524b168c72e8c005f2a3c9bbd28233b4f801c96e29819` in the same scratch area. Source graph/pins bind final fixture identity; complete verbose output is retained.

Count method: independently parsed fully qualified verbose unittest IDs ending `... ok`, deduplicated, and checked the `Ran 17 tests`/`OK` record. **17 distinct IDs** below; owner/port/lease, hardlink/reparse, and cover/context subcases are meaningful but do not add unique tests.

```text
test_offline_repair.OfflineRepair.test_archive_failure_rolls_back_full_attempt_and_four_completed
test_offline_repair.OfflineRepair.test_changed_attempt_refused
test_offline_repair.OfflineRepair.test_changed_candidate_revision_refused
test_offline_repair.OfflineRepair.test_changed_failed_row_refused
test_offline_repair.OfflineRepair.test_changed_source_bytes_refused
test_offline_repair.OfflineRepair.test_cli_wrong_fixed_version_refuses_before_any_repair
test_offline_repair.OfflineRepair.test_cover_and_context_drift_refused
test_offline_repair.OfflineRepair.test_destination_collision_refused
test_offline_repair.OfflineRepair.test_exact_private_failure_archive_and_cas_pending
test_offline_repair.OfflineRepair.test_exact_private_failure_dry_run_native_sources_preserved
test_offline_repair.OfflineRepair.test_lock_hardlink_and_reparse_parent_refuse_unrelated_sentinel_write
test_offline_repair.OfflineRepair.test_owner_port_and_busy_normal_catalog_lease_refuse_before_repair
test_offline_repair.OfflineRepair.test_retirement_intent_refused
test_offline_repair.OfflineRepair.test_running_automatic_worker_refuses_repair
test_offline_repair.OfflineRepair.test_source_validation_row_race_fails_cas_and_rolls_back_archive
test_offline_repair.OfflineRepair.test_unknown_job_associated_schema_refused
test_offline_repair.OfflineRepair.test_unrelated_exception_class_refused_even_when_expected_row_matches
```

Actual manual receipt:

```text
BOOKS_MANUAL_QA|tool=Books Arranger|target=0.12.2-offline-recovery|source=0.12.1|HEAD=a45566237eeeb8b79a15a16f7a046dcdab14ec3c|dirty=true|source_digest=f5082f64cf7fe2eb9e90ad87c37e6e5e075ebb2943240f94cd66c0cf5d34098b|manifest_sha256=77c5145ac68837ca65d91a26174dce8e4fbf3bab4e64e124bf70fe36853241e2|python=pass|node=n/a(unchanged frontend; released v0.12.1 baseline)|package=n/a(manual nonpackage contract)
```

## Meaningful behavior and remaining limits

Tests construct private real WAL SQLite databases from the pinned failed-row/group/context shape, bind private source identity/hash/cover context through actual native VerifiedFile and DirectoryBoundary guards, and preserve four private completed records. Accepted private repair archives the entire prior attempt and atomically compares every row column before changing only the queue state/stage/reason/time. Archive failure and row mutation force rollback, preserving failed row/completed records and no repair table. Changed row/attempt/revision/source/cover/context/class/retirement intent/unknown job-associated schema or existing destination refuse.

The accepted private path exercises normal catalog byte lease plus final-file protection during real SQLite connection, transaction commit and last-connection close. Active owner sentinel, occupied private ephemeral port and held normal private catalog lease refuse before repair. Actual private hardlink and native junction attempts preserve unrelated sentinel bytes. Wrong-version function entry uses a private 0.12.1 base and refuses before any canonical access. Fixture import does not run helper `main`; no test invokes the default live CLI path or accepts it past its version guard.

This is meaningful private guard coverage, not real-row repair evidence. Source fixture bytes are private identity samples, not a real MP3 conversion. Actual catalog eligibility and full native source/cover proof must be repeated freshly after supported app-owner shutdown, with exact fixed v0.12.2 source/ABI loaded, protected catalog lease/port/owner checks held and final boundaries revalidated. Prior read-only actual 66,235,353-byte source/cover preflight cannot substitute for that fresh guarded proof. No owner shutdown, live app/catalog/API/job changes, publication, deletion or recovery CLI were performed here; user normal launch must not race a repair. Any actual application needs separate coordinator approval after current-state proof and exact helper review. Failure archives must be preserved before ordinary native processing; no generic ArgumentError reset, verification bypass or per-book decision is authorized.

Historical private-pass limitation: the CLI source proof intentionally normalizes CRLF to LF for executable-source comparison while its native guards hold actual physical files. Private fixtures alone did not reconcile current canonical physical pins/offline guards; the later actual-call proof above supplied that fresh review and held-source verification. A running stable owner is not an offline repair opportunity; no further helper call is authorized by this report. The old failed attempt remains archived, with the actual job now running under the new attempt. This helper is not a shipped feature.

The 24-hour recovery and verification-before-original-deletion rules remain unchanged. Comics/Comix, Open Library and unrelated work were untouched. Temporary private test directories cleaned via test contexts; unique baseline, failed producer and receiver evidence are retained. **Open Major QA issue:** postpublication temporary cleanup stopped on database is locked; diagnose separately and preserve verified output/recovery/staging evidence, with no unsafe replay. **Current book-recovery/conversion verdict: GO; temporary cleanup remains unresolved.**
