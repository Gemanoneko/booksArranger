# Initialized status reads under SQLite contention — 2026-10-15

## Root cause and scope

Real browser capsule E2E04 exposed a deterministic private-fixture deadlock. The fixture acquired BEGIN IMMEDIATE, then its control response called Fixture.state → BrowserServer.state → MergeService.state/progress_books → groups.sync → groups.setup. setup unconditionally issued INSERT OR IGNORE INTO book_catalog_revision VALUES(1,0), even when that singleton already existed. The separate connection requested a SQLite writer reservation; the driver could not schedule its release because it was waiting for this control response. E2E04 failed, native root 102156 exit 1, active descendants 0, owned-finally closure true. Earlier failed capsules and leases remain preserved.

The fixture correction returns memory-only acknowledgements for barrier controls and schedules release before state polling. Product correction is narrower: SELECT whether the seed exists; only when absent issue the same idempotent INSERT OR IGNORE. Bootstrap, concurrent initializer semantics, algorithm upgrades and other schema/migration logic remain unchanged. This removes a needless writer request from initialized status reads. It does not guarantee read-only behavior when the catalog actually requires regrouping/migration, and does not establish the cause of any historical user-facing request failure without its matching evidence.

Source pins: groups.py cb3552f308470bcdad6c948b72c7d54c0621fbbc9aa652aa3a34dc067b0bf077; tests/test_status_read_contention.py ef03b89b06734a2f122f7274f4e4375ee9a0e1687794580710f853c0464b529f.

## Actual four-case private regression

status-read-qa-01 completed at 2026-10-15 13:26:02.643696 UTC (16:26:02 Jerusalem), outer exit 0 / final ok true / all_owned_descendants_closed true. Four distinct methods discovered and run; zero failures, errors, skips, expected failures or unexpected successes. Tests took 0.661898 seconds; owned child graph elapsed 22,559 ms including setup. Native root 97504 exit 0, active descendants 0, owned-finally true. Zero subprocesses; private ephemeral loopback port 64747 was closed. Operation lease CLOSED.

The tests cover initialized setup while a separate real writer remains held, query_only initialized group sync, absent singleton restoration plus preservation of revision 9, and actual BrowserServer.state while the private writer remains held with unchanged automatic/audio state. No user database, installed port 5210, media, originals or live app controls were used.

Entry 80fff783d3486ecafcdd17ce1b3d4736b5782a1b31c36bfa64f9e913d129e20d; manifest c458b4453bc2ddb33530386ad7fb5f3971fba87cb4c7cbf1a3f3498c80a8c224. Native receipt output/status-read-4-unittest/native-result.json SHA-256 d574fb07a8a87342309c04f53628c3b86f6c1e26758190b2f202f131846cda55. Exact ceec native ownership primitive retained the 600,000 ms whole-operation deadline and descendant closure.

## Actual browser regression and limitation

E2E05 completed its eleven declared real browser/HTTP/private-worker cases at 2026-10-15 13:24:54.842957 UTC. Native root 24912 exit 0, active descendants 0, owned-finally true, 106,601 ms; outer exit 0/all closed; lease CLOSED. Receipt SHA-256 86f78149c8acf3e4a353d9dafcb398be77e73f4f94abd08eb94fd5cbbb920264. Cases covered Running, Pausing, discovery, closing, available-to-conflict 409 with zero automatic mutation, conflict clearing without auto-start, genuine recovery-lock serialization, Needs attention while a distinct actual private audio queue thread progresses, and real SQLite release/exhaustion/Stop/non-BUSY boundaries. The AudioJobs runner is a documented deterministic synthetic callback; these results do not prove encoding, provider approval/admission or real-media publication.

The three auxiliary status_during_writer probes in E2E05 ALL returned HTTP 403, Missing or invalid local request token. They omitted the required token. They prove neither authenticated status health nor a busy error and are excluded from the status-fix validation claim. E2E06 separately tested the fixed groups source and real token; its actual authenticated proof follows. E2E05 remains limited as described.

The installed v0.15 app has not been patched or restarted by this work. No release, installer, full application suite, codec/media test or Apple Books device validation is claimed. Existing earlier failure evidence, the old proof-control RUNNING record, originals/recovery and paused heartbeat are preserved.

## Final authenticated browser proof

E2E06 completed at 2026-10-15 13:33:59.421442 UTC (16:33:59 Jerusalem), outer exit 0/final all_owned_descendants_closed true. All eleven declared real browser/HTTP/private-worker cases passed. Native root 47948 exited 0, active descendants 0, owned-finally true; elapsed 134,453 ms; fresh lease CLOSED. All THREE status_during_writer requests (release, exhaustion and Stop) authenticated with the fixture token, returned HTTP 200, and independently observed the actual private writer held both before AND after the response. The full automatic-processing payload was present. No 403/error response counted as a pass.

Native receipt SHA-256 335dd73a69101c3ae73f1a369000e46bba0b10cae347ee0b96cae58365aebaba. Entry f1e76ff973cbb9b865afea7e06effc8e0f9ad96a65e75cc517888d18b15f0828; manifest 53c3ff9d225f6aa5d76f7175f53a8406f34c14c1510a627eeefc9c53646a6bba. Runtime/helpers/native ownership scope remained the independently reviewed private graph; no installed app, provider admission, encoder, user media or Apple Books device was used. This is the final scoped browser proof for this source correction; no repeat is needed absent changed input or a new finding.
