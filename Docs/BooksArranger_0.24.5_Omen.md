# Books Arranger 0.24.5 — Omen routing and extraction

Date: 2026-11-03. Implementation slice: approved backlog cases 3 and 4 from the end of Team/Docs/Session_2026-11-02_Recap.md. Baseline tool HEAD: cfb64d34e84ab579e2216ef93ef60de2a22f4b22. No commit, version bump, build, full check, live library access or app interaction was performed by this slice.

The Final Conflict (Gordon McGill, Omen 3) now receives the existing shared-series routing proof and plans directly under Audiobooks Sorted/Omen. Omen 4 - Armageddon 2000 now fills Title=Armageddon 2000, Series=Omen, Number=4 and plans under the same shared folder. Author metadata and filename credit remain McGill Gordon under the existing naming policy. The manually moved existing book is not touched: this change produces facts for new acceptance, not receipt migration.

Root causes:

- public_research.attach_shared_routing had only the two exact Omen memberships confirmed on November 1. Book 3 lacked multi-author proof even though its series and position were already known.
- local_identity._unsure_title conservatively treats a word followed by digits as a possible numbered part. That rejected Armageddon 2000, preventing the series-title split and editor defaults.

Changes:

- local_identity.py centralizes the four exact user-confirmed Omen work/author/position memberships, with their decision dates. Its split exception requires the full writer credit, exact work title, series and position; it does not relax generic numbered/part-title detection. The same bounded confirmation prevents a redundant series-prefix question for the confirmed work.
- public_research.py extends the existing approval proof assembly from those memberships. It retains the existing stable-provider peer path, complete author-team handling, source/name proof binding and explicit destination precedence. Unknown authors/titles/positions and same-name-only series do not gain this authority.
- tests/test_omen_0245.py adds 13 private regressions. Eight exercise the real catalog/grouping/local identity/editor-default/approval/planner path with cache misses; five cover identity boundaries, all four members, stale proof rejection and immutable old manifest planning. Only cache lookup is replaced by an empty offline result. No synthetic audio is opened.

Consumers retain their API: PublicResearch.names_read supplies editor defaults; PublicResearch.approved returns the final attached facts; MergeService._approval_result calls approved and feeds both approval preview and approval execution. This slice tests their shared research/planning producer; it does not claim a running-app or queued-conversion test. The separate queue/lifecycle slice owns merge_service.py.

Validation:

- Targeted PASS: 79 loaded/executed, 0 failures, 0 errors, 0 skips: test_omen_0245 (13), test_series_identity_242 (21), test_shared_routing (19), test_organization (26).
- Three principal regressions were run against the baseline versions of only local_identity.py and public_research.py: all three failed for the reported reasons (author/Omen folder for book 3; blank series/number and unsplit title for book 4).
- Canonical audited bounded-check.mjs/runOwned and bounded-child.mjs were used unchanged, with a hard 600000 ms owned deadline and fully awaited 650000 ms outer callback. Private pinned source, installed Node, retained candidate Python and canonical read-only Koffi were hash checked before and after. The passing run exited 0; complete native zero, all 4 retained handles signaled, no force/timeout/overflow. Baseline failure was normal exit 1 with complete zero, not a runtime failure.
- Guards reject network/process attempts and live/media file opens. Fixture catalogs exist only beneath the private test root and are closed and removed by unittest cleanup.
- Two earlier attempts are retained honestly: first loaded no tests because a function-shaped Popen guard broke asyncio subclass import (fixed with a denying subclass); second ran 79 and found new fixture/expectation mistakes, not product failures (series tags require matching filename evidence; typed author spelling is retained; stale routing raises an actionable exception). Corrected assertions retain the intended protections. No production behavior was relaxed to satisfy them.
- git diff --check passed for the two changed production files.

Final source SHA256:

| File | SHA256 |
| --- | --- |
| local_identity.py | 605e43d4d1d1e87aaf064910c8432cd604cd3bad4c8957418f5c84044e3ba9d3 |
| public_research.py | b6fd01762037e6c6ee96f2583e82b96037edef9377a8f4008d8d2d1bb8daa88e |
| tests/test_omen_0245.py | 7fdd063958bc1281c7cec5451b13dd3792d19876495e41ba994d4ef285c8fad0 |

Durable targeted evidence: [summary](Evidence/v0.24.5-omen_2026-11-03/summary.json). Summary SHA256: 1bfb699654c52ee7559728a52e53513164daf3a8dd050df3bada5a5ad6898880. The folder retains each callback, owned result, pin manifest, runner and available test summary, including both resolved setup failures and the baseline failure. This is targeted metadata evidence, not release/native-app QA evidence.

Owned disposable snapshots were removed after the evidence above was saved: 427 files, 12,684,821 logical bytes, exact scratch target verified absent. See [cleanup record](Evidence/v0.24.5-omen_2026-11-03/cleanup.json). Retained runtime/helpers, other agents’ output, previous evidence and live data were untouched.
