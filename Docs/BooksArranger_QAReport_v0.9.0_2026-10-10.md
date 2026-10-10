# Books Arranger QA — v0.9.0 automatic processing

Date: 2026-10-10. Futaba independent behavior QA. Final immutable endpoint: candidate v4.

**Verdict:** GO

**Open findings:** 0 Blocker / 0 Major / 0 Minor. Senua separately issued RELEASE CLEAR for this same source endpoint. This verdict covers the pinned implementation and the methods below; it does not claim a production-library conversion or successful live matching of the two supplied stories.

## Exact endpoint and matching handoff

Target 0.9.0; snapshot source marker 0.8.0; HEAD `11786f36598d058debee2aa108b8e1c12b7a5b60`, dirty true. Baseline `c10f80f0fe597167713b388f30252ee65fd923bf`. Complete 65-file sender snapshot `scratch/automatic-processing-2026-10-10/candidate-v4`, received unchanged into `scratch/automatic-qa-2026-10-10/candidate-run`. Normalized digest `dbd2cacc10601f77a87ec48f8760e0a83dec909830a9c03f80d2504095d68084`; raw manifest SHA-256 `25cdf64750d66194a8ef6960b9cbd0fca0ab43070915bf7fb0db94038be5ca39`. Staged v0.9 frontend overlay is declared in the snapshot; live canonical assets remained coherent v0.8 during QA.

Applied qa-handoff skill. This Python app has no package.json. The reviewed manual non-package contract is `manual-contract-v4.json`, SHA `308b40f14998a643cea209ecb293eb0e04f24db0049280b64cabbbc1479eb377`; inner `qa_checks_v4.py` SHA `2b49c20b1e997e0cf3beccf0b8cd676d342cda29a1f649ef2069e213fe28de56`; outer `run_qa_v4_owned.py` SHA `9770e1f5df0fced1ca5b9e83d2902ccc1f455e357601290add4d97246e362b2b`. No fabricated package check is claimed.

Futaba independently compared all 65 source sizes/hashes, held single-read manifests/contracts, exact eight commands, four executable runtime pins, and before/after identities. Trusted native containment bootstrap precedes source imports. Fixed working-directory FFmpeg/FFprobe resolution is checked. Hidden Windows owned jobs cover descendants, bounded output and one total 600000ms deadline; all runs below closed before that deadline with no timeout.

Sender actual PASS: **70 Python + 3 Node routes**, 80.782 seconds. Receiver independently ran the identical invocation: **70 Python + 3 Node routes**, 101.641 seconds, exit 0, empty owned error. Receipt identity and commands match; timings are descriptive, not a performance comparison.

Matching receipt line, reproduced verbatim:

`BOOKS_MANUAL_QA|tool=Books Arranger|target=0.9.0|source=0.8.0|HEAD=11786f36598d058debee2aa108b8e1c12b7a5b60|dirty=true|source_digest=dbd2cacc10601f77a87ec48f8760e0a83dec909830a9c03f80d2504095d68084|manifest_sha256=25cdf64750d66194a8ef6960b9cbd0fca0ab43070915bf7fb0db94038be5ca39|python=pass|node=pass|package=n/a(manual nonpackage contract)`

Sender receipts in `scratch/automatic-processing-2026-10-10/`: `sender-manual-receipt-v4.json` SHA `e7e1d143c6a733fb4141f394757c8e61a7c53435b30cae34727f41a37f6bf190`, `sender-owned-receipt-v4.json` SHA `9b98b47cc35066dceda5c7d6536d11d637199f24e8d516ddcfa9fa5bfca9936b`. Receiver preserved copies in QA scratch: `receiver-manual-receipt-v4.json` SHA `9870baa4a8f219266a9764d7c8588f2301a0dd9ddb595d2c48dc64cba6772a1f`, `receiver-owned-receipt-v4.json` SHA `15f8582d03bfbd48d6889502ad33e0ea7db314062c2e7d2fa8e792d0be09ad81`.

## Executed behavior coverage

The formal 70 Python cases comprise 33 automatic-processing, 7 actual-media, 10 grouping/filter, 14 ephemeral HTTP, and 6 merge-service cases. The three Node routes cover automatic, progress and recovery frontend behavior. Counts are explicit discovered unittest cases and fixed Node scripts, not their individual assertions; sender repetition is excluded from receiver totals.

- Filename, embedded tags and folder clues are retained. The supplied unrelated Кабир Максим – Классные рога, чувак! [НЕОСФЕРА].mp3 and Масахико Симада - Дельфин в пустыне - 1991.mp3 separate into work candidates; embedded numbered tracks remain one recording with exact order and chapters. Missing membership/order, disc gaps and conflicting work clues stay held without source deletion.
- Fetched independent work/credit/language evidence is required. Search snippets, Wikipedia references alone, distant name/title co-occurrence, translator credits, conflicting author roles, duplicate or nonfinite evidence do not approve. Generic invented fixture books exercise lookup and prove approval is not a supplied-story hardcode. Citation leads still require fetched pages.
- Stop saves pending work; restart stays paused until explicit Start. Waiting/cooldown is Paused with saved work, not an unscheduled retry promise. Held or waiting candidates do not block other eligible books. Long Unicode queries hold one candidate and continue the pass. Owned resolver timeout/Stop are tested with private resolver fixtures, without external network.
- Fresh held source tags are revalidated before admission. Destination collisions and queue-insertion failures leave no approval or queued job. Pending admission is excluded from ready/approved presentation. Last/only-track cover interruption and second-track Stop remain stopped without approval.
- The actual-media case generates private MP3 tracks and cover, passes a fake public-provider decision through automatic admission, creates and verifies a chaptered M4B without a manual form, removes only included fixture originals after verification, cleans working copies and registers retained recovery with its 24-hour deadline. This is actual local encoding/verification, not a production conversion or a 24-hour elapsed soak. The converted/approved count reaches 1/1 only after required cleanup. Existing conversion/restart, source preservation, HTTP origin/token and shutdown behavior pass.

Six separately authored independent v4 cases also PASS: translator-role conflict (four punctuation variants within one case), unavailable-source waiting, cover-provider waiting with another-book continuation, held-book continuation, conflicting numbered work membership, and existing-destination counter/source preservation. Explicit suite count: **6 cases, 0 failures, 0 errors**, 21.658 seconds. Probe `independent_v4.py` SHA `b1616811531410d740bf55feb39630fa1ce449edf6968be135e4a0821f3477ed`; evidence is the first extra receipt below. These six were not repeated after their PASS.

## Rendered and keyboard verification

Used the studio-owned `scripts/qa/headless-browser.mjs` with a fresh private Edge lease, exact executable and fixed headless root. All 180 extra dependencies, including the existing compiled holder DLL SHA `d3011c2791ab511fb2a0fea17fae13f70e667f87fb07e7154efe1aeb4cf0cca9`, were held before browser import/launch. No signed-in session, focus or audio was used.

Served actual pinned HTML/CSS/JS through a private loopback allowlist fixture. Only the known initial polling tail was suppressed. Six synthetic authoritative lifecycle states (Idle, Running, Stopping, Paused, Completed, Disconnected) × widths 1440/700/350 produced **18 frames**, with no body overflow/control overlap and automatic controls at least 32px tall. Held long-Russian-title inspection remained readable, with optional manual disclosure. Source-link focus, Enter disclosure, and unsaved title/focus retention through automatic render passed. These synthetic state frames prove presentation; they are not backend lifecycle transitions.

Two distinct zoom methods were checked: CSS zoom 2 and a layout-equivalent 720 CSS-pixel viewport/DPR2 on a nominal 1440px display. CDP emulation is not browser chrome zoom. Manual screenshot inspection caught the first CDP capture using an outdated wider Playwright viewport; the fixture was corrected and only that capture repeated. Corrected image is 705×2903, narrow media/reflow true, scrollWidth 705 within viewport720, visually inspected. Matrix/browser route PASS 17.639s, lease `c5959194e0b0` remaining=0. Corrected single-view route PASS 12.732s, lease `92790424f52d` remaining=0. Every route requires zero remaining processes and always attempts browser/lease/server teardown.

Preserved screenshot paths in QA scratch: `automatic-idle-1440.png`, `automatic-running-350.png`, `automatic-paused-700.png`, `automatic-disconnected-700.png`, `automatic-css-200-percent.png`, `automatic-200-percent-layout-equivalent.png`. Futaba inspected representative desktop, narrow, Paused, Disconnected and corrected zoom frames. Existing table columns use an internal horizontal scroll region at narrow widths; new automatic/inspection panels fit the body. No separate light-theme/OS-theme or browser chrome zoom claim is made.

Extra evidence, all under `scratch/automatic-qa-2026-10-10/`:

| Receipt | Actual result | SHA-256 |
|---|---|---|
| first-extra-check-receipt-v4.json | Six probes PASS; browser fixture syntax failure before frames | f1340df9c6124dc537e9b4e7261c5e46feeb8fdd56d36050c15c079c064ec71a |
| first-extra-owned-receipt-v4.json | Closed33.293s; lease d70efdb033ec remaining0 | 316b709a3a364ee45e56d3dbe30edd233fd4eba2da2d9dac59a8e2b98e90eca1 |
| second-extra-check-receipt-v4.json |18frames, CSSzoom, keyboard PASS |877d3456ab007206ae245c4f254a1cc6c782a7748ab3d799a9595782e2fbf446 |
| second-extra-owned-receipt-v4.json | PASS17.639s, remaining0 | bf51c2f4c33de3facc09f2c1f1eddc922ca40c0f8e6deac7e19d0082e464795e |
| extra-check-receipt-v4.json | Corrected CDP capture PASS |3bfdd195699d45028dae379ee72d6587719046eaafeb757bba4063fc17e366fb |
| extra-owned-receipt-v4.json | PASS12.732s, remaining0 |32600df78218b16d0a0f7620b49d1ece2c689aadea17bd9b5ac3b57ddd1c0883 |

Each harness revision received narrow independent Senua clearance before execution. First-/second- harnesses, pin manifests and original clipped capture remain preserved. Final single-view pins: outer `b0e97078b8d8e292e16044c81c7e8ae3525a2006ef4a36fde92913767eff7e75`, inner `9b636416d00bc1763e3f3c95ced97a532626b1a1d3c025f6cf6ec05b869c7ebd`, extra manifest `6056d2e81bf021d88761fcf943507ee612bed926ce8019ee1d446d85a7994ca8`, browser `63613054a466df2a1d2baa2eff252ee1d992ca8f0c42bacf7b1f29f10c0faf47`.

## Preserved v1 failures and verified resolutions

V1 digest `398709ba6ed9ed587397e6a85afd5451099f95a18af3671db2c961ecae1cd9cd`, manifest `deb8dc159bdac63ce67d6d6ff46af4c7076b7c5c4ca7550c4ac65a15e5e04f2c`. Five independent probes then yielded 2 PASS/3 FAIL,0errors; no failed formal graph was duplicated. Original detailed report preserved as `v1-QAReport-preserved.md`, with pinned `independent_v1.py` and `independent-owned-receipt-v1.json`.

| Original finding | Severity | Final v4 status |
|---|---|---|
| Explicit translator/conflicting author accepted as author | Blocker | Resolved: independent four-variant probe rejects; formal typed-credit tests pass |
| Waiting candidate reported Completed with no retry worker | Major | Resolved: Paused, saved pending, explicit Start after cooldown; independent/backend/UI checks pass |
| Rejected destination entered approved denominator | Major | Resolved: independent collision reads0/0; destination/source bytes preserved; atomic queue/approval regressions pass |
| Sender v1 read0/1 after publication before required working cleanup | Major | Resolved: drain waits cleanup; final real-media receipt verifies1/1 |
| Provenance object/boolean UI mismatch, last-track Stop catch, pending-ready leak | Reported by Senua | Final formal frontend/media/filter regressions pass on corrected v4 |
| Cover wait halted pass; Unicode input halted other candidates | Source review findings | Backend continuation cases pass; cover-wait independently verified |

Fix verification is against the exact frozen v4 digest above, not an invented fix commit; Sully owns the subsequent release commit/version. V1/v2/v3 copies remain immutable evidence.

## Public sources, exclusions and cleanup

Private fake-response research, private actual media, synthetic rendered states, and real anonymous public fetches are separate evidence classes. Prior producer `public-network-evidence-v2.json` demonstrates actual fetched public pages/catalog under the earlier transport/parser; it cannot certify final-v4 live transport. Final-v4 anonymous evidence-only smoke is now recorded below; no cover approval, queue admission or real-library conversion is inferred.

No Z: scan/conversion/delete/purge, production catalog/library operation, Comics mutation, desktop focus, audio playback, paid connector, product edit, git operation, version bump or runtime replacement was performed. HTTP tests use ephemeral fixture servers. Unique source/evidence/receipts/screenshots remain held for release acceptance. Private fixture TemporaryDirectory outputs cleaned themselves within their audited contexts.

After GO acceptance, applied studio-cleanup to completed own v1 `independent-bytecode`. Original frozen plan SHA `825990EF4EF0874F5DA96766F3A33BB8470D1840E9C0B876CDE88040BDAA5B01`. One file passed individual Check and literal native removal. Reassessed the known remaining tree under a second frozen plan SHA `3C3C2D7791D3977881D35760955CB1871056797CF8B37DF5E01C181690D1B9AE`; two complete bounded files-only CheckBatch commands were reviewed in full and executed as exact literal native PowerShell calls, without loops, recursion, Force or cross-shell deletion. No host refusal occurred. Original-plan Verify confirms all116files absent,3,076,728 absent logical bytes,0 remaining file bytes. This is not measured filesystem free-space gain.29 nested empty planned directories remain; their required separate individual emptiness checks/removals were not completed. Per Jane's instruction to provide the stable report promptly rather than delay release for optional cache removal, those zero-file-byte directories are preserved. Exact remaining directory paths and actual absent file list are in `cleanup-independent-bytecode-final-verify.json`, SHA `82f0928bce1e88bfc51658fae1b6d8eb1f08654f455e5e22475bc93e090caef1`. No complete-root removal is claimed. Unique snapshots, receipts, screenshots, harnesses and newer/current release caches remain outside this reviewed cleanup scope; sources with protected names require individual review. At final handoff, read-only QA scratch inventory found724retained files totaling18,066,535logical bytes,0links, including owned-bytecode5,665,763bytes and independent-v4-bytecode3,131,169bytes. Active/unique evidence stays preserved.

**Pattern alerts:** none open. Individual confidence, lifecycle and admission bugs were fixed and regressed; no cross-tool or historical recurring pattern is established.

## Final-v4 anonymous public-source smoke

Producer Ender executed this separately authorized, Senua-cleared route once using the same65-file source digest/manifest and public_research.py SHA `2914db510aefaab63a9d30855ca5d8cdc01fbeb6eef96b13b3c978bfe16c27e9`. Futaba independently verified the two receipt hashes and read their source identity, outcomes and limits; Futaba did not repeat the network calls. Empty private cache;12 request attempts,11 fresh fetched responses; owned PASS18.700s, exit0, error empty, source_pin_drift=false. Synthetic title/author clues only,0 paid/API-credential calls,0 library/productionDB/queue operations.

Kabir work668099 is a Russian contained short story. Final transport fetched the FantLab work and AST page with adjacent author/title credit; metadata reasons are empty. Shimada work176045 is a Japanese contained short story; fetched FantLab and the Russian journal independently confirm the adjacent Russian credit, but the published English title, canonical title/author and author-folder bridge remain unverified. Kodansha/OUP pages fetched but had no matching author/work credit. Both catalog cover_url values are empty; recording completeness is unknown. Neither sample was admitted or approved: actual recording/source hashes and cover comparisons were not attempted. DuckDuckGo was unavailable with an explicit wait; no bypass occurred. This demonstrates live final-transport identity evidence and honest holds, not full audio eligibility.

Receipts under `scratch/automatic-processing-2026-10-10/`: `public-network-evidence-v4.json` SHA `3c931e5eb4ec3f509471be4da4f481094a225359212127102620fe0eafc3b769`; `public-network-owned-receipt-v4.json` SHA `a8be1bd0c30cd35ccd7b56c7d47ebe8de5be0861c8ec2110fd9fef3f21851269`. Exact URLs, fetched timestamps, response hashes and compact per-work evidence are retained in those receipts.
