# Books Arranger code review — v0.11.0

Date: 2026-10-11. Reviewer: Senua. Scope: normal windowless Open/Restart entrypoints, exact-owner handover, private shortcut publication and current-owner browser acknowledgement.

## Certified range and endpoint

Reviewed release baseline `d1d71c27125722836fcdf1f2c927464cdead923b` (v0.10.0) through committed Judy UX HEAD `c5a083ad496078e8cb69fac1ae0604a9a18c930f`, plus the exact frozen candidate-v6 payload at `scratch/app-launch-2026-10-11/candidate-v6`. This certificate applies to the pinned payload. Source VERSION remains 0.10.0; Sully owns the target 0.11.0 bump and release.

- Full 71-file source digest: `9c80a1e4da2c4d9298fe6e3e783261979913608a9488a11243e0e5c73a7f233b`.
- Raw manifest SHA256: `8da9d08d67322b79a209ee26b2cfb3cb83679363ec141529b96fb0945a53506d`.
- Digest method: SHA256 of sorted UTF-8 path + NUL + raw size + NUL + raw SHA256 + LF per manifest entry. All 71 raw size/hash pins were independently checked, including the final rehash after matching receipts.
- Eleven promotion paths: `app_launcher.py`, `install_app_entries.py`, `launch-web.pyw`, `restart-web.pyw`, `web_server.py`, `tests/test_app_launcher.py`, `tests/test_web.py`, `tests/test_connection.js`, `web/app.js`, `README.md`, `Docs/BooksArranger_Brief.md`. The twelfth changed path against the release baseline is the committed LaunchRestart UX document. The full baseline map and successive exact v1–v6 deltas account for the remaining unchanged 59 paths; line-ending differences were allowed when comparing text with Git.
- Declared staged frontend SHA256: `bd534cc224f742c2db3eb72c0ecbc05c409e1c42074b05a4a8873561d332db75`, kept outside the live serving path. Released canonical frontend SHA256: `c33d731696b400bcde97866ef9f93846e3a4b0ae86cf56d2a793a0afdda4244d`. The staged overlay and matching backend are part of the release payload.
- Committed UX document: `Docs/BooksArranger_LaunchRestart_UX_2026-10-11.md`, SHA256 `4a553de5653b980cf93206067fd9fbaf1ed4356dc34c53fc0964b3810c246eea`.

## Findings and disposition

Open findings: Critical 0; Major 0; Minor 1. No open safety-floor finding in this endpoint.

**Minor — inherited HTTP-error notice conflicts with the older copy exception.** In `web/app.js:58`, a failed status poll with an HTTP error preserves the specific backend error, then marks facts stale, disables submissions and displays the generic connection notice. The same behavior exists in the released v0.10.0 baseline. `Docs/BooksArranger_ConnectionInventory_UX_2026-10-09.md:11` explicitly excludes meaningful backend validation/authentication/server errors from that generic notice. The newer AutomaticProcessing UX at line 47 requires last-confirmed facts and disabled submissions after a failed poll and supplies updated connection copy, but does not explicitly override the HTTP exception. The conservative action gate is correct; the generic notice remains copy/doc drift. A later copy repair should distinguish unavailable status from transport loss while retaining the specific error and action gate. V6 tests align with the actual safety behavior and do not claim compliance with the older exception. Advisory; does not block release.

Closed findings in the frozen sequence:

- Safety-floor corrections, before any v1 test invocation: replace the potentially substituted/reparse-following writable startup lockfile with a fixed-name native mutex; hold DirectoryBoundary across shortcut COM writes/publication; and replace exists()/write_text instance-record creation with lexists refusal plus protected native CREATE_NEW. Unknown or changed entries are preserved. No unconditional name-based unlink remains in these new paths.
- Major, closed in v2: all work after BrowserServer construction, including instance-record writing, signal registration and readiness, is enclosed by deterministic server/inventory teardown. Receipt-write failure cannot strand the already-started retention worker.
- Major, closed in v3: `app_launcher.completed_records` now uses contextlib.closing for its read-only/query-only SQLite connection. The fixtures also close all three connections explicitly, preserving transaction commit/rollback with an inner connection context. The v2 Windows database cleanup failure was real connection-lifetime evidence, not an in-memory HTTP-error warning.
- Minor, closed in v2: native failure and entrypoint help use committed bounded Judy wording, without exposing raw Job/error codes or promising an unverified retry. Browser acknowledgement is tied to a complete current-owner response and actual Paused/Idle state.

## Nine review dimensions

| Dimension | Result and evidence |
| --- | --- |
| Security | No shell command, broker, scheduler, administrator route or tool-host persistent-launch bypass. Launcher requires ordinary Pythonw execution and a positively successful IsProcessInJob(false) result before owner actions. Local control requests use the fixed loopback endpoint with no proxy/redirect and the authenticated owner token. Native directory/file guards protect new records and shortcut publication; tokens are not written to the instance record. |
| Correctness and logic | Healthy Open reuses the exact verified owner. Restart captures its process handle/image/generation, verifies current owner and idle state, requests supported instance-bound shutdown, waits for that exact process exit and checks port/catalog availability before replacement. Wrong, busy, timed-out or unknown owners are refused. Normal startup/restart never starts automatic processing. Loaded version is cached at server construction; browser acknowledgement occurs once per owner after complete refresh and suppresses false Paused acknowledgement for Running/later-Paused state. |
| Crash and stability | Query failure cannot mean outside-Job eligibility. Main teardown covers post-construction record/readiness failures and absent standard streams. Native record and COM handles have explicit lifetimes; SQL connections close deterministically. Failed replacement opens no success page and adds retry help only after verified safe release. No generic exception path approves or starts a book. |
| Performance | One session-local startup mutex serializes launch decisions; no supervisor process, new daemon or dependency is introduced. Local HTTP reads/timeouts and exact-process exit waits are bounded. Existing controller, worker, provider budgets and retention loops remain unchanged. |
| State and data safety | Restart requires no active scan, research, encoder, cleanup or recovery operation, and rechecks under the server control lock. Completed-record comparison includes verified output, frozen metadata/manifest and current candidate/context identities. Protected instance records deny outside writes/deletes from creation; retirement reopens by handle and checks FileId128/hash/link/stream identity before exact disposal. Unknown changes are retained. New owner construction preserves the existing Paused contract. |
| Input handling | Entrypoints fix their isolated import path and reject unexpected arguments/runtime. Bounded records validate application, port, URL, PID and instance format. Owner image and authenticated health must agree. Private shortcut COM output is round-trip checked and published by the existing no-replace native publisher; unrelated existing entries are refused. Error surfaces use fixed safe text or bounded approved causes. |
| Maintainability | Small launch/shortcut modules reuse existing native primitives and the current service process. Open and Restart share explicit checks. Tests exercise failure ordering and native refusals independently of any live app. Exact v3–v6 repairs remained narrow; no helper framework or product rewrite was added. |
| Documentation/code drift | README, Brief and committed Judy entrypoint/restart copy match the new ordinary-user route, no console, paused continuation and truthful success/failure acknowledgements. The inherited HTTP-notice Minor above is retained openly. Neither old process exit cause nor ordinary-user launch success is inferred from fixture/native diagnostic results. |
| Build/release hygiene | The complete 71-file graph, declared frontend overlay, five runtime identities, fixed finite QA route and matching actual producer/receiver receipts identify the release input. VERSION awaits Sully. Source clearance does not substitute for the separate approved installer invocation or actual normal-user launch verification. |

## Validation and limits

Reviewed fixed route: 19 launcher/state/native-private-COM cases, 17 HTTP/windowless cases and one pure-Node connection/restart route. Three commands, exits [0,0,0]. No shortcut target or persistent app is executed. Native COM writes only private fixture folders; HTTP fixtures use ephemeral loopback servers and controlled/mock lifecycle operations. The Node route uses a VM and mocked requests, without a browser window.

Route pins: `manual-contract-v6.json` SHA256 `c10cec4dc2d0eaaa3012f86a1574db8d2acc75da39c1dfbc947578d9b80f165e`; `qa_checks_v6.py` SHA256 `b42f6a4e28b723cf89ab4aebd9d977fcf8a1a8ebd08631445829d0d5a28a6039`; `run_qa_v6_owned.py` SHA256 `8f507424c7ff621044dab052f64f8786300b04b3ac0002030ca57b264c060193`. Nonexecutable HANDOFF.txt: 1114 bytes, SHA256 `74dd87109ae089144dd4ff519890c13809f839f487a7f8c00c0ca85b1d5231ca`.

The unchanged reviewed native containment helper is pinned to `9939de63b3448e02f0c664d43242fe46e728a2f4f77ad21ed62f0bf98c7fad44`. The fixed hidden suspended child is assigned to its owned Windows Job before resume; all nested test descendants remain contained. One shared 600000 ms deadline covers identity checks and commands, with no launch after budget expiry, bounded 2 MiB retained per stream and exact child/descendant/drain closure. Single-read hashed manifest, all 71 sources and five executable runtime pins stay held through commands and final rehash. Pythonw is pinned as a shortcut target and is never executed by this QA route.

Actual producer v6: **PASS**, all 36 Python cases and the Node route. Manual elapsed 8.139 seconds; owned elapsed 8.185 seconds, exit 0 and empty error. Receipts at `scratch/app-launch-2026-10-11/producer-manual-v6-passed.json` SHA256 `fd76ba571f781e0226572135c28a564dcff3546978f89b7181988da5fe988990` (7892 bytes), and `producer-owned-v6-passed.json` SHA256 `7822341f26580f548811afe0dce4b340dd886a04e5469e1864592d0aab4a06c6` (8477 bytes).

Actual independent receiver v6: **PASS**, the identical 36 Python cases and Node route. Manual elapsed 5.766 seconds; owned elapsed 5.804 seconds, exit 0 and empty error. Receipts at `scratch/app-launch-qa-2026-10-11/receiver-manual-v6-passed.json` SHA256 `a3d62157dced95cf9f3a1682822dea5bb5ac2e695c29c02c48f7bc1f44e91a0b` (7892 bytes), and `receiver-owned-v6-passed.json` SHA256 `1791ab0373734cbb6f2ac5d6e0a8c4848176db2674a784d2f7afa113a6eef1e5` (8477 bytes). Reviewer independently hash-verified both pairs and matched tool/versions/HEAD/dirty/source/manifest/commands, test-case names/results, Node output and complete receipt line. All streams are untruncated. The new Paused/Idle/Running/later-Paused/dedup acknowledgement assertions were reached and passed.

Identical actual producer/receiver handoff line:

```text
BOOKS_MANUAL_QA|tool=Books Arranger|target=0.11.0|source=0.10.0|HEAD=c5a083ad496078e8cb69fac1ae0604a9a18c930f|dirty=true|source_digest=9c80a1e4da2c4d9298fe6e3e783261979913608a9488a11243e0e5c73a7f233b|manifest_sha256=8da9d08d67322b79a209ee26b2cfb3cb83679363ec141529b96fb0945a53506d|python=pass|node=pass|package=n/a(manual nonpackage contract)
```

Qualified earlier evidence remains preserved under the sender scratch folder:

| Candidate | Actual result | Manual / owned SHA256 |
| --- | --- | --- |
| v1 | Frozen, unexecuted; native guard findings repaired before tests. | No PASS claimed. |
| v2 | 18/19 launcher PASS, one SQLite/Windows32 cleanup ERROR; web and Node unrun. | `25f2185f5bde5799a1a5408c7af8b9fe29323ed473ec431ffc01e1193b70c650` / `fb816f5800f819661be4ce9dd4a3ec275cd831ebbf532e3262233ddca832f9e4` |
| v3 | 19/19 launcher PASS; web 16/17 PASS plus fake-health Mock/dict TypeError before intended injected OSError; Node unrun. V4 sets realistic fake health, preserving every assertion. | `f0d5ba7a17c9841b7e81d147fe62b3c961f342f839f1b01e8a448391db18a86e` / `5d01c7f109fc3b45118fc6da7aed0725a7cb11801b843e77059d85660960f245` |
| v4 | All 36 Python PASS; first stale scan-only notice literal failed in Node, so restart assertions were not reached. V5 strictly aligns the released automatic wording. | `fc723963cd6cccecc0541e26a8e52620808b9842fc1f6dbe28f7a9490a14ec73` / `bc7dd866086ddddfb4256d5ea4db3dc8d39d8639679ae30e56b4d3b5a9ede99a` |
| v5 | All 36 Python PASS; old HTTP-notice visibility assertion failed before later restart cases. V6 retains the backend error and tests stale/disabled availability, blocked synthetic shutdown, then successful poll before unchanged intentional-stop assertions. Production unchanged. | `6ac2ca07815814029e7a7a6dd430b549d0f38b80f9a1d7c5b2326854a2859350` / `1197c197f948f2dd64d547e19e9f25ba55b234f1fc09ea6411357f27cbaf6ec4` |

Runtime boundary evidence remains distinct: `scratch/app-launch-2026-10-11/job-boundary-probe-v1.json`, SHA256 `ff81fee5589f7a65c7ca093df21f033125d858d9e7546c86da26c74b080db388`, records a never-resumed suspended no-op with successful IsProcessInJob queries and actual member=true on both exact/reopened handles. Only that owned suspended child was terminated and awaited. This proves the tool-host route is ineligible for persistent app launch, and does not explain any earlier service exit. The implementation requires an ordinary eligible user-launched Pythonw process; no alternate broker/bypass is approved.

No actual normal user click, live Start-menu installation, persistent runtime startup/restart, real browser rendering, queue/Start/library/provider operation or Comics change occurred in this review/QA route. Real shortcut publication and normal-user startup remain separate scoped post-release actions. Confidence, fetched evidence, language, source membership/order, covers, collisions, conversion verification, original cleanup and 24-hour recovery implementations are unchanged. No Senua disposable output was created; unique immutable source and failed/actual proof remain preserved.

**Verdict:** RELEASE CLEAR
