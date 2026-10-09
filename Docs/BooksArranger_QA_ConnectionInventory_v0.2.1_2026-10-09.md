# Books Arranger — connection and inventory patch QA — v0.2.1

Date: 2026-10-09. **Verdict:** GO

Scope: frontend-only correction on the published v0.2.0 baseline; anthology feature remains excluded. **10/10 targeted checks passed:** supplied connection regression 1/1, existing review-fingerprint regression 1/1, independent stale-library failure regression 1/1, rendered browser checks 7/7. A stale-library failure defect was found in the initial patch and independently verified fixed. No backend/scanner/catalog schema changes or broad backend retesting.

## Frozen candidate

Committed UX spec: `Docs/BooksArranger_ConnectionInventory_UX_2026-10-09.md`, commit `40ef3fa`, SHA-256 `6c3dff22261bbdbf9103878ef0469b015e80f26effb393a80aacbf3f327d9299`.

Futaba copied Ender's explicitly frozen candidate into gitignored `scratch/connection-qa-2026-10-09/candidate`. Initial failed patch is retained separately as `candidate-initial`. Revised candidate was tested only after its new pin arrived; all six changed-file hashes matched the revised manifest on final read-back.

| Changed file | Accepted SHA-256 |
| --- | --- |
| web/index.html | 3881fcba98282e08d787a6a030fac77571ffae7b2359721cb8c4e0ff6d0931de |
| web/app.js | ae27649da135fe58fd522fff984739194ab5935a9e507f59d5bae8fca653fd8c |
| web/style.css | 481d3e1f6b2e17025cda95c5c1a26087b697aadffcfa33c3cd238204edcc0265 |
| tests/test_connection.js | f1dcac973363bfc49cbc5ec656067e0a91c299a5d4584aa692b825751aed3930 |
| README.md | 8e27e1213cfcc37ff6abd5de87f9969f5e63da131ce191e4724fc7800d44fc5b |
| Docs/BooksArranger_Brief.md | 5aa7b20c2b3ad40327ede09895e35795262a208507d4546c305615580bfd6c3b |

Unchanged production-baseline pins independently checked: web_server.py `69d7ece4d7ad996d28b00397dbacc4341e4f77df61a20ef252d00bc9c1990cb0`; scanner.py `0c6a70b380c7c8e69d06a344bec53daa99383475b149782f085acc9968721916`; metadata.py `9ae8504127c65fd45ffbc3ac0b4843cb4417ce19e10c311ddf1429d4011a0a02`; app.py `0dcf5a40d0655274d7b2462fa9ab5a79b5cafbbfa4f7d3e03cefeeb49e664522`.

Fixture display version was 0.2.0 while the intended patch marker is 0.2.1; Sully owns the marker-only bump. This GO authorizes no additional runtime code change, server restart or user scan mutation.

## Finding and independent regression

**BA-CONN-01 — Major — fixed and independently verified.** Initial JS pin `fc741204a1dac7670098fc5e2f71e0db455507426e9ec4a4c98aa9bad866c3f9` incorrectly displayed connection loss on a healthy newly selected library when an older request failed.

Repro: hold a pending Audiobooks poll, switch to Ebooks and complete that library's refresh, then reject the old Audiobooks request. The initial `poll()` catch applied `refreshFailed()` to the current library and showed the interrupted-connection notice. Supplied tests covered stale success but did not initially cover stale failure. Futaba's actual-script VM regression in `scratch/connection-qa-2026-10-09/stale_failure.cjs` observed the failure and reported it immediately; no QA implementation fix was made.

Ender revised refresh sequence checks. The unchanged independent repro passes on accepted JS pin `ae27649d...`, and its positive control still detects a failure for the selected library. Revised supplied connection cases and the existing unsaved-review source-fingerprint regression also pass. Initial failed and revised snapshots are retained; fix commit correspondence belongs to Sully's subsequent publication.

## Targeted checks

Actual-script VM checks: `node tests/test_connection.js`, `node tests/test_browser.js`, and `node scratch/connection-qa-2026-10-09/stale_failure.cjs`. They cover repeated transport failure without duplicate announcements, complete recovery, incomplete state/inventory refresh, superseded success/failure, retained action/read-error feedback, preserved unsaved values and original review fingerprint, old-HTML fallback, and intentional shutdown without reconnecting.

Rendered browser checks ran through the existing guarded `scripts/qa/headless-browser.mjs` launcher, a fresh disposable profile, and bundled Playwright. No native desktop input, user's browser profile, installs, generic guard changes or account access. Driver has a 600000ms total deadline and 600-second lease. The isolated fixture backend listened only on **127.0.0.1:5211**, using a separate scratch catalog and four generated files. **No browser request or control targeted the user's port 5210.**

Rendered checks **7/7**:

1. Status shows **Files cataloged 4 / Files checked 4 / Files reused 0 / Pending tasks 0 / Read errors 1**. Page label is **Files 1–4 · 100 per page**, with explicit source-file/chapter/companion helper text.
2. A deliberately failed fixture metadata read remains a visible **Read error** with its detail; it is not mislabeled as connection loss.
3. Aborted polling shows the separate uncertain connection notice and **Last received** status while retaining all four rows and an existing action validation error.
4. A state response followed by an aborted required inventory request leaves the notice visible. A controlled fixture state increments Checked to force that inventory refresh; this simulated increment is not a performance measurement or a claim of additional source processing.
5. Complete state/inventory recovery clears only the connection notice. Read errors, action validation feedback, and **Unsaved canonical review** remain. The actual 700px viewport has no page-wide horizontal overflow.
6. Both **new JS / old HTML** and **old JS / new HTML** combinations initialize and render four rows without page errors, supporting compatible static-file promotion. New JS inserts its missing helper/notice into old HTML. This does not claim that an already loaded old script gains the new behavior without a page reload.
7. Intentional **fixture** Stop server retains shutdown UI without displaying reconnect failure. The fixture process exits naturally.

## Actual visual evidence

`scratch/connection-qa-2026-10-09/screenshots/interrupted-wide.png` and `recovered-narrow.png` are actual rendered 1440px/700px captures. Futaba viewed both. Jane independently viewed and accepted these captures: separate notice visible during failure and absent after complete recovery; **Read errors 1**, action validation message and unsaved form title retained; explicit file/task units readable. Narrow inventory uses its existing internal table scrolling. No guarantee is inferred for every viewport or data combination.

## Runtime ownership, integrity and disk hygiene

- Fixture service PID **37684**, instance `acb66d70277b535554a8e812cb4ba3b6`, port **5211**, execution session **39928**. It exited through fixture Stop server with **code 0**. Subsequent exclusive bind proved **5211 released**.
- Owned guarded browser lease **d4cbea0f80a1** ended normally with **remaining 0**.
- Full SHA-256 verification: **4/4 source fixtures unchanged**. The four disposable generated sources were removed afterward under verified literal scratch paths; source hash manifest, snapshots, scratch catalog, screenshots and reports were preserved as evidence.
- No live user server/catalog file was edited, stopped or restarted; no real library source was written, moved, converted, renamed or deleted. QA makes no new live-server availability claim from these isolated checks.

No unresolved Blocker/Major defect in the accepted patch. Existing unrelated prototype limitations remain unchanged. Pattern alerts: none new; previously dispositioned tooltip-polish alert remains deferred to Daily Use.

## Published correspondence

Published tag v0.2.1 resolves to `f7b185ce416da1aa014df929a4da95773e5437e9`. A bounded read-only guarded browser visit showed **v0.2.1**, the new file/task labels and helper, and exact served JS/CSS hashes matching the accepted pins above. The original user process **PID 3100**, instance **1171e36d693625c4667d9a276e28826c**, and **generation 1** remained active: **9431 files checked / 53 pending tasks / 1 read error** at observation. This records a source-read error counter, not a connection failure.

Screenshot: `scratch/connection-qa-2026-10-09/screenshots/published-v0.2.1.png`; Jane independently viewed and accepted the displayed version/count labels. Only GET requests were issued; no user control, tab reload, server restart or scan mutation occurred. Temporary browser lease **9d0c3065fe3c** closed with **remaining 0**; the user server remained untouched. No additional checks are required for this correspondence append.
