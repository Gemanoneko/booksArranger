# Code Review — Books Arranger v0.22.3

## Final re-review at 943998e (2026-10-28)

Release source commit: 943998edbd00d8676b00d95a3311e26b7c79ae36
Release artifact manifest SHA256: 7b8468a5e8608d4ecd910ac2c20c7f4b899ea60cfa07fefba40819ac17c9b4d9

This closes the corrective range `3545d178d6315cff8c8acb383a590081d7627dd1..943998edbd00d8676b00d95a3311e26b7c79ae36`; combined with pass 9 below, reviewed coverage is continuous from v0.22.2. The final clean candidate is `cand-0223j` at 943998e. Installer `dist/builds/7645da69-bb47-497e-8754-ab7f90d70995/Books-Arranger-Setup-0.22.3.exe`: **174244357 bytes**, SHA256 `9babdb6d9cf00af0c283f12fdd978a04b13a6fc8d8fcf3b8b5c347ca01dcb53d`. I independently hashed the installer, artifact manifest and frozen smoke inputs.

### Corrective findings closed

| Finding | Final result and evidence |
|---|---|
| M11 | **Fixed.** `_answer_then_ask_series` saves the proposal/no-author answer, then resets **only that book's** cached automatic row to Pending through `book_restart.reset_automatic`. The production `Held/until_change` skip cannot retain the old author question; siblings remain held. The three regressions now begin with an actual automatic run and assert its `until_change` positive control before approving as shown. |
| M13 | **Fixed.** `approve_automatic` calls `resume(recheck=False)` only for non-human automatic admission (`approved_by is None`). Human Approve queues without starting either queue. The unrelated-pending-job regression asserts no resume call, both jobs pending and sources intact, then an explicit Start completes both. The sole production non-human caller is the authorized automatic run. |
| M15 | **Fixed.** English-author checking no longer depends on an unrelated entered title/author flag. Title-only, series/number-only and Cyrillic-author entries still ask for English; an actual English answer is the positive control. A fetched English title cannot replace an explicit entered title. Approve/preview suppress live author lookup, retaining the question without planning a Cyrillic destination. |
| Preview hold | **Fixed in the final delta.** `_approval_destination` accepts a missing review and returns an empty destination with the existing hold reason, instead of `dict(None)`. `routing_preview` already guards missing reviews; `approved()` still provides its separate approval metadata for the row. The new real attention-list test proves no destination, no lookup, refused blank Approve, then an English submission queued until Start and filed correctly. |
| m11 | **Fixed.** The stale queued-job/global-alias/first-book-releases-set comments now describe per-book approval and completed-only Sorted confirmation. |

I read the tiny product diff, test retargets and both ends of the names/approval callers. No final full suite or broad scan was repeated by this reviewer. Tests which previously relied on implicit conversion now explicitly call Start; the shared `wait()` remains a wait and never starts work. Assertions and time limits remain in force.

Futaba's independent final packaged-engine pass reports **10/10 intended flows passing**, including all three actual Held-cache answers, a paused queue with two jobs, the entered-field English-author controls and Russian/English author-order controls. Its **11 outputs decode with zero errors**. This corroborates the construction review; her behavior verdict remains separate.

Actual final entry: **1920/1920 Python, 143/143 Node, zero failures/errors/skips**, 511.2 s owned wall time, slowest worker **500.6/540 s**, native owned closure zero. The real receipt in `q23j/logs/ender-entry.log` binds 943998e, dirty N, source `bdf838e278b8152ab6131ef30068904f6b76decc20012f74f83a699d1741e23f`, harness `c1ca100354d22501175d0edf2947685c41ceec13cd6331bb1859b05f12e75960`, runtime `e3925548d1915af5e8582c47b627025256b7f565adb3a989012d662c818efb70` and checker `a448c08c150e63019cfd6e49ceed5ec5b8652a97078abde197e7a50882b759cf`, with `check pass` and entry exit 0. The earlier failed entries remain historical failures; none is reclassified as a pass.

### Nine dimensions (corrective delta)

Security **Pass**: no new executable input, shell-out, Electron/IPC or credential surface. Correctness & logic **Pass**: the three reproduced obligations are corrected and represented by production-flow regressions. Crash/stability **Pass**: the missing-review preview now uses a bounded fallback. Performance **Concerns**: broader m9 headroom work remains deferred; final slowest worker uses 92.7% of its unchanged deadline. State/data safety **Pass**: per-book Held invalidation and human no-resume retain unrelated state; existing verified-publication-before-source-removal checks remain. Input handling **Pass**: required English answers cannot be replaced by unrelated name edits or a guessed destination. Maintainability **Pass**: no new orchestration layer; existing reset/admission boundaries are reused. Doc/code drift **Pass**: m11 corrected. Build/release hygiene **Pass for construction and artifact identity**: final entry and exact built payload are bound; Futaba's actual hidden packaged launch/Quit evidence is a separate release prerequisite.

### Hidden packaged route approval

Current approved route: exact helper SHA256 `eff639068f219b3a7cc0ef95cd95df72b4b469c75d2f4cade81d076b2ea48d6e` and fresh plan `q23j/hidden-smoke-plan-943998e-export.json`, SHA256 `41223690a874342e8637eed12d6051a6771b080e6adbe0ce0cb491b1824bcb6c`. Independent read-only verification matched final source/manifest/installer, passing context SHA256 `05b87ad3c5ebbf8efbc9dcd5ffd094674f1aa7fe51602a8503814bcd93f3b270`, Node SHA256 `1c63f1417e2e26d83ca9a9ec1d548524ab1305bc7209d90ebca56257ff0d84ed`, **all five canonical owner files and all 92 ownership/Koffi files**, with no extra files or links. The exact private work directory and generic result-output path did not yet exist. Only the outer helper invocation is approved; its worker must be created by canonical ownership, never invoked directly.

The route uses a pinned private payload, profile, roots, environment and distinct ports. Read-only Win32 image matching covers private-payload window owners, with an existing-window PID positive control and fail-closed image reads. Preexisting tray key IDs/raw values must remain unchanged; cleanup can remove only new IDs matching the copied EXE after it exits. Unknown image/shared-key changes, pin drift, timeouts or unproved native closure must stop and be reported, never weakened. Senua did **not** execute the app; Futaba owns the single native smoke and behavior verdict.

Futaba's first exact invocation (helper `8187c310...`, plan `8523a319...`) failed closed **before app launch** at the tray snapshot's registry query (archived `q23j/logs/hidden-package-smoke-result-v1-registry-preflight.json`: code 1, owned closure zero, no force/owner timeout, 8.2 s, `closedByQuit:false`). This is not passing packaged-smoke evidence. Ender's read-only diagnosis found complete `reg query /s` exceeded its 5000 ms child limit after 491298 stdout bytes; the key existed and was readable. A full same-subtree `reg export` completed in 49 ms, 1755088 UTF-16LE bytes, root plus 160 IDs. The replacement keeps **5000 ms / 16 MiB**, compares complete raw sections including types/multiline/escapes and retains the preexisting-ID/value and new-exact-EXE-only cleanup guards. The instrumented parser checks passed 17 assertions; both diagnostic/parser owned receipts are successful with native zero. Raw registry exports remain private disposable evidence and must never be committed. I reviewed the actual source delta and independently rebound the new plan and unchanged artifact/owner pins before authorizing Futaba's fresh attempt. Publication still requires the actual packaged-smoke result below.

The replacement's actual app flow completed: hidden renderer ready, displayed and engine versions **0.22.3**, window-close hid while the engine stayed alive, normal `--quit` with `closedByQuit:true`, unchanged payload, no detected intrusion and native owned closure zero. Its **original overall result was a failure** (`q23j/logs/hidden-package-smoke-result.json`, code 1, 6.6 s), because the final tray-state comparison detected a preexisting root change and failed closed. That historical result remains a failure; the separate cleanup below resolves its remaining obligation without another app launch.

Read-only classification proved the sole root delta was `UIOrderList` REG_BINARY **1856 → 1864 bytes**: exactly one aligned 8-byte reference for the new own leaf `8953604142261800089`. All preexisting child IDs/raw values were unchanged; the new leaf's `ExecutablePath` matched the unique pinned private EXE. A proposed atomic root-plus-leaf transaction was **not used**: its read-only availability probe failed at the first transacted open with **6801 / ERROR_RM_NOT_ACTIVE**, rolled back and closed successfully, reached no write API and had native closure zero. No transaction-manager repair, alternate namespace retry, root rewrite or registry import was attempted.

Sergei explicitly approved the bounded alternative: **"Yes—leave OS history and finish release"**, authorizing deletion of only the own temporary leaf while leaving its single numeric 8-byte Windows history reference, with no name/path record. Reviewed leaf helper SHA256 `3327b6cae94f64af3058d764ed57e30739b242c85855409c5371bac9a46e5e38` has no root/value write API: the root opens KEY_READ only, the exact leaf opens KEY_READ|DELETE, current private EXE/no-subkeys ownership is checked through that **same handle**, and only that handle is passed to `NtDeleteKey`. This handle-based API is documented for user mode by [Microsoft](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwdeletekey); it avoids reopening a different key generation by path. Shared root data is never rewritten. The authorized plan SHA256 `44b4fe04b234b63d18192dfe46c8fdcdf95af2a7f9dfb48b149cc5b51a9176d8` changed only the three approved authorization fields from the reviewed fresh default-deny plan; all source/proof/owner pins and unused nonce/output targets were reverified before Futaba's single outer invocation.

**Actual authorized cleanup passed** (`q23j/logs/owned-tray-leaf-delete.json`): exit 0, `ok:true`, `closed:true`, native zero; same-handle exact-EXE/no-subkeys checks passed, own leaf deleted and ordinary-read absence confirmed. `rootWritten:false`, `uiOrderWritten:false`, current UIOrderList and every other current/preexisting record unchanged. Only the explicitly accepted numeric history reference remains. This successful separate owned cleanup plus the actual hidden normal-Quit/payload-unchanged evidence completes the packaged launch/Quit prerequisite. No app relaunch, product rebuild or guard weakening was used. Raw registry exports remain private disposable evidence; the durable record contains only the executed helper identities, compact proof and this precise user exception.

Durable compact evidence: `Docs/BooksArranger_NativeSmokeProvenance_v0.22.3_2026-10-28.json`, SHA256 `6e30aeb731bc8b3316fba3393b6100fc80f516ddee1cfc5aff21012aa05d6279`, alongside Ender's exact executed-helper copies. It records the original composite guard failure and separate authorized cleanup success without private registry values; disposable `q23j` paths above are historical reproduction/evidence locations, not files to retain after release.

### Final construction verdict

**Critical: 0. Open Major: 0.** All 15 tracked Major findings are fixed or superseded as recorded across the continuous review. The 23 tracked Minor findings retain their earlier dispositions, with m11 closed again; m23, broader m9, Judy's notes and other deferred minors remain backlog work. No new Critical/Major/Minor in the corrective range. Safety floor intact. The final source/artifact construction is clear and the packaged launch/Quit prerequisite is complete as documented above; Futaba's final behavior GO remains its independent report.

**Verdict:** RELEASE CLEAR

## Previous re-review at 3545d17 (2026-10-28; superseded)

Historical source commit: 3545d178d6315cff8c8acb383a590081d7627dd1
Historical artifact manifest SHA256: 43dfc69c2358c4840ec912c36c76dbf9c0c273091613dad073263eaccb9e1aa4

Reviewed range: `cf166bfa7cab8c1381a14c82b7409fbc75b91139..3545d178d6315cff8c8acb383a590081d7627dd1` (five commits, including the report-only d0f7121). Candidate: `C:/Antigravity Projects/Worktrees/Books Arranger/cand-0223j`, clean. Four product Python modules, the two runner files, four Python test modules and two docs changed; the range also adds the previous reports. Full diff: 14 files, +1806 / -223. No desktop or page code changed. The installer is build `b631e687-8fc0-46be-aad0-3b8daa5813e1`, SHA256 `6019c49ac6b4357325cff7ab3f17e31e9c481233d4d20011d1045653193e7c6d` (identity supplied by Ender; no shell launch in this pass).

### Method and evidence

Lean delta review: read the changed code and both ends of its approval/names/rule paths. No full suite repeated. Ender's actual passing entry is `q23j/logs/ender-entry.log`: 1,916/1,916 Python and 143/143 Node cases, no failures/errors/skips, 527.5 s owned wall time, slowest worker 516.8/540 s, owned closure zero. One earlier identical-source entry failed the existing media case's 30 s wait; that case then passed 5/5 isolated in 15.20–16.66 s and the official retry passed. The cause of the original wait is unproven; this review does not assert CPU contention caused it.

Two finding-specific probes used a private copy of the candidate's root Python files, with the four changed product files checked byte-for-byte, pinned QA Python/FFmpeg, and canonical `bounded-check.runOwned` (600000 ms private kill-on-close Job). Both final probe results are `ok:true`, `closed:true`, `forced:false`, native zero. No real library or catalog was read or written. The catalog-only probe uses synthetic `Z:` path strings, never filesystem access to that drive.

- `q23j/senua/r56-result.json` (17.7 s): queue initially **Paused**, one unrelated approved job **pending** with `resume` intercepted only to seed that pending job. Approve a second book with the real queue resume. It calls `resume(recheck=False)` once; **both jobs complete and both source files are removed after verified publication**, without a Start. The automatic research run stays **Idle**, so checking its status alone misses this effect. The initial probe printed non-ASCII paths and its supervisor refused the streamed/final-output mismatch; it did not certify a result. The final ASCII-escaped run has a successful owned receipt.
- `q23j/senua/r59-result.json` (0.55 s): old `keep` on «Джеймс Роллинс». Positive control: one English-name lookup and an `english_spelling` question. Save **only the title** as `Map of Bones` with `entered_names.save`, then research again with the same inconclusive lookup stub. Result: **zero lookups, no ask, no reasons, canonical author «Роллинс Джеймс»**, with only `title` in `entered_names` fields. This is an automatic-filing plan under a Cyrillic foreign-author folder, contrary to ruling 59.

### Findings and prior obligations

- **M11 [Major]: answer saving is fixed, but the real Held-cache loop remains open (Futaba's packaged finding).** `automatic_processing.py:629` skips an unchanged `Held` record with `until_change=True` when author rules did not change; a book-local `entered_names` answer does not change those rules. Requeue alone does not invalidate this cached answer. Futaba's actual automatic run creates that flag; Approve says saved/Press Start, but the next actual Start still asks `author_missing`, `name_language` or `two_people`, with zero jobs. Her formal no-author repetition is `q23j/futaba/m11-confirm-owned.json` (`ok:true`, code 0, native zero, 3.3 s) and `m11-confirm-results.json`; the other two shapes are in her delta results. The new `test_set_release` helpers inject Held via `_record` without `until_change`, so they miss the production path. Preserve saved answers but invalidate/research this book on the next Start; regressions must begin with an actual automatic run's Held record.
- **M12: fixed by reading**: no `series_answer` aliases, no `_continue_after_series`, no queued-job confirmation, and Approve filters author-wide `fix/series` entries at the actual save. Its book-local series entry remains. The corrected Discworld test has positive controls that book 19 actually becomes City Watch and books 20/21 remain Discworld.
- **M13 [Major]: partially fixed, still open for the conversion queue.** `merge_service.py:3397`, `approve_book` → `_approve_once` → `approve_automatic` → unconditional `self.resume(recheck=False)`. Removing `_release` fixes the automatic research run's restart, but an already-settled conversion Pause is still undone, including unrelated pending jobs and cleanup. `resume` captures the current generation, so the Pause's generation is treated as permission to start again. The real two-book probe above confirms the effect. Ruling 56 and the handoff explicitly require no `request_start` **or** `resume` from an Approve. Keep a user-approved job pending until Start; automatic-run admission needs its separate existing start path. Add a regression with a paused conversion queue and a different pending job; mocking only `automatic.request_start` is insufficient.
- **M14: original order mismatch fixed by reading**: Cyrillic `keep` now passes through the same surname-first step as Approve; canonical English `same_as` still wins. The broadened language requirement has the separate M15 gap below.
- **M15 [Major]: new review finding; ruling 59 remains bypassable by a title-only saved value.** `public_research.py:1300` sets `sergei` when **either title or author** is entered; `:1317` gates the English lookup with `not sergei`. Clearing the old keep's `rule` field at `:1198` does not clear this unrelated title flag. Thus a title correction prevents the author's required English lookup/question, and the automatic path can file the foreign author in Cyrillic. The new manual-Approve guard does not protect automatic `approve_automatic`. Require the English-author check independently of title/series corrections and prove the title-only control above still asks; preserve Russian-writing authors and canonical English answers. This is a newly explicit requirement in rulings 58/59; the older title-entered bypass predates the new guard.
- **m11 [Minor], reopened doc drift**: `local_identity.py:2610-2623` still says a queued approval confirms the set, a corrected series aliases the old name, and the first approval files the rest. That mechanism has been removed under ruling 57. Update these comments in the same corrective batch. Existing m23, Judy's notes and broader m9 tuning remain deferred.

### Nine dimensions (delta only)

| Dimension | Status | Result |
|---|---|---|
| Security | Pass | No new shell-out, executable input, Electron/IPC surface or credential handling. |
| Correctness & logic | Concerns | M11 still loops through the real Held cache; M12/original M14 corrected; M15 leaves a foreign-author automatic-filing bypass. |
| Crash / stability | Pass | New writes use existing catalog transactions; no new long-lived worker. |
| Performance | Concerns | Five whole-module moves preserve every test and all nine workers/deadlines; actual slowest remains 95.7% of 540 s. Broader m9 is deferred. |
| State & data safety | Concerns | Residual M13 resumes a stopped conversion queue and its unrelated pending jobs. Publication verification still precedes source removal. |
| Input handling | Concerns | English-question non-Latin answers are refused, but a saved unrelated title skips the question (M15). |
| Maintainability | Pass | Set-wide continuation/alias machinery removed; runner placement overrides are bounded. |
| Doc/code drift | Concerns | m11 stale set-release comments; Brief/backlog describe the new per-book policy. |
| Build & release hygiene | Concerns | Official passing receipt exists; no packaged-shell smoke executed or certified yet. |

Critical: **0**. Tracked Majors: **15**, with **M11, M13 and M15 open**; M1–M10, M12 and M14 are fixed or superseded as described above. Tracked Minors: **23**, m11 reopened; all other prior dispositions carry. Safety floor intact. This advisory severity verdict does **not** mean the requested fix batch is complete: Iris is holding release for these three demonstrated requirements and final candidate QA/review.

Hidden-package helper `q23j/hidden-package-smoke.mjs`, SHA256 `343f67fac8201a32268f7a8a0bcd7ee732c04b2a0156598b38efeed7e5d437e1`, was read but **not approved or executed**. It uses private paths and native ownership, but its tray cleanup must distinguish genuinely new registry key IDs from preexisting IDs whose path changed; its visibility/focus PID set omits descendants, and the detector needs a PID-matching positive control. Require distinct engine/CDP ports. Ender has the precise correction requests; final helper bytes and final artifact plan need separate vetting before native execution.

The revised helper, exact SHA256 `8187c310a1727a27ec005711f068a3eaf973c33b5bb079895e6b28fef294453d`, is **structurally approved by static review**, not executed. It snapshots all existing tray key IDs/raw values, refuses any preexisting change and deletes only new IDs matching the fresh copied EXE after exit. Read-only Win32 image queries cover window owners anywhere under the unique byte-pinned private payload; a real existing-window PID positive control exercises matching without displaying or focusing anything. Failed image queries/callbacks fail closed, engine/CDP ports differ, and canonical native Job closure must be zero. This constrained private-payload route does not need the worker to hold the parent's Job handle. **Execution still requires the final accepted artifact plan/pins**, plus the canonical owner/Koffi identities verified against the passing entry context. A shared-key or image-query failure must stop and be reported, never softened or restored over unrelated user activity.

Verdict of that superseded candidate (3545d17): RELEASE CLEAR, with the three Major obligations above still open at that time.

## Historical header (through cf166bf)

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-27 (passes 7 and 8: 2026-10-28)
Tool: Books Arranger (Electron / Python)
Release: v0.22.3
Commit range: v0.22.2..cf166bfa7cab8c1381a14c82b7409fbc75b91139 (45 commits), certified in eight passes:
  1. v0.22.2..40d3c63b33f5d978a7e5d112d3976d1effe21378 (18 commits), the first pass. The 0.22.2 review certified up to 4b9fdba; the tag v0.22.2 (0560019) adds docs only, so coverage has no gap.
  2. 40d3c63..65ddd72e978d1969b70bfcc11d975749d1b4290b (10 commits), the first fix re-review (section "Re-review at 65ddd72").
  3. 65ddd72..d4a74503221d3dbc587b6f42189f7dbe6746d298 (6 commits), the second fix re-review (section "Re-review at d4a7450").
  4. d4a7450..92376c7c354a082803d38fb63253305620a83941 (3 commits), the third fix re-review (section "Re-review at 92376c7").
  5. 92376c7..067315fbd22836f7192633c2b2a054f04f2ea9bc (2 commits: 4e8171a, 067315f), the targeted M6 re-review (section "Re-review at 067315f").
  6. 067315f..ddfbfa79df8907699c89dcc5f1386b8388200b9f (2 commits: 1138712, ddfbfa7), the targeted ruling-52 re-review (section "Re-review at ddfbfa7").
  7. ddfbfa7..51caef103219a6c07731de4c2b6783a8e0fa316b (2 commits: b2f8660 code, 51caef1 backlog), the targeted rulings 53-55 and M9 re-review (section "Re-review at 51caef1").
  8. 51caef1..cf166bfa7cab8c1381a14c82b7409fbc75b91139 (2 commits: 798001a code, cf166bf docs), the targeted M10, Futaba M-1, m20 and m22 re-review (section "Re-review at cf166bf").
Reviewed source: the main checkout (read only; at 65ddd72 for pass 2, at d4a7450 for pass 3, at 92376c7 for pass 4, at 067315f for pass 5, at ddfbfa7 for pass 6, at 51caef1 for pass 7, at cf166bf for pass 8), and scratch exports (git archive) for the tests and probes: 40d3c63 and 65ddd72 in pass 2, 65ddd72 and d4a7450 in pass 3, 92376c7 and d4a7450 in pass 4 (with 65ddd72 and v0.22.2 as well, to date each name result), 067315f, 92376c7 and v0.22.2 in pass 5, ddfbfa7, 067315f and v0.22.2 in pass 6, 51caef1, ddfbfa7 and v0.22.2 in pass 7, cf166bf, 51caef1 and v0.22.2 in pass 8. Every probe ran on both trees of its pass, so each one is seen to fail where the old code had the bug.
Files changed, pass 1: 35 files, +1564 / -179. Product code: 12 files (web/app.js +400, local_identity.py +106, merge_service.py +99, author_rules.py +47, public_research.py +37, desktop/main.js +32, desktop/quit-watch.js +22, desktop_backend.py +16, web_server.py +9, index.html, style.css, scripts). Tests: 17 files. Docs: 3 files. package.json and package-lock.json: version only, one commit (cd8d956).
Files changed, pass 2: 21 files, +296 / -48. Product code: 9 files (local_identity.py, public_research.py, merge_service.py, desktop/main.js, desktop/quit-watch.js, author_rules.py, review_backend.py, web/app.js, web_server.py). Tests: 10 files. Docs: 2 files. No version or lockfile change.
Files changed, pass 3: 15 files, +290 / -31. Product code: 6 files (merge_service.py +51, local_identity.py +41, public_research.py +21, review_backend.py +11, author_rules.py +8, web_server.py +3), and a comment in scripts/python-check-batches.mjs. Tests: 6 files. Docs: 2 files (Brief, backlog). No page code, version or lockfile change.
Files changed, pass 4: 8 files, +114 / -23. Product code: local_identity.py +23 / -10 and merge_service.py +6 / -3; comments only in author_rules.py and public_research.py. Tests: 2 files, +66 / -1. Docs: 2 files (Brief, backlog). No page code, script, version or lockfile change.
Files changed, pass 5: 5 files, +187 / -9. Product code: local_identity.py +29 / -2 (ruling 51: `_LOOKALIKE`, `_skeleton`, `_MARKERS`, `_unsure_series` and one call in `_series_split`); merge_service.py +2 / -1, a comment only. Tests: tests/test_folder_structure.py +154 / -5. Docs: 2 files (Brief, backlog). No page code, script, version or lockfile change.
Files changed, pass 6: 6 files, +323 / -76. Product code: local_identity.py +111 / -25 (ruling 52: `sorted_series`, `sorted_spelling`, `series_unconfirmed` in `identify`, one-file siblings in `sibling_series`, `_unsure_title`, `_MARKER_FOLD`, the "_" strip, the any-word script check); public_research.py +10 (the filled-in ask). Tests: tests/test_folder_structure.py +186 / -45, tests/test_identity_v5.py +14 / -5. Docs: 2 files (Brief, backlog). No page code, script, version or lockfile change.
Files changed, pass 7: 7 files, +219 / -46. Product code: local_identity.py +42 / -22 (ruling 53: `overridden` in `identify`, approved queued jobs in `sorted_series`; ruling 54: `folder_books` in `catalog_index`, per-book, same-author and root limits in `sibling_series`); public_research.py +14 / -10 (the ruling-52 ask moved after rulings 33 and 39; `his` replaces `sergei` for it); merge_service.py +28 (`_continue_after_series`, called after every accepted Approve). Tests: 3 files, +132 / -13. Docs: the backlog, +3 / -1 (51caef1).
Files changed, pass 8: 11 files, +304 / -67. Product code: merge_service.py +77 / -16 (M10's `SeriesAsked` and `_answer_then_ask_series`; `_release`, which requeues and starts or continues the run; `series_answer` in the job's metadata facts; `series_answered` in the to-do list), local_identity.py +43 / -21 (`series_answered`; the corrected series' `asked` name in `sorted_series`; m22: the override no longer confirms; m20: votes counted by series and number, uncredited siblings only for uncredited books), automatic_processing.py +10 / -1 (a held book whose series is answered is researched again), public_research.py +3 / -1 (`approval.series_question`). Scripts: the new test module in the gate, weighed 200 s. Tests: tests/test_set_release.py +121 (new), tests/test_folder_structure.py +44 / -4, tests/test_approve_as_is.py -21 (moved). Docs: Brief +2 / -1, backlog +2 / -2 (cf166bf). No page code, version or lockfile change. No page code, script, version or lockfile change.
Method: LEAN (ProcessRules § Lean verification). The full suite passed once per build in the entry check:
  - pass 1 in q23b/logs/ender-entry.log (receipt v2, books-arranger v0.22.3 @ 40d3c63, dirty N, code 0);
  - pass 2 in q23c/logs/ender-entry.log (receipt v2, books-arranger v0.22.3 @ 65ddd72, dirty N, check pass, entry exit 0);
  - pass 3 in q23d/logs/ender-entry.log (receipt v2, books-arranger v0.22.3 @ d4a7450, dirty N, check pass, entry exit 0; 187 tests in the last worker, 443 s in all);
  - pass 4 in q23e/logs/ender-entry.log (receipt v2, books-arranger v0.22.3 @ 92376c7, dirty N, check pass, entry exit 0; 438 s in all);
  - pass 5 in q23f/logs/ender-entry.log (receipt v2, books-arranger v0.22.3 @ 067315fbd22836f7192633c2b2a054f04f2ea9bc, dirty N, check pass, entry exit 0; 187 tests in the last worker, 434 s in all);
  - pass 6 in q23g/logs/ender-entry.log (receipt v2, books-arranger v0.22.3 @ ddfbfa79df8907699c89dcc5f1386b8388200b9f, dirty N, check pass, entry exit 0; 9 workers OK, 442 s in all);
  - pass 7 in `C:\Antigravity Projects\Worktrees\Books Arranger\q23h\logs\ender-entry.log` (receipt v2, books-arranger v0.22.3 @ 51caef103219a6c07731de4c2b6783a8e0fa316b, dirty N, `npm run check` code 0; 9 Python workers, 1,903 Python cases, the slowest worker at 82 % of its deadline). The 142 node cases are from Jane's brief;
  - pass 8 in `C:\Antigravity Projects\Worktrees\Books Arranger\q23i\logs\ender-entry.log` (receipt v2, books-arranger v0.22.3 @ cf166bfa7cab8c1381a14c82b7409fbc75b91139, dirty N, `npm run check` code 0; 9 Python workers, 1,910 Python cases, 142 node cases, 0 failed; the slowest worker, 6, at 452.1 s of 540, 84 %, against 364 s projected).
  I read the diff and ran only targeted tests and probes on the pinned runtime.
Stand-down dimensions: none
```

**Targeted runs, pass 1 (scratch copy of 40d3c63, pinned runtime `build-cache/qa-runtime`):**
- Python: `test_desktop_quit`, `test_folder_structure`, `test_live_cases_0222`, `test_original_title_wait.EnglishSpellingAnswerTests`, `test_merge_http…test_learned_author_rules_route_reads_the_list`, `test_approve_as_is…test_a_refused_approve_keeps_no_same_author_answer`, and the two new `test_entered_names.EditNamesTests` answer tests. 66 tests, all pass.
- Page scripts: `test_panel_lock_frontend.js`, `test_0223_ui_frontend.js`, `test_save_metadata_frontend.js`, `test_metadata_frontend.js`, `test_todo_holds_frontend.js`, `test_todo_frontend.js`, `test_browser.js`. All pass.
- Node: `quit-watch.test.mjs` and `python-check-batches.test.mjs`. 26 tests, all pass.
- Probes I wrote: they back M1, M2, M3 and m1, and are listed under each finding. They ran on throwaway catalogs inside the scratch copy and were deleted afterwards.

**Targeted runs, pass 2 (scratch copy of 65ddd72, same runtime):**
- Python: `test_author_rules`, `test_approve_as_is.ReviewFindingsTests`, `test_entered_names.EditNamesTests`, `test_folder_structure.OddNameTests`, `test_merge_http`, `test_original_title_wait`, `test_review_backend.ReviewTests`, `test_ruling35`, `test_desktop_quit`. 125 tests, all pass.
  - The first attempt had 18 errors. All of them were "Verified metadata exceeds the supported Windows output path length", caused by my long scratch path. I re-ran with the shared audio fixture folder moved to a short path, which is what the gate's own `fixtureRootMap` does. All pass. This was the environment, not the product.
- Page scripts: `test_save_metadata_frontend.js`, `test_0223_ui_frontend.js`, `test_panel_lock_frontend.js`, `test_metadata_frontend.js`. All pass.
- Node: `quit-watch.test.mjs`. 9 tests, all pass.
- Probes I wrote: 19 probes in 5 files (rules, MergeService, names, panel Save, learned rule). Each one ran on both 65ddd72 and 40d3c63. Results are under each item below. They ran on throwaway catalogs and audio in the scratch folder and were deleted afterwards.

**Targeted runs, pass 3 (scratch copy of d4a7450, same runtime; the shared audio fixture folder on a short path, as the gate maps it):**
- Python: `test_approve_as_is.ReviewFindingsTests`, `test_author_rules`, `test_entered_names.EditNamesTests`, `test_folder_structure.OddNameTests`, `test_merge_http`, `test_original_title_wait`. 86 tests, all pass.
- Negative controls: the 8 new tests, run on the 65ddd72 copy. 7 fail, each for the reason its fix names: StartRefused and "The book was not approved" (M4), `changed_for` False (m13), «Гарри Поттер 1: …» unsplit (m12), no `MergeService.routing_preview` and the route planning the hidden inputs (m14), «Волшебники - Grossman Lev.m4b» (ruling 49). The eighth is ruling 49's own control, which passes on both, as a control should.
- No page script or node test: pass 3 changes no page code, and its one script change is a comment.
- Probes I wrote: 6 files on the real MergeService, the rules and the folder-structure helpers: the M4 row read, the m13 requeue, the m13 loop, 24 names for m12, and the ways to name a title for ruling 49. Each ran on both d4a7450 and 65ddd72. They ran on throwaway catalogs and audio in the scratch folder and were deleted afterwards.

**Targeted runs, pass 4 (scratch copy of 92376c7, same runtime, the shared audio fixture folder on a short path):**
- Python: `test_folder_structure.OddNameTests`, `test_approve_as_is.ReviewFindingsTests`, `test_author_rules`. 45 tests, all pass.
- Negative controls: the 3 new tests, with the 92376c7 test files on the d4a7450 copy. All 3 fail, each for the reason its fix names:
  - M5: the four plain Warhammer names split as «Warhammer 40», No. 0, and the «… Книга 1. …» one is not asked;
  - ruling 50: «Мастер и Маргарита. CD 1. …» is series «Мастер и Маргарита», No. 1;
  - m15: `requeue` is called zero times.
  - The rest of `OddNameTests` passes there.
- No page script or node test: pass 4 changes no page code and no script.
- Probes I wrote:
  - 107 names end to end on the folder-structure helpers (offline research, the real identity and the real planner). Each ran on 92376c7, d4a7450, 65ddd72 and v0.22.2.
  - Two m15 probes on the real MergeService, run on 92376c7 and d4a7450.
  - They ran on throwaway catalogs and audio in the scratch folder and were deleted afterwards.

**Targeted runs, pass 5 (scratch copies of 067315f, 92376c7 and v0.22.2, same runtime):**
- Python: `test_folder_structure.OddNameTests` on 067315f. 14 tests, all pass.
- Negative control: the 067315f test file on the 92376c7 copy. The M6 test fails there for all 17 names it lists (15 M6 names, «Черная книга 2», "Star Wars Episode 4"). The 98-name "kept" test passes there, as a regression guard should.
- No page script, node test or MergeService test: the merge_service.py change is a comment (checked in the diff).
- Probes I wrote. Unless noted, each ran end to end on the folder-structure helpers (offline research, the real identity and the real planner), on 067315f, 92376c7 and v0.22.2:
  - The pass-4 name hunt. My probe file was deleted after pass 4, so I used Ender's rebuild: the 115 names in the test file, read with `ast`, nothing retyped. I checked it against my pass-4 text; it holds every name that text names. My own harness, not Ender's test.
  - 105 new names in 11 groups (below), and 9 rows shaped like live books.
  - The 34 live-library names that Ender's read-only listings of Z: quote in `Docs/` and that read "Series N. Title". These went through `_series_split` only, with the author each line names, on 067315f and 92376c7.
  - Three ruling-45 sibling probes (on 067315f and 92376c7), and a unit and end-to-end probe of `latin_lookalikes`.
  - A module scan for top-level names bound twice, on all three trees.
  - All on throwaway catalogs in the scratch folder, deleted afterwards. Nothing read Z: or live data.

**Targeted runs, pass 6 (scratch copies of ddfbfa7, 067315f and v0.22.2, same runtime):**
- Python: `test_folder_structure` and `test_identity_v5` on ddfbfa7. 87 tests, all pass.
- Negative control: the ddfbfa7 test files on the 067315f copy. 57 failures and 2 errors, every one in a test or subtest this delta adds or changes: ruling 52, M7, the two M8 live names, m18, m19, the filled-in asks, and the 98-name table now expecting an ask.
- No page script, node test or MergeService test: the delta changes no page code, script or merge_service.py.
- Probes I wrote. Each ran end to end on the folder-structure helpers (offline research, the real identity and the real planner), on ddfbfa7, 067315f and v0.22.2:
  - The pass-4 hunt, 115 names read with `ast` from the ddfbfa7 test file. Each one alone, with Sorted holding its split's series, and with two sibling book folders carrying the same pattern.
  - My pass-5 names, rebuilt from this report's text (72 names; the pass-5 probe file was deleted), in the same three layouts.
  - 26 name patterns in five layouts: one or two sibling book folders, one or two one-file books beside it, and two one-file books in the library root. Also one multi-file sibling book beside a one-file book, and ruling 45 with mixed file counts and with other authors' books.
  - The live names: every «…» name and backtick path segment in Ender's read-only listings of Z: in `Docs/` that reads "Series N. Title" (90 names), alone.
  - Sorted confirmations: 9 author folders, 4 credits, 8 series spellings and 3 job states. Sergei's own answers: a legacy "Entered by you" record (4 shapes), an author-only Edit names Save, and Approve of a filled-in ask (3 names).
  - Rulings 33 and 39 with a series split, with `_author_latin` stubbed and the real `original_titles.translation`.
  - The M7 unit and end-to-end probes, the module scan, and the cost of one-file siblings and of `sorted_series` (synthetic: 3,000 files, 5,000 jobs).
  - All on throwaway catalogs in the scratch folder, deleted afterwards. Nothing read Z: or live data.

**Targeted runs, pass 7 (scratch copies of 51caef1, ddfbfa7 and v0.22.2 under a short Temp folder, same runtime):**
- Python on 51caef1:
  - `test_folder_structure.OddNameTests`, `test_approve_as_is.ReviewFindingsTests`, `test_original_title_wait`, `test_identity_v5`, `test_live_cases_0222`: 103 tests, all pass.
  - `test_approve_as_is` (whole), `test_entered_names.EditNamesTests`, `test_author_rules`: 56 tests, all pass. These cover the Approve path the delta changes.
- Negative control: the three b2f8660 test files on the ddfbfa7 copy. 10 failures in 9 tests, every one a test this delta adds or changes: M9 (two tests), ruling 52, ruling 53 (both sets), the «Червь» set, ruling 54, m21, the set's first Approve on the real MergeService, and the sibling-spelling test. Ruling 55's test passes on both trees, as Ender says.
- No page script or node test: the delta changes no page code or script.
- Probes I wrote, each run on 51caef1 and ddfbfa7 (and 0.22.2 for the folder-structure ones):
  - End to end on the real MergeService (real audio, offline research, the job held in the queue unless noted): 12 Approve flows on one-, two- and three-book sets. The first book's Approve answers the series question, "Same author?", ruling 39's English spelling or ruling 33's spelling; then the other books are researched again.
  - The spread of a set's Approve: another author, the same author in another folder with a near-identical name, and a corrected series.
  - M8: 21 junk patterns in 4 layouts (84 books).
  - Ruling 54: uncredited siblings, another author's book folders, siblings credited in Latin, and one book whose files carry two album spellings (two ways).
  - Ruling 45's override beside a junk set; M9 with an English original title; the cost of `_continue_after_series` (synthetic: 500, 2,000 and 5,000 held records).
  - All on throwaway catalogs and audio in the scratch folder, deleted afterwards. Nothing read Z: or live data.

**Targeted runs, pass 8 (scratch copies of cf166bf, 51caef1 and v0.22.2 under a short Temp folder, same runtime):**
- Python on cf166bf: `test_set_release`, `test_folder_structure.OddNameTests`, `test_approve_as_is`, `test_original_title_wait`, `test_identity_v5`, `test_live_cases_0222`. 117 tests, all pass (524 s; `test_set_release` runs six real automatic runs).
- Negative control: the cf166bf `test_set_release.py` and `test_folder_structure.py` on the 51caef1 copy. 13 failures in 11 tests: all 6 in `test_set_release`, and in `OddNameTests` m20 (three), m22, ruling 54, m19 and the sibling-spelling test (the last three changed for m22 and m20).
- No page script or node test: the delta changes no page code; the two script lines add the new module to the gate.
- Probes I wrote, on cf166bf and 51caef1 (and 0.22.2 where noted):
  - End to end on the real MergeService and the real automatic run (real audio, offline research): 11 flows.
    - Approve as shown on four questions that come before the series question (ruling 33's spelling, no author, two credits in two tags, two people in one credit), three presses each.
    - The English spelling kept as shown.
    - A run Sergei stopped with other work saved; an ended run with a new book on disk.
    - A credit spelled differently from the library (a middle name, a typo).
    - A corrected series: «Мертвый ноль 7. Мертвый ноль» with m22's fill-in, and a Discworld set with one book moved into "City Watch".
  - On the folder-structure helpers: a corrected series in Sorted and later books of the same author (5 cases); a 'keep' rule's automatic and Approve folders (also on 0.22.2).
  - All on throwaway catalogs and audio in the scratch folder, deleted afterwards. Nothing read Z: or live data.

---

## Re-review at cf166bf (fix delta 51caef1..cf166bf)

Ender fixed M10, Futaba's M-1, the rest of m20 and m22, made a corrected series carry to the rest of a set (ruling 53), and fixed the m11 doc lines (798001a code, cf166bf docs). I read both commits red-team style, ran the new tests on 51caef1 as a negative control, and drove the new flows through the real automatic run.

Each fix does what its commit says for the cases its tests name. M10's answers are kept and the series is asked next; the set files after book 1's Approve, after the run has ended and from a paused run. But the delta opens three new Majors, and the release makes an older one reach whole sets:

| Item | Status at cf166bf | Evidence |
|---|---|---|
| **M10** | **Fixed for answers that save something; it opens M11.** | "Same author?": the rule is kept, nothing is filed, both books ask the series next, and Approve files the set (Ender's test). The English spelling kept as shown: a 'keep' rule, then the series question, then Approve files. |
| **Futaba M-1** | **Fixed.** | After book 1's Approve, book 2 files from an ended run, a rescan and a paused run (Ender's three tests fail on 51caef1). On 51caef1 my book 2 stays asked in both layouts. |
| **m22** | **Fixed as specified.** | «Мертвый ноль 7. Мертвый ноль» beside «Сновидения Ехо 4» and «5» asks with «Сновидения Ехо» filled in (51caef1 filed it by itself). Ender's test fails on 51caef1. |
| **m20** (the rest) | **Fixed.** | Ender's tests (uncredited siblings in two places, two album spellings) fail on 51caef1 and pass. |
| **m11** (pass 7 lines) | **Fixed.** | The Brief has the rulings 53-55 row, the ruling-52 row says siblings are superseded, the comments match, and the backlog marks m20. |
| **M11** (new) | **Major, new in 798001a.** Approve as shown on a question before the series question never files. | Ruling 33's spelling, no author, two credits: each press answers "Your answer is saved … its series is asked next", saves nothing, and the same question comes back. Three presses, nothing filed. 51caef1 filed; 0.22.2 filed unsplit. |
| **M12** (new) | **Major, new in 798001a.** A series he corrects at one Approve renames that series for every book of the author, in any folder, for good. | Book 19 moved to «City Watch» No. 3: «Discworld 20. Hogfather» (same folder) and «Discworld 21. Jingo» (another folder) file as `City Watch - 20` and `- 21`, no row. With m22's fill-in, «Сновидения Ехо 4» and «5» file as `Мертвый ноль - 4` and `- 5`. |
| **M13** (new) | **Major, new in 798001a. Product call for Sergei.** A releasing Approve continues a run Sergei stopped, and starts a whole new run when none is running. | Stopped run with another book saved: the run resumes and files «Другая книга». Ended run: a new run discovers and files «Новая книга». On 51caef1 neither happens. |
| **M14** (new to this review) | **Major, older than 0.22.2, not in this delta.** A 'keep' rule files a Cyrillic credit given-name first by automatic filing, surname first by Approve. | «Джеймс Роллинс» with a keep rule: automatic `Джеймс Роллинс\…`, Approve `Роллинс Джеймс\…`, on cf166bf, 51caef1 and 0.22.2. The release now splits one set between the two folders. |
| **m23** (new to this review) | **Minor, new in 0.22.3 (ruling 41), not in this delta.** | On 51caef1, Approve of «Курс истории. Лекция 1. Греция» with no author files `Без автора\Греция.m4b`: the series and number are dropped from the name. |

**What the probes showed**

- **M11, Approve as shown loops** (`merge_service.py:3083`, `:3173-3192`; `approval.series_question`, `public_research.py:656`):
  - The page sends a title or author only when it differs from the proposal (`askValues`, web/app.js:2529). So "Approve as shown" sends nothing, and `_answer_then_ask_series` has nothing to save (`:3183`). The book is released, researched again, and asks the same question.
  - Two-book sets «Курс истории. Лекция N. …», after a full run, three presses on book 1 each:

    | Question before the series | cf166bf, each press | Book 1 after 3 presses | 51caef1 |
    |---|---|---|---|
    | Ruling 33's spelling, "Ilya Marchenko" (proposal Marchenko Ilya) | SeriesAsked: "Your answer is saved …" | still the spelling question; nothing filed | filed `Marchenko Ilya\Курс истории. Лекция\…` (M10) |
    | No author anywhere ("Title or author missing") | the same | still the same question | filed `Без автора\Греция.m4b` |
    | Two credits in two tags (Лев Толстой, Антон Чехов) | the same | still "Author unclear" | filed `Толстой Лев\Курс истории. Лекция\…` |
    | Two people in one credit | the same | still "Author unclear" | filed under the joint credit |

  - Ways out exist, but nothing on the row says so: pick a candidate other than the proposal, type a different value, or set the series in Edit names (`his`). For a book with no author there is no value to pick.
  - Each press also calls `_release` and so starts or continues the run (M13).
  - "Same author?" (a choice is always sent) and the English spelling (an empty author saves a 'keep' rule) do not loop; my probe and Ender's tests agree.
  - Why the suite passed: both M10 tests send an answer (`choice='same'`, a typed author). No test approves an author question as shown.
- **M12, a corrected series spreads** (`local_identity.py:3026-3031`: the job's `series_answer.asked` maps the asked name to his series for every book of the author; `merge_service.py:3130-3155` releases every book whose split carries either name):
  - End to end, a Discworld set (`Terry Pratchett\Discworld\19`, `\20`, and `Terry Pratchett\Other\21`, all asked). Book 19 approved with Series "City Watch", No. 3 in the editor. cf166bf files `Pratchett Terry\City Watch\City Watch - 20 - Hogfather - Pratchett Terry.m4b` and `… - 21 - Jingo - …` by themselves; Hogfather is no City Watch book, and Jingo is in another folder. 51caef1: both still ask.
  - With m22's fill-in: «Мертвый ноль 7. Мертвый ноль» asks with «Сновидения Ехо» filled in; Sergei sets «Мертвый ноль». The siblings «Сновидения Ехо 4. Я иду искать» and «5. Сундук мертвеца» then file as `Фрай Макс\Мертвый ноль\Мертвый ноль - 4 - …` and `- 5 - …`, no row. His answer said "this book is not in that series"; the code read "that series is called «Мертвый ноль»".
  - For good: on the helpers, one completed job carrying `series_answer` {asked "Discworld", series "City Watch"} makes a later «Discworld 20. Jingo», alone in another folder, file as `City Watch - 20`. A later «Сновидения Ехо 8. …» files under «Мертвый ноль». With a plain Discworld job as well, the result depends on which job row comes first (`sorted_spelling` returns the first match). Another author's book still asks.
  - Older, latent: the editor's series change is also an Edit names fix (`entered_names.FIXED` holds 'series'; author scope), which reaches the same books when they are next researched. On 51caef1 they stayed asked after the run, so it never fired there; the release now researches them at once.
  - Why the suite passed: the one corrected-series test renames the set's own name («Курс истории. Лекция» → «Курс истории»), where spreading is the point.
- **M13, the release starts work Sergei did not ask for** (`merge_service.py:3157-3167` → `automatic_processing.py:371-387`):
  - A run Sergei stopped ('Paused — pending work saved') with another book in its saved list: Approve of the set's first book. cf166bf: the run is Running a second later, and «Другая книга» is filed (`Петров Иван\Другая книга - Петров Иван.m4b`; its source is removed after the verified result). 51caef1: the run stays Paused, only the approved book is filed.
  - An ended run, a new book copied in afterwards: cf166bf starts a new run, which discovers and files «Новая книга». 51caef1 files only the approved book.
  - Every M10 answer (`:3191`) and every M11 press releases one book, so these presses start or continue the run too.
  - `stop()`'s own docstring: "a start the app or Sergei has just stopped must never come back by itself". The app's safety stops (disk space, working-file hold, `merge_service.py:243-244`) end in the same 'Paused' state, and `_start_block` names no such hold. By reading, a release continues those runs too, unless the audiobook queue's state blocks the start; I did not probe it.
  - The Brief lists "Sergei wants a paused run left paused" as a revisit trigger, and Start over (O9) already continues a run. So this is Sergei's call. My view: a stopped run must stay stopped. Requeue into the saved run and say on the row that it waits for Start; for an ended run, research only the released books, without a discovery pass.
- **M14, the 'keep' rule's two folders** (`local_identity.py:2339-2342` takes the credit as written; `approved()` files it surname first):
  - Helpers, «Карта костей» by «Джеймс Роллинс» with a 'keep' rule: automatic `Джеймс Роллинс\Карта костей - Джеймс Роллинс.m4b`, Approve `Роллинс Джеймс\Карта костей - Роллинс Джеймс.m4b`, on cf166bf, 51caef1 and 0.22.2.
  - End to end on cf166bf: the English spelling kept as shown, then the series question. Book 1 (Approve) files `Роллинс Джеймс\Курс истории. Лекция\…`; book 2 (released, automatic) files `Джеймс Роллинс\Курс истории. Лекция\…`. One author, two folders.
  - A 'keep' rule comes from every "keep this name" answer to ruling 39, from the lookup's "written in Russian" result, and from a "different" answer to "Same author?". I checked the Cyrillic credit only.
- **m23** (51caef1, the no-author row of the M11 table): `Без автора\Греция.m4b` for «Курс истории. Лекция 1. Греция»; 0.22.2 filed the whole name. On cf166bf the same book cannot be approved as shown (M11); by reading, the series question's Approve would file it the same way.
- **Re-research and dropped answers**:
  - No research loop: a run visits a released book once, and `series_answered` only lets a held book through when Sorted answers its series.
  - A held book whose `series_answered` is true is hidden as "Still checking" until researched. If research then asked again, it would stay hidden. `series_answered` reads the ask's author proposal, research reads the identity's author. I tried two divergent spellings (a middle name, a typo); ruling 3's spelling made them agree both times, and both books filed. Not reproduced; noted.
  - Answers kept: the Same author? rule, the English spelling, typed names and the editor's names (`approve_book` keeps them on `answered`). "Convert what's there" is not kept: it is pressed again on the series question.
  - The row reads `SeriesAsked` as a refusal (`approve_code` → 'refused'). A note for Judy: the answer was kept.
- **The gate** (Ender's note): worker 6 took 452.1 s of 540 (84 %), 24 % over its 364 s projection. A machine 20 % busier, as the 0.22.2 notes measured, would cross the deadline. That makes the entry check flaky, not the build unsafe. Not a release risk (m9).
- **Earlier fixes**: M1, M4, m1, m13, m15 (`test_approve_as_is`), M5 to M9, m12, m16, m18, m19, m22, rulings 50 to 55 (`OddNameTests`), rulings 38, 39 and 49 (`test_original_title_wait`) and the live cases all pass on cf166bf. The split is unchanged.

**New findings (details under their dimensions):**
- **M11 [Major], new in 798001a; a regression against 0.22.2 and 51caef1.** Approve as shown on a question that comes before the series question never files, and says the answer was saved.
- **M12 [Major], new in 798001a; a regression against 0.22.2 and 51caef1.** A series corrected at one Approve renames that series for every book of the author, in any folder, for good, and m22's fill-in turns "not this series" into a rename of the siblings' series.
- **M13 [Major], new in 798001a; new against 0.22.2.** A releasing Approve continues a run Sergei stopped and starts a new run when none is running. Sergei's call.
- **M14 [Major], not new: 0.22.2 has it.** A 'keep' rule files a Cyrillic credit in two folders.
- **m23 [Minor], new in 0.22.3 (ruling 41), not in this delta.** A split book with no author loses its series from the file name.
- **m9 [Minor]** updated: the gate's slowest worker at 84 %.

### Verdict at cf166bf

- Total Critical: 0
- Total Major: 14 (M1 to M10 fixed and verified; M11, M12, M13 and M14 open)
- Total Minor: 23 (m1, m4, m11 to m16, m18 to m20, m22 fixed and verified; m21's first half fixed; m2, m3, m5 to m10, m17, m21's second half and m23 open)

This certifies the range v0.22.2..cf166bf. No Critical finding: nothing is lost (M12 misfiles, M11 blocks a flow, M13 does unasked work), and the safety floor is intact. Pass 8 adds no shell-out, kill, route, file write or network request; the release calls the existing requeue and `request_start`. But cf166bf is worse to ship than 51caef1 in one respect: M11 stops a common Approve from working at all, and M12 is a new silent misfile. I would fix M11 and M12 before shipping, and ask Sergei about M13.

Verdict of that pass (cf166bf, superseded): RELEASE CLEAR.

---

## Re-review at 51caef1 (fix delta ddfbfa7..51caef1)

Ender fixed M9, closed M8's sets with ruling 53, fixed m20 with ruling 54 and the first half of m21, and added a test for ruling 55 (b2f8660). 51caef1 updates the backlog. I read both commits red-team style, ran the new tests on ddfbfa7 as a negative control, and probed the set's Approve end to end on the real MergeService.

Every fix does what its commit says for the cases it names. M8's sets now ask: 84 of 84 junk books, where ddfbfa7 filed all 84 under the junk folder. But two changes in b2f8660 combine into one new Major (M10):
- ruling 53 counts any queued Approve of Sergei's as confirming its series, whatever question that Approve answered;
- the M9 move puts two more author questions in front of the series question.

| Item | Status at 51caef1 | Evidence |
|---|---|---|
| **M9** | **Verified fixed. It opens M10.** | Ender's two tests fail on ddfbfa7. «Отряд Сигма 2. Карта костей» by «Джеймс Роллинс»: one lookup, the rule «Джеймс Роллинс» → Rollins James, then the series question. Approve files `Rollins James\Отряд Сигма\…`. "Ilya Marchenko" is asked the spelling first. |
| **M8** (sets) / ruling 53 | **Fixed for sibling confirmation.** | 21 junk patterns × 4 layouts: 84 of 84 ask (ddfbfa7: 84 of 84 file under the junk folder). Approving the set's first book files the rest while its job is still queued (Ender's test, and my control). What is left goes through M10 and m22. |
| **m20** / ruling 54 | **Narrowed, still open (Minor).** | Credited siblings now vote once per book, only for the same author, and never in the library root. Ender's test fails on ddfbfa7, and another author's book folders now ask. Uncredited siblings still vote for any author. One book whose files carry two album spellings still votes twice. |
| **m21**, first half | **Fixed.** | Ender's test fails on ddfbfa7. An entered title alone behaves the same by reading (the same `his`). The second half is in the backlog for 0.22.4. |
| **Ruling 55** | **Holds, as before.** | Ender's test passes on both trees. |
| **M10** (new) | **Major, new in b2f8660.** An Approve that answered an author question confirms the set. | Two-book set «Курс истории. Лекция N. …». The first book's "Same author?" or English-spelling Approve files it under the junk folder, and the second book then files there by itself, with no row. On ddfbfa7 the second book asks. |
| **m22** (new) | **Minor, new in 0.22.3 (rulings 45 and 53), not in this delta.** | «Финал 3. Финал» beside two «Шерлок Холмс. Аудиоспектакль» books files silently into that folder, while the two siblings ask. |

**What the probes showed**

- **M10, the set follows an Approve that answered another question.** The code: `public_research.py:1348-1349` (`his`: an 'approved' title or author skips the series question), after the asks at `:1301-1341`; `approved()` settles both names as 'approved' (`:643`); `local_identity.py:3016-3018` (a queued or converting job of Sergei's confirms its series); `merge_service.py:3104` and `_continue_after_rule` (`:2955-2980`) put the other books back on the run.
  - Two-book sets, one sibling each (one sibling never confirmed, so ddfbfa7's M8 does not decide them). The first book's job is held in the queue:

    | Book 1's question, and his answer | 51caef1: book 1 | 51caef1: book 2, researched again | ddfbfa7: book 2 |
    |---|---|---|---|
    | "Same author?" (credit Dean Koonts; the library has Koontz Dean): Same | Files `Koontz Dean\Курс истории. Лекция\Курс истории. Лекция - 1 - Греция - Koontz Dean.m4b`. The series was never asked; the Goes to line showed it. | Files by itself: `Koontz Dean\Курс истории. Лекция\…- 2 - Рим -…`. No row. | Asks the series. |
    | English spelling (ruling 39, lookup inconclusive), «Джеймс Роллинс»: types "James Rollins" | Never asked the series (ddfbfa7 asked it first). Files `Rollins James\Курс истории. Лекция\…`. | Files by itself under the same junk folder. | Asks the series. |
    | Spelling (ruling 33), "Ilya Marchenko": picks Marchenko Ilya | Never asked the series. Files `Marchenko Ilya\Курс истории. Лекция\…`. | Asks the spelling again (no rule); its Approve does the same as book 1's. | Asks the series. |
    | The series question (control): Approve | Files the split, as ruled. | Files by itself (ruling 53, as ruled). | Asks the series. |

  - "Same author?" with the two books in separate folders gives the same result.
  - With the first book's job completed before the second book is researched again, ddfbfa7 also files the second book by itself, through Sorted. That path is older. But the answer's rule puts the other books back on the run at once, and a conversion takes minutes. So on ddfbfa7 they asked in practice; on 51caef1 they never do.
  - Three-book sets give the same results for books 2 and 3. On ddfbfa7 a set of three in one folder filed by itself anyway (M8).
  - By reading, untested: a bulk "Approve as is" of a non-odd "Author unclear" row asked by the identity (`:910`) also files its split. Such a row is held before the series question, and the set then follows it.
  - Why the suite passed: every ruling-53 test approves through the series question. The M9 tests approve after a successful lookup, or check only the first ask. No test answers an author question on a book with an unconfirmed split.
- **The spread of "Approve once confirms the set"** (`sorted_spelling`, `local_identity.py:3028-3041`; `_continue_after_series`, `merge_service.py:3108-3131`):
  - Another author: «Курс истории. Лекция 3. Египет» by Сергей Сидоров is put back on the run, researched again, and asks. Confirming needs the same person (`same_person`, or a rule's target). The requeue itself ignores the author, which costs one research per book.
  - The same author, another folder, a near-identical name: «Курс истории: лекция 4. Вавилон» by «Петров Иван» files by itself into «Курс истории. Лекция», the folder his Approve made. The key keeps only letters and digits (`norm`), so the two names are one series, as ruling 46 intends. Note, no finding.
  - Another library root: by reading, neither `sorted_series` nor `_continue_after_series` looks at the root. A book by the same author, with the same series key, under another source root files into the same Sorted folder. That is how ruling 52 treats Sorted. Note, no finding.
  - His corrected series: with Series «Курс истории» set in the editor at the first Approve, nothing is requeued by series. The editor's author-scope fix reaches the other books, and they file as «Курс истории», No. 2 and No. 3. Good.
  - Timing: once the first book is approved, the rest are queued at once. If he then corrects the first book (its job turns "needs attention"), the correction does not reach them. Note for Sergei; ruling 53 asks for exactly this.
  - Cost: `_continue_after_series` parses every held record on every accepted Approve: 62, 75 and 172 ms at 500, 2,000 and 5,000 held records of 16 KB (synthetic). Note, no finding.
- **M8, sets** (`local_identity.py:2611-2629`):
  - 21 junk patterns from passes 5 and 6 («Шерлок Холмс. Аудиоспектакль», «Курс истории. Лекция», "Hamlet. Act", «Ведьмак. Сборник», «Отцы и дети.Гл.», «Цикл «Хроники Амбера»», «Карр Д Д - ШХ», "The Hobbit. Track", "Perry Rhodan Band", «Отряд Сигма_» …), each the third of a set (Nos. 11, 12, 13).
  - Four layouts: two sibling book folders; two one-file books in the author folder; two in the library root; one 4-file sibling book.
  - 51caef1: all 84 ask, filled in. ddfbfa7: all 84 file under the junk folder.
- **m20, what is left** (`local_identity.py:2970-2972`, `:2976-2978`, with `catalog_index` `:916-920`). Each probe ran on 51caef1, ddfbfa7 and 0.22.2:
  - Two uncredited one-file «Червь» books beside «Мертвый ноль 7. Мертвый ноль» by Макс Фрай, in `Unsorted\` or in `Макс Фрай\`. On 51caef1 and ddfbfa7 the book files silently as `Фрай Макс\Червь\Червь - 7 - Мертвый ноль - Фрай Макс.m4b`. 0.22.2 asks. `same_author` lets a sibling with no credit vote for any author; uncredited book folders do the same.
  - One two-file book whose files carry two album spellings («Темная» / «Тёмная», or "… CD1" / "… CD2"). The catalog groups it as one book, but the one-file branch counts album strings, so it is two votes. «Мертвый ноль 7. Мертвый ноль» beside it files as `Фрай Макс\Лабиринты Ехо\Лабиринты Ехо - 7 - …`, with no other sibling. The same on ddfbfa7. 0.22.2 asks.
  - Fixed: another author's book folders under `Unsorted\` (ddfbfa7: «Червь», No. 7) now ask.
  - Good: siblings credited "Max Frei" still vote for «Макс Фрай», the same person across scripts («Сновидения Ехо», No. 7).
- **m22** (`local_identity.py:2611-2614`; the comment at `:2621` says "another, real series"):
  - In `Иванов Петр\Шерлок Холмс\`, «Финал 3. Финал» beside «Шерлок Холмс. Аудиоспектакль 1. …» and «… 2. …» files as `Иванов Петр\Шерлок Холмс. Аудиоспектакль\Шерлок Холмс. Аудиоспектакль - 3 - Финал - Иванов Петр.m4b`. The two siblings themselves ask.
  - The override confirms whatever series the siblings carry; only `_unsure_series` checks it, not "real".
  - The same on ddfbfa7. 0.22.2 asks.
- **M9 with an English original title (ruling 38)**:
  - With `_author_latin` stubbed to return "Map of Bones", the ask's Title field shows "Map of Bones", while the Goes to line and Approve use «Карта костей».
  - The stub skips the client, so the cache that Approve's ruling-49 step reads is empty. By reading, the real lookup's FantLab query is by title only and is cached, so Approve should find "Map of Bones".
  - Untested end to end, and no test covers M9 with an English title. Note, no finding.
- **Earlier fixes**: M1, M4, m1, m13 and m15 (`ReviewFindingsTests`), M5 to M8, m12, m16, m18, m19 and rulings 50 to 52 (`OddNameTests`, with the 98-name table, unchanged on both trees), rulings 38, 39 and 49 (`test_original_title_wait`) and the live cases all pass on 51caef1. The split itself (`_series_split`, `series_title_parts`) is unchanged, so a book alone keeps its pass-6 outcome.

**New findings (details under their dimensions):**
- **M10 [Major], new in b2f8660.** 0.22.2 did not have it: it filed these names unsplit.
  - The Approve that answers "Same author?", ruling 39's English spelling or ruling 33's spelling files the book's unconfirmed split, and the series question is never asked.
  - Ruling 53 then counts that Approve as the set's answer. The rest of the set files by itself under the split's series, with no row.
  - The M9 move added two of these three questions. I recommended that move in pass 6.
- **m22 [Minor], new in 0.22.3 (rulings 45 and 53), not in this delta.** Ruling 45's override confirms a set's series that ruling 53 does not confirm for the set itself.
- **m20 stays open, narrowed:** uncredited siblings, and a book with two album spellings.
- **m11:** the Brief's ruling-52 row still says sibling books confirm, and it has no row for rulings 53 to 55 or M9's order. The studio repo holds rulings 44 to 55 only in its working tree.

### Verdict at 51caef1

- Total Critical: 0
- Total Major: 10 (M1 to M9 fixed and verified, M8 for its sets; M10 open)
- Total Minor: 22 (m1, m4, m12 to m16, m18 and m19 fixed and verified; m21's first half fixed; m2, m3, m5 to m11, m17, m20, m21's second half and m22 open)

This certifies the range v0.22.2..51caef1. No Critical finding: M10 misfiles, but nothing is lost; the audio is intact in Sorted. The safety floor is intact. Pass 7 adds one read-only query clause, one requeue loop over the catalog's own records, and no shell-out, kill, file write, route or network request. M10 is the one to fix before shipping if Sergei wants 0.22.3 free of the regressions this review knows about.

Verdict of that pass (51caef1, superseded): RELEASE CLEAR.

---

## Re-review at ddfbfa7 (fix delta 067315f..ddfbfa7)

Ender built ruling 52 (1138712) and recorded it in the Brief and backlog (ddfbfa7). I read both commits red-team style, ran the new tests on 067315f as a negative control, re-ran my name probes, and hunted for an unconfirmed split that still files by itself.

Ruling 52 works for a book on its own. No name I tried files by itself any more unless something confirms its series. M7, m18 and m19 are fixed. But M8 is only narrowed, and the ask opens one new Major (M9):

| Item | Status at ddfbfa7 | Evidence |
|---|---|---|
| **Ruling 52** | **Verified for a book on its own.** | Alone, 0 of 277 names file by themselves (the 115-name hunt, 72 pass-5 names, 90 live names). Each of the hunt's 32 splits asks with the values it filed under on 067315f, and files exactly those once Sorted holds the series. |
| **M7** | **Fixed.** | `_MARKER_FOLD`. «Аnita Blake», «Сlive Barker» and «Тhe Expanse» read as Latin again, and the book files under `Anita Blake`. Ender's test fails on 067315f. The module scan finds no name the delta binds twice. |
| **M8** | **Narrowed, still open (Major).** | Alone or beside one sibling, every M8 name asks. Beside two siblings that carry the same name pattern, 36 of my 44 split names still file by themselves under a junk folder; the other 8 are real series. |
| **m18** | **Fixed.** | My 10 names ask, alone and with Sorted holding the series. |
| **m19** | **Fixed.** | Both pass-5 probes: «Сновидения Ехо», No. 7; with two «Лабиринты Ехо» siblings as well, it asks. |
| **M9** (new) | **Major, new in 1138712.** The ruling-52 ask comes before rulings 33 and 39. | «Отряд Сигма 2. Карта костей» by «Джеймс Роллинс»: no lookup, no rule. Approve files `Роллинс Джеймс\Отряд Сигма\…`. 067315f and 0.22.2 file under `Rollins James`. |
| **m20** (new) | **Minor, new in 1138712.** One-file siblings count files, not books, and ignore the root limit and the author. | One 4-file sibling book outvotes two one-file books: «Мертвый ноль 7. Мертвый ноль» files into «Лабиринты Ехо». In the library root, another author's two «Червь» books make it «Червь», No. 7. |
| **m21** (new) | **Minor, new in 0.22.3 (ruling 41), not in this delta.** An "Entered by you" title or author skips the ruling-52 ask. | A 0.22.2-era panel record with the whole name files as `Отряд Сигма\Отряд Сигма - 1 - Отряд Сигма_01. Песчанный дьявол`. |
| Ender's interpretation 1: one-file books in one folder are siblings | **Needed, but too wide as built.** | It is what files the live «Червь» folder by itself. As built, it brings m20 and widens the M8 residual. |
| Ender's interpretation 2: a source folder named like the series does not confirm | **The safe side. Sergei's call.** | A book folder in `James Rollins\Отряд Сигма\` asks. A one-file book in the same folder files under «Отряд Сигма» by item 9, as it has since 0.22.1. |

**What the probes showed**

- **Every way an unconfirmed split still files by itself** (public_research.py:1287-1305; local_identity.py:2614-2618, :2668):
  1. Two siblings that carry the same name pattern (M8, below). Ruling 52 counts them as a confirmation.
  2. An "Entered by you" title or author (m21). `sergei` is then True, so the ask at :1294 is skipped.
  3. An author-only Edit names Save. `with_names` settles both names as 'entered'. Note, no finding: the editor showed the Series and Number the book then files under.
  4. Approve of another question on the row ("Same author?", Author unclear). Note, no finding: the Goes to line shows the series.
  - I found no other path. `one_source` is always True for a v5 identity, a part never splits, and `reasons` is empty there.
- **Ruling 52 on a book alone:**
  - The pass-4 hunt, 067315f → ddfbfa7, alone: 32 splits ask with the same values. "S.T.A.L.K.E.R. 2 - 1. Зона" asks with nothing filled in (m18). 43 whole names, 37 asks and 2 held books are unchanged. With Sorted holding the series, the 32 file exactly the filled-in values.
  - My pass-5 names: 44 ask filled in; 17 ask with nothing filled in (the 10 m18 names, the 6 plurals and «Sigmа Force»); 11 asks are unchanged. None files alone.
  - Live names: 90 names read "Series N. Title" (this time every «…» name and backtick path segment; pass 5 took 34 «…» names). None files alone. 63 go from a silent split to a filled-in ask. 9 ask with nothing filled in: «Discworld 26. Death 5. Thief of Time» and four «Оно - N - ИЮНЬ 1958 ГОДА. …» parts (m18), the safe side. 18 are unchanged.
  - Approve of a filled-in ask files the values the ask holds (Ender's tests, and my three probes).
  - Note, no finding: m18's check also asks titles that start with a word and a number, such as «Метро 2. Метро 2034» and «S.T.A.L.K.E.R. 12. Зона 51». That is the safe side, one question each. They ask even when confirmed.
- **Sorted confirmation** (local_identity.py:2983-3021). No wrong folder found:
  - Author: "Дивов О.", "Дивов О", "Дивов Олег Игоревич" and "Дивов Олег; Иванов Петр" confirm nothing. "Олег Дивов", "дивов олег", a double space and "Divov Oleg" confirm, as the same person. Sorted "Rollins James" confirms «Джеймс Роллинс».
  - Spelling: «Профессия инквизитор», «профессия: Инквизитор», «Профессия - инквизитор» and «Профессия: инквизитор.» confirm, and the book takes Sorted's spelling, so it files into the same folder. «Профессия: инквизиторы», «Профессия» and «Инквизитор» ask.
  - State: a pending, running or needs-attention job confirms nothing.
  - A stale job, by reading. A completed job keeps counting after the published check keeps it as "an exact authorized former-output retirement" (audio_jobs.py:484-486, a replaced book). So a series the replacement dropped still confirms. That is narrow: note, no finding. A job whose output was moved by hand turns "needs attention" at the next published check and stops counting.
- **M8, what is left** (local_identity.py:2617, siblings from `sibling_series` :2942-2980):
  - My 44 pass-5 split names, each beside two sibling book folders with the same pattern (numbers 11 and 12): 36 file by themselves under the junk folder, the same as on 067315f. The other 8 are real series and file right. On 0.22.2 all 44 filed unsplit.
  - 21 junk patterns in five layouts. With one sibling (a book folder, or a one-file book) every one asks. With two, every one files under the junk folder: two sibling book folders, two one-file books beside it in the author folder, or two beside it in the library root. One multi-file sibling book is enough too (m20).
  - Examples: «Шерлок Холмс. Аудиоспектакль 3. Финал» → `Иванов Петр\Шерлок Холмс. Аудиоспектакль\Шерлок Холмс. Аудиоспектакль - 3 - Финал - Иванов Петр.m4b`. Likewise «Курс истории. Лекция», "Hamlet. Act", «Ведьмак. Сборник», «Хроники Амбера N°», «Хроники Амбера_Книга», «Отцы и дети.Гл.», «Цикл «Хроники Амбера»» and «Карр Д Д - ШХ».
  - The cause: the siblings carry the same name pattern, so they confirm junk as readily as a real series. Numbered junk (a lecture course, radio plays, cassettes, a collection's volumes) comes in sets, so a set is the common case, not the rare one.
  - The any-word script check holds: «Sigmа Force» and «Хрoники Амбера» ask in every layout.
  - Live: «Отряд Сигма_01. …» now reads «Отряд Сигма» (the "_" strip), and files into it once siblings or Sorted confirm it. «Карр Д Д - ШХ 06. …» asks; the listings hold one such book.
- **M9** (public_research.py:1294-1305, before :1311 and :1319-1351; `approved()` settles the author as 'approved', :643):
  - Probe, with `_author_latin` stubbed to find "James Rollins" and the real `original_titles.translation`:
    - «Отряд Сигма 2. Карта костей» and «Отряд Сигма_01. Песчанный дьявол» by «Джеймс Роллинс». The row asks about the series. The lookup is never made (0 calls) and no rule is learned. Approve files `Роллинс Джеймс\Отряд Сигма\Отряд Сигма - 2 - Карта костей - Роллинс Джеймс.m4b`.
    - On 067315f the same names look up once, learn «Джеймс Роллинс» → Rollins James, and file under `Rollins James\Отряд Сигма\…`. On 0.22.2 they file under `Rollins James\`, unsplit.
    - Control: «Песчанный дьявол», with no series, looks up and files under Rollins James on all three trees.
  - Ruling 33: «Мир драконов 1. Начало» by "Ilya Marchenko" asks about the series instead of the spelling. Approve files it under `Marchenko Ilya` with no spelling question. 067315f and 0.22.2 ask the spelling.
  - By reading: the English original title that the same lookup returns (`found['title']`, ruling 38) is lost the same way, and so is the "Original title" fact. Approve's own ruling-49 step reads only the research cache, which the skipped lookup would have filled.
  - Older odd-name asks already came before these steps. Ruling 52 makes every unconfirmed split one of them.
- **m20** (local_identity.py:2958-2962; the docstring above still says "not directly under the library root"):
  - `folder_albums` counts files. A one-file book's siblings are every file in its folder, so one sibling book of four files is four votes.
  - In `Макс Фрай\`, «Мертвый ноль 7. Мертвый ноль.m4b» beside «Сновидения Ехо 4. …» and «5. …», one file each: «Сновидения Ехо», No. 7, which is ruling 45. Add one 4-file «Лабиринты Ехо 3. …» book, and it files as `Фрай Макс\Лабиринты Ехо\Лабиринты Ехо - 7 - Мертвый ноль - Фрай Макс.m4b`. With a 2-file one, the 2-2 tie asks.
  - In the library root, beside two one-file «Червь» books by Джон МакКрэй: `Фрай Макс\Червь\Червь - 7 - Мертвый ноль - Фрай Макс.m4b`. The one-file branch drops ruling 45's root limit, and no sibling vote checks the author.
  - The same with book folders in a shared `Unsorted\`: the same on 067315f. Ruling 45 never checked the author; I missed it in pass 1.
  - 067315f filed these as «Мертвый ноль» (M8); 0.22.2 asked.
  - One sibling book of two files also confirms a split by itself, where one sibling book folder does not.
- **m21** (public_research.py:895-901, then `settled` keeps identify's split series; :1287):
  - A record {title «Отряд Сигма_01. Песчанный дьявол», author «Джеймс Роллинс»} files by itself as `…\Отряд Сигма\Отряд Сигма - 1 - Отряд Сигма_01. Песчанный дьявол - Роллинс Джеймс.m4b`: the split series plus the whole name. With the author only, it files as `…\Отряд Сигма\Отряд Сигма - 1 - Песчанный дьявол - …`. «Курс истории. Лекция 3. Греция» files the same way, under the junk folder.
  - On 067315f the same, with «Отряд Сигма_». On 0.22.2 it files whole, under the author.
  - Who has such a record: 0.22.2's panel Save stored the title and author inputs as "Entered by you" (M3's history). 0.22.3 no longer writes them for a book, and a 0.22.3 panel Save replaces the record. So it takes a book saved in the 0.22.2 panel that is still unfiled and is researched again (a file change, an Edit names Save, or a rule learned for its credit).
- **Cost** (synthetic; note, no finding):
  - In a flat folder, one-file siblings add 3 ms (200 files), 17 ms (1,000) and 52 ms (3,000) to `identify`, which already takes 23 to 306 ms there on both trees.
  - `sorted_series` takes 34 ms (1,000 completed jobs of 16 KB) and 162 ms (5,000) on a cache miss, once after each completed job. Otherwise it takes 3 to 8 ms per `catalog_index` call, because its key query scans the table.
- **The page** (a note for Judy and Futaba, not a construction finding):
  - The row's ask shows Title and Author only (`askFieldPlanOf`, web/app.js:2516). The filled-in Series and Number show only in the Goes to path and in Edit names. No page code reads `ask.split` or `ask.fields.series`.
  - The reason line still says "The title starts with what looks like a series name and number", while the Title field shows the title without it.

**New findings (details under their dimensions):**
- **M9 [Major], new in 1138712:** the ruling-52 ask is built in the odd-name slot, before ruling 33's spelling question and ruling 39's lookup. Approve then settles the author, which turns both off. A foreign author credited only in Cyrillic files under the Cyrillic credit, with no lookup and no rule; a Latin name with a Russian first name is never asked. 0.22.2 did not have this: it looked the name up, or asked.
- **m20 [Minor], new in 1138712:** one-file siblings count files, not books, and the one-file branch drops ruling 45's root limit. One multi-file sibling book can outvote real siblings or confirm by itself, and another author's books in the root decide a title-repeat name.
- **m21 [Minor], new in 0.22.3 (ruling 41), not in this delta:** an "Entered by you" title or author skips the ruling-52 ask, and an entered whole name keeps the split's series beside it.
- **M8 stays open, narrowed:** a junk name with two siblings that carry it files by itself.

---

## Re-review at 067315f (fix delta 92376c7..067315f)

Ender fixed M6 with ruling 51 (4e8171a) and the m11 comment (067315f). I read both commits red-team style, ran the new tests on 92376c7 as a negative control, re-ran the pass-4 name hunt, and hunted 105 more names.

M6 is fixed for every name and spelling it listed. But the fix commit adds one Major of its own (M7), and the class M6 belongs to is still open (M8):

| Item | Status at 067315f | Evidence |
|---|---|---|
| **M6** | **Verified fixed for its 15 names and the spellings it named.** | The pass-4 hunt, 115 names: 17 go from a split to a question (the 15 M6 names, «Черная книга 2», "Star Wars Episode 4"). The other 98 keep their 92376c7 outcome, each equal to Ender's table. No name became a split, and no split changed its series. |
| **m11** (merge_service.py) | **Fixed.** One new stale line (dimension 8). | |
| **«Черная книга 2», "Star Wars Episode 4"** | **The safe side. Confirmed.** | Below. |
| **M7** (new) | **Major, new in 4e8171a.** `_LOOKALIKE` is bound twice. | A series folder with an upper-case Cyrillic look-alike («Аnita Blake», «Тhe Expanse») now files under that spelling. On 92376c7 and v0.22.2 it files as "Anita Blake". |
| **M8** (new) | **Major. New in 0.22.3, not in this delta.** M6's class, beyond the words in the list. | 54 of my 105 names, and a live name, «Отряд Сигма_01. Песчанный дьявол», file silently under a junk series folder. All split the same way on 92376c7; all filed unsplit on v0.22.2. |
| **m18** (new) | **Minor. New in 0.22.3, not in this delta.** | 10 names: the title after the split is not checked (a range, or a chapter abbreviation). |
| **m19** (new) | **Minor, new in 4e8171a.** | Siblings that ruling 51 asks about no longer vote in ruling 45. |

**What the probes showed**

- **M6 / ruling 51** (local_identity.py:2778-2797, :2873):
  - Pass-4 hunt, 92376c7 → 067315f: 33 splits stay splits, 43 whole stay whole, 20 questions stay questions, 2 held stay held, and 17 splits become questions. No error on any tree.
  - The turned-round check reaches past its own list. 11 of my new names went from a junk split on 92376c7 to a question:
    - "Star Wars Ep. 4", «Звёздные войны. Эпиз. 4», "Discworld No.1", «Хроники Амбера.№1», «Калейдоскоп.№ 2»;
    - a Cyrillic о in "Discwоrld", a Cyrillic "Bооk", «Хроники Амбера КНИГА 1», «Сага о Копье. T. 3» with a Latin T, "The Dark Tower Series 1";
    - and «Хроники Амбера Книга 1. Девять», an M6 shape with another title.
  - Controls still split right: «Хроники Амбера. КНИГА 1.», «Хроники Амбера.Книга 1.», «Хроники Амбера,Книга 1.», "Harry Potter-Book 1 -", «Ведьмак. Кн1.», "Discworld #1."
  - The skeleton fold makes only extra questions, never a split:
    - Latin "Tom", "T" and "Kh" fold to «том», «т» and «кн», so a series ending in them asks.
    - Only four all-Cyrillic strings fold onto a Latin marker: «воок», «вк», «рт» and «сн». None is a Russian word, and each would only ask. I checked every marker against the fold by script.
- **«Черная книга 2» and "Star Wars Episode 4"**: asking is the safe side.
  - Both ask (title_series) with a plain folder; «Черная книга 2» also asks with a folder named after the book. On 92376c7 they filed as series books («Черная книга», No. 2; «Star Wars Episode», No. 4). On v0.22.2 they filed unsplit.
  - Approve as shown files the whole name, «Черная книга 2. Возвращение», which is the 0.22.2 result. Sergei sets the series through Edit names.
  - In a series folder (`Иванов Петр\Черная книга\2. Возвращение`), the folder still decides. The book files as `Черная книга\Черная книга - 2 - Возвращение` on all three trees.
  - No live series is caught by this. «Межавторский цикл» ends in «цикл», which is not a marker, and its universe folder decides it anyway (`test_live_cases_0222` passes in the entry check).
  - The cost is one question per such book.
- **M7** (local_identity.py:2778 over :1783; `latin_lookalikes` :1786-1792, used at :2020):
  - 4e8171a adds `_LOOKALIKE = str.maketrans('авекмнорстухіј', 'abekmhopctyxij')` at module level. The name already held the table that `latin_lookalikes` uses: `str.maketrans('аеорсухкмтіАВЕКМНОРСТХІ', 'aeopcyxkmtiABEKMHOPCTXI')`.
  - Python looks the name up when the function runs, so the later binding replaces the table for every caller. It is the only module-level name the delta binds twice (scan of the module).
  - Unit probe:
    - On 92376c7 and v0.22.2: «Аnita Blake», «Сlive Barker» and «Тhe Expanse», each with an upper-case Cyrillic first letter, come back in Latin letters.
    - On 067315f: all three keep the Cyrillic letter, and «Discвorld» becomes "Discborld".
    - Lower-case а and о still fold, so the live Sigma Force folder is unaffected. That is why the suite passes.
  - End to end:
    - `Laurell K Hamilton\Аnita Blake\1. Guilty Pleasures` files as `Hamilton Laurell K\Аnita Blake\Аnita Blake - 1 - …`. A Latin "Anita Blake" folder sits beside it and looks the same.
    - On 92376c7 and v0.22.2 the book files as `Hamilton Laurell K\Anita Blake\…`.
    - «Тhe Expanse» files the same way.
- **M8** (local_identity.py:2786-2797): 105 names, by group. "Junk" means that the book files silently under a series folder named with the junk word.
  - A word the set does not hold (27 names, all junk). Examples:
    - «Курс истории. Лекция 3. …» → «Курс истории. Лекция»;
    - "The Hobbit. Track 3. …", "… Tape 2. …", «Мастер и Маргарита. Кассета 2. …»;
    - «Шерлок Холмс. Аудиоспектакль 2. …», «Ведьмак. Сборник 2. …», «Хроники Амбера. Роман 1. …»;
    - «Калейдоскоп номер 2. …» (English "number" is in the set; Russian «номер» is not);
    - «Червь. Арка 1. …», "Hamlet. Act 2. …", «… Песнь 5. …», "Perry Rhodan Band 1. …", «Аудиокнига 1. …», «Радиоспектакль 3. …».
  - A plural with a range (6 names, all junk): «Ведьмак. Книги 1 - 2. …» → «Ведьмак. Книги», No. 1, title «2. …». The same for "Books", «Тома», «Части», "Chapters" and «Диски».
  - An abbreviation with no dot, or one of five letters (6 names, all junk): "Star Wars Ep 4." → «Star Wars Ep»; «Эп», "Chap", «Сер», «Сез», "Chapt.".
  - A number sign other than «№» (3 names, all junk): «Хроники Амбера N°1.» → «Хроники Амбера N°»; "Discworld Nº 1.", «Хроники Амбера N 1.».
  - A marker joined to the word before it (6 names, all junk):
    - «Хроники Амбера_Книга 1.» → «Хроники Амбера_Книга»; «Хроники Амбера/Книга 1.»;
    - "Harry_Potter_Book 1 -", «Отцы и дети.Гл. 1.» → «Отцы и дети.Гл.», «Радиоспектакли.Вып. 3.», "Treasure Island.Ch. 1.".
    - The check reads only the last whitespace-separated token, so a joined marker is never seen.
  - A marker before the series name (6 names, all junk): «Цикл «Хроники Амбера» 1. …» and «Цикл «Хроники Амбера». Книга 1. …» → «Цикл «Хроники Амбера»»; «Серия «S.T.A.L.K.E.R.» 12. …», «Серия Сталкер 12.», «Трилогия «Тёмный эльф» 1.», «Цикл Хроники Амбера 1.».
  - A look-alike letter in a word that is not the last one (2 names): "Sigmа Force 2." files under «Sigmа Force» with the Cyrillic а; «Хрoники Амбера 1.» likewise. Ruling 51 names look-alike letters, but only the last word is checked.
  - Live names (Ender's read-only listings of Z: in `Docs/`):
    - «Отряд Сигма_01. Песчанный дьявол» (Rollins James; SortedRenames § 16) files as `Rollins James\Отряд Сигма_\Отряд Сигма_ - 1 - Песчанный дьявол - Rollins James.m4b`, whether the name is in the album or the title tag. Its sibling «Отряд Сигма 03 - Око Бога» files under «Отряд Сигма». On v0.22.2 it filed unsplit under the author.
    - «Карр Д Д - ШХ 06. Тайна закрытой комнаты» (NewAuthors Q26, not yet converted) files as `Doyle Arthur Conan\Карр Д Д - ШХ\…` with Doyle as the author, or `Карр Д Д\ШХ\…` with Carr. On v0.22.2 it filed unsplit.
    - The other 29 live names that split, split as before; none changed between 92376c7 and 067315f.
  - Dating: every M8 name splits the same way on 92376c7 and files unsplit on v0.22.2. So 4e8171a neither opened nor closed any of them. They came with ruling 41's split, which is new in 0.22.3.
- **m18** (local_identity.py:2868-2870, `_PART_TITLE` :2770): the title after the number is not checked.
  - A range or a second number:
    - «Ведьмак 1 - 2. Последнее желание. Меч предназначения» files as `Ведьмак\Ведьмак - 1 - 2. Последнее желание. …`;
    - the same for «Гарри Поттер 1 - 3. Сборник», «Ведьмак. Книга 1 - 2. Сборник», "Discworld 1 - 3. …", «Хроники Амбера 1 - 5. …» and «Хроники Амбера 2. 1. Карты судьбы» (No. 2, title «1. Карты судьбы»).
  - A part abbreviation:
    - «Хроники Амбера 1. Гл. 2» files as book 1, titled «Гл. 2»; the same for "Ch. 2", «Вып. 2» and «Части 1-2».
    - «Глава 2», "Track 2", «Трек 2», «Лекция 2», «CD 2» and «Кассета 2» are held as "One part of a bigger book".
  - The series folder is right in all 10. The number or the title is wrong, and the file name shows it.
  - All 10 split the same way on 92376c7, and filed unsplit on v0.22.2.
- **m19** (`sibling_series`, local_identity.py:2926):
  - Siblings go through `series_title_parts`, which now returns None for a name ruling 51 asks about. So such siblings no longer vote.
  - With «Сновидения Ехо №4 - …» and «Сновидения Ехо №5. …» beside «Мертвый ноль 7. Мертвый ноль», the book files as series «Мертвый ноль», No. 7. That is the series ruling 45 says it is not.
    - On 92376c7 it went to «Сновидения Ехо». The junk «№» spelling folded to the ruled spelling through ruling 46's key, by chance.
  - Add two clean siblings of «Лабиринты Ехо», and the same book files as `Фрай Макс\Лабиринты Ехо\Лабиринты Ехо - 7 - Мертвый ноль`, a series it is not in. On 92376c7 the 2-2 tie carried nothing.
  - With clean siblings (the live folder), it is unchanged: «Сновидения Ехо», No. 7.

**New findings (details under their dimensions):**
- **M7 [Major], new in 4e8171a:** the ruling 51 fold reuses the name `_LOOKALIKE`, which replaces the folder-structure fold for its one caller. An upper-case Cyrillic look-alike in a Latin series folder name is no longer read as Latin. The book files under a second folder that looks the same as the real one. 0.22.2 did not have this.
- **M8 [Major], new in 0.22.3, not in this delta:** M6's class. The test for a clean series name is still a closed list, so a marker outside it stays in the series name and files silently. One live name: «Отряд Сигма_01. …» → «Отряд Сигма_». 0.22.2 did not have this; it filed every such name unsplit.
- **m18 [Minor], new in 0.22.3, not in this delta:** the title after the split is not checked. A range or a chapter abbreviation files as a whole series book under the right series folder.
- **m19 [Minor], new in 4e8171a:** siblings whose names now ask no longer count for ruling 45. One rare layout files a book under a sibling series it is not in.

---

## Re-review at 92376c7 (fix delta d4a7450..92376c7)

Ender fixed M5, m15 and m16 (with ruling 50) and the three m11 comments. I read the three commits red-team style, ran the new tests on d4a7450 as negative controls, and ran 107 names end to end on four trees. Every fix does what its commit says, and every new test fails on the old code.

3ecfd23 adds no new split. Of the 107 names, 55 changed between d4a7450 and 92376c7. Each went from a split to unsplit (39) or to a question (16), never to another split.

What is new is one Major the name hunt found (M6). 15 names still file silently under a junk series folder. 9 of them did the same on 65ddd72, and 6 were opened by the m12 fix. I missed all 15 in passes 1 to 3.

| Item | Status at 92376c7 | Evidence |
|---|---|---|
| **M5** thousands group | **Verified fixed.** | My five pass-3 names now file unsplit (4) or ask (the «… Книга 1. …» one). On d4a7450 all five split as «Warhammer 40», No. 0. Six more spellings of the group hold too (below). |
| **m16 / ruling 50** | **Verified for the words it lists.** Three spellings are missed: M6. | 26 names with CD, Диск, Disc, Том, Т., т2, Часть, Ч., Глава, Chapter, Part, Pt., Vol. or Volume are unsplit now; each was a series book on d4a7450. «Книга N» still splits in 7 forms. |
| **m15** undo requeue | **Verified fixed. It reaches no further than it should.** | The new test fails on d4a7450. A partner book researched before the press is not requeued. A requeue that raises leaves the refusal and its undo as they were. |
| **m11** comments | **Fixed.** One new stale line (dimension 8). | |
| **M6** (new) | **Major, open.** | 15 names, below and under dimension 6. |

**What the probes showed**

- **M5** (local_identity.py:2757, :2852-2854):
  - The five pass-3 names:
    - «Warhammer 40 000. Ересь Хоруса», «Warhammer 40 000 - Ересь Хоруса», "Warhammer 40,000: Dawn of War" and «Вселенная Warhammer 40 000: Кайафас Каин. Герой Империума» file unsplit under the author. That is the 65ddd72 and 0.22.2 result.
    - «Warhammer 40 000: Ересь Хоруса. Книга 1. Возвышение Хоруса» asks (title_series).
  - Other ways to write the group. On d4a7450 all six split as «Warhammer 40», No. 0:
    - a dot ("40.000"), a no-break space, a narrow no-break space and a double space now file unsplit;
    - an apostrophe ("40'000", "40’000") gets past the lookbehind, and the zero check asks instead. So the zero check is a real backstop.
  - A number after the group: «Warhammer 40 000. Ересь Хоруса 2. Лживые боги», «… Ересь Хоруса - 02 - …», «… Ересь Хоруса #3 - …», «Warhammer 40 000 - 1. Ересь Хоруса» and "Warhammer 40K 1. …" ask. «Warhammer 40 000 1. Ересь Хоруса» files unsplit.
  - «Колесо времени 1.2. Око мира» files unsplit. On d4a7450 it went to the junk series «Колесо времени 1». «Колесо времени 1, 2. …» asks.
  - Position 0: «Ведьмак 0. …» and «Ведьмак 00. …» ask. 0.5 still splits as 0.5.
  - The lookbehind cannot make a new split. A later match carries the blocked digits in its series, and the digit check then asks. The 107 names agree.
  - Note, no finding: the two new asks also catch names that split correctly on d4a7450:
    - "Anita Blake 0 - Those Who Seek Forgiveness" (a real prequel), «13-й отдел 2. …», «Война 1812 года 2. …» and «Вселенная Метро 2033. Питер 2. …».
    - Asking is the safe side. The live Anita Blake book sits in its series folder, which still decides it (`OrderTests` passes in the entry check).
    - The Brief has no revisit trigger for these asks. One is worth adding if «Вселенная Метро 2033» books ask often.
  - Note, no finding: "S.T.A.L.K.E.R. 2 - 1. Зона" splits as «S.T.A.L.K.E.R.», No. 2, title "1. Зона", on 65ddd72, d4a7450 and 92376c7. The series' own number is read as the position. A title that itself starts with "N. " could ask. The name is my own invention; the repo's samples have none like it.
- **Ruling 50 / m16** (local_identity.py:2763, :2767-2768, :2840-2842):
  - These are unsplit now. Each split as a series book on d4a7450:
    - «Мастер и Маргарита. CD 1. Главы 1-10», «… Диск 2. …», «… CD 1.» with no dot, «- CD1 -», «CD-1», «CD 01», «, диск 1:», "Disc 1";
    - «Часть 1», «Ч. 1», «Ч.1», «Зеленая миля. Часть 2 - Мышь на миле», «Двенадцать стульев. Часть 1. Одиссея»;
    - «Том 2», «, т.2», «т2», «- Том 2 -», «Сага о Копье. Т. 3. Драконы», «Война и мир. Том 1 - Аудиоспектакль»;
    - «Глава 1», "Chapter 1", "Part 1", "Pt. 2", "Vol. 2", "Volume 2", "Kill Bill Vol 2".
  - «Отцы и дети. Главы 1-5. Приезд» asks. On d4a7450 it went to the junk series «Отцы и дети. Главы 1», No. 5.
  - «Книга N» still splits: «Хроники Амбера. Книга 1.», «Ересь Хоруса. Книга 2.», "The Wheel of Time, Book 3:", «Ведьмак. Кн. 1.», «Ведьмак - книга 1 -», «Ведьмак, книга 1:», and «Тёмная Башня. Книга 4.5.» as 4.5. «Книга 12:» asks, as before.
  - Missed: «Гл. 1», "Ch. 1", and «СD 1» typed with a Cyrillic С, still number a book in a series. See M6.
  - Note, no finding: the code goes further than ruling 50's three words.
    - An episode, season or issue set apart from the name now leaves it unsplit too: «Звёздные войны. Эпизод 4. Новая надежда», «Радиоспектакли. Выпуск 3. Ревизор», «Метро. Сезон 2. Питер». On d4a7450 these filed as series books.
    - That is the safe side, and the Brief records it under ruling 50. If Sergei wants an episode filed as a series book, it is one word list.
- **m15** (merge_service.py:3022, :3029-3040):
  - Ender's test fails on d4a7450 (`requeue` called zero times) and passes here.
  - Probe A: a partner book of the same credit is researched and held before the press. After the refusal, `changed_for` is False for it and nothing is requeued, on both trees. So the undo puts back only the books researched under the answer, not every book of the credit.
  - Probe B: `requeue` raises. The refusal still says "Destination changed", and the answer is still undone. The guard holds.
  - Quit: while the engine drains, `requeue` answers 'next_run' and starts nothing (pass 3).

**New finding (details under dimension 6):**
- **M6 [Major]:** a number marker that the split's word lists do not hold stays in the series name. The book files silently under a junk series folder named with it:
  - "Harry Potter Book 1 - …" → «Harry Potter Book»;
  - «Хроники Амбера №1. …» → «Хроники Амбера №»;
  - «Отцы и дети. Гл. 1. …» → «Отцы и дети. Гл».
  - There are 15 names in all, and every one filed unsplit on 0.22.2.

---

## Re-review at d4a7450 (fix delta 65ddd72..d4a7450)

Ender fixed M4, m12, m13 and m14 and the m11 comments, and added ruling 49. I read the six commits red-team style, ran the new tests on 65ddd72 as negative controls, and probed the next case over for each fix. Every fix does what its commit says. No fix loops, and every new test fails on the old code. What is new is one Major opened by the m12 fix (M5), and three Minors:

| Item | Status at d4a7450 | Evidence |
|---|---|---|
| **M4** queued Approve reported as refused | **Verified fixed.** Residual: m17 (Ender's stated gap). | Ender's Pause and Quit tests pass; both fail on 65ddd72. My probe makes the row read after `jobs.enqueue` raise once: the Approve answers with its job id and row, and «Koontz Dean» is kept. On 65ddd72 the same press raised and the answer was dropped. |
| **m12** split misfires | **Verified for its table.** It opens **M5** (Major) and **m16**. | Ender's table passes here and fails on 65ddd72. 24 more names end to end, below. |
| **m13** `changed_for` after the undo | **Verified. No loop.** Residual: m15. | The new test fails on 65ddd72. Loop probe below. |
| **m14** panel preview | **Verified fixed.** | Both new tests pass here and fail on 65ddd72. Every candidate goes through it (`candidate_identity` admits Audiobooks only; `namesLocked()` is true for every candidate), so no visible name input is overridden. |
| **Ruling 49** English original title on Approve | **Verified.** | Ender's test passes here and fails on 65ddd72. The lookup is cache-only: budget 0 raises `ResearchWait` before any request, and `_gap_fill` catches it. |
| **m11** comments | **Mostly fixed.** Three small items left (dimension 8). | |
| Ender's gap: the queue is not started after a failed row read | **Confirmed. Minor (m17), not blocking.** | Probe below. |

**What the probes showed**

- **M4** (merge_service.py:3083-3090, :3325-3328):
  - `approve_automatic` marks the press accepted as soon as `jobs.enqueue` returns. `enqueue` commits at the end of its `with` block and returns straight away, so nothing runs between the commit and the mark.
  - After the mark, `_approve_once` catches any `Exception`, and `_approve_book` and `approve_book` skip the undo and the names take-back.
  - For the three triggers (Pause settling, Quit, a failed row read) nothing is lost and nothing is reported as refused. Only a `BaseException` (KeyboardInterrupt, SystemExit) after the insertion still reports a failure, and it too keeps the answer and the names. On a server thread that is theoretical.
  - The page's queued route returns only `job_id` and `list_row` (web_server.py:432-435). So a `row` of None from `_queued_row` reaches no page code.
  - In the Quit case, the English-spelling save and `_continue_after_rule` now run during drain. `requeue` only writes the run's checkpoint, or returns 'next_run' while the run closes (automatic_processing.py:330-345). It starts nothing.
- **Ender's gap (m17):**
  - Probe: the row read fails once after the insertion. 3 s later the job is still `pending`, the worker has not started, and the state reads "Paused", although Sergei never paused. Start runs it to completed.
  - 65ddd72 left the same job unstarted, and reported the press as refused as well.
  - The trigger is rare: a read failure under the review and group locks, just after a committed insertion. Nothing is lost, and Start recovers it. While the run is approving books, its next approval starts the queue anyway.
- **m12** (local_identity.py:2755-2766, :2828-2842): 24 names end to end on the folder-structure helpers, on both trees.
  - Now right, and unsplit at 65ddd72:
    - «Хроники Амбера. Книга 1. …»;
    - «Сага о Копье. Т. 3. …»;
    - «Ересь Хоруса. Книга 2. Лживые боги»;
    - "The Wheel of Time, Book 3: The Dragon Reborn";
    - «Зеленая миля. Часть 2 - Мышь на миле».
  - Unchanged and right: «Агент 007 - Казино Рояль», «Метро 2033: Питер», and «Иванов. Книга 1. Начало» by Петр Иванов (the author's own name is no series).
  - The new asks: «Ведьмак 12: Сезон гроз» and «Перри Родан 101: Корабль» now ask (Title or author missing, title_series), where 65ddd72 filed them unsplit.
    - Asking is the safe side, and the Brief names its revisit trigger.
    - On that row, Approve as shown still files the name unsplit. Sergei sets the series through Edit names.
  - **M5:** «Warhammer 40 000: …» splits as series «Warhammer 40», No. 0.
  - **m16:** «CD 1», «Диск 2» and «Глава 1» now number a book in a series.
- **m13** (author_rules.py:116-120, :174), loop probe at rules level:
  - A research taken after the undo has the current generation and the newest stamp, because `stamp` is the maximum over every row, the undo pair included. It is never "changed" again, even after three unrelated rules are added. No loop.
  - The research taken in the press window stays "changed" until it is researched again. That is the fix.
  - Side effect, no finding: a research from before the press whose generation is stale for an unrelated reason is now also "changed", once (True here, False on 65ddd72). That costs one extra research and is bounded.
  - **m15:** nothing requeues the book researched in the window when the answer is undone (probe on the real MergeService).
- **m14** (merge_service.py:2588-2600; review_backend.py:532-551; web_server.py:1229-1231):
  - The preview goes through `_approval_result`, the same cached result as the row's Goes to line, so ruling 49 and Edit names reach it too.
  - A panel field left empty takes the row's value. A filled one is the panel's, which is what a Save with `names_row_only` keeps. `canonical_author` is a panel field, not one of the six.
  - An `OSError` from the book's source root is not caught here, so the line shows the server's error. The approve-preview route behaves the same. Display only.
- **Ruling 49** (public_research.py:636-669): probe with a cached English record for «Волшебники».
  - Plain Approve, and a typed author only: "The Magicians - Grossman Lev.m4b". With «Волшебники» typed as the title: «Волшебники - Grossman Lev.m4b». On 65ddd72 all three are «Волшебники».
  - The to-do row's Title proposal is the preview's title (merge_service.py:2349-2352). So the row, its Goes to line, the panel preview and the Approve agree.
  - Note, no finding: Edit names can't pin the Russian title.
    - Its editor reads the files' title, so a Save of «Волшебники» is "unchanged", and the next Approve files "The Magicians".
    - Typing the title on the row at Approve works.
    - This is a product question for Sergei, if he cares about it.
  - Note, no finding: `_approval_stamp` does not include the research cache.
    - A Goes to line computed before the cache learns the English title keeps the Russian one until another part of the stamp changes.
    - Approve uses the same cached result, so the path shown is still the path used.

**New findings (details under their dimensions):**
- **M5 [Major]:** a number written with a thousands space or comma ("Warhammer 40 000") splits at its last group. The book files silently under the junk series «Warhammer 40», No. 0. This is a regression against 65ddd72, and I missed it in pass 1.
- **m15 [Minor]:** after the m13 fix, the book researched in the press window is marked for research, but nothing requeues it. It shows as "Still checking" until a new run's scan.
- **m16 [Minor]:** the m12 strip makes a disc or a chapter («CD 1», «Глава 1») number a book in a series.
- **m17 [Minor]:** Ender's stated gap. After a failed row read the Approve stands, but the queue is not started, and the state reads "Paused" until Start.

---

## Re-review at 65ddd72 (fix delta 40d3c63..65ddd72)

Ender fixed M1, M2, M3, m1 and m4 from this review, and Futaba's M-1, m-1 and m-2. I read the delta red-team style and re-ran my pass-1 probes. Every fix does what its commit says for the case that was reported. Four gaps remain, three of them opened by these fixes:

| Item | Status at 65ddd72 | Evidence |
|---|---|---|
| **M1** refused-Approve undo | **Verified fixed.** New side effect: m13. | My pass-1 probes now pass on 65ddd72. P1, P3 and the older-learned-rule case all fail on 40d3c63. |
| **M2** ruling 45 too wide | **Verified fixed.** | My pass-1 probe: «Серия Б 3. Третья» keeps Серия Б, number 3. On 40d3c63 it moved to Серия А. The ruled title-repeat case still works. |
| **m4** split misfires | **Verified for the four examples.** It reaches too far: m12. | "Apollo 13:" and «Агент 007» are not split. «Ведьмак 01.5» files as 1.5. |
| **M3** hidden names saved | **Verified fixed.** Display-only residual: m14. | Stale hidden names are never saved, and no name enters "Entered by you". The never-saved-book case is unchanged from before. |
| **m1** post-queue error | **Verified for the case I probed.** Not closed for errors inside `approve_automatic` after the queue insertion: **M4**. | `restart_view` raising once: the Approve stands and the answer is kept. |
| **Futaba M-1** re-read after learning | **Verified. No loop and no repeated research.** | Two books of «Лев Гроссман» in one run: one research each, one re-read, one rule learned once, both converted under Grossman Lev. |
| **Futaba m-1** queued Approve's list row | **Verified** (read + tests). | Both the direct route and the queued outcome carry `list_row` when there is one. |
| **Futaba m-2** Quit waits for its host | **Verified. No kill by name or PID.** | `child.kill()` on our own spawned host only. The host's exit handler ends the shell as soon as the host exits. |

**What the probes showed**

- **M1** (author_rules.py:113-121, :62-68; merge_service.py:3012):
  - Probe P1: a Take back, then a refused press carrying a new answer. `taken_back` stays True and `same_as` stays `''`, so ruling 42 holds. `learned()` does not list the taken-back rule again. Run on the real MergeService and at rules level.
  - Probe P3: an accepted "Same author?" answer, then a refused "Different author" on a second row of the same credit. `same_as('Dean Koonts')` stays «Koontz Dean». Run on the real MergeService.
  - An older learned rule survives two refused presses in a row, and is listed again with Take back.
  - Undoing the same press twice is refused, and changes nothing.
  - A newer answer given after the press is not undone.
  - `retract()` now sees what `Rules` sees, so the rule back in force can be taken back.
- **M2** (local_identity.py:2601):
  - The ruled case still takes the siblings' series. «Мёртвый ноль 7. Мертвый Ноль» beside Серия А 1 and 2 goes to Серия А, number 7; the key folds case and ё.
  - The taken-number guard holds: «Крысы 2. Крысы» keeps Крысы when Серия А already has a 2.
  - The test now has the negative control I asked for.
- **m4** (local_identity.py:2759, :2823, `series_number`):
  - `_same_number('01.5', '1.5')` is True.
  - Correction to my pass-1 m4: «Война и мир. Том 1. Часть 2» was never filed. End to end, both trees hold it as "One part of a bigger book". Only `series_title_parts` mis-split it.
- **M3** (review_backend.py:554-558; web/app.js:776-783, :798; web_server.py:1242-1244):
  - Server, saved draft: a Save with stale hidden title, series and number keeps the saved draft's names («Book», `''`, `''`). The new "Entered by you" record has no name field, and its other fields are saved.
  - Server, never-saved book (the missing negative control): its first Save writes empty names into the draft. That is the same as before the fix, because the panel inputs were already empty for such a book (`app.js:508`). The record carries no name.
  - HTTP: `names_row_only` is allow-listed and must be a boolean.
  - Page: the panel sends the flag and the saved names (test case 7).
- **m1** (merge_service.py:2770-2779, :3003-3009, :3069): my pass-1 probe makes `restart_view` raise once. On 65ddd72 the Approve answers with its job id, the job completes, and the answer is kept. On 40d3c63 the press raised. `_press_after` is now fully guarded, and the requeue after an accepted answer is guarded too.
- **Futaba M-1** (public_research.py:884-887, :1093-1109):
  - The re-read is local only (`identify` + `with_names`): no network, no requeue, no recursion.
  - It runs once per research, and only when that research learned a rule.
  - On 40d3c63 the same probe never finishes its run, and one book stays held.
  - Ruling 48 ("B") settles the open product part.
  - Note, no finding: the re-read skips the "Entered by you" `settled` step (public_research.py:873-878). The approval's `revalidate` compares `identify` with the same re-read summary, so no misfile follows. It only matters for a book with an old manual title whose credit also learns a rule.
- **Futaba m-2** (desktop/quit-watch.js:42-53; desktop/main.js:364-373, :528-534):
  - `endOwnEngine` closes the pipe and waits up to 30 s. Then it calls `child.kill()` on `state.backend`, which is Node's handle-based TerminateProcess on the ChildProcess we spawned, and waits 5 s more.
  - There is no `taskkill`, no `process.kill(pid)` and no image-name kill in the delta. Every kill in desktop/main.js is `child.kill()` on a child it spawned itself.
  - The engine closes its server socket only at the end of shutdown, and its own watchdog (`EXIT_AFTER` = 20 s) forces its exit after that. So on an accepted Quit, the shell's kill is a backstop that should not fire.
  - The refused or silent path (m3) is unchanged: 30 s, then the kill.

**New findings (details under their dimensions):**
- **M4 [Major]:** an Approve whose job is already queued is still reported as refused, and takes his answer back. This happens when Pause is still settling or Quit arrives. The code is older than this delta, but the m1 commit claims to cover it.
- **m12 [Minor]:** the m4 fix reaches too far. "Series N: Title" and "Series 00N. Title" now file silently with the series inside the title. «Хроники Амбера. Книга 1. …» no longer splits at all. This is a regression against 40d3c63.
- **m13 [Minor]:** after the M1 fix, `changed_for` cannot see the app's undo. A book researched while the refused press's answer was in force is never researched again. This is a regression against 40d3c63.
- **m14 [Minor]:** the panel's "Unsaved destination preview" still builds its path from the hidden name inputs. This is a residual of M3.

---

## Summary

0.22.3 does eleven things:
- It fixes the false panel lock: only edits Sergei made count.
- Approve files a Russian edition under its English original title, from the research cache, as automatic filing does; a typed title wins (ruling 49, pass 3).
- It adds "Series N. Title" splitting (ruling 41), the sibling-folder series (ruling 45) and one spelling per series (ruling 46).
- A name that numbers a disc, volume, part or chapter is never split into a series book (ruling 50, pass 4).
- A split files by itself only when its series name is clean; otherwise the app asks (ruling 51, pass 5).
- A split files by itself only when something confirms its series: a series folder in Sorted for the same author, or a series tag. Otherwise the row asks with Series, Number and Title filled in (ruling 52, pass 6). Siblings that only repeat its name pattern confirm nothing, and Sergei's Approve of a set's first book files the rest, even while its job is queued (ruling 53, pass 7).
- It changes the refused-Approve undo. The English-spelling answer is saved only after acceptance. The "Same author?" answer is written first and taken back by an app retraction.
- Author rules now follow chains. A cached catalog's Latin name is learned as a rule. There is a read-only learned-rules route with Take back, and Take back asks once.
- Quit: the engine answers at once, and the shell resends Quit and falls back to the pipe stop.
- Gate: each worker has its own deadline, and `test_inplace_m4b.py` runs as two halves.
- Page: save feedback and blocked-reason lines.

The new code has no security problem. The rule-chain loop is bounded. The quit kill only ever ends our own child. The panel-lock fix is correct.

Pass 1 found the breakage in three places: the refused-Approve undo (M1), ruling 45 (M2) and the hidden name inputs (M3). All three are fixed and verified at 65ddd72.

Pass 2 found M4: an Approve that was already in the queue could say it was refused, and take back the answer it carried. Pass 2 also found three Minor side effects of the fixes (m12, m13 and m14). All four are fixed and verified at d4a7450, and ruling 49 is in.

Pass 3 found M5: a thousands-group number like «Warhammer 40 000: …» filed silently in the junk series folder «Warhammer 40», at No. 0. Pass 3 also found two Minors, m15 and m16. All three are fixed and verified at 92376c7, with ruling 50.

Pass 4 found M6: a number marker that the split's word lists did not hold stayed in the series name, so the book filed silently in a junk series folder ("Harry Potter Book", «Хроники Амбера №»). It is fixed and verified at 067315f with ruling 51. All 17 names it covers now ask, and the other 98 names of the pass-4 hunt keep their outcome.

Pass 5 found M7 (the look-alike table renamed by accident) and M8 (M6's class beyond the list), and m18 and m19. M7, m18 and m19 are fixed and verified at ddfbfa7. Ruling 52 narrows M8 to sets.

Pass 6 found M9 (the series question came before the author's lookup and spelling question) and left M8 open for sets, with m20 and m21. Pass 7 verified M9, M8's sets (ruling 53) and m21's first half, and narrowed m20 (ruling 54).

Pass 8 verified M10, Futaba's M-1, m20 and m22. What is open after pass 8 is four Majors. None loses data:
- **M11, new in 798001a.** Approve as shown on a question that comes before the series question (ruling 33's spelling, no author, two credits) never files. Each press says "Your answer is saved … its series is asked next", saves nothing, and the same question comes back. 51caef1 filed these books; 0.22.2 filed them unsplit.
- **M12, new in 798001a.** A series Sergei corrects at one Approve renames that series for every book of the author, in any folder, for good: book 19 moved to «City Watch» makes «Discworld 20» and «21» file as `City Watch - 20` and `- 21`, with no row. With m22's fill-in, «Сновидения Ехо 4» and «5» file under «Мертвый ноль».
- **M13, new in 798001a, Sergei's call.** A releasing Approve continues a run Sergei stopped, and starts a whole new run when none is running. Both file other books.
- **M14, older than 0.22.2.** A 'keep' rule files a Cyrillic credit given-name first by automatic filing and surname first by Approve; the release now splits one set between the two folders.
- Fix M11 and M12 before shipping, and ask Sergei about M13.

What was open after pass 7 (kept as history) is one Major. It misfiles; it loses no data, and the audio is intact.
- **M10, new in the fix commit b2f8660.**
  - When the first book of an unconfirmed set is asked about its author ("Same author?", ruling 39's English spelling, ruling 33's spelling), Sergei answers with Approve. That Approve files the book's split and never asks the series. The series shows only inside the Goes to path.
  - Ruling 53 then takes that Approve as the set's answer. The answer's rule puts the author's other books back on the run, and they file by themselves under the split's series, with no row: «Курс истории. Лекция 2. Рим» → `Koontz Dean\Курс истории. Лекция\…`.
  - On ddfbfa7 the other books asked the series. 0.22.2 filed these names unsplit.
  - The fix: count a queued job as the set's answer only when its Approve answered the series question, and keep the series question for a book whose author question comes first. One test each.

Minors open after pass 7 (m20, m22 and m11 fixed in pass 8): m20 (uncredited siblings vote for any author; a book with two album spellings votes twice), m21's second half (in the backlog), m22 (ruling 45's override confirms a junk set's series), m17 (the queue is not started after a failed row read), and m11 (the Brief has no rows for rulings 53 to 55). Open after pass 8: m21's second half, m17, m23 (a split book with no author loses its series from the file name), m9 (the gate at 84 %) and the older ones.

---

## Rubric

### 1. Security

- Status: Pass
- Findings: none.
  - Electron webPreferences are unchanged: context isolation on, sandbox on, no Node in the renderer.
  - The new `/api/author-rules` route is a token-checked POST that only reads.
  - A learned rule's source link is rendered only for http(s) and opens externally.
  - No new shell-outs. The Quit fallback kills only `state.backend`, our own native host. There is no PID or image-name kill.
  - No secrets were added.
  - Pass 2: `names_row_only` is allow-listed in the route's shape and type-checked as a boolean. The only new kill is `child.kill()` on our own host (Futaba m-2, verified above). No new shell-out and no secret.
  - Pass 3: no new shell-out, kill, route or secret. The routing-preview route is the same token-checked POST, and `reviews.routing_preview` still bounds the review it is sent. Ruling 49's lookup reads the research cache only, so no new request leaves the machine.
  - Pass 4: no new shell-out, kill, route, file operation, request or secret. The m15 change is one guarded call to an existing function. The rest is two regular expressions and comments.
  - Pass 5: no new shell-out, kill, route, file operation, request or secret. The change is string handling only: one linear `\S+` scan, a translate table and a set lookup. No pattern can backtrack badly.
  - Pass 6: no new shell-out, kill, route, file write, request or secret. `sorted_series` opens the catalog read-only (`mode=ro`, `query_only`), the same way `catalog_index` and `confirmed_spellings` do; its path goes through `Path.as_uri()`, which quotes spaces, `#`, `?` and brackets. Any read error yields {}, so the book asks. `_unsure_title` adds three anchored patterns with no nested repeats.
  - Pass 8: no new shell-out, kill, route, file write, request or secret. `_release` calls the existing `requeue` and `request_start`; `_answer_then_ask_series` writes through the existing `entered_names.save` and English-spelling rule. `sorted_series` stays read-only.
  - Pass 7: no new shell-out, kill, route, file write, request or secret. `sorted_series` gains one clause on the same read-only connection. `_continue_after_series` reads the catalog's own tables and calls the existing `requeue`, guarded, after the Approve is accepted; a failure there never refuses the Approve.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **M2 [Major] — FIXED in 2be2d0b, verified at 65ddd72.** `local_identity.py:2600`. Ruling 45's override also fired when the name "names another series". It was not limited to a name that repeats its title, which is the case Sergei ruled. The result was that any book of a second series was moved, silently, into the series its siblings carry, unless its number was already taken there.
    - Pass-1 probe, end to end on `test_folder_structure.OddNameTests` helpers. «Серия Б 3. Третья» sits beside «Серия А 1. Первая» and «Серия А 2. Вторая». It got reasons `[]`, series «Серия А», number 3. It went to `…\Иванов Петр\Серия А\Серия А - 3 - Третья - Иванов Петр.m4b`, with no question.
    - At 65ddd72 the same probe gives series «Серия Б», number 3, `…\Серия Б\Серия Б - 3 - Третья - Иванов Петр.m4b`. The ruled case and the number guard still hold (see Re-review).
  - **M11 [Major] — new in pass 8, opened by 798001a (the M10 fix). A regression against 0.22.2 and 51caef1.** `merge_service.py:3083` and `_answer_then_ask_series` (`:3173-3192`).
    - When the book's series is unconfirmed and the held question is not the series question, every Approve raises `SeriesAsked`. Only a title or author that differs from the proposal is saved (`:3183`), and the page sends one only when it differs (`askValues`). So "Approve as shown" saves nothing, and the book asks the same question again.
    - Probes, three presses each, on the real MergeService and the real run: ruling 33's spelling ("Ilya Marchenko"), a book with no author, two credits in two tags, two people in one credit. Every press answers "Your answer is saved. The book is checked again with it, and its series is asked next …"; nothing is saved, nothing is filed, the same question is back. 51caef1 filed each book; 0.22.2 filed them unsplit.
    - The ways out (another candidate, a typed value, a series in Edit names) are nowhere on the row; a book with no author has no value to pick.
    - Major: a common press stops working for a class of books, with a message that says the opposite. Nothing is lost.
    - Fix: when the Approve saves nothing (no rule, no spelling, no typed value), treat the shown author as answered: save it as his entered author (or a 'keep' rule for the credit) before releasing; or let the author-question row carry the split's Series and Number so one Approve answers both. Add a test: Approve as shown on ruling 33's question and on a book with no author, with a split; it must not raise twice.
  - **M12 [Major] — new in pass 8, opened by 798001a. A regression against 0.22.2 and 51caef1.** `local_identity.py:3026-3031` (`sorted_series` maps the job's `series_answer.asked` to his series for every book of the author) with `merge_service.py:3130-3155` (every held book carrying either name is released).
    - Ruling 53 says the rest of the set follows his answer. The code applies it to every book of the author whose split carries the asked name, in any folder, now and later (the completed job keeps the mapping).
    - Probes:
      - Discworld 19 approved as "City Watch" No. 3: «Discworld 20. Hogfather» (same folder) and «Discworld 21. Jingo» (another folder) file as `Pratchett Terry\City Watch\City Watch - 20 - Hogfather - …` and `- 21 - Jingo - …`, no row. 51caef1: both ask.
      - m22's fill-in: «Мертвый ноль 7. Мертвый ноль» asks with «Сновидения Ехо»; set to «Мертвый ноль», it makes «Сновидения Ехо 4» and «5» file as `Фрай Макс\Мертвый ноль\Мертвый ноль - 4 - …` and `- 5 - …`.
      - Later books: one completed job with the mapping makes a later «Discworld 20. Jingo» alone in another folder file under «City Watch», and a later «Сновидения Ехо 8» under «Мертвый ноль». With a plain Discworld job too, the job rows' order decides.
    - The editor's series change is also an Edit names fix (series is a FIXED field, author scope, since 0.22.2), which reaches the same books when they are next researched. On 51caef1 it never fired in my run, because nothing researched them; the release now does at once.
    - Major: a silent misfile of whole series, from one answer about one book; the sources are removed after conversion.
    - Fix: confine "the rest follow" to the books released by that Approve (its set: the same parent folder, or the ids `_continue_after_series` found), and record no lasting alias; or only when his series keeps the asked name as a prefix (a rename, «Курс истории. Лекция» → «Курс истории»), never when it moves the book. Do not carry an answer made on an override's fill-in to the siblings. Tests: the Discworld and «Мертвый ноль» cases.
  - **M10 [Major] — FIXED in 798001a, verified at cf166bf, for answers that save something. It opens M11.** "Same author?" keeps its rule, the English spelling its rule, typed names their entries; nothing is filed, the series is asked next, and only a series-question Approve releases the set (Ender's tests fail on 51caef1; my English-spelling probe agrees). The pass-7 text follows. An Approve that answered an author question files the book's unconfirmed split, and the rest of its set then files by itself.
    - Where:
      - `public_research.py:1348-1349`: `his` skips the series question when the title or author is 'approved', which `approved()` sets for every Approve (`:643`), whatever question the row asked.
      - The asks before it: "Same author?" (`:1242-1250`), the odd-name asks (`:1289-1300`), and, since this delta, ruling 33's spelling (`:1301-1308`) and ruling 39's English spelling (`:1336-1341`).
      - `local_identity.py:3016-3018`: `sorted_series` counts any queued or converting job of Sergei's (`metadata_actor` 'user') as confirming its series.
      - `merge_service.py:2955-2980` (`_continue_after_rule`) and `:3104` (`_continue_after_series`) put the other books back on the run at once.
    - Probes on the real MergeService, two-book sets «Курс истории. Лекция 1. Греция» and «… 2. Рим», the first job held in the queue (table under Re-review at 51caef1):
      - "Same author?" answered Same on book 1: book 1 files `Koontz Dean\Курс истории. Лекция\…`; book 2, researched again, files there by itself with no row. ddfbfa7: book 2 asks the series.
      - Ruling 39's English spelling (lookup inconclusive), "James Rollins" typed: book 1 is never asked the series (ddfbfa7 asked it first, then M9 broke the author). It files `Rollins James\Курс истории. Лекция\…`, and book 2 follows by itself.
      - Ruling 33, Marchenko Ilya picked: book 1 is never asked the series. Book 2 asks the spelling again, and its Approve does the same.
    - What follows: a junk set by such an author files under the junk folder, though Sergei never saw a series question, only an author one. For the books after the first there is nothing to see at all. The sources are removed after conversion, so only a manual move puts them right.
    - The trigger needs an unconfirmed split (the names ruling 52 exists to catch) on a book whose author is asked. Junk titles («Греция», «Финал») rarely match a catalog record, so ruling 39's lookup is likely to come back inconclusive for exactly these books.
    - Major, as M8 and M9 were. 0.22.2 filed these names unsplit; ddfbfa7 asked the series for every book but the one approved.
    - My pass-6 fix for M9 ("build the ask after the author steps") is what put ruling 33's and ruling 39's questions in front. I did not follow it through to the Approve that answers them.
    - Why the suite passed: every ruling-53 test approves through the series question. No test answers an author question on a book with an unconfirmed split.
    - Fix:
      - record what an Approve answered (the held ask's `why`, or his entered series) in the job's manifest, and let `sorted_series` count a queued job only when it answered the series question;
      - for a book whose author question comes first, keep the series question. Either the author answer learns its rule and puts the book back on the run, or the author ask carries the split's Series and Number fields. Which one is a product call for Sergei and Judy;
      - add a test: "Same author?" and the English-spelling answer on the first of a two-book set; the second book must ask. It should fail on b2f8660.
  - **M9 [Major] — FIXED in b2f8660, verified at 51caef1. It opens M10.** The ruling-52 ask is built after ruling 33's spelling question and ruling 39's lookup (`public_research.py:1342-1355`). Ender's two tests fail on ddfbfa7. My probe: «Отряд Сигма 2. Карта костей» by «Джеймс Роллинс», one lookup, the rule learned, then the series question; Approve files `Rollins James\Отряд Сигма\Отряд Сигма - 2 - Карта костей - Rollins James.m4b`. The pass-6 text follows. `public_research.py:1294-1305` (the ruling-52 ask, in the odd-name slot) returns before `:1311` (ruling 33's spelling question) and `:1319-1351` (ruling 39's lookup and its English title). Approve then files through `approved()` → `settled(..., 'approved')` (`:643`), so `sergei` (`:1287`) is True and both steps are skipped for good.
    - A foreign author credited only in Cyrillic with no rule yet, whose name splits and is not confirmed, files under the Cyrillic credit. No lookup is made and no rule is learned.
    - Probe, with `_author_latin` stubbed to find "James Rollins" and the real `original_titles.translation`: «Отряд Сигма 2. Карта костей» by «Джеймс Роллинс» asks the series, makes 0 lookups and learns nothing. Approve files `Роллинс Джеймс\Отряд Сигма\Отряд Сигма - 2 - Карта костей - Роллинс Джеймс.m4b`. On 067315f: one lookup, the rule «Джеймс Роллинс» → Rollins James, `Rollins James\Отряд Сигма\…`. On 0.22.2: `Rollins James\`, unsplit. «Отряд Сигма_01. …» behaves the same.
    - Ruling 33 the same way: «Мир драконов 1. Начало» by "Ilya Marchenko" asks the series, and Approve files `Marchenko Ilya\…` with no spelling question. 067315f and 0.22.2 ask the spelling.
    - By reading: the English original title the lookup returns (ruling 38) and the "Original title" fact are lost too. Approve's ruling-49 step reads only the research cache, which the skipped lookup would have filled.
    - What follows: the author's books split between `Роллинс Джеймс\` and `Rollins James\`. His later books look the name up and go to the Latin folder, because nothing learned it. The audio is intact; only a manual move puts the first one right.
    - It reaches every unconfirmed split by a foreign author in Cyrillic, which is common in Sergei's library, wherever no rule exists yet. Sergei sees the Cyrillic folder only inside the Goes to path. So this is Major, like M5 to M8. 0.22.2 did not have it.
    - Why the suite passed: `test_folder_structure` patches `original_titles.translation` to False for the whole module (`setUpModule`), so ruling 39 never runs beside a split, and no ruling-39 test has a series in the name.
    - Fix:
      - build the ruling-52 ask after the author steps, just before `build_policy`, so ruling 33 asks first, ruling 39 looks up and learns, and the ask's author is the settled one;
      - or have Approve of a ruling-52 ask settle only the title, series and number;
      - add a test with a foreign author in Cyrillic and a series split, seen to fail on ddfbfa7.
  - **M14 [Major] — new to this review (pass 8). Older than 0.22.2; not in any reviewed delta.** `local_identity.py:2339-2342` (a 'keep' rule takes the credit as written) against `approved()`, which files the same credit surname first.
    - «Карта костей» by «Джеймс Роллинс» with a 'keep' rule: automatic filing goes to `Джеймс Роллинс\Карта костей - Джеймс Роллинс.m4b`, Approve to `Роллинс Джеймс\Карта костей - Роллинс Джеймс.m4b`. The same on cf166bf, 51caef1 and 0.22.2.
    - End to end on cf166bf: the English spelling kept as shown, then the set's series question. Book 1 (Approve) files `Роллинс Джеймс\Курс истории. Лекция\…`, book 2 (released) `Джеймс Роллинс\Курс истории. Лекция\…`.
    - A 'keep' rule comes from a "keep this name" answer (ruling 39), the lookup's "written in Russian" result, and a "different" answer to "Same author?". I checked a Cyrillic credit only; a Latin one is untested.
    - Major, as M7 was: one author silently split between two folders. Not a regression of 0.22.3, but the release makes it reach whole sets. Worth checking against the live Sorted folder before choosing which order wins.
    - Fix: put a 'keep' credit through the same surname-first step as Approve (ruling 33), or have Approve keep the credit as written; one test for both paths.
  - **m22 [Minor] — FIXED in 798001a, verified at cf166bf.** The override fills in the siblings' series and confirms it only when Sorted or a tag does (`local_identity.py:2610-2629`); my pass-7 probe now asks, and Ender's test fails on 51caef1. The fill-in feeds M12 when Sergei corrects it. The pass-7 text follows. New in pass 7. It came with rulings 45 and 53 (new in 0.22.3); this delta did not change it. `local_identity.py:2611-2614` (ruling 45's override, now `overridden`, confirms the series it carries).
    - The override confirms whatever series two siblings carry, and only `_unsure_series` checks it. Ruling 53 says that same set confirms nothing for its own books.
    - Probe: in `Иванов Петр\Шерлок Холмс\`, «Финал 3. Финал» beside «Шерлок Холмс. Аудиоспектакль 1. …» and «… 2. …» files as `Иванов Петр\Шерлок Холмс. Аудиоспектакль\Шерлок Холмс. Аудиоспектакль - 3 - Финал - Иванов Петр.m4b`, while the two siblings ask. The same on ddfbfa7; 0.22.2 asks.
    - Minor: it needs a name that repeats its title beside a set of another pattern. The live case («Мертвый ноль» among «Сновидения Ехо») is right.
    - Fix, or a ruling for Sergei: let the override confirm only a carried series that something else confirms (Sorted, a tag, his Approve); otherwise ask with the override filled in.
  - **m20 [Minor] — FIXED in 798001a, verified at cf166bf.** Uncredited siblings vote only for an uncredited book, and votes are counted by series and number, once per book (`local_identity.py:2972-2997`). Ender's tests, my two pass-7 cases among them, fail on 51caef1. The pass-7 text follows. NARROWED in b2f8660 (ruling 54), verified at 51caef1. Credited siblings vote once per book, only for the same author, and never in the library root (`local_identity.py:2970-2978`, `folder_books` at `:920`, `:945`). Ender's test fails on ddfbfa7, and another author's book folders in `Unsorted\` now ask. Two cases are left:
    - `same_author` (`:2972`) lets an uncredited sibling vote for any author. Two uncredited one-file «Червь» books beside «Мертвый ноль 7. Мертвый ноль» by Макс Фрай file it as `Фрай Макс\Червь\Червь - 7 - Мертвый ноль - Фрай Макс.m4b`, in `Unsorted\` or in `Макс Фрай\`; uncredited book folders do the same. Ender's commit makes this choice; ruling 54's text does not say.
    - The one-file branch counts album strings, not catalog books. One two-file book whose files carry «Темная» and «Тёмная», or "… CD1" and "… CD2", is two votes, and with no other sibling it files «Мертвый ноль 7. Мертвый ноль» into «Лабиринты Ехо», No. 7. The catalog groups it as one book.
    - Both behave the same on ddfbfa7; 0.22.2 asks.
    - Fix: count siblings by the catalog's book groups (or by `series_key`, once per book), and let an uncredited sibling vote only for an uncredited book, or ask.
    - The pass-6 text follows. `local_identity.py:2958-2962` (`sibling_series`, the one-file branch).
    - `folder_albums` counts files, so a one-file book's siblings are every file in its folder. One sibling book of four files is four votes. The branch also runs in the library root, which ruling 45's limit (the docstring, `:2943-2948`) still excludes. No vote checks the author.
    - Probes:
      - In `Макс Фрай\`, «Мертвый ноль 7. Мертвый ноль.m4b» beside one-file «Сновидения Ехо 4. …» and «5. …» files as «Сновидения Ехо», No. 7, which is ruling 45. Add one 4-file «Лабиринты Ехо 3. …» book, and it files as `Фрай Макс\Лабиринты Ехо\Лабиринты Ехо - 7 - Мертвый ноль - Фрай Макс.m4b`. With a 2-file one, the 2-2 tie asks.
      - In the library root, beside two one-file «Червь» books by Джон МакКрэй: `Фрай Макс\Червь\Червь - 7 - Мертвый ноль - Фрай Макс.m4b`.
      - Book folders in a shared `Unsorted\` give the same «Червь», No. 7, on 067315f as well: ruling 45 never checked the author. I missed that in pass 1.
      - 067315f filed the first two as «Мертвый ноль» (M8); 0.22.2 asked about all three.
      - One sibling book of two files in the same folder also confirms a split by itself, where one sibling book folder does not.
    - The wrong series needs a name that repeats its title, and a mixed or shared folder. That is rare, so this is Minor, as m19 was.
    - Fix: one vote per sibling book (row), not per file; keep the root limit for the one-file branch; count only siblings credited to the same author, or at least never let them override a title-repeat name.
  - **m19 [Minor] — FIXED in 1138712, verified at ddfbfa7.** Siblings whose names ask vote again, and carry a clean spelling or none (`local_identity.py:2963-2977`). Both pass-5 probes now give «Сновидения Ехо», No. 7, and a filled-in ask with the «Лабиринты Ехо» pair. Ender's test fails on 067315f. Two more of mine: «№» siblings alone, with no ruled spelling, carry nothing, so the book asks; one «№» sibling and one clean one carry the clean spelling. The pass-5 text follows. `local_identity.py:2926` (`sibling_series` reads siblings through `series_title_parts`) with `:2873`.
    - A sibling whose name ruling 51 now asks about returns None, so it no longer votes for the series of its parent folder.
    - Two probes, with «Мертвый ноль 7. Мертвый ноль» in `Max Fray\Сновидения Эхо\`:
      - Siblings «Сновидения Ехо №4 - …» and «Сновидения Ехо №5. …» only: the book files as series «Мертвый ноль», No. 7, which ruling 45 says it is not. On 92376c7 it went to «Сновидения Ехо». The «№» spelling folded to the ruled spelling through ruling 46's key, by chance.
      - Add two clean siblings «Лабиринты Ехо 1. …» and «… 2. …»: the book files as `Фрай Макс\Лабиринты Ехо\Лабиринты Ехо - 7 - Мертвый ноль - Фрай Макс.m4b`, a series it is not in. On 92376c7 the 2-2 tie carried nothing.
    - With clean siblings, as in the live folder, nothing changes («Сновидения Ехо», No. 7).
    - It needs a name that repeats its title, two or more siblings with an unclean name, and, for the wrong series, two clean siblings of another series in the same folder. That is rare, so this is Minor.
    - Fix: let a sibling vote by its series key whether its own split is 'split' or 'ask'. Carry only a clean spelling: a 'split' sibling's, or the ruled one.
  - **m6 [Minor]** `web/app.js:3205` `noteLeavers`. Any current list answer requested after the press counts as "the reload". If Sergei pages, filters or searches right after a Save or Approve, the strip says "It left this list" and offers Show it for a book that only left the view. Open.
  - **m7 [Minor]** `web/app.js:4103`. `loadAuthorRules` runs at page start while the engine is still loading. `/api/author-rules` is in LOOKING only once `books` has loaded, so the first read gets 409 and the list reads "Author rules learned online · unavailable" for up to 30 s after every start. Open.
  - **m14 [Minor] — FIXED in a59914d, verified at d4a7450.** A book's preview is now planned by the engine (`MergeService.routing_preview`) from the row's names and metadata facts. The pass-2 text follows. `web/app.js:53-59` `queueRoutingPreview`, with `review_backend.py:532-544` `routing_preview`.
    - When Sergei types in a book's panel, say a Reader, the "Unsaved destination preview" line is built from the hidden name inputs. The M3 fix did not touch this path, and the server's preview applies no Edit names.
    - So while the panel is dirty, the line can show a path made from the saved draft's names:
      - names from before a row Edit names Save;
      - "Confirm the book title" for a book never saved;
      - never the names his row uses.
    - The row's "Goes to" line meanwhile shows the real path.
    - It is display only; nothing is saved.
    - Fix: for a book, build the preview from the row's names, or show the row's "Goes to" instead.
    - Two smaller points:
      - The server takes `names_row_only` on the page's word. Enforcing it for every Audiobooks candidate would not depend on the page.
      - `sendMetadata` reads the flag from the current `selectedRow`, not from the row being sent.

### 3. Crash / Stability Safety

- Status: Concerns
- Findings:
  - **m1 [Minor] — FIXED in f93455c for the case probed, verified at 65ddd72. The wider gap is M4.** `merge_service.py:2991-3001` and `:1577-1584`. `_approve_book` caught `BaseException` around all of `_approve_once`, including the code after `approve_automatic` had queued the job. `_press_after` → `restart_row` → `restart_view` was guarded only for `sqlite3.Error`. Any other exception there did two things: the accepted Approve reported a failure, and it retracted the "Same author?" answer.
    - Pass-1 probe: `restart_view` raises `RuntimeError` once. The press raised. The job ran and completed under «Koontz Dean». `rule('Dean Koonts')` was None.
    - The same gap made a names Save that was saved report a failure.
    - At 65ddd72, the same probe gives the Approve's job id and keeps the answer. `_press_after` is fully guarded (`:2770-2779`), the requeue is guarded (`:3007-3009`), and the names Save test passes.
  - **M4 [Major] — FIXED in 9e8c0c1, verified at d4a7450. Residual: m17.** The press is accepted when `jobs.enqueue` returns (`merge_service.py:3327`). After that, Start refused, the press's stop or a failed row read leave the job queued and every answer kept (`:3084-3090`). Both new tests fail on 65ddd72, and so does my row-read probe. The pass-2 text follows. `merge_service.py:3292-3311`, with `:3069` and `:3005` (pass-2 lines).
    - `press['accepted']` is set only when `approve_automatic` returns. Inside `approve_automatic`, three things still run after `jobs.enqueue` (`:3292`): `reviews.enrich` (`:3293`), `if stop.is_set(): raise InterruptedError()` (`:3309`) and `self.resume(recheck=False)` (`:3311`). Any of them can raise.
    - When one raises, the job is already durable in the queue, but the press is reported as refused and the "Same author?" answer is taken back.
    - Two ordinary states trigger it. Both probes ran on the real MergeService, and 40d3c63 behaves the same:
      1. **Pause is settling.** `_pause_depth` is 1, which is what `pause()` holds while the queue reaches its checkpoints. The Approve raises `StartRefused: Pause is still reaching the queue checkpoints. Retry Start after it completes.` The job is `pending` under «Koontz Dean», and `same_as('Dean Koonts')` is `''`. The action queue does not hold an Approve during Pause (`action_queue.py` `blocker`), so this is reachable from the row.
      2. **Quit arrives just after the queue insertion** (`drain()` sets the press stop). The Approve raises `Books Arranger is closing. The book was not approved.` The job is pending, and the answer is taken back.
    - What follows:
      - The row says the Approve was refused. Pressing it again answers "Audiobook job already exists".
      - His "Same author?" answer is gone, so the credit's other books ask again.
      - An English-spelling answer is never saved, because it is saved only after `approve_automatic` returns (`:3072`).
      - With the names editor open and not closing, `approve_book` takes his names back (`:2993`) while the queued job carries them. The queue's names check then sets that job aside. I found this by reading only; I did not probe it.
      - No file is at risk.
    - Fix:
      - End the rollback scope at the queue insertion: mark the press accepted when `jobs.enqueue` returns.
      - Treat `resume`'s `StartRefused` after the insertion as "queued, starts when the queue settles" (ruling 35), never as a refusal.
      - Once the job is in the queue, do not raise on `stop`.
      - Add the two probes above as tests.
  - **m17 [Minor] — new in pass 3; Ender's stated gap, confirmed.** `merge_service.py:3328` (the row read after the insertion) and `:3090`. `:3346` (`resume`) never runs then.
    - When the row read after `jobs.enqueue` fails, the Approve is accepted and kept, but `resume` is skipped.
    - The job waits as pending, the worker never starts, and the state reads "Paused" until Sergei presses Start.
    - Probe: 3 s after the press the job is still `pending`, and the worker is not running. Start runs it to completed.
    - This does not block:
      - the trigger is rare (a read failure under the review and group locks, just after a committed insertion);
      - nothing is lost;
      - the row says it is queued;
      - Start, or the run's next approval, starts it.
    - Fix: in the accepted branch of `_approve_once`, call `self.resume(recheck=False)`, guarded, unless the error was the press's stop or a `StartRefused`.
  - **m3 [Minor]** `desktop/main.js:518-524` with `:363`. After a silent or refused Quit, the shell closes the pipe and kills its host after 30 s. Open; unchanged at d4a7450.
    - The kill does not consult `critical_sections`, which the update path waits for. It relies on crash recovery instead: the in-place M4B journal, SQLite WAL replay, and the stale-owner retirement. That recovery exists, so no data loss was found.
    - `finish_shutdown` alone can take longer than 30 s. It waits on admissions with no bound, joins the inventory for 20 s, and joins merge threads for 30 s each. So under load the kill is the likely end, not the exception.
    - Each forced stop leaves an ownership record. The next start keeps it as `web-instance.stale-*.json`, so these files pile up in the data folder.
    - Consider a longer bound, or a bound that waits while `critical_sections` are open.
    - Pass 2: Futaba m-2's change gives the same 30 s bound and kill to an accepted Quit whose engine has gone (`engineGoneExit`). There it is only a backstop: the server socket closes at the end of shutdown, and the engine forces its own exit 20 s later.

### 4. Performance

- Status: Concerns
- Findings:
  - **m5 [Minor]** `web/app.js:160`. While a Take back is pending, `pressTick` calls `renderAuthorRules()` every second. That rebuilds up to 200 rule entries, so a mouse press that lands on a rebuilt button can be lost. Focus is restored for the keyboard only. `controls()` now also re-renders from 2 s instead of 3 s. Open.
  - **m8 [Minor]** `author_rules.py:118-123`. The new chain resolution for every known author costs about 32 ms per `Rules()` at 8,000 job authors and 533 rules (synthetic data; the 0.22.2 loop took 2.6 ms). `load()`'s cache key includes `audio_jobs` `max(updated)`, which moves several times a second during a conversion, so the rebuild repeats while converting. This is small now and worth knowing. Open. Pass 2: the M1 filter adds one pass over the rows, which is negligible.
  - Pass 3, no finding: ruling 49 adds a few cache reads (FantLab, then Wikidata) to each `approved()` that is not already cached. `_approval_results` caches the answer, so a listed row pays them once.
  - Pass 6, no finding (synthetic data):
    - One-file siblings (`local_identity.py:2958-2962`) split every other file's album in the folder, once per copy, so a flat folder costs O(n²). They add 3 ms (200 files), 17 ms (1,000) and 52 ms (3,000) per `identify`, which already takes 23 to 306 ms there on both trees.
    - `sorted_series` (`:2983`) runs on every `catalog_index` call. Its key query scans `audio_jobs`: 3 ms at 1,000 completed jobs and 8 ms at 5,000. Each completed job changes the key, and the next call re-reads every manifest: 34 ms and 162 ms at 16 KB each.
    - Worth knowing if the library grows; counting each album once would remove the repeats.
  - Pass 7, no finding (synthetic data): `_continue_after_series` (`merge_service.py:3108-3131`) runs after every accepted Approve, bulk Approve as is included, and parses every held record: 62, 75 and 172 ms at 500, 2,000 and 5,000 held records of 16 KB. `sorted_series`'s key query gains one count over the same scan.

### 5. State & Data Safety

- Status: Concerns
- Findings:
  - **M13 [Major] — new in pass 8, opened by 798001a. New against 0.22.2. A product call for Sergei.** `merge_service.py:3157-3167` (`_release` → `automatic.request_start`, `automatic_processing.py:371-387`), called by `_continue_after_series` and by every M10 / M11 press (`:3191`).
    - A run Sergei stopped ('Paused — pending work saved') continues when an Approve releases books, and a new run (with its discovery pass) starts when none is running.
    - Probes on the real run: with another book in the stopped run's saved list, the Approve of a set's first book makes the run Running within a second, and «Другая книга» is filed and its source removed. With the run ended and a new book copied in, a new run discovers and files «Новая книга». On 51caef1 the run stays Paused, or ended, and only the approved book is filed.
    - `stop()` says a start Sergei or the app stopped "must never come back by itself". The app's safety stops end in the same state; by reading, a release continues them too unless the queue blocks the start (not probed).
    - Ender records the paused case in the Brief as Sergei's call, and Start over (O9) already continues a run. Major all the same: an explicit Stop is undone by an ordinary press, and the work it resumes removes sources.
    - Fix, if Sergei agrees: for a stopped run, requeue into its saved list and leave it stopped, with the row saying the rest wait for Start; for an ended run, research only the released books, with no discovery.
  - **M1 [Major] — FIXED in 1f80255, verified at 65ddd72. Side effect: m13.** `merge_service.py:3003` (`_drop_answer_rule`) with `author_rules.py:113` and `:213`. The undo of a refused Approve was an app retraction. Rules counted it as a newer `none` row for the credit, which hid every older row for that credit, not just the answer it undid. Three cases, each probed in pass 1:
    1. **An earlier accepted answer was erased.** Sergei answers "Same author?" on one row, and that Approve is accepted. A second row of the same credit still shows the stale question. He answers it, and that Approve is refused. Result: `same_as('Dean Koonts')` went from «Koontz Dean» to `''`. (Probe P3 on the real MergeService.)
    2. **His Take back was erased, which broke ruling 42.** A refused Approve carrying an answer replaced his `user` retraction with an `app` one, which `taken_back()` ignores. Result: `taken_back` changed from True to False, and the next research looked the name up again. (Probe P1.)
    3. **An older learned rule was erased.** «Бром» → Brom was in force before the press. After a refused press, `same_as('Бром')` was `''`. (Helper probe.)
    - At 65ddd72, `Rules` drops an app retraction together with the rule it retracts, and `retract()` applies the same view. All three probes pass on the real MergeService and at rules level; on 40d3c63 all three fail. The new test covers all three cases.
  - **m13 [Minor] — FIXED in 6817bb3, verified at d4a7450. No loop. Residual: m15.** `Rules.undone` keeps the dropped pairs, and `changed_for` counts them. The pass-2 text follows. `author_rules.py:160-177` `changed_for`, with `:116-121`.
    - `changed_for` looks for a rule newer than the research among `self.rules`. The app's undo row is no longer in `self.rules`, and the rule back in force is older than the research.
    - So a book researched while the refused press's answer was in force (between the answer's commit and its undo, during the approval's file checks, hashing and probes) is never researched again. Its stored research was decided by an answer that is no longer kept.
    - Probe: a research taken with the answer in force (`same_as` → «Koontz Dean»), then the undo, then `changed_for(record)`. It returns False on 65ddd72 and True on 40d3c63.
    - At worst, that one book is filed under the answer Sergei gave on a press that was then refused. The window is narrow, and the result matches his own answer.
    - Fix: keep the dropped undo pairs, with their `saved_utc` and credit, and count them in `changed_for`.
  - **m15 [Minor] — FIXED in 117044f, verified at 92376c7.** `_drop_answer_rule` now calls `_continue_after_rule(skip=id)`, guarded (`merge_service.py:3039`). Ender's test fails on d4a7450. My probes show that a partner book researched before the press is not requeued, and that a requeue which raises leaves the refusal as it was. The pass-3 text follows. `merge_service.py:3029-3037` (`_drop_answer_rule`), with `:2286`.
    - After m13, `changed_for` marks the book researched in the press window. But the undo calls no `_continue_after_rule`, so nothing puts that book back on the run.
    - `needs()` then counts it as "Still checking" and leaves it off the to-do list until a new run's scan (`rules_changed_for`, automatic_processing.py:630). That is the 0.22.0 M-1 state again.
    - Probe on the real MergeService:
      - A second «Dean Koonts» book is researched inside the refused press, with the answer in force. The probe gives it a hold of its own.
      - After the refusal: `changed_for` is True, `requeue` is called zero times, the book is not listed, and `still_checking` is 1.
      - On 65ddd72 the book stays listed, with research that the undone answer decided.
    - It is narrow. It needs three things: the run researches a book of that credit during the press's file checks; that book stays held for another reason; and the press is refused.
    - Fix: call `_continue_after_rule(skip=id)`, guarded, in `_drop_answer_rule`, as the accepted path does.
  - **M3 [Major] — FIXED in 7012da8, verified at 65ddd72. Display residual: m14.** `web/app.js:776` and `:3240`, with `review_backend.py:609`. Ruling 40 hides and disables the six name inputs for a book, but `metadataReview()` still sent them, and `reviews.save` captured them as an "Entered by you" manual metadata source on every Save preview metadata.
    - While the panel is dirty, a list refresh does not refill them. 0.22.3 lets the row's Edit names Save run while the panel is dirty, so the hidden inputs kept the names from before that save.
    - Pass-1 probe (fake DOM, real `app.js`): Save preview metadata sent `title="Saved" series="Old series"` from the hidden inputs. `compare_research` then flagged "Saved manual metadata disagrees with researched identity" over a value Sergei could not see or edit.
    - At 65ddd72:
      - The page sends the saved draft's names and `names_row_only`.
      - The server keeps the saved draft's names and leaves the six name fields out of the "Entered by you" record.
      - The probes and the negative control are under Re-review.
  - **m2 [Minor]** `merge_service.py:2868-3001`. The "Same author?" undo is not atomic. Open.
    - The answer is committed in its own transaction before the approval. The job is queued in later transactions, and the requeue (`_continue_after_rule`) runs after that.
    - A crash in between leaves the rule in force with no Approve. So does power loss, or the Quit's own 30 s kill (m3) while Approve is hashing files. Sergei's books answered by the rule are then not requeued until a new run's scan, which is the 0.22.0 M-1 "Still checking" state again, in that window.
    - For the English-spelling answer, a crash after the job is queued and before the rule is saved loses the rule. This is documented and accepted: his other books ask again.
    - No file is at risk.

### 6. Input Handling

- Status: Concerns
- Findings:
  - **m4 [Minor] — FIXED in 2be2d0b for the examples, verified at 65ddd72. The fix reaches too far: m12.** `local_identity.py:2756` and `:2804`. `_NOT_A_SERIES` rejected only a series that is just a part word. In pass 1 these split as follows:
    - «Война и мир. Том 1. Часть 2» → series «Война и мир. Том», No. 1, title «Часть 2». Correction: end to end, the part check holds this book as "One part of a bigger book" on both trees, so it was never filed.
    - "Apollo 13: The Untold Story" → series Apollo, No. 13.
    - «Агент 007 - Казино Рояль» → series «Агент», No. 7.
    - «Ведьмак 01.5. Меч» kept "01.5", not "1.5", so `_same_number('01.5', '1.5')` was False against the folder form.
    - At 65ddd72 the first three are not split, and «Ведьмак 01.5. Меч» files as 1.5.
  - **m23 [Minor] — new in pass 8. It came with ruling 41's split (new in 0.22.3), not with this delta.** On 51caef1, Approve of «Курс истории. Лекция 1. Греция» with no author anywhere filed `Без автора\Греция.m4b`: the split's title is kept, and the series and number are dropped from the name. 0.22.2 filed the whole name. Two such sets with a «… 1. Греция» would collide on the name. On cf166bf the book cannot be approved as shown (M11); by reading, its series-question Approve files the same way. Fix: for a book with no author, keep the whole name, or put the series into the file name.
  - **m21 [Minor] — first half FIXED in b2f8660, verified at 51caef1; the second half is open (backlog, 0.22.4).** An entered title or author alone no longer skips the series question: only his Approve or his saved series or number does (`public_research.py:1348`). Ender's test (an entered author) fails on ddfbfa7; an entered title takes the same path by reading. The row now asks, and the Goes to line shows the split's series beside the entered whole name. The pass-6 text follows. `public_research.py:895-901` (an "Entered by you" title or author: `settled(..., 'entered')` keeps identify's split series) with `:1287` (`sergei` skips the ask at `:1294`).
    - A book whose current "Entered by you" record holds a title or author files its unconfirmed split by itself. An entered whole name keeps the split's series beside it.
    - Probes (title + author, author only, title only, and a junk name):
      - {title «Отряд Сигма_01. Песчанный дьявол», author «Джеймс Роллинс»} → `…\Отряд Сигма\Отряд Сигма - 1 - Отряд Сигма_01. Песчанный дьявол - Роллинс Джеймс.m4b`. Title only gives the same.
      - Author only → `…\Отряд Сигма\Отряд Сигма - 1 - Песчанный дьявол - …`.
      - «Курс истории. Лекция 3. Греция» → `Иванов Петр\Курс истории. Лекция\Курс истории. Лекция - 3 - Курс истории. Лекция 3. Греция - Иванов Петр.m4b`.
      - On 067315f the same, with «Отряд Сигма_». On 0.22.2 all file whole, under the author.
    - Who has such a record: 0.22.2's panel Save stored the title and author inputs as "Entered by you" (see M3). 0.22.3 no longer writes them for a book, and a 0.22.3 panel Save replaces the record. So it takes a book saved in the 0.22.2 panel that is still unfiled and is researched again: a file change, an Edit names Save, or a rule learned for its credit.
    - Minor: the trigger is narrow, and the folder is under the right author. But it is the one path I found where a split nobody confirmed files without Sergei having seen a series.
    - Fix: when an entered title differs from the title the split left, drop the split's series and number (or split the entered title instead); and let `sergei` skip the ruling-52 ask only when the series and number are his.
  - **M7 [Major] — FIXED in 1138712, verified at ddfbfa7.** The ruling-51 table is `_MARKER_FOLD` (`local_identity.py:2798`); `_LOOKALIKE` (`:1786`) is bound once again.
    - Unit: «Аnita Blake», «Сlive Barker» and «Тhe Expanse» come back in Latin letters; "Discвorld" stays as it is, as on v0.22.2. End to end, `Laurell K Hamilton\Аnita Blake\1. Guilty Pleasures` files as `Hamilton Laurell K\Anita Blake\Anita Blake - 1 - …`. On 067315f, both fail.
    - Ender's new test has the upper-case look-alikes and fails on 067315f.
    - Module scan (top-level names bound twice) on ddfbfa7: only `KNOWN_AGREEMENT_VERSIONS` and `GIVEN_NAMES`, both bound twice on v0.22.2 too, outside this range.
    - The pass-5 text follows. `local_identity.py:2778` rebinds `_LOOKALIKE`, defined at `:1783`. `latin_lookalikes` (`:1786-1792`) reads the table when it runs. Its one caller is the folder structure's series name (`:2020`).
    - The new table folds lower-case letters for `_skeleton`. The old one turned Cyrillic look-alikes, upper case included, into Latin, inside a word that is mostly Latin.
    - Since 4e8171a, every call of `latin_lookalikes` gets the new table:
      - an upper-case А, В, Е, К, М, Н, О, Р, С, Т, Х or І is no longer read as Latin;
      - a lower-case в or н now becomes b or h ("Discвorld" → "Discborld").
    - Probes (unit and end to end, on 067315f, 92376c7 and v0.22.2):
      - `latin_lookalikes('Аnita Blake')`, with a Cyrillic А, returns it unchanged on 067315f, and "Anita Blake" on both older trees. «Сlive Barker» and «Тhe Expanse» behave the same.
      - `Laurell K Hamilton\Аnita Blake\1. Guilty Pleasures` files as `Hamilton Laurell K\Аnita Blake\Аnita Blake - 1 - Guilty Pleasures - …`. On the older trees it goes to `…\Anita Blake\…`. «Тhe Expanse» does the same.
      - The live Sigma Force folder (a lower-case Cyrillic а) still files as "Sigma Force", because the new table folds lower-case а too. That is why the entry suite passes: no test has an upper-case look-alike.
    - What follows:
      - one series gets two folders whose names look the same, and the books split between them silently;
      - the sources are removed after conversion, so only a manual rename puts it right;
      - the audio is intact and under the right author.
    - Sergei's library has look-alikes in Latin series folder names; item 9 added `latin_lookalikes` for the live «Sigmа Force». A look-alike in the first, upper-case letter of a word is just as likely.
    - So this is the same kind of silent misfile as M5 and M6, and it is Major. 0.22.2 did not have it.
    - Fix:
      - give the ruling 51 table its own name, or build `_skeleton` on the existing table after `casefold`;
      - add a `latin_lookalikes` test with an upper-case look-alike, seen to fail on 067315f;
      - scan for other module-level names bound twice. My scan found only this one in the delta.
  - **M8 [Major] — FIXED for its sets in b2f8660 (ruling 53), verified at 51caef1. What is left goes through M10 and m22.** Siblings that carry the same series no longer confirm it (`local_identity.py:2611-2629`; only ruling 45's override, `overridden`, does).
    - 21 junk patterns, each the third of a set, in four layouts (two sibling book folders, two one-file books in the author folder or the library root, one 4-file sibling book): 84 of 84 ask on 51caef1, and 84 of 84 file under the junk folder on ddfbfa7. Ender's two sets fail on ddfbfa7.
    - The set's first Approve, through the series question, files the rest while its job is queued (Ender's test, my control).
    - The pass-6 text follows. `local_identity.py:2617` (a sibling carrying the same series key confirms), with `sibling_series` (`:2942-2980`).
    - On a book alone it is closed. Every M8 name this report names (rebuilt from its text; the pass-5 probe file is gone), and the live «Отряд Сигма_01. …» and «Карр Д Д - ШХ 06. …», ask: filled in, or with nothing filled in. 0 of 277 names file by themselves alone.
    - With two siblings that carry the same name pattern, the junk still files by itself. My 44 pass-5 split names, each beside two sibling book folders numbered 11 and 12: 36 file under the junk folder, as on 067315f, and 8 are real series. 21 junk patterns behave the same with two one-file books beside them, in the author folder or the library root, and with one multi-file sibling book (m20).
      - «Шерлок Холмс. Аудиоспектакль 3. Финал» → `Иванов Петр\Шерлок Холмс. Аудиоспектакль\Шерлок Холмс. Аудиоспектакль - 3 - Финал - Иванов Петр.m4b`; likewise «Курс истории. Лекция», "Hamlet. Act", «Ведьмак. Сборник», «Хроники Амбера N°», «Хроники Амбера_Книга», «Отцы и дети.Гл.», «Цикл «Хроники Амбера»», «Карр Д Д - ШХ».
      - With one sibling, all ask. The mixed-script names ask in every layout.
    - The cause: the siblings' series is the same parse of the same naming pattern, not a second source. Numbered junk (a lecture course, radio plays, cassettes, a collection's volumes) comes in sets, so the set is its common case.
    - The code does what ruling 52 says: "sibling books carrying that series" confirm. So the rest is a product call for Sergei, through Jane:
      - (a) siblings confirm only a series name that also passes the cheap structural checks from my pass-5 fix (no "_", "/" or a dot joined to a letter; no sign other than a letter at the end; no «Цикл», «Серия» or «Трилогия» in front);
      - (b) a set is asked once: one question for the books that carry the pattern, and his answer files them all;
      - (c) accept it: every such set files under the name its files carry.
    - 0.22.2 filed every one of these unsplit.
    - The pass-5 text follows. `local_identity.py:2786-2797` (`_unsure_series` reads only the last whitespace-separated token and checks it against `_MARKERS`).
    - Ruling 51 turned the check round for the words in the set, for any abbreviation of four letters or fewer with a dot, for «№», and for a mixed-script last word. A marker outside those still stays in the series name, and the book files silently under a junk series folder.
    - My pass-4 advice for M6 was itself a list ("any marker word … from any of the lists"). Ender built what I advised, so the gap is in my advice as much as in the code.
    - 54 of my 105 new names file under a junk folder on 067315f (examples under Re-review at 067315f):
      - a word the set does not hold (27): «Лекция», "Track", "Tape", «Кассета», «Аудиоспектакль», «Сборник», «Роман», «номер», «Арка», "Act", "Band" …;
      - a plural with a range (6): «Ведьмак. Книги 1 - 2. …» → «Ведьмак. Книги», title «2. …»;
      - an abbreviation with no dot, or of five letters (6): "Ep", «Эп», "Chap", «Сер», «Сез», "Chapt.";
      - a number sign other than «№» (3): "N°", "Nº", a Latin "N";
      - a marker joined to the word before it by "_", "/" or a dot with no space (6): «Хроники Амбера_Книга», «Отцы и дети.Гл.»;
      - a marker word before the series (6): «Цикл «Хроники Амбера»», «Серия Сталкер».
    - Two more file under a look-alike spelling ("Sigmа Force", «Хрoники Амбера»). Ruling 51 names look-alike letters, but only the last word is checked.
    - Two live names from Ender's read-only listings of Z: split the same way:
      - «Отряд Сигма_01. Песчанный дьявол» (Rollins James, SortedRenames § 16) → `Rollins James\Отряд Сигма_\Отряд Сигма_ - 1 - Песчанный дьявол - Rollins James.m4b`, while «Отряд Сигма 03 - Око Бога» goes to «Отряд Сигма»;
      - «Карр Д Д - ШХ 06. Тайна закрытой комнаты» (NewAuthors Q26, not yet converted) → «Карр Д Д - ШХ» or «ШХ», depending on the author.
    - Every M8 name splits the same way on 92376c7 and files unsplit on v0.22.2.
    - What follows is what follows M5 and M6: a junk folder per series and marker, the series and number wrong, and only a manual rename once the sources are removed. The audio is intact and under the right author.
    - Major, as M6 was. A live name shows that it reaches Sergei's library.
    - Fix. No word list can close this. Three steps, cheapest first:
      1. Structural checks, which need no words:
         - ask when the series name holds "_", "/" or a dot joined to a letter, or ends in a sign that is not a letter («Отряд Сигма_», "N°");
         - ask when any word mixes scripts, not only the last;
         - ask when the series begins with цикл, серия, трилогия or дилогия, words `_SERIES_WORDS` already strips at the end (not сага or chronicles: «Сага о Копье» is a series name);
         - ask when the last word is an all-caps or undotted abbreviation of three letters or fewer that is not a known series («ШХ», "Ep").
      2. Words by category, not by spelling: the parts of a recording (lecture, lesson, track, tape, cassette, side, act, arc, canto), containers (audiobook, collection, radio play), plurals, and the book word in German or Ukrainian (Band, Частина).
      3. The real turn-round, a product call for Sergei: file a split by itself only when something else names the same series. That is a sibling, a series folder, a tag, or another book in the catalog with the same series key and another number. Otherwise ask. The live measurement for `_series_in_title` (91 questions, 31 of them «Червь») is the data to weigh, and the catalog would corroborate «Червь».
      - Add these names as end-to-end controls, each seen to fail on 067315f.
  - **m18 [Minor] — FIXED in 1138712, verified at ddfbfa7.** `_unsure_title` (`local_identity.py:2822`) asks when the title left starts with a number, a marker, or a word and a number.
    - My 10 names ask with nothing filled in, alone and with Sorted holding the series; on 067315f all 10 filed as book 1 or 2 with the stray number or part word in the title. The 6 held as "One part of a bigger book" stay held. Ender's test fails on 067315f.
    - Note, no finding: it also asks real titles that start with a word and a number («Метро 2. Метро 2034», «S.T.A.L.K.E.R. 12. Зона 51», «Discworld 26. Death 5. Thief of Time»), even when confirmed. That is the safe side.
    - The pass-5 text follows. `local_identity.py:2868-2870` (`rest` is checked only against `_PART_TITLE`, `:2770`).
    - The ruling 51 check looks at the series side only. A title that begins with a number, or with a part abbreviation the title list does not hold, files as a whole series book.
    - In all 10 names the series folder is right. Each split the same way on 92376c7, and filed unsplit on v0.22.2:
      - «Ведьмак 1 - 2. Последнее желание. Меч предназначения» → `Ведьмак\Ведьмак - 1 - 2. Последнее желание. …` (an omnibus filed as book 1). The same for «Гарри Поттер 1 - 3.», «Ведьмак. Книга 1 - 2.», "Discworld 1 - 3.", «Хроники Амбера 1 - 5.», and «Хроники Амбера 2. 1. Карты судьбы» (No. 2, titled «1. Карты судьбы»).
      - «Хроники Амбера 1. Гл. 2» → book 1, titled «Гл. 2». The same for "Ch. 2", «Вып. 2» and «Части 1-2». «Глава 2», "Track 2", «Трек 2», «Лекция 2», «CD 2» and «Кассета 2» are held as "One part of a bigger book".
    - Minor: the folder is right, the file name shows the stray number or part word, and I found no live name of this shape in the docs.
    - Fix: ask (title_series) when the title after the number starts with a digit, or with any word or abbreviation in `_MARKERS`, folded the same way.
  - **M6 [Major] — FIXED in 4e8171a with ruling 51, verified at 067315f. The class remains open as M8.** `_unsure_series` (`local_identity.py:2786-2797`, called at `:2873`) asks rather than splits when the series name is not clean.
    - All 15 names, «Черная книга 2» and "Star Wars Episode 4" ask. The 98 others in the pass-4 hunt keep their outcome. The new test fails on 92376c7.
    - The check also catches 11 of my new names that split as junk on 92376c7 (see Re-review at 067315f).
    - The pass-4 text follows. `local_identity.py:2757-2770` (pass 4: the marker word lists), with `:2839-2842`.
    - New in pass 4. 9 of its names split the same way on 65ddd72; 6 were opened by the m12 fix.
    - The split knows a fixed set of marker words. A marker that is not in the set stays inside the series name. The book then files silently, with no question, under a junk series folder. End to end on the folder-structure helpers (all paths under `…\Иванов Петр\`):
      - A book word with no punctuation before it (opened by m12; these were unsplit on 65ddd72):
        - "Harry Potter Book 1 - The Philosopher's Stone" → `Harry Potter Book\Harry Potter Book - 1 - The Philosopher's Stone - Иванов Петр.m4b`;
        - "Discworld Book 1 - …", "The Wheel of Time Book 3 - …" and "The Wheel of Time Book 3: …" go the same way;
        - «Хроники Амбера Книга 1. Девять принцев Амбера» → «Хроники Амбера Книга».
        - "The Hobbit, Ch. 1: An Unexpected Party" → «The Hobbit, Ch». 65ddd72 left it unsplit only because it refused every ":".
      - Number signs and abbreviations (split the same way on 65ddd72):
        - «Хроники Амбера №1. Девять принцев Амбера» and «… № 1. …» → «Хроники Амбера №»;
        - «Калейдоскоп № 2. Мистика и ужасы» → «Калейдоскоп №»;
        - "Discworld No. 1. …" → «Discworld No»;
        - "The Wheel of Time Bk. 3 - …" → «The Wheel of Time Bk».
      - Part words that ruling 50 means but the lists do not spell (split the same way on 65ddd72):
        - «Отцы и дети. Гл. 1. Приезд» → «Отцы и дети. Гл»;
        - «Радиоспектакли. Вып. 3. Ревизор» → «Радиоспектакли. Вып»;
        - «Доктор Кто. Серия 3. Далеки» → «Доктор Кто. Серия». `_NOT_A_SERIES` lists «серия», but neither tail list does;
        - «Мастер и Маргарита. СD 1. Главы 1-10», typed with a Cyrillic С → «Мастер и Маргарита. СD».
    - On 0.22.2 all 15 filed unsplit under the author.
    - The 9 that split on 65ddd72 were missed in passes 1 to 3. The 6 from m12 were missed in pass 3, when I tried only the words in the lists.
    - Sergei's library uses «№»: the repo's own samples have «Калейдоскоп № 1» and «Пртоколы SCP. Сейф №1». It also holds English series (Sigma Force, Anita Blake). "Series Book N - Title" is a common English release name. So this can fire on the first run, like M5.
    - What follows is what follows M5:
      - there is one junk folder per series and marker;
      - the series name and number are wrong;
      - once the sources are removed, only a manual rename puts it right;
      - the audio is intact and under the right author, so no data is lost.
    - This is the same kind of silent misfile as M5 and M2, so it is Major.
    - Fix:
      - Don't grow the lists word by word. Turn the check round: ask (title_series) rather than split when the series ends in a marker word or an abbreviation of one, from any of the lists, or in "№", "No." or another short abbreviation with a dot. The one exception is книга, кн or book set apart by punctuation: strip it, as now.
      - Fold Latin and Cyrillic look-alike letters (С/C, Т/T, В/B, Р/P …) before matching the lists.
      - «Черная книга 2» and "Star Wars Episode 4" would then ask. That is the safe side.
      - Add the 15 names as end-to-end negative controls, each seen to fail on 92376c7.
  - **M5 [Major] — FIXED in 3ecfd23, verified at 92376c7.** The lookbehind `(?<!\d[\s,.])`, plus asking on position 0 and on a series name that holds a number. My five names and six more spellings of the group no longer split as «Warhammer 40» (see Re-review at 92376c7). The pass-3 text follows. `local_identity.py:2755` (`_SERIES_PARTS`: the number may follow another digit group), with `:2840` (no guard against a 0 is left).
    - A number written with a thousands space or comma splits at its last group. The series becomes the text before that group, and the position is 0. The book files silently, with no question:
      - «Warhammer 40 000: Ересь Хоруса. Книга 1. Возвышение Хоруса» → `…\Иванов Петр\Warhammer 40\Warhammer 40 - 0 - Ересь Хоруса. Книга 1. Возвышение Хоруса - Иванов Петр.m4b`.
      - «Warhammer 40 000. Ересь Хоруса», «Warhammer 40 000 - Ересь Хоруса», "Warhammer 40,000: Dawn of War" and «Вселенная Warhammer 40 000: Кайафас Каин. …» do the same.
      - On 65ddd72 all five filed unsplit, under the right author.
    - "Warhammer 40 000" is how Russian editions write the setting. Sergei's library has its authors: the seeds rule Abnett Dan and Farrer Matthew, and the collection «Сборник рассказов Warhammer 40000». So this can fire on the first run.
    - What follows:
      - Every such book lands in one junk series folder, «Warhammer 40», at No. 0.
      - Its own series and number stay in the title.
      - The audio is intact and under the right author, so no data is lost.
      - But the sources are removed once the result is verified, so only a manual rename puts it right.
    - This is the same kind of silent misfile as M2, so it is Major.
    - I missed this in pass 1: 40d3c63 split these names the same way. The m4 fix hid it by chance, through its ":" and `00N` refusals, and m12 lifted those refusals.
    - Fix:
      - Treat a number that follows a digit group and a space, comma or dot as part of that number, never as a position. A lookbehind such as `(?<!\d[\s,.])` on the number does it.
      - Reject position 0.
      - Add the five names as end-to-end negative controls.
  - **m16 [Minor] — FIXED in 3ecfd23 with ruling 50, verified at 92376c7. Three spellings are left: M6.** Only книга, кн and book are dropped now (`_BOOK_TAIL`, `local_identity.py:2763`). A CD, disc, volume, part or chapter word ends the split (`_PART_TAIL`, `:2767-2768`; `:2840`). 26 names are unsplit now that split on d4a7450. «Гл.», "Ch." and a Cyrillic «СD» still number a series book. The pass-3 text follows. `local_identity.py:2762` (`_PART_TAIL` drops every part word) and `:2832`.
    - The strip reads every part word as "book N of the series before it". So a disc or a chapter now numbers a book in a series. These filed unsplit on 65ddd72:
      - «Мастер и Маргарита. CD 1. Главы 1-10» → `…\Мастер и Маргарита\Мастер и Маргарита - 1 - Главы 1-10 - Иванов Петр.m4b`, and «… Диск 2. Главы 11-20» → No. 2.
      - «Отцы и дети. Глава 1. Приезд» → series «Отцы и дети», No. 1.
    - The `_PART_TITLE` guard catches only a title that is itself a part word and a number, so «Главы 1-10» passes it.
    - A volume or part of one novel files the same way: «Двенадцать стульев. Часть 1. …», «Граф Монте-Кристо. Том 2. …», «Война и мир. Том 1 - Аудиоспектакль». Rulings 13 and 15 file a numbered part under "set name + number", which this matches, so that one is Sergei's call.
    - The disc and chapter cases are not his call: a CD or a chapter is never a book in a series.
    - Nothing is lost, and the books stay under the right author.
    - Fix: drop only the words that number a book (книга, кн, том, т, часть, book, volume, vol, part, pt). Leave a name with CD, диск, disc, глава or chapter unsplit, or ask about it.
  - **m12 [Minor] — FIXED in 565d912 for its table, verified at d4a7450. It opens M5 and m16.** The pass-2 text follows. `local_identity.py:2759` (`_PART_TAIL`) and `:2823` (no split after ":" or on a `00N` number).
    - The new rules also stop names that 40d3c63 split correctly. These books are now filed with no question and with the series inside the title. That is the shape ruling 41 removed. End to end on the folder-structure helpers:
      - «Гарри Поттер 1: Философский камень» → `…\Иванов Петр\Гарри Поттер 1_ Философский камень - Иванов Петр.m4b`. On 40d3c63: `…\Гарри Поттер\Гарри Поттер - 1 - Философский камень - Иванов Петр.m4b`. "Dune 2: Dune Messiah" and «Ведьмак 3: Кровь эльфов» are not split either.
      - «Перри Родан 001. Звездная пыль» → `…\Иванов Петр\Перри Родан 001. Звездная пыль - Иванов Петр.m4b`. On 40d3c63: `…\Перри Родан\Перри Родан - 1 - …`. «Конан 005 - Час дракона» is not split either.
      - «Хроники Амбера. Книга 1. Девять принцев Амбера», a very common "Cycle. Книга N. Title" form, files with the whole name as its title. On 40d3c63 it made the junk series «Хроники Амбера. Книга». «Сага о Копье. Т. 3. Драконы» behaves the same.
      - A real series that ends in a part word no longer splits: «Черная книга 2. Возвращение», "Star Wars Episode 4. A New Hope".
    - The new comment (`:2822`) says "the odd-name check still asks when it should". None of these asks.
    - My own pass-1 advice ("reject a series that ends in a part word") produced the «Хроники Амбера» case.
    - The book still goes under the right author. Only the split is lost, which is the 0.22.2 result for these names. So this is Minor.
    - Fix:
      - Strip a trailing part word and keep the split («Хроники Амбера», 1).
      - For ":" and `00N`, ask (`title_series`) rather than file unsplit, unless the name is a known title-with-number shape.
      - Add these end-to-end negative controls.

### 7. Maintainability (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **m10 [Minor]** `local_identity.py:2824`. `SERIES_SPELLINGS` is a hard-coded table. Every future ruling-46 pair needs a code release. Sergei's other lasting answers live in the catalog, as `author_rules` and `names_entries`. Open.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **m11 [Minor] — every pass-7 line fixed at cf166bf.** The Brief has the rulings 53-55 row and calls the ruling-52 sibling confirmation superseded; the `identify` comment, `_continue_after_series`'s docstring and the backlog's m20 line match the code. Pass 8, no drift found: the Brief's M10 text ("keeps its answer, files nothing") describes the code, which is what M11 is about. The studio rulings doc is Jane's (pass 7).
  - The pass-7 entry follows. The pass-6 backlog line is fixed at 51caef1; new lines in pass 7.
    - Fixed: the backlog now says ruling 52 narrowed M8 to sets, and ruling 53 closed them.
    - New in pass 7:
      - The Brief's ruling-52 row (`Docs/BooksArranger_Brief.md:22`) still names "the series its sibling books carry" as a confirmation. The Brief has no row for rulings 53, 54 and 55, nor for the series question's new place after rulings 33 and 39. The backlog records them; the Brief is where the next agent looks.
      - The `identify` comment (`local_identity.py:2621`) says ruling 45's siblings carry "another, real series". Nothing checks "real" (m22).
      - `_continue_after_series`'s docstring (`merge_service.py:3109-3112`) says "his Approve of one of its books answers the rest". The confirmation it relies on counts an Approve that answered another question (M10).
      - The backlog lists M9 and m20 as done in 0.22.3. M9 is; m20 is narrowed (above).
      - The studio repo's `Team/Docs/BooksArranger_Rulings_2026-10-24.md` holds rulings 44 to 55 only in its working tree. Its HEAD (eb0c1c9) ends at ruling 43. For Jane and Sully, not Ender.
    - Pass 7, no drift: the `sibling_series` and `sorted_series` docstrings match the code, and the root limit is kept again.
    - Pass 6: the `_BOOK_TAIL` comment (`local_identity.py:2777-2780`) now says a book word written into the series name is not dropped and the name is asked. That matches `_unsure_series`.
    - New in pass 6: the backlog's 0.22.4 source line says "from pass 5: ruling 52 (it covers M8)". Ruling 52 narrows M8; a junk name with two siblings that carry it still files by itself (see M8).
    - Pass 6, no drift:
      - The Brief's ruling-52 row matches the code. Its "a source series folder" is item 9's `Author\Series\N. Title`, and its rejected "a source folder named like the series" is Ender's interpretation 2.
      - The `identify` comment (`:2609-2613`) and the ask's comment (`public_research.py:1290-1292`) match the code.
      - The `sibling_series` docstring still names ruling 45's root limit, which the one-file branch does not keep (m20).
    - Pass 5: `merge_service.py:3013-3016` now says that an accepted Approve requeues his other books, and that a refused one requeues the books the run researched under the answer (m15). This matches `_drop_answer_rule`.
    - New in pass 5: `local_identity.py:2761-2762` (above `_BOOK_TAIL`) still says that a book word written into the series name "is part of it («Черная книга 2. Возвращение», "Star Wars Episode 4. A New Hope")". It is still not stripped, but since ruling 51 such a name is asked, not filed under that series. The comment reads as if it were.
    - Pass 5, docs:
      - The Brief's ruling 51 row matches the code and my counts (115 names; 98 keep their outcome; 17 ask).
      - Ruling 50 now records Sergei's extension to «Эпизод», «Сезон» and «Выпуск», so my pass-4 product note on the Brief's episode, season and issue words is settled.
      - The backlog's pass-4 entry names no commit hashes, unlike the others. That is cosmetic.
    - History, pass 4: it corrected the three items pass 3 left. I checked each against the code:
      - `author_rules.py:14-18` (the module docstring) and `:111-113` (`Rules`): Sergei's retraction is a 'none' row, and the app's is dropped with the rule it retracts. This matches `Rules.__init__` and the two `retract` callers (actor 'user' and actor 'app').
      - `author_rules.py:121-123`: the window's book is marked for research, and the undo puts it back on the run. This matches m15.
      - `public_research.py:657-660`: the lookup is asked with the identity's author after the rules. This matches `credit` (`record['fields']['author']`).
    - New in pass 4, corrected at 067315f: `merge_service.py:3013-3015` still said "his other books are requeued only once it is accepted". Since m15, a refused press also requeues the books the run researched under its answer.
    - The Brief's pass-3 row matches the code. It puts episode, season and issue under ruling 50, whose text names only CD, Том and Часть. That is a product note (see Re-review at 92376c7), not drift.
    - History, pass 3: it corrected the four items left at 65ddd72. I checked each against the code:
      - `scripts/python-check-batches.mjs:63-66`, against `workerDeadline`;
      - `local_identity.py:2759-2766` and `:2821-2842`;
      - `merge_service.py:3016-3018`, `:3085-3086`, and `approve_automatic`'s `queued` docstring;
      - the Brief's rows for rulings 45/46 and for pass 2.
    - Left at d4a7450, all new in pass 3, corrected at 92376c7:
      - `author_rules.py:14-16` (the module docstring) and `:109-110` (`Rules`) still say that a retraction stays among the rules as a newer 'none' row, so no older answer comes back. Since M1, an app retraction does neither. I missed this in pass 2.
      - `author_rules.py:118-119` says the window's book "is researched again". It is marked for research, and waits for the next scan (m15).
      - `public_research.py:658` says the gap fill is asked "with the credit the files carry". It is asked with the identity's author after the rules: «Grossman Lev» for «Лев Гроссман» in my probe. Automatic filing asks with the same author, so the comment is off, not the code.
    - History, passes 1 and 2 (pass-2 line numbers):
      - Pass 1 listed six comments or docs that no longer matched the code. Five were corrected at 65ddd72: `desktop/main.js:362`; `merge_service.py:3004` (undo "as before the press"); `merge_service.py:2773` (`_press_after`); `web/app.js:3152` and the Brief's ruling 40 row; `local_identity.py:2597`.
      - Left at 65ddd72, corrected at d4a7450: `scripts/python-check-batches.mjs:64-65` ("the copies before it no longer eat its time" held only for copies under 40 s).
      - New in pass 2, corrected at d4a7450: `local_identity.py:2822` ("the odd-name check still asks when it should", m12); `merge_service.py:3000-3001` and the Brief's rulings 45/46 row ("once the job is queued, nothing takes the answer back", M4).

### 9. Build & Release Hygiene

- Status: Concerns
- Findings:
  - The version bump moved package.json and package-lock.json in one commit (cd8d956). The CHANGELOG has no 0.22.3 entry yet; that is Sully's release step. No secrets.
  - Pass 2: no version or lockfile change. The entry check at 65ddd72 passed, dirty N. The backlog lists the open minors under 0.22.4.
  - Pass 3: no version or lockfile change. The entry check at d4a7450 passed: receipt v2, dirty N, check pass, entry exit 0. The backlog at d4a7450 records the pass-2 fixes. It does not list M5, m15, m16 or m17.
  - Pass 4: no version or lockfile change. The entry check at 92376c7 passed: receipt v2, dirty N, check pass, entry exit 0, 438 s. The backlog at 92376c7 records the pass-3 fixes and lists m17. Each fix commit names its root cause. No commit carries an attribution line.
  - Pass 5: no version or lockfile change. The entry check at 067315f passed: receipt v2, dirty N, check pass, entry exit 0, 434 s. 4e8171a names its root cause and its tests. Neither commit carries an attribution line.
    - The suite passed with M7 in it. No test feeds `latin_lookalikes` an upper-case look-alike, so the gate could not see it.
  - Pass 6: no version or lockfile change. The entry check at ddfbfa7 passed: receipt v2, dirty N, check pass, entry exit 0, 442 s. 1138712 names its root causes (M7, M8, m18, m19) and its tests, and each new test fails on 067315f. Neither commit carries an attribution line.
    - The suite passed with M9 in it. `test_folder_structure` turns ruling 39 off for the whole module (`setUpModule` patches `original_titles.translation`), and no ruling-39 test has a series in the name.
  - Pass 7: no version or lockfile change. The entry check at 51caef1 passed: receipt v2, dirty N, `npm run check` code 0, 1,903 Python cases in 9 workers (q23h). b2f8660 names its root causes (M9, M8's sets, m20, m21) and its tests, and every new test but ruling 55's fails on ddfbfa7, as it says. Neither commit carries an attribution line.
    - The suite passed with M10 in it. Every ruling-53 test approves through the series question.
  - Pass 8: no version or lockfile change. The entry check at cf166bf passed: receipt v2, dirty N, `npm run check` code 0, 1,910 Python and 142 node cases (q23i). 798001a names its root causes and its tests; every new test fails on 51caef1, as it says. Neither commit carries an attribution line. The new module joins the gate with a weight of 200 s (`scripts/python-check-batches.mjs`).
    - The suite passed with M11 and M12 in it: the M10 tests always send an answer, and the corrected-series test renames the set's own name.
  - **m9 [Minor]** `scripts/python-check-batches.mjs:67-71` and `scripts/check-desktop.mjs:22`. The gate stops itself 580 s after its own start. After the workers it still checks the worker inventories and digests the whole runtime tree. The entry check's outer bound in the pass-1 log is `timeoutMs: 592288`. So a gate that passes close to 580 s can end in the outer kill instead of the gate's own message. Real margin today is large: the pass-2 entry run took 401 s in all, and the pass-3 run 443 s. Open.
    - Pass 8: the slowest worker took 452.1 s of its 540 s deadline (84 %, worker 6), 24 % over its 364 s projection, with `test_set_release.py` (six real runs) weighed 200 s. A machine 20 % busier would cross the deadline. That makes the entry check flaky; it does not make the build unsafe, so it is no release risk. Re-weigh from this run's module times, or add a worker, before the next feature lands.
  - The split halves are sound. A renamed class fails loudly (`Split classes missing`). A new class goes into the "-" half. The two halves must be complementary, and a module cannot also run whole.

---

## Patterns

The m7 fix from 0.22.2 (save an answer only once its press is accepted) was extended to "Same author?" by writing first and undoing later. In this rule store, an undo was a Take back, so the extension brought back a version of the problem it was meant to remove (M1). Once again the tests proved the case that was asked for and left out the negative control.

Pass 2 shows the same shape one level down:
- Each fix closes exactly the case it was shown, and misses its neighbour:
  - m1 guards the code after `approve_automatic` returns, but not the code after the queue insertion inside it (M4).
  - M1's new view of the rules is applied to lookups, but not to `changed_for` (m13).
  - M3 fixes the Save, but not the preview that reads the same hidden inputs (m14).
  - m4 rejects the misfires without an end-to-end negative control for the names that split correctly before (m12).
- The tests Ender added are good positive controls. What is missing is a probe of the next case over.

Pass 3 closes half of that gap. Every new test fails on 65ddd72, so the negative controls are now there. The next case over is still missed in two places:
- The m12 table proves the names it lists, but no name outside its own vocabulary was tried. A thousands group (M5) and a disc or chapter word (m16) were the ones that broke.
- m13 fixes the predicate (`changed_for`), but not the trigger: nothing calls it when the answer is undone (m15).

Pass 4 reached the next case over for M5. The lookbehind and the zero and digit asks also hold for spellings of the group that no test names (a dot, no-break spaces, an apostrophe). What is left is the pass-3 shape one level up:
- The marker lists are closed vocabularies, and every pass, mine included, tried the words in them.
- A marker outside them stays in the series name and files silently (M6): a book word with no punctuation, «№», an abbreviation, a Cyrillic letter in "CD".
- The lasting fix is to ask whenever the series ends in something marker-like, not to add words.

Pass 5 shows the limit of that advice, and a new shape:
- "Ends in something marker-like" was still a list, mine first. The turned-round check catches more than its own names (11 of my new ones), but a word, a sign, a joined token or a prefix outside the set still files silently (M8). Only structure, or a second source for the series, can close it.
- The fix commit broke a neighbour it never meant to touch (M7). It added a module-level name that already existed, and an older function picked up the new value. The tests prove the new code. Nothing proved the old function's other half: no test feeds it an upper-case look-alike.
- Asking about a name also changed what that name means to its siblings (m19). The ask was safe for the book itself, but `sibling_series` reads the same function.

Pass 6 turned the check round, as Sergei ruled, and it holds for a book alone: no name I tried files without a confirmation. Two shapes are new:
- A confirmation is only as good as its independence. Sorted and a tag are second sources. Siblings are the same parse of the same naming pattern, so a set confirms itself, junk or not (M8). Counting files instead of books made one sibling book count as several (m20).
- An ask moved earlier in the pipeline is also a step that skips what comes after it. The ruling-52 ask returns before rulings 33 and 39, and the Approve that answers it switches them off (M9). The tests could not see it, because the module that tests the split turns ruling 39 off. As in pass 5, a fix broke a neighbour that its own tests never run.

Pass 7 is pass 6's second shape turned round. Moving the series question after the author questions fixed M9. But an Approve answers whatever question its row asked, and it settles every name at once, so the questions after it are never asked. Ruling 53 then reads "Sergei approved a book of this series" as "Sergei answered the series question". Nothing records which question an Approve answered (M10). The fix for M9 was mine, and I checked the flow it moved, not the answer that ends it. The lasting fix is to record what each Approve answered, and to let only the answer to a question confirm what that question asked.

Pass 8 did record what an Approve answered, and the two new Majors are the two edges of that record. Where the Approve answered nothing that can be written down (the proposal accepted as shown), the code still treats it as "not the series question" and asks again, for ever (M11). Where it answered a series, the record has no scope: one book's answer becomes a lasting alias for the author (M12). The same shape as pass 2: each fix closes the case it was shown (an answer given, a set renamed) and misses the neighbour (an answer accepted, a book moved). The release also reached for the nearest start path, which brings a whole run with it (M13).

---

## Verdict

- Total Critical: 0
- Total Major: 14 (M1 to M10 fixed and verified; M11, M12, M13 and M14 open)
- Total Minor: 23 (m1, m4, m11 to m16, m18 to m20 and m22 fixed and verified; m21's first half fixed; m2, m3, m5 to m10, m17, m21's second half and m23 open)

This certifies the range v0.22.2..cf166bf. There is no Critical finding. The safety floor is intact: no machine harm, no secret, no history or source overwrite. Pass 8 adds no shell-out, kill, route, file write or network request; the release reuses `requeue` and `request_start`.

Pass 8: M10, Futaba's M-1, m20, m22 and the m11 lines are fixed and verified. Four Majors are open, none of them data loss, so none blocks. Three are new in 798001a, and cf166bf is in one way worse to ship than 51caef1:
- **M11:** Approve as shown on a question before the series question (ruling 33's spelling, no author, two credits) never files, and says the answer was saved. A regression against 0.22.2 and 51caef1.
- **M12:** a series corrected at one Approve renames that series for every book of the author, in any folder, for good (`City Watch - 20 - Hogfather`; «Сновидения Ехо 4» under «Мертвый ноль»). A silent misfile, new against 0.22.2 and 51caef1.
- **M13:** a releasing Approve continues a run Sergei stopped and starts a new run when none is running. Sergei's call; new against 0.22.2.
- **M14:** a 'keep' rule files a Cyrillic credit given-name first by automatic filing, surname first by Approve. Older than 0.22.2; the release spreads it to sets.
- Fix M11 and M12 before shipping, and ask Sergei about M13. m23 (a split book with no author loses its series from the name) and the gate at 84 % (m9) are Minor.

Pass 7 text, kept as history:

Pass 7: M9, M8's sets and m21's first half are fixed and verified; m20 is narrowed. M10 is new in b2f8660 and logged for Ender. It is not data loss: the audio is intact in Sorted, so it does not block. But it misfiles a whole set silently, and the sources are removed after conversion:
- **M10:** an Approve that answered "Same author?", ruling 39's English spelling or ruling 33's spelling files the book's unconfirmed split without the series question. Ruling 53 then takes it as the set's answer, and the rest of the set files by itself under the split's series, with no row. ddfbfa7 asked the series for those books; 0.22.2 filed them unsplit.
  - The fix is recording what an Approve answered, letting only a series answer confirm the set while its job is queued, and keeping the series question for a book whose author question comes first. It is the one to fix before shipping if Sergei wants 0.22.3 free of regressions the review knows about.
- Minors: m20 (uncredited siblings, and a book with two album spellings), m22 (ruling 45's override confirms a junk set's series), m21's second half, m17. None blocks.
- For Jane: the rulings doc in the studio repo holds rulings 44 to 55 only in its working tree (m11).

Pass 6 text, kept as history:

Ruling 52 works for a book on its own, and M7, m18 and m19 are fixed and verified. M8 and M9 are logged for Ender's next cycle. Neither is data loss: the audio is intact, so neither blocks. But both misfile, and the sources are removed after conversion:
- **M9 is new in the fix commit 1138712**, and 0.22.2 did not have it: 0.22.2 looked the author up, or asked the spelling.
  - The ruling-52 ask comes before ruling 33's spelling question and ruling 39's lookup, and the Approve that answers it switches both off.
  - A foreign author credited only in Cyrillic, with an unconfirmed series in the name, files under the Cyrillic credit (`Роллинс Джеймс\Отряд Сигма\…`), and no rule is learned, so his next books go to `Rollins James\`.
  - The fix is moving the ask below the author steps, and one test. It is the one to fix before shipping if Sergei wants 0.22.3 free of regressions the review knows about.
- **M8 is new in 0.22.3 (ruling 41's split), narrowed in this delta**, and 0.22.2 did not have it: it filed every such name unsplit.
  - A junk name alone, or with one sibling, now asks.
  - With two siblings that carry the same pattern, 36 of my 44 split names still file under a junk folder («Шерлок Холмс. Аудиоспектакль», «Курс истории. Лекция»). Numbered junk comes in sets.
  - The code does what ruling 52 says, so the rest is Sergei's call (dimension 6): structural checks on what siblings may confirm, one question per set, or accept it.

Minors: m20 (one-file siblings count files and ignore the root and the author, new in 1138712), m21 (a 0.22.2 "Entered by you" title or author skips the ruling-52 ask, new in 0.22.3, not in this delta) and Ender's stated gap m17. None blocks.

On Ender's two readings: one-file books in one folder must count, or the live «Червь» folder asks 31 times, but as built they count files, not books (m20). A source folder named like the series not confirming is the safe side and the ruling's own list; it costs one question per book folder there, while a one-file book in the same folder files by item 9. That one is Sergei's call.

| # | Sev | Dim | file:line | Finding | Status / next step |
|---|-----|-----|-----------|---------|-----------|
| M1 | Major | 5 State | `merge_service.py:3003`, `author_rules.py:113` | The app's undo of a refused Approve hid every older rule for the credit. | **Fixed** (1f80255), verified. |
| M2 | Major | 2 Correctness | `local_identity.py:2600` | The sibling series overrode a name that names another series. | **Fixed** (2be2d0b), verified. |
| M3 | Major | 5 State | `web/app.js:776`, `review_backend.py:609` | The hidden name inputs were saved as "Entered by you". | **Fixed** (7012da8), verified. |
| M4 | Major | 3 Crash | `merge_service.py:3292-3311` (pass 2) | After the queue insertion, a Pause still settling or a Quit reports the Approve as refused and takes back its answer; the job stays queued. | **Fixed** (9e8c0c1), verified; see m17. |
| M5 | Major | 6 Input | `local_identity.py:2755`, `:2840` (pass 3) | A thousands-group number ("Warhammer 40 000: …") splits at its last group and files silently under series «Warhammer 40», No. 0 (regression from m12). | **Fixed** (3ecfd23), verified. |
| M6 | Major | 6 Input | `local_identity.py:2757-2770`, `:2839-2842` (pass 4) | A marker outside the word lists stays in the series name: "Harry Potter Book 1 - …", «Хроники Амбера №1. …», «Отцы и дети. Гл. 1. …», "Discworld No. 1", a Cyrillic «СD 1» (15 names) file silently under junk series folders. | **Fixed** (4e8171a, ruling 51), verified; the class stays open as M8. |
| M7 | Major | 6 Input | `local_identity.py:2778` over `:1783`; `:1786-1792`, `:2020` (pass 5) | New in 4e8171a: the ruling 51 table rebinds `_LOOKALIKE`, so `latin_lookalikes` stops reading upper-case Cyrillic look-alikes as Latin. «Аnita Blake» files beside "Anita Blake" (regression against 0.22.2). | **Fixed** (1138712, `_MARKER_FOLD`), verified; the module binds `_LOOKALIKE` once. |
| M8 | Major | 6 Input | `local_identity.py:2617`, `:2942-2980` | M6's class beyond the list (new in 0.22.3). Since ruling 52, only a set: a junk name beside two siblings that carry the same pattern files by itself under the junk folder (36 of 44 names; «Шерлок Холмс. Аудиоспектакль», «Курс истории. Лекция», «Хроники Амбера N°»). | **Fixed for sets** (b2f8660, ruling 53), verified: 84 of 84 junk books ask. What is left goes through M10 and m22. |
| M9 | Major | 2 Correctness | `public_research.py:1294-1305` before `:1311`, `:1319-1351`; `:643` | New in 1138712: the ruling-52 ask comes before ruling 33's spelling question and ruling 39's lookup, and Approve switches both off. «Отряд Сигма 2. Карта костей» by «Джеймс Роллинс» files under `Роллинс Джеймс\`, no rule learned (0.22.2 and 067315f: `Rollins James\`). | **Fixed** (b2f8660), verified; it opens M10. |
| M10 | Major | 2 Correctness | `public_research.py:1348-1349` with `:643`; `local_identity.py:3016-3018`; `merge_service.py:2955-2980`, `:3104` | New in b2f8660 (regression against 0.22.2 and ddfbfa7): an Approve that answered "Same author?", ruling 39's English spelling or ruling 33's spelling files the unconfirmed split without the series question; ruling 53 takes it as the set's answer, and the rest file by themselves (`Koontz Dean\Курс истории. Лекция\…`, no row). | **Fixed** (798001a), verified for answers that save something; it opens M11. |
| M11 | Major | 2 Correctness | `merge_service.py:3083`, `:3173-3192` (pass 8) | New in 798001a (regression against 0.22.2 and 51caef1): Approve as shown on a question before the series question (ruling 33's spelling, no author, two credits) saves nothing, says "Your answer is saved", and the same question comes back; the book never files. | Open. Save the shown author as his answer when nothing else is saved, or carry Series and Number on the author row; a test approving as shown. |
| M12 | Major | 2 Correctness | `local_identity.py:3026-3031`; `merge_service.py:3130-3155` (pass 8) | New in 798001a (regression against 0.22.2 and 51caef1): a series corrected at one Approve renames that series for every book of the author, any folder, for good: `City Watch - 20 - Hogfather`, `- 21 - Jingo` (other folder); with m22's fill-in «Сновидения Ехо 4, 5» under «Мертвый ноль». | Open. Confine it to the set released by that Approve, no lasting alias; never carry a fill-in correction to the siblings; tests for both cases. |
| M13 | Major | 5 State | `merge_service.py:3157-3167`, `automatic_processing.py:371-387` (pass 8) | New in 798001a (new against 0.22.2): a releasing Approve continues a run Sergei stopped (it files the other books in it) and starts a new run with discovery when none is running. | Open; Sergei's call (Brief revisit trigger). Leave a stopped run stopped; research only the released books. |
| M14 | Major | 2 Correctness | `local_identity.py:2339-2342` with `approved()` (pass 8) | Older than 0.22.2, not in any reviewed delta: a Cyrillic credit with a 'keep' rule files given-name first by automatic filing (`Джеймс Роллинс\`) and surname first by Approve (`Роллинс Джеймс\`); the release now splits a set between them. | Open. One order for both paths; a test. Check the live Sorted folder first. |
| m1 | Minor | 3 Crash | `merge_service.py:2991`, `:1577` | An exception after acceptance failed the press and retracted the answer. | **Fixed** (f93455c) for errors after `approve_automatic` returns; the rest is M4. |
| m2 | Minor | 5 State | `merge_service.py:2868-3001` | Answer, approval and requeue are not atomic; a crash leaves the rule without an Approve. | Open. Note; requeue from `changed_for` at start. |
| m3 | Minor | 3 Crash | `desktop/main.js:518` | The 30 s Quit kill ignores critical sections; stale owner records pile up. | Open. Wait for critical sections; longer bound. |
| m4 | Minor | 6 Input | `local_identity.py:2756` | False "Series N. Title" splits ("Apollo 13:", «Агент 007», "01.5"). | **Fixed** (2be2d0b), verified; see m12. |
| m5 | Minor | 4 Perf | `web/app.js:160` | The rules list is rebuilt every second while a Take back waits. | Open. Re-render only the pending entry. |
| m6 | Minor | 2 Correctness | `web/app.js:3205` | "It left this list" fires after a page or filter change. | Open. Match the reload's context. |
| m7 | Minor | 2 Correctness | `web/app.js:4103` | The rules list shows "unavailable" for 30 s after each start. | Open. Load after `books`, or retry sooner. |
| m8 | Minor | 4 Perf | `author_rules.py:118` | About 32 ms more per `Rules()` rebuild; rebuilds repeat during conversions. | Open. Watch; key the cache on manifests, not `updated`. |
| m9 | Minor | 9 Build | `scripts/python-check-batches.mjs:67` | The 580 s gate total plus post-work against the 592 s outer bound. Pass 8: the slowest worker at 84 % (452 s of 540, 24 % over projection). | Open. Leave headroom for the post-work; re-weigh or add a worker. No release risk. |
| m10 | Minor | 7 Maint. | `local_identity.py:2824` | Series spellings are hard-coded. | Open. Store them in the catalog. |
| m11 | Minor | 8 Drift | see dimension 8 | Comments and docs that no longer match the code. | **Fixed** (cf166bf, 798001a): every pass-1 to pass-7 item. The studio rulings doc is Jane's. |
| m12 | Minor | 6 Input | `local_identity.py:2759`, `:2823` | "Series N: Title", "Series 00N. Title" and «Cycle. Книга N. Title» now file silently, unsplit, with the series in the title (regression from m4). | **Fixed** (565d912) for its table, verified; see M5 and m16. |
| m13 | Minor | 5 State | `author_rules.py:160` | `changed_for` cannot see the app's undo, so a book researched in the press window is never researched again (regression from M1). | **Fixed** (6817bb3), verified, no loop; see m15. |
| m14 | Minor | 2 Correctness | `web/app.js:53` | The panel's "Unsaved destination preview" still reads the hidden name inputs. | **Fixed** (a59914d), verified. |
| m15 | Minor | 5 State | `merge_service.py:3029`, `:2286` (pass 3) | The undo of a refused press requeues nothing, so the book m13 marks waits as "Still checking" until a new run's scan. | **Fixed** (117044f), verified; no partner book requeued. |
| m16 | Minor | 6 Input | `local_identity.py:2762`, `:2832` (pass 3) | A disc or chapter word («CD 1», «Диск 2», «Глава 1») now numbers a book in a series (with m12). | **Fixed** (3ecfd23, ruling 50), verified; «Гл.», "Ch." and a Cyrillic «СD» are left, see M6. |
| m17 | Minor | 3 Crash | `merge_service.py:3328`, `:3090` (pass 3) | After a failed row read the Approve stands, but the queue is not started, and the state reads "Paused" (Ender's stated gap). | Open. Resume, guarded, in the accepted branch unless the stop or a `StartRefused` raised. |
| m18 | Minor | 6 Input | `local_identity.py:2868-2870`, `:2770` (pass 5) | The title after the split is not checked (new in 0.22.3): «Ведьмак 1 - 2. …» files as book 1 titled «2. …»; «Хроники Амбера 1. Гл. 2» files as book 1 titled «Гл. 2». | **Fixed** (1138712, `_unsure_title`), verified; all 10 ask. |
| m19 | Minor | 2 Correctness | `local_identity.py:2926` (pass 5) | New in 4e8171a: siblings whose names now ask no longer vote in ruling 45; a rare layout files «Мертвый ноль 7. Мертвый ноль» under «Мертвый ноль» or a sibling series. | **Fixed** (1138712), verified; both probes right. |
| m20 | Minor | 2 Correctness | `local_identity.py:2958-2962` | New in 1138712: one-file siblings count files, not books, and ignore ruling 45's root limit and the author. A 4-file «Лабиринты Ехо» book outvotes two «Сновидения Ехо» files; another author's «Червь» books in the root make «Мертвый ноль 7.» «Червь», No. 7. | **Fixed** (b2f8660 narrowed it; 798001a closed the rest), verified: uncredited siblings vote only for an uncredited book; votes counted by series and number. |
| m21 | Minor | 6 Input | `public_research.py:895-901`, `:1287` | New in 0.22.3 (ruling 41), not in this delta: an "Entered by you" title or author (a 0.22.2 panel Save) skips the ruling-52 ask; an entered whole name keeps the split's series beside it (`Отряд Сигма\Отряд Сигма - 1 - Отряд Сигма_01. …`). | **First half fixed** (b2f8660), verified: the row asks. Second half open (backlog, 0.22.4): drop the split when the entered title differs from it. |
| m22 | Minor | 2 Correctness | `local_identity.py:2611-2614` | New in 0.22.3 (rulings 45 and 53), not in this delta: ruling 45's override confirms whatever series two siblings carry, which ruling 53 does not confirm for the set itself. «Финал 3. Финал» beside two «Шерлок Холмс. Аудиоспектакль» books files into that folder while they ask. | **Fixed** (798001a), verified: asks with the siblings' series filled in. A corrected fill-in feeds M12. |
| m23 | Minor | 6 Input | split of a book with no author (pass 8) | New in 0.22.3 (ruling 41), not in this delta: «Курс истории. Лекция 1. Греция» with no author files `Без автора\Греция.m4b`; the series and number leave the name (51caef1; by reading cf166bf). | Open. Keep the whole name, or put the series into the file name. |

Verdict of the historical review (through cf166bf, superseded): RELEASE CLEAR.
