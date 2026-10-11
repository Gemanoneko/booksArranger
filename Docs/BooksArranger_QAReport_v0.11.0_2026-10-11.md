# Books Arranger QA — v0.11.0 — 2026-10-11

**Verdict:** GO for the pinned candidate-v6 release. **Findings:** 0 Blocker / 0 Major / 1 inherited Minor (accepted). Futaba independently ran the identical producer/receiver manual contract once after actual producer PASS and Senua's exact finite-route CLEAR. All 36 Python cases and the one pure-Node route passed. This certifies private launcher/HTTP/connection fixtures; normal user-click launch and restart remain unexecuted acceptance work.

## Exact build and method

| Identity | Value |
|---|---|
| Tool / target / source version | Books Arranger / 0.11.0 / 0.10.0 |
| Source HEAD / dirty | c5a083ad496078e8cb69fac1ae0604a9a18c930f / true |
| Baseline | d1d71c27125722836fcdf1f2c927464cdead923b |
| Snapshot | scratch/app-launch-2026-10-11/candidate-v6 |
| Receiver | scratch/app-launch-qa-2026-10-11/candidate-run-v6 |
| Complete 71-file source digest | 9c80a1e4da2c4d9298fe6e3e783261979913608a9488a11243e0e5c73a7f233b |
| Raw manifest SHA-256 | 8da9d08d67322b79a209ee26b2cfb3cb83679363ec141529b96fb0945a53506d |
| Manual contract SHA-256 | c10cec4dc2d0eaaa3012f86a1574db8d2acc75da39c1dfbc947578d9b80f165e |
| Inner / outer SHA-256 | b42f6a4e28b723cf89ab4aebd9d977fcf8a1a8ebd08631445829d0d5a28a6039 / 8f507424c7ff621044dab052f64f8786300b04b3ac0002030ca57b264c060193 |
| Nonexecutable handoff | HANDOFF.txt, 1114 bytes, 74dd87109ae089144dd4ff519890c13809f839f487a7f8c00c0ca85b1d5231ca |
| Preparation receipt SHA-256 | ac107dce882c4cc0792f0bb25614252d6f3b828336e4dccd91fc2232a6ad2d76 |

Source digest is SHA-256 of sorted UTF-8 rows path+NUL+size+NUL+sha256+LF. QA copied and rehashed 71 source files plus the manifest and exact descriptor, with no links. The separately reviewed non-package contract declares three fixed commands: unittest discovery for test_app_launcher.py and test_web.py, then tests/test_connection.js using the pinned Node executable. Package checks are inapplicable; none were fabricated.

The audited hidden owned route has one shared 600000 ms limit, suspended-child ownership before release, bounded streams and awaited descendant/stream closure. The outer executed through hidden Node/Git Bash with its 610000 ms enclosing timeout. No timeout occurred. Native bootstrap and all five runtime identities (Python, Pythonw, Node, FFmpeg and FFprobe) matched before and after. Pythonw was a shortcut target, never executed. All 71 source hashes, raw manifest and harness pins were independently rechecked unchanged afterward.

## Actual matching results

| Side | Python | Node | Manual / owned seconds | Closure |
|---|---:|---:|---:|---|
| Ender producer | 36 PASS | 1 PASS | 8.139 / 8.185 | exit 0, error empty, descendants/drains closed |
| Futaba receiver | 36 PASS | 1 PASS | 5.766 / 5.804 | exit 0, error empty, descendants/drains closed |

Receiver's 19 launcher cases completed in 0.213 s and 17 HTTP/windowless cases in 2.682 s. The Node route emitted its actual PASS for polling failure/recovery, stale data, error preservation, once-per-owner Paused/Idle notice, Running suppression and protected shutdown. All three command exits were 0; receiver stderr contained normal unittest output and no warnings. No extra graph or broad probes ran.

Both actual receipts contain this identical line, independently obtained from their owned outputs:

```text
BOOKS_MANUAL_QA|tool=Books Arranger|target=0.11.0|source=0.10.0|HEAD=c5a083ad496078e8cb69fac1ae0604a9a18c930f|dirty=true|source_digest=9c80a1e4da2c4d9298fe6e3e783261979913608a9488a11243e0e5c73a7f233b|manifest_sha256=8da9d08d67322b79a209ee26b2cfb3cb83679363ec141529b96fb0945a53506d|python=pass|node=pass|package=n/a(manual nonpackage contract)
```

Unique proof is preserved under the receiver scratch root:

| Receipt | SHA-256 |
|---|---|
| producer-manual-v6-passed.json | fd76ba571f781e0226572135c28a564dcff3546978f89b7181988da5fe988990 |
| producer-owned-v6-passed.json | 7822341f26580f548811afe0dce4b340dd886a04e5469e1864592d0aab4a06c6 |
| receiver-manual-v6-passed.json | a3d62157dced95cf9f3a1682822dea5bb5ac2e695c29c02c48f7bc1f44e91a0b |
| receiver-owned-v6-passed.json | 1791ab0373734cbb6f2ac5d6e0a8c4848176db2674a784d2f7afa113a6eef1e5 |

## Behavioral coverage and limits

The launcher fixtures verify healthy-owner reuse without restart/Start; exact owner and Job-membership refusal without touching an existing process; active-work rejection; checkpoint/shutdown/exact exit before replacement bind/readiness; timeout without duplicate replacement; failed startup without a success page; completed-record identity protection; dangling/hardlinked records preserved; native mutex contention/reacquisition; protected record readers and exact retirement; and isolated thin pyw import paths. Native Windows COM ShellLink files were actually saved/reopened in private fixture folders; unrelated entries were refused and their bytes preserved. No shortcut was executed or installed in the user's Start menu.

HTTP fixtures verify strict port/catalog ownership, session/Host/origin gates, loaded-version identity, unavailable source-file routes, payload/root limits, incremental inventory/review fingerprints, scan stop/resume admission, exact restart guards and controlled shutdown. Response-disconnect regressions remain passing. Windowless startup fixtures provide no standard streams and verify readiness precedes serving, while an injected receipt-write failure closes the constructed fake server without readiness or serving.

Pure-Node VM checks exercise the existing UI logic, including actual current-owner refresh before success acknowledgement, one Paused/Idle restart notice per owner, Running/later-Paused suppression, stale-data mutation blocking, specific error preservation and intentional shutdown without reconnect. These are executable UI logic fixtures, not rendered visual frames or a real browser launch.

The tool-host diagnostic confirms that a child remained in a Job despite a breakaway request; this route refuses it. QA did not launch the real app, run a real shortcut, open/focus the desktop, install Start-menu entries, scan/convert/purge the library, use provider requests or alter the runtime. Normal user-launched windowless Open/Restart and native message appearance require user acceptance after release. The graph does not re-execute audiobook conversion or 24-hour recovery: production conversion/retention changes are absent from this endpoint; prior release evidence remains the baseline.

## Findings and retained failures

- **Minor — inherited HTTP-error notice copy/doc drift; accepted, unresolved.** A failed authenticated status poll preserves its specific error but also makes the generic connection notice visible. Status remains unverified, last received data stays stale, and mutations remain disabled. V6 asserts this existing behavior explicitly; it does not fix or hide the copy discrepancy. This is not a newly introduced launcher fault.
- **Resolved — SQLite connection lifetime.** V2 producer passed 18/19 launcher cases but errored while cleaning a private database because with sqlite3.connect does not close the connection. V3 uses contextlib.closing for production read-only completed-record access and fixture connections, retaining transaction semantics. Final receiver verifies the completed-record fixture and cleanup pass.
- V1 was frozen and prepared but unexecuted while native ownership/startup guards were corrected. V2 actual producer failed as above; web/Node were unrun. V3 launcher 19/19 passed, web 16/17 passed with a fake-health Mock dictionary-union error before the intended OSError; Node was unrun. V4 Python 36/36 passed, then the first Node old-copy expectation failed. V5 Python 36/36 passed, then an old hidden-notice expectation failed before restart assertions. V4–V6 corrected only these private fixtures, retained strict assertions and left production unchanged. No receiver graph ran against those failed endpoints.

All prior immutable copies and independently hashed producer failure receipts remain retained. V2 manual/owned hashes: 25f2185f5bde5799a1a5408c7af8b9fe29323ed473ec431ffc01e1193b70c650 / fb816f5800f819661be4ce9dd4a3ec275cd831ebbf532e3262233ddca832f9e4. V3: f0d5ba7a17c9841b7e81d147fe62b3c961f342f839f1b01e8a448391db18a86e / 5d01c7f109fc3b45118fc6da7aed0725a7cb11801b843e77059d85660960f245. V4: fc723963cd6cccecc0541e26a8e52620808b9842fc1f6dbe28f7a9490a14ec73 / bc7dd866086ddddfb4256d5ea4db3dc8d39d8639679ae30e56b4d3b5a9ede99a. V5: 6ac2ca07815814029e7a7a6dd430b549d0f38b80f9a1d7c5b2326854a2859350 / 1197c197f948f2dd64d547e19e9f25ba55b234f1fc09ea6411357f27cbaf6ec4.

**Pattern alert — fixture drift across endpoints. Disposition:** current fixture corrections verified by final v6 PASS; broader fixture maintenance deferred outside this release. Jane was notified separately. No extra framework or tests were added by QA. Historical automatic-pass unexpected failure cause remains unknown; this launcher pass makes no claim to resolve it.

## Handoff and hygiene

Committed Judy launch/restart specification c5a083ad496078e8cb69fac1ae0604a9a18c930f was verified at SHA-256 4a553de5653b980cf93206067fd9fbaf1ed4356dc34c53fc0964b3810c246eea. Senua's final source verdict is separate; this report records Futaba's behavior GO on candidate-v6.

All owned receiver jobs and drains are closed. Successful private test temporary fixtures cleaned themselves; failed-endpoint leftovers, immutable sources, native bootstrap and unique failure/acceptance evidence remain preserved. Shared task bytecode is retained while producer/release consumers are checked. Any later verified disposable cleanup is recorded separately under studio-cleanup; this stable report will not be rewritten for routine hygiene.
