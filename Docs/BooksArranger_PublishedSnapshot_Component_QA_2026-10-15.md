# Published source snapshot discharge — component QA

Status: scoped component PASS; source checkpoint only. No installed application or real user-data mutation. Base maintenance commit 15a7ab599595c1d86775fcd7917f3532b40eecbf plus the four explicit source/test files below.

## Behavior and authority

Previously, source snapshots remained tied to full source-retirement/staging cleanup. An enrolled original cleanup held by filesystem streams could therefore keep an extra private input copy even with a verified publication and intact originals.

The new published-only phase holds the exact current verified output, completed attempt/frozen manifest and captured snapshot identity/content. It retires redundant snapshots only with either independently verified surviving frozen originals, exact accepted retirement plus verified registered recovery inputs, or accepted intentional source retirement plus actual terminal recovery disposal receipts. Terminal recovery validates immutable completion/deadline, supported actor, exact native/byte correspondence and absence; an expiry timestamp or deleted flag alone is insufficient. Missing or changed originals without accepted evidence remain held. Actual 24-hour recovery policy and original ADS cleanup policy are unchanged.

Native removal uses the existing durable per-file intent/disposition/outcome ledger and current normalized dependency checks. Changed/replaced files, cross-job references, unknown attempt members and uncertain producer/recovery facts refuse disposal. Existing protected generated cleanup is recognized only through its exact terminal receipts; publication alone does not clear working-file debt.

Fresh publication can discharge its relevant attempt. Source-completion and recovery-purge callbacks only schedule a relevant held row with a short metadata CAS. Startup/idle processes one pending published attempt under preemption; normal all-completed Resume pruning adds no new snapshot hashing. Output/original/recovery hash chunks honor the working guard, and interruption does not become missing-source proof. No central operation lock or SQLite write transaction spans the new idle proof.

## Actual private Windows verification

At 2026-10-15 13:40:49.357373 UTC, published-snapshot-qa-04 completed 47 actual tests: 20 new snapshot cases plus 27 prior lifecycle cases. Zero failures, errors or skips; five fixed fixture producers. Tests took 38.657 s. Native root PID95160 exited 0, reason completed, active_after=0, owned_job_returned_after_native_finally=true; native elapsed 57,648 ms. Parent observed outer exit 0 and final all_owned_descendants_closed=true. Native result SHA256 fe0ef3daed57475467be58315e56e0149d4d72f14e083029029f777291d6c211 at scratch/resume-2026-10-15/published-snapshot-qa-04/output/lifecycle-47-unittest/native-result.json.

The new tests use actual private NTFS files, same-handle disposal, actual CleanupJobs original retirement and RecoveryRetention purge. They cover the three authority paths; ADS-held surviving originals; unexplained missing/changed input; native snapshot/recovery replacement; changed publication/attempt; cross-job refs and unknown entries; interrupted disposition reconciliation; timestamp-only/fabricated/unknown-actor purge refusal; terminal recovery directory absence; hash preemption; metadata-only scheduling and actual Resume pruning without new snapshot hashes. Synthetic output validation contracts are fixtures, not a claim of codec or real-library conversion correctness.

QA03 actually ran 47 tests with 46 passing and one positive-ADS-fixture error. That fixture added the marker after source facts had been frozen, followed by a source-survival refusal. The old native timestamp delta was not captured; changed NTFS last-write metadata is a likely mechanism, not a measured finding. QA04 puts the marker before freezing facts and explicitly asserts native timestamp/hash correspondence. Only the fixture changed after QA03; product modules/runner/owner/runtime stayed unchanged. QA03 native closure/error evidence and lease remain preserved, without replay. Earlier01/02 proposals were never executed.

## Frozen operation and source

Exact ordinary command (Studio root cwd):

    & 'C:/Python314/python.exe' -I -S -B 'C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/resume-2026-10-15/published-snapshot-qa-04/focused-unittest-entry.py'

Entry 0d605614e387d03f8869c16108a9862346353b266ceacb76f778f0edec9dd285; manifest 6fb0bbabd17a293b14c9f68e1ec5e161a83b3260cd848a290499bfdc1b4a5421; review-manifest 876080e41eb76de82df42801ea048e2dece34dfa8cf24ca6e2abd3d8ba242f51. Complete 44-input/9997-file runtime native holds, direct-source import/private-write fences, fixed five-child argv and unchanged ceec owner/4702 supervisor provide a cumulative 600000 ms deadline, bounded drains, descendant closure and postflight. No media subprocess, browser, network, installed port5210 app, real originals/recovery/catalog, hook, build or packaging operation ran.

| File | SHA256 |
|---|---|
| working_lifecycle.py | 8b4aa819faae33df71b0e3bd8e19a8371877b5719c06e25102d2d9e195f5b6ec |
| storage_cleanup.py | fdd6511aec810c6e622df467a7ae1758a945a3c3782d098b388adf38ef0ade8a |
| merge_service.py | 35ee75a57e3541fe62ba15fefe29140cb316a25c0fd42f8151394ee13363123b |
| tests/test_published_snapshot_lifecycle.py | 008022bcbb489aaf73fe3c9a99261962b62f47cf524a0f0a7a4e9bada8957c89 |

## Limits and next work

This checkpoint has not been installed or integrated into the Electron candidate. It does not retire legacy snapshots without producer/native receipts or evaluate the retained 29.586 GB of historical sources. It does not implement the approved Zone.Identifier-only exception for deleting originals, repair M4B presentation, certify codec outputs, or produce a Windows installer. Originals/recovery/publication/history policies and genuine unresolved evidence remain protected. Full combined regression, real conversion, application transition and release review remain required.
