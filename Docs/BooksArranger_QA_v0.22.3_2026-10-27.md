# Books Arranger 0.22.3 — corrective delta QA on candidate 943998e (Futaba)

Pass run 2026-10-28 on the final packaged candidate, checking only the three residual fixes, the unresolved-English preview boundary, the original language/order checks, and one held-cache control. The Discworld correction carries from the previous pass. No full entry check was repeated by QA.

Release source commit: 943998edbd00d8676b00d95a3311e26b7c79ae36
Release artifact manifest SHA256: 7b8468a5e8608d4ecd910ac2c20c7f4b899ea60cfa07fefba40819ac17c9b4d9

## Identity and entry receipt

- Installer `cand-0223j/dist/builds/7645da69-bb47-497e-8754-ab7f90d70995/Books-Arranger-Setup-0.22.3.exe`: 174,244,357 bytes, SHA-256 `9babdb6d9cf00af0c283f12fdd978a04b13a6fc8d8fcf3b8b5c347ca01dcb53d`. Installer and manifest hashes match the handoff. The manifest names source 943998e and version 0.22.3.
- My preflight also checked 218 actual packaged backend/Python/FFmpeg input files against the accepted payload manifest, the passing context's Node pin, all five canonical ownership-helper files, and its ownership/Koffi manifest files. The engine runs the final build's backend with its packaged Python and FFmpeg, not the mutable main checkout.
- Actual builder receipt, compared from `q23j/logs/ender-entry.log`:

```text
Entry-check receipt v2: books-arranger v0.22.3 @ 943998edbd00d8676b00d95a3311e26b7c79ae36 (dirty: N) [source:bdf838e278b8152ab6131ef30068904f6b76decc20012f74f83a699d1741e23f; harness:c1ca100354d22501175d0edf2947685c41ceec13cd6331bb1859b05f12e75960; runtime:e3925548d1915af5e8582c47b627025256b7f565adb3a989012d662c818efb70; checker:a448c08c150e63019cfd6e49ceed5ec5b8652a97078abde197e7a50882b759cf] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a
```

Builder result: 1,920 Python and 143 Node cases pass, zero failures/errors/skips and proven native zero. Earlier failure/debug history remains below; it is not counted as a passing receipt.

## Packaged engine checks

Ten intended real workflows pass. Private tagged audio (two 0.4-second MP3s per book, embedded artwork), fresh private catalogs and Sorted folders; real production scan, automatic holds, Approve, Edit names, attention-list payload, explicit Start and publication. Fetches use the existing offline HTTP-503 seam. A socket guard refuses outbound traffic: its deliberate positive control was logged once, and the workflows made no outbound attempts. The only name-lookup stub is an inconclusive public-author response, so the English-question and entered-field boundaries can be checked deterministically.

| Changed behavior | Result and evidence |
|---|---|
| **M11: a real held author question advances after the saved answer and Start** | **Pass, all three.** No author, ruling-33 spelling (`Ilya Marchenko`), and two credits. Each first real automatic run holds the author question; Approve as shown saves it and files nothing. The next real Start asks `title_series`, not the same author question. Series Approve queues the book; explicit Start then files it. The no-author output goes to `Без автора`. |
| **M13 / ruling 56: Approve cannot resume a stopped conversion queue** | **Pass.** Real stopped queue before the second Approve: Paused, one pending, zero completed. After approving another book: still Paused, two pending, zero completed, all four sources intact. Only explicit Start processes both books. |
| **M15 / ruling 59: entered fields cannot bypass a foreign author's English question** | **Pass, three variants.** An old Cyrillic keep rule plus an entered title, series/number, or Cyrillic author still makes one author lookup and asks `english_spelling`. Blank Approve is refused and creates no job. Typing `James Rollins`, then explicit Start, files under `Rollins James`; the entered title and series remain intact. |
| **Unresolved-English attention row and preview** | **Pass.** The actual `needs_you` entry and `ask_payload` remain usable; no crash and no extra author lookup. Destination path/absolute are empty, with `Enter the author's English name, then approve.` No Cyrillic destination is offered. The English answer then succeeds, retaining `Entered Map`. |
| **M14 / ruling 58: surname order and language agree** | **Pass.** Correct Cyrillic keep credit `Иван Петров` resolves to `Петров Иван` in both the real automatic output and Approve preview. A canonical English `Rollins James` rule wins over the old Cyrillic keep: automatic output and Approve preview both use `Rollins James`. The foreign-author variants above also exercise actual English Approve/conversion. |
| **Ruling 57: changing the held cache stays book-local** | **Pass.** After approving and explicitly processing book 1 of the asked lecture set, rescan and another Start leave book 2 asked `title_series`, its two sources intact, and exactly one completed job/output. |

All 11 created audio outputs decode with zero errors. Counts come from the ten scenario records and actual Sorted output files, not the full suite. The first main driver completed nine valid workflows; my series fixture initially omitted its required number and was correctly refused before the behavior check. I supplied number 1 and repeated only that single scenario, which passed. No product, assertion or time limit changed. Main-driver owned closure is native zero; its exit 1 is solely that invalid fixture. The focused series correction has `ok:true`, exit 0, native zero.

The Discworld → City Watch correction carries from the accepted first-candidate behavior check below: 19 changes only itself; Hogfather 20 and Jingo 21 elsewhere keep Discworld. The corrective code did not change that save path. The existing m23 no-author filename limitation remains deferred: its series is absent from the filename. No new product findings; M11, M13 and M15 are closed by the measured corrective checks. Pattern alert “answer saved but the same question returns” is closed for the three real-held author flows; disposition **fixed**.

## Packaged hidden launch / Quit

**Functional packaged launch/close/Quit passed on the same accepted artifact.** Senua reviewed the exact helper and final source/artifact/Node/ownership binding before execution. The real packaged app used a fresh private payload/profile, roots, environment and ports, with its window hidden. The rendered and engine versions both read **0.22.3**. The hidden renderer reached its private HTTP origin. A visible-window positive control confirmed the observer could detect windows; no owned window became visible and no intrusion was reported.

`--close-window` followed this tray tool's normal close path: hidden, shell and engine still running. The same private profile's normal `--quit` then exited the shell and engine (`closedByQuit:true`); the payload remained unchanged. The private Job closed normally with zero remaining native members. No physical input or focus was taken.

The safety/cleanup history is explicit, not converted into a fictitious passing command:

1. Helper `8187c310…` stopped **before app launch** because its full registry query exceeded the existing 5,000 ms bound. No bound was increased. That result is archived in `logs/hidden-package-smoke-result-v1-registry-preflight.json`.
2. Senua approved replacement helper `eff639068f219b3a7cc0ef95cd95df72b4b469c75d2f4cade81d076b2ea48d6e` with exact plan SHA-256 `41223690a874342e8637eed12d6051a6771b080e6adbe0ce0cb491b1824bcb6c`. Its complete registry export retained all values/types and the same time/output caps. The functional app flow above passed, but that helper's overall exit was **1** because its strict guard detected Windows adding one 8-byte numeric own-ID reference to `UIOrderList`. It correctly stopped and preserved the evidence; that invocation is not claimed as an overall pass. See `logs/hidden-package-smoke-result.json` and the preserved tray classification evidence.
3. Sergei explicitly approved **“Yes—leave OS history and finish release”**: delete only this temporary app's own tray record and leave the path-free, numeric 8-byte OS history reference. Senua then verified the exact same-handle leaf-deletion helper `3327b6cae94f64af3058d764ed57e30739b242c85855409c5371bac9a46e5e38` and authorized plan SHA-256 `44b4fe04b234b63d18192dfe46c8fdcdf95af2a7f9dfb48b149cc5b51a9176d8`.
4. I executed that approved outer cleanup **once**. `logs/owned-tray-leaf-delete.json` records exit 0, `ok:true`, normal closure and native zero. The handle still named the exact private executable; the leaf had no subkeys, and afterward the own leaf was absent. All other current/preexisting records were untouched. Neither root nor `UIOrderList` was written. The current 1,864-byte `UIOrderList` remained unchanged (SHA-256 `50680e5a2cbd419706aa9ac3e506421dcce0f835dc4d9b063a16aac13c4d07b3`), retaining only the expressly authorized 8-byte numeric reference to the deleted own ID, with no name/path. No root rewrite, transaction-history repair or additional app launch occurred.

The accepted exception plus the successful narrow cleanup closes the packaged-smoke prerequisite. It does not waive a product failure or turn either earlier failed helper result into a pass.

## Limits and disposal

No installer was run. No Z: or live `data/` writes, profile install, mouse/keyboard/tray click, focus change or visible test window. The page/HTTP rendering, real X/tray gestures, updater, other themes/viewports and unchanged historical cases were not repeated. The hidden shell check is the packaged launch evidence; it does not claim real-input coverage of every page.

Evidence: `q23j/futaba/c/results.json` and `owned.json`, focused series records under `q23j/futaba/s`, the pinned driver, and the reviewed native helper's logs. All engine owned jobs closed with native zero. Preserve these through release, then the parent removes the complete candidate and run folders via `studio-sweep`; retain only the accepted current installer/build in the main checkout. This report is my only repository edit; no staging, commits or pushes.

Blockers: 0. Open QA Majors: 0. New Minors: 0. No loss of the last audio copy found. M11, M13 and M15 are verified closed; the language/order checks and held-cache control pass. The authorized numeric OS history exception is recorded above.

**Verdict:** GO

---


# Previous pass: candidate 3545d17 (superseded by the 943998e corrective pass above)

Pass run 2026-10-28 against the accepted packaged backend at `cand-0223j`, checking the changes since cf166bf. **NO-GO: two Major behavior failures remain (M11 and M13).** Ruling 57 and the Discworld correction pass. Senua independently found the additional foreign-author/title-only bypass M15; it joins the same corrective batch. This section supersedes the cf166bf pass below.

Historical source commit: 3545d178d6315cff8c8acb383a590081d7627dd1
Historical artifact manifest SHA256: 43dfc69c2358c4840ec912c36c76dbf9c0c273091613dad073263eaccb9e1aa4

## Build identity

- Installer: `cand-0223j/dist/builds/b631e687-8fc0-46be-aad0-3b8daa5813e1/Books-Arranger-Setup-0.22.3.exe`, SHA-256 `6019c49ac6b4357325cff7ab3f17e31e9c481233d4d20011d1045653193e7c6d`. My driver hashes the actual installer and manifest and refuses a mismatch. Both match Ender's handoff. The manifest names version 0.22.3 and the source above.
- Backend driven: the actual build's `win-unpacked/resources/backend`, with its packaged Python and FFmpeg. No installer was run. The full entry check was not repeated.
- Actual builder receipt, from `q23j/logs/entry-passed-summary.json` and the entry log:

```text
Entry-check receipt v2: books-arranger v0.22.3 @ 3545d178d6315cff8c8acb383a590081d7627dd1 (dirty: N) [source:310bf1c80efacab1438bd7648fdbf52e692dc0588b72f062f0647046505efdc4; harness:0c5ae643596e17aeca3aaac22c8b946006bd789bc53f31a55ada42e96a5d8912; runtime:e3925548d1915af5e8582c47b627025256b7f565adb3a989012d662c818efb70; checker:a448c08c150e63019cfd6e49ceed5ec5b8652a97078abde197e7a50882b759cf] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a
```

Ender measured 1,916/1,916 Python and 143/143 Node cases passing, no failures/errors/skips, the slowest worker at 516.8/540 seconds and proven zero owned processes after closure. The preceding official run had one 30-second media-test timeout. That exact case passed 5/5 in isolation (15.20–16.66 seconds), then the unchanged official retry passed. The original timeout's precise cause is unproven; the failed receipt is not treated as a pass.

## Method and measured behavior

Private real tagged audio (two 0.4-second MP3s per book, embedded artwork), private catalogs and Sorted folders under `q23j/futaba`; production Inventory, MergeService, automatic Start/Stop, Approve, preview and research. Public fetches answer HTTP 503 through the existing fetch seam. No live catalog or library was opened, and no SQLite backup API was used. The actual workflows below use no mocked `resume` or `request_start`.

| Item | Result | Measured behavior |
|---|---|---|
| **M13 / ruling 56: a stopped conversion queue stays stopped after Approve** | **FAIL, Major** | First approve `A Quiet Morning`, then real `pause()`: queue `Paused`, one queued job, zero completed. Approve unrelated `The Quiet Road`: immediately `Running`, first job starts again and second is pending. Both later complete and both sources are removed. The two outputs exist in private Sorted. An Approve resumed work Sergei stopped; observing the automatic-run state alone misses this queue boundary. |
| **Ruling 57: every held set member asks individually** | **PASS** | Real automatic run holds both «Курс истории. Лекция 1. Греция» and «… 2. Рим». Approve book 1, let it finish, rescan, then real Start: exactly one job/output; book 2 remains `title_series`, with its two sources still present. The output decodes with zero errors. |
| **M12: correcting one book never renames the author's other series** | **PASS** | Three Terry Pratchett books are really held by the automatic run: Discworld 19, 20 and 21, with 20/21 in another parent folder. Approve 19 as City Watch: one output, `Pratchett Terry/City Watch/City Watch - 19 - Feet of Clay - Pratchett Terry.m4b`, decodes cleanly. Fresh research of Hogfather 20 and Jingo 21 still asks the original Discworld split. |
| **M11: approve as shown on the author question, then Start** | **FAIL, Major** | Real automatic run first creates a held no-author book. Approve as shown says the answer is saved and to press Start. A real next Start leaves exactly the same `author_missing` question, zero jobs and zero outputs. This narrow repro was independently repeated once with a successful owned receipt (`ok:true`, code 0, native zero). The first broader driver also observed the same loop for ruling 33 (`name_language`) and two credits (`two_people`); see the ownership qualification below. |

The important distinction for M11 is **a real automatic hold**: production stores `until_change=True`. The new regression fixtures insert a Held result without that flag. Saving an entered author does not change the author-rule generation, so the real held record is skipped again on Start. Ender and Senua received this evidence before the corrective rebuild.

## Findings and remaining scope

- **Major M13 remains open:** Stop is undone by Approve at the conversion queue, even though set-wide automatic starts were removed. Fix disposition: Ender's same corrective batch.
- **Major M11 remains open:** the saved author answer still loops when the question came from a real held run. Fix disposition: same batch; the no-author, spelling and two-credit cases must use real held semantics.
- **Senua M15, construction finding:** with an old foreign Cyrillic keep rule, saving only the title can suppress the English-name question. Not duplicated by QA; Senua's evidence is `q23j/senua/r59-result.json`. Included in the same batch before the next candidate.
- Pattern alert: **an answer is reported saved, but the book still asks the same question after Start**. Reopened by the real-held M11 flow; disposition **fix** in this batch.
- Blockers: 0. QA Majors: 2 open. New Minors: 0. No loss of the last audio copy was found; M13 removed originals only after their verified private Sorted outputs existed, but still violated Stop.

## Ownership, limitations and disposal

The first broad private driver completed its observations and wrote UTF-8 `delta-results.json`, but its stdout used the Windows encoding while the owner's wire expected UTF-8. The owner rejected the final streamed-byte comparison (`Final supervisor output differs from streamed bytes`); **that invocation is not claimed as a successful command**. It nevertheless closed the exact private job with zero remaining owned processes. The local evidence and actual output files remain for review. I corrected only my logger to emit ASCII JSON, then repeated just the no-author M11 case: `m11-confirm-owned.json` has `ok:true`, exit 0, closed true and native zero. No product files or test assertions were changed by me.

Two earlier probe setup attempts failed before the behavior check (an ESM import URL, then my scan/empty-queue wait assumptions). They are probe mistakes, not product findings. Their owned jobs closed; no retry of the full entry check occurred.

Not run on this superseded candidate: the remaining language variants and m20/m22 controls; the HTTP/page layer; actual hidden packaged-shell launch/Quit; real mouse/keyboard/tray clicks, window X or focus; installer/updater; other viewports/themes. No file under `web/` or `desktop/` changed in this delta, so no screenshot is claimed. The hidden shell check is deferred to the corrective candidate after Senua approves its exact helper. Ruling 57 and Discworld evidence above can carry; the three residual fixes get a narrow recheck after rebuild.

Evidence lives only in `C:/Antigravity Projects/Worktrees/Books Arranger/q23j/futaba`: `delta-results.json`, `delta-owned.json`, `m11-confirm-results.json`, `m11-confirm-owned.json`, my driver and private labs. Preserved until the corrective candidate and reports close these findings, then removed with the parent `q23j` by the studio sweep. No process of mine remains alive. No Z: or live `data/` writes, profile install, desktop interaction, or change to any other tool occurred. This report is my only repository edit; I did not stage, commit or push it.

Verdict of the previous 3545d17 pass (superseded): NO-GO.

---

# Previous pass: candidate cf166bf (superseded by the 3545d17 pass above)

Pass run 2026-10-28 on candidate cf166bf (the rebuild of 0.22.3 that replaces 51caef1, where I gave NO-GO on M-1; code in 798001a), checking only the delta since 51caef1 plus a short smoke. Tester: Futaba. Behavior only; construction is Senua's. Lean verification (ProcessRules, Lean verification): I did not re-run the entry check or the full suite; I compared hashes, then checked each changed behavior once. Sergei was at the machine: no mouse, keyboard, tray click or focus, and no window of mine was ever shown. Everything ran headless from the payload extracted from the installer, with a private profile and private LOCALAPPDATA, APPDATA, TEMP and USERPROFILE. No port was opened. Sergei's profile, live data, Z:, port 5210 and his running app were not touched; no process was killed.

This section replaces the pass on candidate 51caef1 (NO-GO), kept below as a superseded section together with the ddfbfa7 pass.

Historical source commit: cf166bfa7cab8c1381a14c82b7409fbc75b91139
Historical artifact manifest SHA256: 516d559f0901be12ba3fecdcab4b6b7bee31fdeb0ea79702817cce525367f17a

## Result in plain words

- **GO. Blockers: 0. Majors: 0 open (M-1 from the 51caef1 pass is closed). Minors: 0 new. Data loss found: none. Pattern alerts: none open.**
- **M-1 is fixed.** A numbered set is asked; Sergei's Approve of its first book, through the series question, now releases the rest, and they file by themselves under the same series folder in all three states I was asked to check: after the run has ended, after a rescan, and from a run he stopped. All outputs decode with 0 errors.
- **M10 works.** An Approve that answers "Same author?" or the English spelling keeps that answer, files nothing and asks the series next. «Курс истории. Лекция 2. Рим» did not file by itself. Only the Approve on the series question released the set.
- **Typing a better series on book 1 works.** Approving book 1 as «Курс истории» files books 2 and 3 under «Курс истории» too (that was my observation on the 51caef1 pass).
- **m22 and m20 work.** «Финал 3. Финал» is asked; siblings with no author credit no longer vote for another author's book.
- The smoke files cleanly: two books, both decode with 0 errors.
- Nothing in `web/` or `desktop/` changed since 51caef1 (11 files: four backend `.py` files, two check scripts, three test files, two docs), so no screenshots were needed.

## 1. Build identity (compared by hash, entry check not re-run)

- Installer `cand-0223i/dist/builds/062b5136-80f0-47ac-911d-5426abc45c04/Books-Arranger-Setup-0.22.3.exe` SHA-256 `ddcd049262df8c294de0afc1804a95297f1b10c11ca5ab48bc47c594c4728c9e`: equals the handoff.
- Manifest `cand-0223i/dist/release-artifacts.json` SHA-256 `516d559f0901be12ba3fecdcab4b6b7bee31fdeb0ea79702817cce525367f17a`: equals the handoff. It names `source_head` cf166bfa7cab8c1381a14c82b7409fbc75b91139 and version 0.22.3.
- `cand-0223i` HEAD `cf166bfa7cab8c1381a14c82b7409fbc75b91139`, 0 changed paths (checked at the start and again at the end). Two commits since 51caef1: `798001a` (the fix) and `cf166bf` (docs: Brief and backlog).
- Ender's receipt, last receipt line of `q23i/logs/ender-entry.log`: `Entry-check receipt v2: books-arranger v0.22.3 @ cf166bfa7cab8c1381a14c82b7409fbc75b91139 (dirty: N) [source:9fd4c052... harness:5d5187d5... runtime:da70c9a7... checker:...] ... check pass`, followed by `entry exit 0`. Reads `check pass`, dirty N, at cf166bf.
- Payload extracted from the installer with the repo's pinned 7-Zip (`node_modules/7zip-bin/win/x64/7za.exe`, SHA-256 `b0cfdeaf429f5cc53f85123dd8f5a5feb92c19d31aa34df257edf9a26be05f95`, the same as my earlier passes): 292 files; the one warning is "data after the end of archive" (the NSIS trailer). `resources/backend/VERSION` reads 0.22.3. All 81 backend `.py` files in the payload are byte-identical to the files in the clean `cand-0223i` worktree (compared with `cmp`, 0 differing). I did not re-hash all 292 files against the manifest. The installer was not run.
- The pinned QA runtime at `WIP/Books Arranger/build-cache/qa-runtime` holds the same `python.exe` (SHA-256 `434b361f...`) and `ffmpeg.exe` (`a3bf949b...`) as the payload, byte for byte; I ran that Python with the packaged backend.

## 2. Method and limits

- Engine: the pinned runtime's `python.exe -I -B` with the **packaged** backend and FFmpeg, driven in-process by a script of mine: the real `Inventory`, `MergeService`, `PublicResearch.lookup`, `approval_preview`, `approve_book` (with `choice`, `author` and `names`), `automatic.start()`, `automatic.stop()` and `automatic.cancel_start()`, over real tagged files in a private audio root with a separate Sorted folder. Multi-file books are two 0.4 s MP3s; one-file books (m20) are `.m4b` files made with the packaged FFmpeg. One private lab per scenario (m1a to m1e, m10a, m10b, m22, m22b, m20 with five labs, smoke), each with its own catalog. The shell, the HTTP layer and the page were not exercised (none changed). Each Approve passed the "Goes to" path the preview showed, as the page does.
- Settling: after each Approve I waited until no run, job or pending start existed for several polls in a row, because a release can start a run after the job.
- **No outbound network, with a positive control:** the script refuses every non-loopback `socket.connect` and logs it. A deliberate connect to 93.184.216.34:80 was refused and logged (1 attempt). All 11 scenario runs logged 0 attempts. Research transport: the seam the repo's own tests use, offline everywhere (HTTP 503); no canned answers this time.
- **One fault injection, named:** scenario m1e replaces `automatic.request_start` with a stub that answers "blocked" (Ender's own test does the same). Without it the release starts a run at once (see item 1), so the rescan path could not be reached otherwise. Nothing else was patched.
- Names with a colon are written with `_` in the folder names (Windows); the album tag keeps the colon. Cyrillic authors are written in Cyrillic.
- Time: over the 30-minute budget, because the first paused-run attempt was wrong (my own wait condition never matched, so that run had already ended when I stopped it; I fixed the driver and reran it).

## 3. The delta, each item checked once (packaged cf166bf)

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | M-1 re-check: set on hold, approve book 1, the rest file after the run has ended, after a rescan, and from a paused run | **Pass (all three)** | Set «Курс истории. Лекция N» (Иван Петров), three two-file books. One run: `Completed`, all three Held, asked `title_series`, 0 jobs, Sorted empty. **After the run has ended (m1a):** Approve of book 1 (Goes to `Петров Иван\Курс истории. Лекция\Курс истории. Лекция - 1 - Греция - Петров Иван.m4b`). Right after `approve_book` returned, the automatic state was already `Running` (the release started a run); settled `Completed`; books 2 and 3 filed by themselves at `...\Курс истории. Лекция - 2 - Рим - ...` and `... - 3 - Египет - ...`; 3 jobs `completed`, all decode with 0 errors, no further action from me. **After a rescan (m1b, m1e):** unblocked, the release run files the rest at once, so no rescan was needed (m1b: cancelling the pending start had nothing to cancel, the run was already going; 3 files). With the release start blocked (m1e, fault injection): after the Approve job the control shows books 2 and 3 still Held (`title_series`) and 1 job; then Scan again plus a run: books 2 and 3 filed, 3 files, decode clean. **From a paused run (m1c):** a second run with five new padded filler books was stopped with the real Stop while it was alive; state `Paused` ("Paused - pending work saved"); Approve of book 1 while paused; settled `Completed`; books 2 and 3 filed, 3 set files completed and clean. |
| 2 | M10: an Approve that answers an author question keeps the answer, files nothing, and the series is asked next; only the series Approve releases the set | **Pass (both author questions)** | **"Same author?" (m10a):** books «Курс истории. Лекция 1. Греция» and «... 2. Рим» credited «Dean Koonts» beside a real book credited «Dean Koontz» (that book filed itself as `Koontz Dean\Odd Thomas - Koontz Dean.m4b`). Both set books asked `same_author` (why `near`). `approve_book(choice='same')` raised `SeriesAsked`: "Your answer is saved. The book is checked again with it, and its series is asked next: check Series, Number and Title, then approve. Nothing was filed yet." After it: 0 jobs added, the rule `Dean Koonts -> Koontz Dean` kept, both books asked `title_series` with Series «Курс истории. Лекция» and author «Koontz Dean»; «Лекция 2. Рим» was **not** filed. Then the Approve on the series question: both filed under `Koontz Dean\Курс истории. Лекция\`, decode clean. **English spelling (m10b):** set by «Джеймс Роллинс», every source offline, both asked `english_spelling`; `approve_book(author='James Rollins')` raised `SeriesAsked`; rule `Джеймс Роллинс -> Rollins James` kept, 0 jobs, Sorted empty, both now asked `title_series` with author «Rollins James»; the series Approve then filed both under `Rollins James\Курс истории. Лекция\`, decode clean. |
| 3 | Edit the series on book 1 to «Курс истории» and approve; the rest follow under «Курс истории» | **Pass** | Lab m1d: Approve of book 1 with `names={'series': 'Курс истории', 'number': '1'}`: Goes to `Петров Иван\Курс истории\Курс истории - 1 - Греция - Петров Иван.m4b`. Settled `Completed`: books 2 and 3 filed `...\Курс истории\Курс истории - 2 - Рим - ...` and `... - 3 - Египет - ...`, all 3 completed and clean; the Sorted tree holds only the «Курс истории» folder (no «Курс истории. Лекция» folder). |
| 4 | m22: «Финал 3. Финал» asks, and does not file into the asked «Шерлок Холмс. Аудиоспектакль» set | **Pass** | Lab m22: books 1 and 2 «Шерлок Холмс. Аудиоспектакль N. ...» and book 3 album «Финал 3. Финал», same parent folder, same author. One run: all three Held, `title_series`; book 3's split is {series «Шерлок Холмс. Аудиоспектакль», number 3, title «Финал»} (the sibling series filled in, not filed); 0 jobs, Sorted empty. Control lab m22b (ruling 45 case): «Мертвый ноль 7» beside two same-author «Сновидения Ехо» books now also asks (split «Сновидения Ехо», 7); Approve of «Сновидения Ехо 4» then filed all three under `Фрай Макс\Сновидения Ехо\`, decode clean (see observations). |
| 5 | m20: siblings with no author credit don't vote for another author's book | **Pass** | Lab m20: two «Червь» books with **no** artist tag beside «Мертвый ноль 7. Мертвый ноль» credited «Макс Фрай», in `Unsorted` and in the author's own folder: asked, split {Мертвый ноль, 7, Мертвый ноль}; not book 7 of «Червь». One two-file book whose files carry two album spellings («Темная» / «Тёмная») beside it (the book list shows 2 books, of 2 and 1 files): the book is asked, split {Мертвый ноль, 7}, the two spellings did not make two votes. Control: «Червь» siblings credited to another author (Джон МакКрэй): asked. |
| 6 | Smoke: the core filing flow | **Pass** | Two books, two files each (album «Тихий Дон» and album «The Long Road», author Peter Hale), one automatic run: `Completed`, 2 jobs `completed`, filed `Hale Peter\Тихий Дон - Hale Peter.m4b` and `Hale Peter\The Long Road - Hale Peter.m4b`, both decode with 0 errors, all source files gone. |

## 4. Findings

### Blocker (0)

### Major (0)

M-1 (the 51caef1 Major) is **closed**: verified fixed in the packaged build after the run ended, after a rescan and from a paused run (item 1).

### Minor (0 new)

### Observations, not defects (flag only)

- **The answer to an author question arrives as a refusal.** `approve_book` reports the kept answer by raising `SeriesAsked` (a `ValueError`) with the message above. The engine behaves correctly (answer saved, nothing filed, series asked next). How the page shows it was not exercised: if the page renders every `ValueError` of Approve as a refusal, Sergei sees an error-looking message for an answer that was in fact saved. A question for Judy, not a code bug.
- **The ruling 45 case changed on purpose (m22).** In my 51caef1 pass «Мертвый ноль 7» beside two «Сновидения Ехо» books filed silently into «Сновидения Ехо»; it now asks (filled in) until Sorted holds that series, and approving one «Сновидения Ехо» book releases it (lab m22b). My 51caef1 statement "the ruling 45 case still confirms" no longer holds; the new outcome is what m22 and Ender's tests say.
- **«Финал 3. Финал» follows the set without its own question.** It is asked first (item 4), but when Sergei approves book 1 of the «Шерлок Холмс. Аудиоспектакль» set, «Финал» files with the set as number 3 (`Шерлок Холмс. Аудиоспектакль - 3 - Финал`), because its ask named the same series. That is what Ender's test expects ("his answer for the set"); I flag it only so Sergei knows a book can join a set through its first book's answer.
- Carried, not new: a split asked under rulings 52 and 53 shows the existing label `Held - Title or author missing` for a question that is really "confirm this series?". How the page words it was not exercised.
- Carried unchanged from the earlier passes: a manual Approve before research has learned a rule mixes scripts in "Goes to".

## 5. Screenshots

None taken. No file under `web/` or `desktop/` changed between 51caef1 and cf166bf.

## 6. Not run

- **Real-input checks: not run (Sergei present).** The tray's Quit item and tooltip, every real click, the window's X button, and closing the app from every top-level screen. The shell and its close paths were not exercised (not in the delta).
- The HTTP layer and the page (unchanged): where the question shows, the refusal-style message for M10, the Approve button for a `title_series` ask, the names editor. The engine-level ask, Goes to line (`approval_preview`), `approve_book`, `automatic.stop()` and `cancel_start()` only.
- A rescan reached through the real path only with the start blocked (fault injection, named in section 2); unblocked, the release run starts at once.
- A set whose books are one-file `.m4b` (ruling 53 with ruling 54): not run; the sets were two-file MP3 books.
- The M10 case "an author choice" and "a hold" (the other Approves the code lists as no answer to the series question): only "Same author?" and the English spelling were run.
- The real NSIS install, the updater, Restart to update, Cancel update (not in the delta). No light theme, no other viewport.
- Carried, not re-run: M9, rulings 54 and 55, m21 and the smoke items from the 51caef1 pass (below), and everything older. m22 and m20 changed how rulings 45 and 54 resolve; the controls above were re-run for that.

## 7. Disposal

All of my output lives in `C:/Antigravity Projects/Worktrees/Books Arranger/q23i/f2` (about 590 MB: the extracted payload, the labs with their private catalogs and Sorted folders, the private profile, logs and my launcher), as the brief allows. **Left on disk for Ender's cleanup of `q23i`:** that folder. My scratchpad driver and draft files are removed with `node scripts/studio-sweep.mjs --apply --path`. From the earlier 51caef1 pass, `C:/Antigravity Projects/Worktrees/Books Arranger/q23h/f1` (about 590 MB) is also still on disk. No engine or process of mine outlives the run (each driver exits itself). I read source and `q23i/logs/ender-entry.log` and ran the repo's pinned `7za.exe` from `cand-0223i`'s `node_modules` (the extraction wrote only into my run folder); `cand-0223i` still shows 0 changed paths. This report is the only repo file I changed, uncommitted.

## 8. Pattern alerts

Pattern alerts: none open. Pattern alert 1 from the 51caef1 pass ("an answer from Sergei does not release the other books that depend on it") is **closed**: its fix is verified through the real run in the ended, rescanned and paused states (item 1), and M10 now keeps the answer to an author question without releasing the set early (item 2).

## 9. Verdict basis

GO: the Major from the 51caef1 pass is fixed in the packaged build, the four other changes pass, the smoke is clean, nothing was lost and every output decodes. The open questions are for the page (how the kept-answer message reads), not for the engine.

Verdict of the previous cf166bf pass (superseded): GO.

---

# Previous pass: candidate 51caef1 (superseded by the cf166bf pass above)

Pass run 2026-10-28 on candidate 51caef1 (the rebuild of 0.22.3 after M9, rulings 53, 54 and 55 and m21; code in b2f8660), checking only the delta since ddfbfa7 plus a short smoke. Tester: Futaba. Behavior only; construction is Senua's. Lean verification (ProcessRules, Lean verification): I did not re-run the entry check or the full suite; I compared hashes, then checked each changed behavior once (and the ruling 53 question several ways, see M-1). Sergei was at the machine: no mouse, keyboard, tray click or focus, and no window of mine was ever shown. Everything ran headless from the payload extracted from the installer, with a private profile and private LOCALAPPDATA, APPDATA, TEMP and USERPROFILE. No port was opened. Sergei's profile, live data, Z:, port 5210 and his running app were not touched; no process was killed.

This section replaces the pass on candidate ddfbfa7 (GO), which is kept below as a superseded section for its carried items. The 51caef1 pass does not repeat them.


### Result in plain words

- **NO-GO. Blockers: 0. Majors: 1 open (M-1, new). Minors: 0 new. Data loss found: none. Pattern alerts: 1 (section 8).**
- Four of the five changes work in the packaged build, and the smoke files cleanly:
  - M9: «Отряд Сигма 2. Карта костей» by «Джеймс Роллинс» is looked up first, the author's rule is learned, and Approve files it under `Rollins James\Отряд Сигма\`.
  - Ruling 54: one-file siblings vote once per book, never in the library root, and only the same author's books vote. The ruling 45 case (Мертвый ноль, siblings carrying «Сновидения Ехо») still confirms.
  - m21: an "Entered by you" title or author alone no longer skips the series question. His saved series or number, or his Approve, answers it.
  - Ruling 55: a book folder inside a folder named like the series asks, with Series, Number and Title filled in.
- **Ruling 53 works only half.** A numbered set that only repeats its own name pattern is now asked, and nothing files silently into a junk folder (good). But "approve the first book and the rest file themselves" does not happen in the normal flow: after the automatic run has finished, Sergei's Approve of book 1 leaves books 2 and 3 asked, and they stay asked after another run and after a rescan. It works only if the run is still running when he approves. That is M-1.
- Nothing in `web/` or `desktop/` changed since ddfbfa7 (7 files: `local_identity.py`, `merge_service.py`, `public_research.py`, three test files, one doc), so no screenshots were needed.
- Every output of every run decodes with 0 errors.

### 1. Build identity (compared by hash, entry check not re-run)

- Installer `cand-0223h/dist/builds/21f3a90e-1d05-4da2-ba77-0279298db70a/Books-Arranger-Setup-0.22.3.exe` SHA-256 `ab2724469ca00916f0c6fd38f118e6ed088849c674b4e3b35ef653d7d2ccfc90`: equals the handoff.
- Manifest `cand-0223h/dist/release-artifacts.json` SHA-256 `6883c310425f9ae345f6f6a30615b63b755633f6b6da3530e7b4e89789d8fea2`: equals the handoff.
- `cand-0223h` HEAD `51caef103219a6c07731de4c2b6783a8e0fa316b`, 0 changed paths (checked at the start and again at the end). Two commits since ddfbfa7: `b2f8660` (the fix) and `51caef1` (docs: backlog).
- Ender's receipt, last receipt line of `q23h/logs/ender-entry.log`: `Entry-check receipt v2: books-arranger v0.22.3 @ 51caef103219a6c07731de4c2b6783a8e0fa316b (dirty: N) [source:8853f145... harness:d6a2b088... runtime:da70c9a7... checker:a448c08c...] - pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a`, followed by `entry exit 0`. Reads `check pass`, dirty N, at 51caef1.
- Payload extracted from the installer with the repo's pinned 7-Zip (`node_modules/7zip-bin/win/x64/7za.exe`, SHA-256 `b0cfdeaf429f5cc53f85123dd8f5a5feb92c19d31aa34df257edf9a26be05f95`, the same as my earlier passes): 292 files; the one warning is "data after the end of archive" (the NSIS trailer). `resources/backend/VERSION` reads 0.22.3. All 81 backend `.py` files in the payload are byte-identical to the files in the clean `cand-0223h` worktree (compared with `cmp`, 0 differing). I did not re-hash all 292 files against the manifest (the payload comes straight from the hashed installer). The installer was not run.
- The pinned QA runtime at `WIP/Books Arranger/build-cache/qa-runtime` holds the same `python.exe` (SHA-256 `434b361f...`) and `ffmpeg.exe` (`a3bf949b...`) as the payload, byte for byte; I ran that Python with the packaged backend.

### 2. Method and limits

- Engine: the pinned runtime's `python.exe -I -B` with the **packaged** backend and FFmpeg, driven in-process by a script of mine: the real `Inventory`, `MergeService`, `PublicResearch.lookup`, `approval_preview`, `approve_book` (with and without `names`), `names_save` and `automatic.start()` over real tagged files in a private audio root with a separate Sorted folder. Multi-file books are two 0.4 s MP3s; one-file books (ruling 54) are `.m4b` files made with the packaged FFmpeg. One private lab per scenario (m9a, m9b, m9c, m9d, r53a to r53e, r54a to r54e, m21, m21b to m21d, r55, smoke), each with its own catalog. The shell, the HTTP layer and the page were not exercised (none changed).
- **No outbound network, with a positive control:** the script refuses every non-loopback `socket.connect` and logs it. A deliberate connect to 93.184.216.34:80 was refused and logged (1 attempt). Every scenario run logged 0 attempts.
- Research transport: the seam the repo's own tests use (`PublicClient(fetch=...)`). Offline everywhere (HTTP 503), except labs m9a and m9b, where a canned stand-in for api.fantlab.ru answers the two requests `_gap_fantlab` makes (a search record and the extended work record). I did not patch `_author_latin` or any function under test; the lookup, the learning of the rule, the ask and the filing are the packaged code.
- Names with a colon are written with `_` in the folder names (Windows); the album tag keeps the colon. Cyrillic authors are written in Cyrillic.
- Time: well over the 30-minute budget, because ruling 53 needed several variants to pin down M-1.

### 3. The delta, each item checked once (packaged 51caef1)

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | M9: «Отряд Сигма 2. Карта костей» by «Джеймс Роллинс» files under `Rollins James\` | **Pass** | Lab m9a (FantLab record with no English original title): one automatic run: `Completed`, the book Held, asked `title_author / title_series`, split {series «Отряд Сигма», number 2, title «Карта костей»}. The two FantLab requests were made, and the author rule `Джеймс Роллинс -> Rollins James` was learned before the ask. Goes to `Rollins James\Отряд Сигма\Отряд Сигма - 2 - Карта костей - Rollins James.m4b`; 0 jobs and an empty Sorted before Approve. Real `approve_book`: job `completed`, filed at exactly that path, decodes with 0 errors, sources removed. Lab m9b (record carries the English original «Map of Bones»): the same, filed `Rollins James\Отряд Сигма\Отряд Сигма - 2 - Map of Bones - Rollins James.m4b` (ruling 38 replaces the title; see observations). Control m9c (every source answers 503): asked `author_unclear / english_spelling` first, no series question, no rule, nothing filed. Control m9d (ruling 33): «Ilya Marchenko - Мир драконов 1. Начало» asked `author_unclear / name_language` first, 0 jobs. |
| 2 | Ruling 53: a set that only repeats its name pattern is asked once; approving the first book lets the rest file themselves | **Half. Ask: pass. The rest following: FAIL (M-1)** | Sets «Курс истории. Лекция N» (Иван Петров, lab r53a) and «Шерлок Холмс. Аудиоспектакль N» (Петр Иванов, lab r53b), three two-file books each. One run: `Completed`, all three of each set Held, asked `title_series` with the split filled in (series «Курс истории. Лекция», numbers 1 to 3), 0 jobs, Sorted empty: nothing filed silently. Approve of book 1 (Goes to `Петров Иван\Курс истории. Лекция\Курс истории. Лекция - 1 - Греция - Петров Иван.m4b`): job `completed`, decodes with 0 errors. **Books 2 and 3 right after: still Held. After one more automatic run: still Held (r53a, r53b). After Scan again plus a run (r53e): still Held. Same when he typed his own series (r53c).** Only when the run was still running at the moment of Approve (r53d: six padded filler books, book 1 approved while the run was alive) did books 2 and 3 file themselves, into the same series folder, all three decode with 0 errors. The ruling 45 control is item 3. |
| 3 | Ruling 54: one-file siblings vote once per book, not in the library root, same author only | **Pass** | Lab r54a (same author, three one-file books plus one 4-file book «Лабиринты Ехо 3» in the same folder; the page shows books of 1, 1, 1 and 4 files): «Мертвый ноль 7. Мертвый ноль» is not asked, series «Сновидения Ехо», number 7, Goes to `Фрай Макс\Сновидения Ехо\Сновидения Ехо - 7 - Мертвый ноль - Фрай Макс.m4b`: two books outvote one 4-file book, and the ruling 45 case still confirms. Lab r54b (the same books directly in the library root): asked, split {Мертвый ноль, 7, Мертвый ноль}; nobody votes in the root. Lab r54c (another author's «Червь 1» and «Червь 2» beside it, in Unsorted): asked, split {Мертвый ноль, 7}; never book 7 of «Червь». Lab r54e (the same «Червь» books, other author, library root): asked. Control r54d (the «Червь» books credited to the same author): not asked, files as «Червь» 7: the vote counts when the author matches. |
| 4 | m21: an "Entered by you" title or author alone no longer skips the series ask | **Pass** | Lab m21: baseline asked `title_series`. With an "Entered by you" record holding only the author (saved the way the 0.22.2 panel does, through `manual_metadata`): author state `entered`, still asked `title_series` with the split filled in. Lab m21d: a record holding only the title: still asked. Controls: `names_save` with only the author: `unchanged`, still asked; `names_save` with series «Курс истории» and number 3 (lab m21c): `saved`, then no ask, series «Курс истории», number 3. Approve with those names files `Петров Иван\Курс истории\Курс истории - 3 - Греция - Петров Иван.m4b` (lab m21); a plain Approve files `Петров Иван\Курс истории. Лекция\Курс истории. Лекция - 3 - Греция - Петров Иван.m4b` (lab m21b); both decode with 0 errors. |
| 5 | Ruling 55: a source folder named like the series asks, fields pre-filled | **Pass** | Lab r55: `Unsorted\Олег Дивов\Профессия_ инквизитор\Профессия_ инквизитор 2. Живые и мертвые` (two files, author «Олег Дивов»). One run: Held, asked `title_series`, 0 jobs, Sorted empty. The ask carries title «Живые и мертвые», author «Дивов Олег», series «Профессия: инквизитор», number 2. Goes to `Дивов Олег\Профессия_ инквизитор\Профессия_ инквизитор - 2 - Живые и мертвые - Дивов Олег.m4b`. Approve filed exactly that path; decodes with 0 errors. |
| 6 | Smoke: the core filing flow | **Pass** | Two books, two files each (album «Тихий Дон» and album «The Long Road», author Peter Hale), one automatic run: `Completed`, 2 jobs `completed`, filed `Hale Peter\Тихий Дон - Hale Peter.m4b` and `Hale Peter\The Long Road - Hale Peter.m4b`, both decode with 0 errors, all source files gone, 0 outbound attempts. |

### 4. Findings

#### Blocker (0)

#### Major (1)

- **M-1 (new, caused by b2f8660, ruling 53): approving the first book of an asked set does not release the rest once the automatic run has ended.** Repro (labs r53a, r53b, r53c, r53e, all the same):
  1. Three books «Курс истории. Лекция 1. Греция», «... 2. Рим», «... 3. Египет» in `Иван Петров\Курс истории\1`, `2`, `3`, two MP3 files each, author tag «Иван Петров». Scan, then one automatic run. It ends `Completed` with all three Held, asked `title_series`. Correct so far.
  2. Approve book 1 (the filled-in split). It files under `Петров Иван\Курс истории. Лекция\`. Correct.
  3. Look at books 2 and 3: still Held, still asked `title_series`, no job. Run automatic again, or Scan again and run: still Held, still no job. Nothing releases them; he has to approve each one by hand.
  - Expected (ruling 53, Ender's handoff): books 2 and 3 file by themselves after step 2.
  - What I read in the code (evidence, not a fix): `MergeService._continue_after_series` (`merge_service.py` around line 3108) only calls `automatic.requeue(id)`. When the run has ended, `AutomaticProcessing.requeue` (`automatic_processing.py` line 326) puts nothing anywhere and returns `'this_run'` (line 336). On the next run a Held book with `until_change` is skipped unless its research is "changed" (`automatic_processing.py` lines 629 to 633, `rules_changed_for`); a new approved job in Sorted is not a rules change. The 0.22.0 rule path (`_continue_after_rule`) works because a new rule does make `rules_changed_for` true. Ender's ruling 53 test (`test_ruling_53_approving_the_first_book_of_a_set_files_the_rest`) replaces `automatic.requeue` with a recorder, so it checks that the call is made and never runs the real run.
  - Where it does work: with the run still alive at Approve time (r53d), books that are then researched see his approved job and file by themselves. The bad case is the ordinary one: the run finished with the set asked, then Sergei works through his to-do list.
  - Why Major, not Blocker: nothing files wrongly and nothing is lost; the rest stay safely asked and he can approve them one at a time, as he could before 0.22.3. But it is the headline of ruling 53 and Sergei will see it on the first set he meets.

#### Minor (0 new)

#### Observations, not defects (flag only)

- **Typing a better series name on book 1 can never release the rest.** The set asks every book with the pattern's own series («Курс истории. Лекция»), which is the junk name. If Sergei corrects book 1 in Edit names to «Курс истории» (lab r53c), its job holds «Курс истории», while books 2 and 3 are still asked with «Курс истории. Лекция», so even a working release (M-1 fixed) would not match them. Tested only on the ended-run path, where nothing releases the rest anyway. A question for Jane and Sergei about what ruling 53 means in that case, not a code bug as written.
- With the FantLab record carrying an English original title (lab m9b), the book files as `Rollins James\Отряд Сигма\Отряд Сигма - 2 - Map of Bones - Rollins James.m4b`: a Cyrillic series folder and an English title in one name. That is ruling 38 (the English original replaces the title), unchanged by this delta; I only note that the split the series question shows then reads «Map of Bones», not «Карта костей».
- Control r54d shows the ruling 45 trade-off: a book of another series by the same author, beside two books of «Червь», files silently as «Червь» 7 when its number is free. That is how ruling 45 is meant to work; I flag it only because ruling 54 now makes the author the one gate.
- Carried, not new: a split asked under rulings 52 and 53 shows the existing label `Held - Title or author missing` for a question that is really "confirm this series?". How the page words it was not exercised.
- Carried unchanged from the earlier passes: a manual Approve before research has learned a rule mixes scripts in "Goes to".

### 5. Screenshots

None taken. No file under `web/` or `desktop/` changed between ddfbfa7 and 51caef1.

### 6. Not run

- **Real-input checks: not run (Sergei present).** The tray's Quit item and tooltip, every real click, the window's X button, and closing the app from every top-level screen. The shell and its close paths were not exercised (not in the delta).
- The HTTP layer and the page (unchanged). Where the question shows on Sergei's page (labels, the filled-in Series, Number and Title in the names editor, the Approve button for a `title_series` ask): not exercised; the engine-level ask, Goes to line (`approval_preview`), `approve_book` and `names_save` only.
- Ruling 53 with the run **paused** (not running, not ended) at the moment of Approve: not run. `requeue` stores the book in the saved run's list in that state; I did not drive it. In r53d the already-researched set books were not yet Held when I approved (only book 1 was), so the `requeue` of an already-Held book on a live run was not exercised either.
- A set whose books are one-file `.m4b` (ruling 53 with ruling 54): not run; the sets were two-file MP3 books.
- The real NSIS install, the updater, Restart to update, Cancel update (not in the delta). No light theme, no other viewport.
- Carried, not re-run: the items of the ddfbfa7 pass below (ruling 52's asks, the look-alike and junk-series traps), the 067315f, 92376c7, d4a7450 and 65ddd72 passes. Where an earlier item involved siblings carrying the same pattern (ddfbfa7 item 3, "two sibling books confirm it and the third files by itself"), ruling 53 changed its outcome on purpose: those sets are now asked.

### 7. Disposal

All of my output lived in `Worktrees/Books Arranger/q23h/f1` (the payload extraction, the labs with their private catalogs and Sorted folders, the private profile, logs and my launcher) and my driver scripts in my session scratchpad. No engine or process of mine outlives the run (each driver exits itself). I read source and `q23h/logs/ender-entry.log` and ran the repo's pinned `7za.exe` from `cand-0223h`'s `node_modules` (the extraction wrote only into my run folder); `cand-0223h` still shows 0 changed paths. This report is the only repo file I changed, uncommitted.

**Not fully cleaned up.** My three driver and draft files in the session scratchpad were removed with `node scripts/studio-sweep.mjs --apply --path`. The run folder `C:/Antigravity Projects/Worktrees/Books Arranger/q23h/f1` (about 590 MB: the extracted payload, the labs, the private profile, logs) is **still on disk**: the sweep refuses a `--path` that is a subfolder of a Worktrees entry ("under Worktrees, --path must name one <Tool>\<purpose> entry"), and the per-path planner refuses the location ("Container must be strictly inside the studio ... or the system temp directory"). I did not work around either refusal. `q23h` itself is Ender's folder (his entry-check log and receipt live there), so I did not name it. Jane or Ender: once the receipt is no longer needed, `node scripts/studio-sweep.mjs --apply --path "C:/Antigravity Projects/Worktrees/Books Arranger/q23h"` removes `q23h` with my `f1` inside it, or the 48 h idle rule does.

### 8. Pattern alerts

**Pattern alert 1 (new): an answer from Sergei does not release the other books that depend on it.** First seen in the 0.22.0 pass (the interim report on b946ee7, Major: a book never continues after his "Same author" answer; fixed with `_continue_after_rule`). Seen again here (M-1: the rest of a set after his Approve of its first book; `_continue_after_series` copies the same `requeue` call, but the trigger that made the first one work, a changed rule, is missing). Same friction in different clothes: he answers one question and the other books that answer decides stay asked. Disposition: **fix** (proposed; Jane to confirm), together with M-1. Suggested check for any later "continue after" path: run it through the real automatic run with the run ended, not with `requeue` replaced by a recorder.

### 9. Verdict basis

NO-GO because the one open Major is the headline behavior of ruling 53 and fails in the normal flow (the run has ended when Sergei approves). Everything else in the delta passes and the smoke is clean, so the re-check after a fix is narrow: the r53a to r53e sequence above (Held set, Approve book 1, rest file by themselves after the run ended, and after a rescan), plus one run of the same smoke. If Sergei prefers to accept M-1 and ship, that is his call to make; I will not issue GO without the fix or his explicit acceptance.

Verdict of that pass (51caef1, superseded): NO-GO.

---

---

# Previous pass: candidate ddfbfa7 (superseded by the 51caef1 pass above; kept for the carried items)

Pass run 2026-10-27 on candidate ddfbfa7 (the ruling 52 rebuild of 0.22.3), checking only the delta since 067315f plus a 1-book smoke. Tester: Futaba. Behavior only; construction is Senua's. Lean verification (ProcessRules, Lean verification): I did not re-run the entry check or the full suite; I compared hashes, then checked each changed behavior once. Sergei was at the machine: no mouse, keyboard, tray click or focus, and no window of mine was ever shown. Everything ran headless from the payload extracted from the installer, with a private profile and private LOCALAPPDATA, APPDATA, TEMP and USERPROFILE. No port was opened. Sergei's profile, live data, Z:, port 5210 and his running app were not touched; no process was killed.

This file replaces the pass on candidate 067315f (GO). That pass's items (the ruling 51 asks, the "must still split" names, the whole «Мастер и Маргарита. CD 1» name) and the earlier ones are carried, not re-run (section 6); the "98 other names keep their outcome" claim lives in Ender's test (`RULING_51_KEPT` in `tests/test_folder_structure.py`), which is part of the suite the entry check passed; I did not repeat it and did not check its 98 names myself.


### Result in plain words

- **GO. Blockers: 0. Majors: 0. Minors: 0 new. Data loss found: none. Pattern alerts: none.**
- Ruling 52 works in the packaged build. A "Series N. Title" split that nothing confirms is asked, with Series, Number and Title filled in, and one Approve files exactly the path shown. A split whose series is confirmed (Sorted already holds it for this author, or two sibling books carry it) files by itself, into the same series folder.
- The two look-alike traps are closed end to end: «Аnita Blake» with a Cyrillic А files under "Anita Blake" (Latin), and «Отряд Сигма_01. Песчанный дьявол» and "Harry Potter Book 1 - ..." never file into a junk folder.
- The 1-book smoke files and decodes cleanly. Every output of every run decodes with 0 errors.
- Nothing in `web/` or `desktop/` changed since 067315f (6 files: `local_identity.py`, `public_research.py`, two test files, two docs), so no screenshots were needed.

### 1. Build identity (compared by hash, entry check not re-run)

- Installer `cand-0223g/dist/builds/3cc477d8-7896-4735-9a51-4f07f2b95009/Books-Arranger-Setup-0.22.3.exe` SHA-256 `8fb6ee90c4406f1c18f1761aa4ed691476eda1a4d69ad355b2d42fd7b9afae51`: equals the handoff.
- Manifest `cand-0223g/dist/release-artifacts.json` SHA-256 `2a26cb13354cf859f2ffcc401e577fd654a004f7c5420120094dffa9b6bc8cff`: equals the handoff. It names `source_head` ddfbfa79df8907699c89dcc5f1386b8388200b9f, build id 3cc477d8-7896-4735-9a51-4f07f2b95009, version 0.22.3.
- `cand-0223g` HEAD `ddfbfa79df8907699c89dcc5f1386b8388200b9f`, 0 changed paths (checked before and after my pass). Two commits since 067315f: `1138712` (the fix, ruling 52) and `ddfbfa7` (docs: ruling 52 and Senua's pass 5 in the Brief and backlog).
- Ender's receipt, last receipt line of `q23g/logs/ender-entry.log`: `Entry-check receipt v2: books-arranger v0.22.3 @ ddfbfa79df8907699c89dcc5f1386b8388200b9f (dirty: N) [source:c3815ed4... harness:b2197c2c... runtime:da70c9a7... checker:a448c08c...] - pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a`, followed by `entry exit 0`. Reads `check pass`, dirty N, at ddfbfa7.
- Payload extracted from the installer with the repo's pinned 7-Zip (`node_modules/7zip-bin/win/x64/7za.exe`, SHA-256 `b0cfdeaf429f5cc53f85123dd8f5a5feb92c19d31aa34df257edf9a26be05f95`, the same as my earlier passes): 292 files; the one warning is "data after the end of archive" (the NSIS trailer). `resources/backend/VERSION` reads 0.22.3. All 81 backend `.py` files in the payload are byte-identical to the files in the clean `cand-0223g` worktree (compared with `cmp`, 0 differing), including the two the delta changed (`local_identity.py`, `public_research.py`). I did not re-hash all 292 files against the manifest (the payload comes straight from the hashed installer). The installer was not run.

### 2. Method and limits

- Engine: the packaged `python.exe -I -B` with the packaged backend and FFmpeg, driven in-process by a small script of mine: the real `Inventory`, `MergeService`, `PublicResearch.lookup`, `approval_preview`, `approve_book` and `automatic.start()` over real tagged MP3 files (two per book, 0.4 s each, tags written with the packaged FFmpeg) in a private audio root with a separate Sorted folder. One private lab per scenario (A: items 1 and 2; B and B2: item 3 and its control; C: items 4, 5 and 6). Scenario A ran three times (the second and third time to read the page row's flags); the outcome was identical each time. The shell, the HTTP layer and the page were not exercised (none changed).
- **No outbound network, with a positive control:** the script refuses every non-loopback `socket.connect` and logs it, and the research transport answers HTTP 503. All scenario runs logged 0 attempts (the tags and the folders were enough). Positive control: a deliberate connect to 93.184.216.34:80 was refused by the block and logged (1 attempt).
- Names with a colon are written with `_` in the folder names (Windows); the album tag keeps the colon. The author on the English-named fixtures is "Peter Hale" (an English credit, as in the earlier passes); Cyrillic authors are written in Cyrillic.
- A shell command of mine that fed Python through stdin was refused by the studio's guard before it ran; nothing executed and I wrote the script to a file instead.

### 3. The delta, each item checked once (packaged ddfbfa7)

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | «Профессия: инквизитор 1. Леди не движется» alone asks, filled in; Goes to shows the series path; Approve files it under `Дивов Олег\Профессия_ инквизитор\…` | **Pass** | Lookup: `ask = title_author / title_series`, split `{series «Профессия: инквизитор», number 1, title «Леди не движется»}`, fields filled in (title, author «Дивов Олег», series, number). Goes to (`approval_preview`): `Дивов Олег\Профессия_ инквизитор\Профессия_ инквизитор - 1 - Леди не движется - Дивов Олег.m4b`. One automatic run: `Completed`, 1 book held, 0 jobs, both source files still in place, Sorted empty (not filed by itself). Then the real `approve_book` with the Goes to path: job `completed`, filed at exactly that path, decodes with 0 errors, manifest series «Профессия: инквизитор», number 1, title «Леди не движется», sources removed only after. |
| 2 | A second book of that series, after (1), files by itself into the same folder | **Pass** | «Профессия: инквизитор 2. Живые и мертвые» in a different parent folder (`Unsorted\Новое\Дивов Олег - …`), after (1) completed and a rescan, so Sorted is the only confirmation. Lookup: no reasons, no ask, series «Профессия: инквизитор», number 2. One automatic run: `Completed`, 0 held, filed `Дивов Олег\Профессия_ инквизитор\Профессия_ инквизитор - 2 - Живые и мертвые - Дивов Олег.m4b`, the same folder as book 1 (the Sorted tree holds one author folder, one series folder, two books), decodes with 0 errors, sources removed. |
| 3 | Two sibling books carrying a series confirm it, and the third files by itself | **Pass** | Three book folders `Unsorted\Иван Петров\1`, `2`, `3`, albums «Тайны Севера 1. Первый след», «… 2. Второй след», «… 3. Третий след». Lookups of all three: no ask, series «Тайны Севера». One automatic run: `Completed`, 0 held, three jobs `completed`, all under `Петров Иван\Тайны Севера\Тайны Севера - N - … - Петров Иван.m4b`, all decode with 0 errors, all 6 sources removed. **Control:** the same books 1 and 2 alone (one sibling each) are both asked `title_series` with the split filled in, 2 held, 0 jobs, Sorted empty: one sibling confirms nothing, two do. |
| 4 | «Аnita Blake» with a Cyrillic А files under "Anita Blake" | **Pass** | The fixture folder `Аnita Blake` holds U+0410 (checked by code point). Book "Guilty Pleasures" (Laurell K. Hamilton): lookup clean, series "Anita Blake", number 1. Filed by the automatic run as `Hamilton Laurell K\Anita Blake\Anita Blake - 1 - Guilty Pleasures - Hamilton Laurell K.m4b`; the filed path holds no Cyrillic code point; manifest series "Anita Blake" (Latin); the Sorted tree has one "Anita Blake" folder and no look-alike twin; decodes with 0 errors. |
| 5 | Silent junk-series check: «Отряд Сигма_01. Песчанный дьявол» and "Harry Potter Book 1 - …" never file into a junk folder | **Pass** | Sigma (Джеймс Роллинс): asked `title_series`, split `{series «Отряд Сигма», number 1, title «Песчанный дьявол»}` (the `_` before the number is gone from the series), Goes to `Rollins James\Отряд Сигма\Отряд Сигма - 1 - Песчанный дьявол - Rollins James.m4b` (clean folder). "Harry Potter Book 1 - The Philosopher's Stone" (Peter Hale): asked `title_series`, no split filled in (nothing guessed), Goes to `Hale Peter\Harry Potter Book 1 - The Philosopher's Stone - Hale Peter.m4b` (whole name, no series folder). One automatic run: both `Held`, their 4 source files untouched, and the Sorted tree holds no folder or file with «Отряд Сигма_» or «Harry Potter Book» in it. |
| 6 | 1-book smoke | **Pass** | One book (album «Тихий Дон», two MP3 files, Peter Hale) in the same run as items 4 and 5: lookup clean, filed `Hale Peter\Тихий Дон - Hale Peter.m4b`, decodes with 0 errors, both source files gone, no outbound attempts. The four-book run as a whole: state `Completed`, 2 jobs `completed` (Anita Blake, Тихий Дон), 2 held (Sigma, Harry Potter). |

### 4. Findings

#### Blocker (0)

#### Major (0)

#### Minor (0 new)

#### Observations, not defects (flag only)

- A split asked under ruling 52 shows the existing label `Held - Title or author missing` (the lookup's reason reads "Title or author missing"; the same label the Apollo question and the ruling 51 asks carry). It is the carried observation for Judy, not new, but it now reaches more books: the first book of any series that nothing confirms asks, so Sergei will meet this label for a question that is really "confirm this series?". The ask carries the fields filled in; how the page words and lays them out was not exercised (section 6).
- After an Approve and a rescan, the filed book's row stays in the engine's page rows with status `Needs review`, but flagged `all_sources_retired` (2 sources), cleanup "Originals removed", `current_audiobook` verified, `can_approve` False. This is the carried observation (the in-process page snapshot labels filed books `Needs review`; whether the page hides them was not exercised). Flag only if Sergei ever sees a filed book stay on his list.
- Carried unchanged from the earlier passes: a manual Approve before research has learned a rule mixes scripts in "Goes to".

### 5. Screenshots

None taken. No file under `web/` or `desktop/` changed between 067315f and ddfbfa7.

### 6. Not run

- **Real-input checks: not run (Sergei present).** The tray's Quit item and tooltip, every real click, the window's X button. The shell and its close paths were not exercised (not in the delta).
- The HTTP layer and the page (unchanged). Where the question shows on Sergei's page (labels, the filled-in Series, Number and Title in the names editor, the Approve button for a `title_series` ask): not exercised; the engine-level ask, Goes to line (`approval_preview`) and `approve_book` only.
- The other changes in 1138712 that are not on the six-item list were not exercised by me: m18 (a title left that starts with a number or a part word is asked), m19 (siblings that are themselves asked still name the series), the `_unsure_title` guard. They live in Ender's tests inside the suite the entry check passed (`test_folder_structure.py`, `test_identity_v5.py`).
- Carried, not re-run: the items of the 067315f, 92376c7, d4a7450 and 65ddd72 passes (ruling 51's five asks and three splits other than «Профессия», the whole «Мастер и Маргарита. CD 1» name, Warhammer numbers, part words, the refused-Approve undo). Their outcome under ruling 52 is that a split asks first until confirmed; the one split I ran end to end is item 1.
- The real NSIS install, the updater, Restart to update, Cancel update (not in the delta). No light theme, no other viewport.

### 7. Disposal

All of my output lived in `%LOCALAPPDATA%\Temp\bq223g` (the payload extraction, the lab folders A, A_2, A_3, B, B2 and C with their private catalogs and Sorted folders, the private profile, my run script and logs) and my driver script in my session scratchpad. No engine or process of mine outlives the run (each driver exits itself; checked by command line, not by name: no `python.exe` or `ffmpeg.exe` of the lab was running afterwards). The lab folder is removed with `node scripts/studio-sweep.mjs --apply --path`, and the driver script by its own path. I left alone `Worktrees\Books Arranger\cand-0223g` and `q23g`: I read source and ran the repo's pinned `7za.exe` from `cand-0223g`'s `node_modules` (the extraction wrote only into my lab) and read `q23g/logs/ender-entry.log`; `cand-0223g` still shows 0 changed paths. This report is the only repo file I changed, uncommitted.

### 8. Pattern alerts

Pattern alerts: none.

Verdict of that pass (ddfbfa7, superseded): GO.
