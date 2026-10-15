# Failed generated working-file cleanup — 2026-10-15

154 unused checked/compatible M4B files from 77 failed attempts were removed: **59,306,533,081 logical bytes (59.31 GB)**. Each of the five separately reviewed, once-dispatched native operations exited 0 and reported `complete-after-native-release`. C: free capacity was 43,286,507,520 bytes before the canary and 101,994,811,392 bytes after the final batch. These are timestamp-separated drive observations; concurrent disk activity and allocation mean they are not an exact physical-byte attribution to deletion.

The installed v0.15.0 app shut down normally at 11:49:07 UTC (14:49:07 Jerusalem). Its exact PID54960/generation134365295749473510 exited 0, removed its ownership record, and released port/catalog ownership. The shutdown operation preserved the 11 protected catalog projections, 24 completed jobs and five pending IDs. This cleanup did not restart it or change its source.

## Scope and preservation

Accepted inventory02 SHA `e0c3e1cd427e7a5c31ce31904f20c25c6ff0afdd7d800cbee7748affe8b05189` identified 80 failed jobs / 160 generated files / 61,130,967,335 logical bytes. The three unresolved diagnostic jobs below were excluded, preserving six generated files totalling 1,824,434,254 bytes:

- `07d89b9c-ff57-445d-88f9-3a44c844470a`
- `139b3941-bfa4-4199-ab4e-8380a97dbd70`
- `f96f5926-74d0-4f77-8a20-7a427a4fa404`

The 77 selected jobs retained 77 source snapshots totalling **29,585,897,364 bytes**. Each was checked against its approved manifest and full SHA-256 before disposal and rehashed afterward under the same native lease. Originals, all other snapshots, recovery sets, manifests, journals, logs, other attempt members and the separate shared-hook proof evidence were outside the deletion scope. Catalog and existing lock-file bytes and logical references remained unchanged in every operation. No retry flags, queue rows or publication receipts were edited. The remaining source copies are preserved pending a separate actual-use/original-survival/re-stage assessment; failed status alone does not require permanent retention or establish disposability.

## Actual operation receipts

Canonical scratch root: `WIP/Books Arranger/scratch/resume-2026-10-15/`. Disposal helper `failed-generated-dispose-01.py` SHA `29a76e715670567bf3f439133cc60d0161d923ec37286ba3c499fc23f57ae8d9`. Shutdown result SHA `52770431ec3813a31999bdd0ccdd11fa8dcfb7d3946ced96d38a2cf7da609a47`. The shutdown disk receipt is deliberately a before-release observation; its producer actual exit 0 and final post-release stdout were independently accepted. Every disposal reacquired its own startup mutex, exclusive localhost5210 socket, existing catalog byte lock, raw catalog leases, ordinary ancestry leases and exact file handles.

| Operation | Files | Logical bytes | Completion SHA-256 |
| --- | ---: | ---: | --- |
| canary | 1 | 371501419 | `51909531ae4e549ed4634ff6f5a947101f0c44aae70466280cb0c0608dd6bdef` |
| batch-01 | 39 | 12583883661 | `6b276324b41fe15bc30e0c3915771a965a609d254606967fb8834ef16890d784` |
| batch-02 | 40 | 17081784700 | `eed916f9edd04d249caec0a4e8df196fe3edada727764701d9f5b736347bcde9` |
| batch-03 | 40 | 16616511923 | `24dac21859a30a4923c0dddf8a48c88ac58629f15af2e3845585fd2200585f68` |
| batch-04 | 34 | 12652851378 | `488552359ac047f9586c42fac8e74cb2489ec84df05846b98683db6c2a599556` |

Each completion is under `failed-generated-disposal-<operation>-01/completion.json`, with a frozen per-job plan, full failed-row evidence, exact native target/source facts, durable per-file intent, disposition-set and removed receipts. Native same-handle disposition was used after current normalized cross-reference checks; pathname-only deletion was not used. All evidence-directory holds stayed live through final receipt writes. Every operation retained a 600,000 ms process-local deadline and launched no children. No partial failures occurred. Completion files alone are not proof of native release: actual exit 0 and final post-release stdout were required and observed for all five.

## Remaining work

This was one-time independently reviewed failed-derived maintenance. It does not implement the permanent lifecycle fix, resolve the M4B timeline defects, enable tests/builds, release an installer or establish that all former 98 GB were disposable. The installed application remains unchanged. Permanent success/failure/cancel/retry/startup retirement, bounded working-space admission and the approved narrow Zone.Identifier exception still require implementation and verification. The three diagnostic pairs need a finite compact-evidence/defect-validation discharge; the source snapshot inventory requires a separate protected-input assessment.
