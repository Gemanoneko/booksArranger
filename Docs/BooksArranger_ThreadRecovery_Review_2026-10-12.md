# One-off ThreadEntry recovery — construction and private proof review

Reviewer: Senua. Date: 2026-10-12. This helper is separate from released v0.12.2 and its ABI review range `a45566237eeeb8b79a15a16f7a046dcdab14ec3c..3762d2650c078245f55c68cf65111cecdc027a3a`. The helper is an uncommitted, exact pinned scratch artifact; this report does not certify a product recovery feature or enlarge that release range.

**Disposition: STATIC CONSTRUCTION / PRIVATE FIXTURE CLEAR. Exact final actual invocation: CLEARED ONCE under the offline guards below.** No open Critical or safety-floor findings remain. At private-proof handoff the app was active and no actual call was allowed. The user subsequently explicitly authorized safe recovery; supported shutdown and exact data binding now satisfy the final pre-execution review. No actual recovery success, publication, playback, source retirement or deletion is claimed by this clearance.

## Exact scope and pins

Paths are relative to `scratch/native-thread-check-2026-10-12`.

| Input | SHA-256 |
| --- | --- |
| recover_failed_thread_job.py | 716e5db0ddd3e6dc0d22efa21ad9a0bf28e1536117a370297ff2dbca07ced889 |
| recovery-tests/test_offline_repair.py | 4adf903c8aae46fc692633879048cbe45215cd558d159cc99f87e2b3bd8d0bf9 |
| recovery-baseline.json | 10dae49946e3ff8e8e623dcdb2e87968e7f50ee78678fca90acf97b111214f1e |
| repair-receiver-contract.json | 7c1be6829a9d4ddc92eea1cd4deaacf69718f59f864fa9da9b1197c421e63297 |
| repair_checks_independent_receiver_owned.py | 5082bc82a8fee72bd8a49d1ed18d90fac89afdefec35e3738f549b84b8cce812 |
| run_repair_checks_independent_receiver_owned.py | 921fc388757dea0a3af7ffa0a2b71d29efd4c6c1670f4bff2ebe555a10257ec1 |

Final helper/test source digest: `f5082f64cf7fe2eb9e90ad87c37e6e5e075ebb2943240f94cd66c0cf5d34098b`. Unchanged core candidate manifest: `77c5145ac68837ca65d91a26174dce8e4fbf3bab4e64e124bf70fe36853241e2`, core source digest `83cb44b8b5f079358cc6e70815c044015c00f3a74a11b1a1327ab9de5603d4fa`.

The helper accepts only the frozen failure of job `96f89af4-c6ce-46ad-a795-bd792445c6c1`, attempt `0e6812bc-41a7-47a3-85d9-a1c65f791c95`. Full row, exact ArgumentError, candidate/context revision, checking-sources history, manifest hash and absence of all known/unknown associated intents are checked. An unrelated ArgumentError refuses. Existing approved metadata/order/source/cover binding and fresh native identities/full hashes are mandatory; destination collisions and active work refuse. Atomic original-row/archive/source-proof preservation precedes a full-row CAS to pending; rollback retains the complete failure and four private completed rows. The 24-hour policy and verification before original deletion remain unchanged.

## Closed findings and actual guard proof

The initial proposal invoked catalog_lock before final-file protection. Its ordinary first-byte write could follow a linked lock file. Amended code establishes the parent DirectoryBoundary first, then holds ordinary single-link native handles opened with OPEN_REPARSE_POINT, sharing read/write but denying deletion, for the lock, actual database and SQLite sidecars. Normal catalog locking then runs under those held identities. Actual private tests prove hardlink and junction-parent refusal without unrelated sentinel writes, owner/port/normal lease refusal, and fresh SQLite opening/commit/last-connection closing while native guards remain, followed by reopening to verify archive/pending/completed rows.

The initial post-commit receipt overwrite could follow an existing linked target. The helper now writes no receipt file: its atomic DB archive is authoritative and the owned caller captures stdout. A post-commit reporting failure explicitly reports a committed repair and directs archive inspection before retry. CAS races, failed archives, cover/context drift, unknown job-associated state, changed attempts/revisions/sources, destination collision and running controller all refuse with preserved state.

## Actual validation and finite closure

Producer achieved **17 distinct passing test IDs across two stages: 16 retained passes plus one corrected failed-case continuation**. The first17 invocation failed only because the fixed cmd.exe executable spelling made junction creation return a syntax error before the junction existed. The one-line executable spelling correction left helper bytes unchanged. Its focused continuation then created the real junction and passed native refusal/sentinel assertions. The failed source/routes/receipts remain in failed-repair-producer-v1. No discarded failure or single-invocation producer pass is claimed.

Independent Futaba receiver passed the same **17 distinct IDs in one invocation**, suite/outer exit0, inner7.3528237s / outer7.3950701s, no runner errors, warnings or stream truncation. Senua independently read the verbose IDs, actual check/owned receipts, source/contract pins and closure fields. Subcases do not inflate unique counts.

| Actual proof | SHA-256 |
| --- | --- |
| repair-continuation-check-receipt.json | 74fc53b662308522605899dd0124d9ef5567320c0bbd750b5a1b04275d4b174c |
| repair-continuation-owned-receipt.json | 38be099d6dd61e1dffd82cb502a2b113071f9c66b3b67775658f2baf24ddb33e |
| repair-receiver-check-receipt.json | 536eb466968dfb34d6d31225f012928c038e777b954e4ae645995858a710e54f |
| repair-receiver-owned-receipt.json | 32109bbfa7a0ae0d0a0524b168c72e8c005f2a3c9bbd28233b4f801c96e29819 |

Private receiver command was fixed `C:/Python314/python.exe` plus run_repair_checks_independent_receiver_owned.py, no arguments. Its 600000ms total deadline, pinned audited native/Python/media/cmd runtime/source holds, suspended owned child assignment, inherited containment of the one fixed hidden junction command, bounded drains and descendant/output closure were reviewed before execution. It touched only generated private fixture data. No helper CLI against the real catalog was executed.

## Actual-call construction review after explicit authorization

**CONSTRUCTION CLEAR; execution pending exact shutdown-data binding.** Senua independently read and SHA-verified actual-route-packet.json's contract `f22e0cbd312d1f3d32be8dae6306ed2d6ea6582ce40e6177b7e3e4c5e691bbed`, inner `1c6d8a1896b74864e50da13f27b6278cf0a94bdc7bac7e573539af57d9058bb1`, outer `b172bee58c9a79b77d421faea6a915a6645e40bbbfc93386d36eb2f588ad413c`. Fixed outer argv: C:/Python314/python.exe -I -B run_actual_recovery_owned.py; child adds -u and uses actual_recovery_inner_owned.py. Total deadline is 600000ms with reserved teardown, suspended child and output drains installed before owned Job admission/resume; output retention is capped, truncation fails, and exclusive receipt creation occurs before actual work to prevent unknown-target overwrite/repeat.

The first draft read SQLite before acquiring final-file protection and released the offline lease before post-verification. This actual-boundary gap was rejected. Frozen construction retains a single reviewed helper.offline_lease before **any** SQLite read, through completed/checkpoint comparison, exact repair_transaction with apply=True, source/cover verification, commit/last connection close and post-verification. No helper.main nesting or weakened transaction predicate is introduced. Exact original row/archive digest, only permitted queue-field changes, unchanged completed records/checkpoint and absent owner are checked before releasing the lease.

Holding .py files alone could permit existing matching cached bytecode. The frozen caller now imports all 30 canonical modules with a finder/loader that compiles the held physical bytes directly, never reading canonical .pyc. Installed source/runtime pins record physical CRLF bytes separately from normalized released hashes. Installed VERSION 0.12.2, actual loaded native file, fixed normalized native source and 28-byte ThreadEntry/function-pointer identity are explicit checks; JOB/ATTEMPT and full pinned failure remain mandatory. No product/helper source was changed.

The frozen contract currently has a null shutdown-proof hash and refuses execution. Root may perform supported Stop/shutdown and bind the exact owner (PID54388, instance79ad53f86f9804c510bda3e3a3f01756), Paused saved checkpoint and four completed records. Final data-only contract/caller pins must be checked before execution clearance. No broad tests or repeated unchanged backend review are needed for that binding.

Senua additionally checked the actual installed native file's physical SHA-256 `46affe8d8ba8304944c5a2f0e4ad7ca2db79566c40016ab694b366b3dbf5becd` and VERSION physical SHA-256 `0e273d66f6f5e0b3fceaac55acd2238cfe254e3f64f93f9626349ea43326cd93` against the frozen contract. Its declared normalized released native hash is `6509963b1ff3aa414441a7ec4728874ee41ebfbc6c2d13c76a17c04193f65e80`; CRLF normalization is explicit. The contract contains exactly30 canonical-module entries; the caller holds and validates all installed/task/runtime inputs before their use. This is read-only identity review, not an executed recovery result.

## Final actual invocation clearance

**ACTUAL INVOCATION CLEAR**, one fixed call only, after explicit user authorization and root-coordinated supported Stop/shutdown. Senua independently hashed final inputs and diffed them against the preserved construction packet. Changes are only the bound shutdown-proof hash, corresponding inner/outer hash constants, and a terminal JSON newline; helper/source/runtime/lease/CAS logic is unchanged. No broad test rerun was required.

| Final input | SHA-256 |
| --- | --- |
| actual-call-contract.json | 97cae720a35129e480017206aa8a4b5c9e8f0e57fa0fc8edaa82e62a5e92a077 |
| actual_recovery_inner_owned.py | b080a5fc108780104adcd484a4f4aae6e2d70c1f1410fd8382658ab997f6611a |
| run_actual_recovery_owned.py | af6c93e18699c9c009cc632b927fe5150b9126b828a2b3171f1fa970d7cbb455 |
| actual-recovery/shutdown-proof.json | 396ade432030752de508cf9ae6c8e591037e286e22f4807e38cb9f9c5ed44e07 |

Fixed argv: `C:/Python314/python.exe -I -B C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/native-thread-check-2026-10-12/run_actual_recovery_owned.py`. Existing 600000ms contract and all guards remain mandatory.

Pinned shutdown proof reports the exact v0.12.2 owner PID54388 / instance79ad53f86f9804c510bda3e3a3f01756, Paused run96cbe916-3b2b-4858-b386-89d493cb4f24, no active scan/job/cleanup, checkpoint SHA-256 `623db0ce10a272f757347af308c698dfff2aa2f66048547cf72d1f63cd2bcb40`, four completed records digest `dba3bd841c2ae9f2d98cfeff4e694a936f38d8c930a25243595f20758b28c22e`, and supported shutdown reply. Root/Ender reported old PID exited. The caller independently rechecks absent owner, dead old PID, reserved normal port, normal catalog lease and held final database/sidecar identities before any SQLite operation. Any change refuses before mutation.

Authorized sequence: keep the app offline; run this exact call once; inspect owned exit/drain receipt and actual archive/queue/checkpoint/completed-record proof; only then proceed to the normal Windows launch and separately guarded owner/Start verification. If execution, truncation or post-commit proof fails, STOP and inspect the authoritative archive/queue before considering any retry. The receipt's started marker deliberately prevents blind repetition. Actual success evidence is pending; the known original failure cannot be declared repaired solely from this review.

## Historical minimum actual-operation gate

## Actual outcome and replacement verification/Start guard

The one authorized actual invocation completed. Senua independently matched actual-operation-owned-receipt.json SHA-256 `54adde30659fda2a04b23c068f7771c2950a3e49e63f08e78cfc9c55daa4ef39`, read passed=true/exit0/no error, outer6.4506625s, stdout170785bytes/stderr0 and no truncation. Its actual proof reports the exact Pending/queued result, complete original archive, freshly protected source proof, unchanged four completed records and unchanged saved checkpoint. Root and independent Futaba confirmed the full saved proof launch-safe. This establishes saved queue recovery; it does not certify the retried book's encoding/playback/publication or claim resumed processing before a new owner/Start is observed.

The replacement live_control.py adaptation replaces the old failed-row guard with the immutable actual-success receipt pin, exact full Pending row and full original archive comparisons; it requires queued1, Paused, failed0, completed4 and no current job. Existing idle checks, unchanged checkpoint/four records, fresh v0.12.2 owner with different instance/PID, dead previous PID, 84 released source checks and a single Start remain. Senua read the exact adaptation and rejected the old exists()+write_text Start marker: it was non-atomic and could follow an unknown final link. Ender added a retained DirectoryBoundary around the existing owner/output scope and exclusive marker creation/flush before the API call; refusal or API failure does not remove the marker.

**Replacement verification / single-Start guard CLEAR:** actual-recovery/live_control.py SHA-256 `b0c9d68be5a92df0d495311b9bb1f033c277090c0c49f0ba329586998728f85f`, independently hashed and relevant guards read. Normal user Windows launch may proceed. Run verify-new against that owner, then at most one start-new only if every exact predicate passes. No broad unchanged tests were repeated for this local guard correction. The caller is transient; this is no tool-launched persistent app authorization. New-owner and actual Running/processing observations remain root/Ender follow-through work, not an outcome already observed by this report.

## Historical minimum actual-operation gate

Subsequent user authorization: the user explicitly requested safe actual recovery and root reactivated Senua's exact actual-call review. That authorization supersedes the earlier permission status, but it does not satisfy the technical offline/identity/finite-route gate. Actual execution remains pending a new frozen invocation and verified shutdown; the prior private17 result cannot substitute for that review.

Before final binding the actual route was unreviewed/not cleared. The required separately frozen bounded owned invocation must hold helper/bootstrap/runtime and actual installed executable-source bytes before import. Record exact physical installed bytes, including CRLF, separately from any documented normalized source comparison; confirm the actual loaded fixed v0.12.2 module and stable ThreadEntry ABI identity. Immediately revalidate absent owner, reserved normal port, protected final database/sidecars, normal catalog lease, exact failure provenance, fresh source/cover proof, collision/intent absence and completed records. An app that is running closes this gate. These conditions remain mandatory in the cleared invocation; private fixture proof alone cannot bypass them or promise uninterrupted processing.

No broader unchanged backend regressions are required by this helper review. Canonical code, registry, live catalog and library files were not changed by Senua. Review history and unresolved/failed proofs remain in scratch; no disposable output was created by the reviewer.
