# Books Arranger: QA report, release candidate v0.19.0, build `6f7680a`

Date: 2026-10-19. Futaba (QA). Scope: regression pass on the committed build after my GO on `c2abd97` (report `BooksArranger_QA_RefusedRetry_c2abd97_2026-10-19.md`). It covers the four changes since then, the pending-start behaviour on Stop and Quit, and a short regression of the core flows. Not covered by this first pass: Senua's construction verdict, installer, packaged build (the packaged build is covered by "Packaged build acceptance (2026-10-19)" at the end of this file).

Summary: no Blocker and no Major. All four changes behave as intended in the real app. Every delete-safety attack failed to remove anything outside the app's own staging folder, and every original, victim and trap file stayed byte-identical. One new Minor (a count label), found on behaviour that predates this build. One pattern alert (PA-1), data only. The machine-readable verdict is the last line of this file.

## Build under test

| | |
|---|---|
| Tool / version | Books Arranger, release candidate v0.19.0. `package.json` still reads 0.18.0 at this commit; the bump is Sully's release step |
| Commit | `6f7680adb8711522aeea9ce93dcb9506d63bed70`, branch `codex/books-electron-m1` |
| Worktree | `C:/Antigravity Projects/Worktrees/Books Arranger/electron-m1/`, `git status` empty at the start, after every seed batch, and at the end |
| Entry-check receipt | **Not produced.** qa-handoff needs a reviewed protocol-2 context from Ender and none was supplied (same as the c2abd97 pass). Identity is pinned by full HEAD hash and a clean tree only. Not a substitute for the release receipt |
| Run on | Electron, unpackaged, bundled Python and ffmpeg, isolated profile, port 5212 only (loopback debug port 9334 for the QA driver), about 22 launches, each ended with `--quit` |
| Sergei's live instance | Never touched. Port 5210 was not listening and no `Books Arranger.exe` was running at any check, before or after. The only window ever sent a close message was the single `electron.exe` QA window (the driver refuses if it finds more or fewer) |

## How it was run

- Ender's launch command, with the same scratch-only additions as before (`env -u ELECTRON_RUN_AS_NODE`, `--catalog-mode=new` on the first launch of each new scratch catalog, `--remote-debugging-port=9334`). Nothing read from or written to Z: or the real library.
- Four fresh synthetic catalogs and libraries, so nothing was inherited from the c2abd97 pass: `fuR3` and `fuR4` (delete-safety attacks, 36 books each, new originals), `fuH3` (82 books: file-lock rows, refused clear-first rows, stuck rows for the note cases), `fuS3` (2,502 tiny books, so a scan lasts long enough to block the pass; its first scan took 5.6 minutes, rescans 17 to 40 s).
- Seeds were written with the app closed, through the worktree's own modules (read-only import, no bytecode). Every state was then read from the live window (DOM text, button state, `document.hasFocus()`) and from the server API. File locks were real: a second process holding the exact file open without delete sharing (the Windows sharing violation an antivirus scan can cause).
- sha256 snapshots (no link or junction followed) of originals, victims, trap folders and the staging tree before and after every attack and test batch.
- A foreground-window watcher (read-only Win32 query, 100 ms) ran through the pass. See PA-1.

## 1. Delete safety (priority 1): PASS

| Attack | Through | Result |
|---|---|---|
| Control: ordinary receipt-owned attempt | Clear, Retry (clear first), Repair (clear first), Retry all | Cleared exactly its own files each time; originals identical |
| A receipt `path` names the original source | Clear, Retry | refused, original identical |
| A receipt `path` names a victim file outside the folder | Clear, Retry | refused, victim identical |
| A receipt `path` names another book in the library | Clear, Retry | refused, identical |
| A receipt whose name and path climb out with `..\..\..\..` | Clear (Retry never offered: row already blocked) | refused, victim identical |
| Job folder is a junction to an outside folder | Clear, Retry never offered | refused, outside folder identical |
| Attempt folder is a junction | Clear | refused, identical |
| A recorded file replaced by a junction to a folder with a sentinel | Clear | refused, sentinel identical |
| Two attempts, the second with an escaping receipt | Clear, Retry | refused for both, the good attempt not partly removed |
| Source copy replaced by a hard link to the original | Clear, Retry | refused, original identical |
| Original moved away / original changed | Clear (Retry and Repair never offered) | refused, working copies kept |
| `ownership.json` names another job; published attempt | Clear, Retry | refused, files identical |
| Job id `..`, `../../victimsR3A09` (forged ownership and receipts for a trap file), upper-case id | the HTTP boundary | 400 "Identity must be a canonical UUID", trap identical |
| Retry all across the remaining cleanable rows | Retry all | the safe rows cleared, escaping rows refused; originals and victims identical |

Totals: the original libraries (`libR3` 77 entries, `libR4` 77, `libH3` 173, `libS` 5,009), the victim folders (15, 15, 7) and the three trap folders are identical at the end against their first snapshots. The only files that left the staging trees were the receipt-owned files of the positive controls (6 files in the Clear run, 12 in the Retry/Repair/Retry-all run) and the app's own background clean-up (see observations).

Retry attacks were run on a second, untouched catalog (`fuR4`), because a refused Clear blocks its row and Retry then only reports "This book's status changed". Rows that are blocked at the row level were never offered Retry or Repair and the server answered 409 for a forced press, as in the c2abd97 pass.

## 2. The four changes (priority 1)

### 2.1 `f4829fc`: a file held open reads "try again" and the row recovers (my Minor 1): PASS

| Step | Result |
|---|---|
| Hold a working file open, press **Clear** in the page | "Some working files weren't cleared. A file couldn't be removed; try again in a moment." (warning). Nothing removed (tree identical). Row stays "Stopped — ready to retry" with Retry and Clear still offered |
| Same row, press **Retry** while still held | "Retry was not accepted: the working files weren't cleared. Nothing was queued." Nothing removed, row still cleanable |
| Release the lock, wait | Row stayed cleanable at +5 s, +15 s and +30 s (past the 20 s re-check). It never went to "can't clear working files" |
| Press **Clear** again, no restart | "Cleared 753 B of working files. Safe to retry now." Only that book's two files left the staging tree |
| **Retry** (held, refused, released, again) | Refused while held, then "Queued — runs next" with no restart. The worker then refuses the seeded job as "review changed" (a property of the seed, as in the c2abd97 pass) |
| **Repair** (held, refused, released, again) | Same: "Repair was not accepted: ... Nothing was queued." then "Queued — runs next" |
| **Retry all** with one of 16 rows locked | The other rows cleared, the two escaping rows refused and blocked, the locked row stayed whole and cleanable. After release, Retry all cleared it with no restart |
| The **original** held open (read sharing) | Clear worked and the original stayed identical: the app takes no delete access to originals, so this is not a refusal case |

Judy's file_problem sentence is on screen for Clear. Retry and Repair keep the one sentence they use for every cause, as in the c2abd97 pass.

### 2.2 `8fc4e8e`: a refused Retry or Repair refreshes the details panel (my Minor 2): PASS

Seeded cleanable rows whose receipt points outside the working folder, so the clear-first is refused (`not_safe`) and the book's state really changes. With the details panel open:

| Press | Result |
|---|---|
| Repair (panel open) | At +0.2 s the row and the panel both read "Stopped — can't clear working files", the panel hint "Working files from an earlier attempt are still present, and the app can't clear them safely right now.", and no Retry, Repair or Clear is offered. Sampled for 14 s, no change |
| Retry (panel open) | Same, at +0.2 s |
| Retry from a row, a different book's panel open | The row and the selected panel update together at +0.2 s |

The c2abd97 behaviour was a stale panel for more than 10 s with the old buttons still enabled. For the lock case the refreshed state equals the old one (still cleanable), which is correct.

### 2.3 `10f3375`: the Start over note promises "Let the app handle it" only when it will appear (my Minor 3): PASS

Note text read from the live panel after a plain Start over:

| Book | Note ends | Row hint |
|---|---|---|
| Stuck, no saved review (baseline) | no saved-review sentence | none |
| Multi-file book with a saved review | "...will then hold this book because it has a saved review. Find it under Status: Started over." (no promise) | "...because it has a saved review." |
| Single M4B, saved review, editing lease | same, no promise | same |
| Row rendered as plain, a saved review lands, then Start over (release expected) | "...because it has a saved review; Let the app handle it appears once it is held. Find it under Status: Started over." | "...Then Let the app handle it appears here." |

The promise is also true in practice: the book with a release expected reached "Held — saved review kept" with the "Let the app handle it" button once the pass visited it, while the multi-file and leased books were held with no button, as their shorter notes said.

### 2.4 `05d08d9`: Stop, Quit and the safety stops end a pending start; nothing starts once Quit has begun: PASS (two safety-stop kinds not run)

Setup: a library scan of the 2,502-book catalog is running, Start over is pressed on a stuck book, and the server reports a pending start of kind `scan`. The pass was sampled every 0.5 s through the whole window.

| Check | Result |
|---|---|
| **(a) Stop** through the server's stop route while pending | 202. At once the pending start was gone, the row read "Started over — waiting for you", the Cancel control disappeared and Start was enabled. Scan ended 21 s later. For 15 s after the scan ended the pass never left Idle (69 samples), and no run row was created in the catalog |
| Stop **button** in the page while pending | Disabled while the pass is idle (see observation), so the route is the only way to reach Stop in that state. Cancel automatic start is the page's control and behaves as in the c2abd97 pass (same result: pass stays idle through the scan end) |
| **(b) Quit** while pending, scan still running | `--quit` sent mid-scan. The server read "closing" with the pending start already gone and the scan stopped; three Start presses sent straight after Quit began were all refused (the first two with the scan block, the third with "The local server is stopping or stopped. Start is unavailable."); the server stopped answering at +0.7 s and the process and port were gone in 2.3 s wall-clock. No run row was created. After relaunch: pass Idle, no pending start, the books read "Started over — waiting for you", Start enabled |
| Quit with the pass Running (research) | Pass read Running, `--quit` sent: Paused within the Quit, process gone in 2.2 s, no new run row. Same with the pass Paused: 2.3 s |
| Stop and Start in the page with the pass Running | Stop: Stopping, then Paused in 0.3 s. Start from Paused: Running again within 0.3 s, continuing the same run |

Shutdown itself calls the forced stop, so the forced path was exercised by every Quit above. **Not run:** the disk-full and working-file safety stops in the real app (they need a conversion that fails mid-run; a conversion cannot run without an approved book, as in the c2abd97 pass), the pending kinds "conversion" and "stopping", and the exact race of a press admitted just before Quit. Ender's tests stand for those; I did not re-run the Python suite.

## 3. Core flows (priority 2): PASS

- **Start over, release, picked up:** a book held for its saved review, "Let the app handle it", dialog "Discard this book's saved review?" with Cancel focused and the window not focused, confirm: "Discarding the saved review…", then within 1 s "Started over — waiting its turn" and the note "Review discarded. Automatic processing is running and will reach this book. Find it under Status: Started over." The pass picked it up on its own.
- **Counts:** around a Start over press, attention total 41 to 40, Started over 7 to 8, all candidates 82 to 82. Server counts and the group labels agreed at every sample.
- **Narrow widths:** Output needs attention (41 rows), Started over (8), Held (51), All candidates (82) at 1440, 950, table box 801, 799, 700, 601, 599, 475 and 720 at 200% zoom: no horizontal scroll (table or page), 0 intersecting rects, 0 buttons under 96 x 32, 0 covered buttons, 0 controls off screen. The three bands switch where they did (wide at a box of 801, medium at 799 to 601, compact at 599 and below). The Files view (90 rows) has no overflow; its "Open folder" button is still 90 x 37 (older, unchanged).
- **Close and Quit from every top-level screen** (Audiobooks candidates, Audiobooks files, Podcasts, Ebooks): the real close message (WM_CLOSE) hides the window to the tray (process alive, port listening, page `hidden`; the documented tray exception), and Quit ended every Electron process and freed 5212 in about 2.3 s on each screen.
- The seven pure-node frontend test files for the touched pages (attention, automatic, pre-check, refused-retry, retry, retry-selected, Start over) pass at this commit. Worktree status stayed empty.

## Findings

| # | Severity | Finding | Repro / evidence |
|---|---|---|---|
| 1 | Minor | The result count label disagrees with the list after a Start over press: "Showing 1–4 of 3 candidates · Output needs attention" with 4 rows on screen. The pressed row is deliberately held in place (the server total already dropped to 3). It corrects itself only when the list reloads (switching the group). Also seen as "1–5 of 4". Not caused by the four changes; it came with the Start over build and I did not flag it at c2abd97. UX-shaped, so Judy's | Output needs attention, press Start over on any stuck row, read the line under the list; switch the group to clear it. `evidence3/T7_pagelabel.txt` |

Observations (no severity, no action requested):

- The page's Stop button is disabled while a start is pending (the pass is idle), so a user cannot press Stop in that state; Cancel automatic start is the control. The fix guards the route, shutdown and the safety stops.
- The panel's result note from a Start over press ("...will start by itself when the scan ends or is stopped") stays on screen after Cancel and after Stop, while the row and the notice say "waiting for you". The note is a record of the press and it is the same after Cancel, so this is not new. Judy may want it cleared.
- The app's own retention sweep removes one leftover working folder per minute by itself (it cleared several seeded folders during this pass). I pinned the rows I needed by holding a file open on each. Existing behaviour; it means a "Can retry" row can vanish from that group while it is on screen.
- After Quit during a library scan, the next launch reads "Use Resume scanning to continue saved progress" for Start scanning (400) and Resume works (200). By design.
- A second launch onto a running instance puts that window in the foreground even with `--show-inactive` (the app forwards it as "show the window"). By design for a user clicking the shortcut; relevant for PA-1.

Pattern alerts (separate channel):

- **PA-1, unattributed foreground appearances of the QA window, third pass in a row. Data only; Sergei declined further work on it.** This pass: 7 appearances of the QA window in the foreground (watcher log `evidence3/focus5.log`, 52 events in all; timestamps jump from 17:47 to 20:10 because work paused for an API limit).
  1. 17:34:40, 4 s, between two Comic Metadata windows, around the end of an HTTP-only attack run on the first catalog (no UI driver attached; the exact call at that second is not known).
  2. 20:14:33 to 20:17:18, 2 min 45 s, directly after an explorer and Edge switch (`document.hasFocus()` read true in the QA window for the presses during this time).
  3. to 6. 20:34:42, 20:34:48, 20:35:01 and 20:35:10, a few seconds each, among Slack, ChatGPT, Sunshine and several "System tray overflow window" events of the user's own, starting 2 s after I pressed Start over (which started the pass).
  7. 20:40:08, 12 s: **attributed.** I launched a second copy onto the instance I had left running. Reproduced under control with the watcher on: 12 s of idle gave no event, and the second launch put the QA window in the foreground in the same second. That is `showWindow()` in `desktop/main.js` (second instance), which the `--show-inactive` flag does not cover. My mistake in the loop; my launches are now one instance at a time.
  The main process has only four paths to the foreground: a start without `--show-inactive` (mine always pass it), a tray icon click (`tray.on('click', showWindow)`), the tray menu "Open Books Arranger", and a second launch. Events 3 to 6 sit beside the user's tray-overflow activity, which is consistent with tray-icon clicks, but I cannot prove it. Two other pass starts (20:36, 20:41) produced no appearance. Treated as unproven for events 1 to 6.

Pattern alert disposition: Sergei declined further work (defer, per Jane's brief). No new action requested.

## Not covered

- The disk-full and working-file safety stops, the pending kinds "conversion" and "stopping", and a Start press racing the start of Quit (section 2.4).
- The approve, queue and convert half of the pass for a fixture (the live public sources declined every fixture in the c2abd97 pass, and I did not retry it).
- A symlink variant of the junction attack (no privilege on this account).
- Setup screen (every launch passed `--data-dir`), `--show`, packaged build, installer, Senua's review, the Python unit suite (Ender's own run stands).
- Entry-check receipt (see Build under test).

## Evidence and scratch (Sergei deletes)

Folder: `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/7be0fa3c-ad7a-444a-aa4a-6a232ded8ba0/scratchpad/shared/futaba-precheck/`, about 945 MB (this pass adds `evidence3/` with 123 files, the new catalogs `fuR3`, `fuR4`, `fuH3`, `fuS3`, their libraries `libR3`, `libR4`, `libH3`, victims `victimsR3`, `victimsR4`, `victimsH3`, and drivers in `tools3/`; the earlier passes' folders are still there). Key files: `evidence3/R_attacks1.txt`, `R4_attacks.txt` (attack runs with tree diffs), `F1a_*.txt`, `F1b_*.txt`, `F1c_orig_locked.txt` (file-lock runs), `F2_*.txt` (panel refresh), `F3_notes.txt`, `F3_held_watch2.txt` (note text and promise), `F_release_QB052.txt`, `T1_pending_stop.txt`, `T2_pending_quit.txt`, `T3_pending_cancel4.txt`, `T4_run_stop_start_quit.txt`, `T5_start_then_quit.txt`, `T6_close_quit.txt`, `T7_pagelabel.txt`, `layout_v19_*.json`, `focus5.log` and `focus6.log` (foreground logs). No QA process is running, both watchers are stopped, no lock helper is running, and the worktree is clean.

Source-build verdict for `6f7680a` (before the version bump): GO. It is carried into the release verdict on the last line of this file, which is given only after the packaged build acceptance below.

## Packaged build acceptance (2026-10-19)

Futaba (QA), same day, after Sully's version bump. Scope: the shipped v0.19.0 installer and its manifest, bound to the release commit and run on an isolated profile. No Blocker, no Major, no Minor in this section. A real install, the updater and the tray are not covered (see the end of this section).

### Pinned build

| | |
|---|---|
| Worktree head | `a62530c905911b8b847036bbe7ba65197396620b` (`git rev-parse HEAD` in `C:/Antigravity Projects/Worktrees/Books Arranger/electron-m1/`), `package.json` 0.19.0 |
| Manifest | `dist/release-artifacts.json`: schema `books-desktop-artifacts-v1`, version 0.19.0, `source_head` equal to the head above, build ID `d977850e-c012-4170-8ad9-a3a0b52d13de` |
| Installer | `dist/builds/d977850e-c012-4170-8ad9-a3a0b52d13de/Books-Arranger-Setup-0.19.0.exe`, 173277568 bytes, SHA256 `4fed020ef9cab0e491c6c7a3dd06ce7a86c5ed5319df40cbeb02cd74a9190543` |

Release source commit: a62530c905911b8b847036bbe7ba65197396620b
Release artifact manifest SHA256: f1ed7a1bde447d1892d1a1253cd99fc53c6cf08a610ab4bcba3b6d0bd38d7f6b

### 1. Binding: PASS

- I recomputed the installer and the manifest hashes myself (`sha256sum`) and both equal the pinned values above, before the smoke and again after it (I only read from `dist/` and wrote nothing there).
- The manifest's `source_head`, version and build ID equal the head, 0.19.0 and the build ID above. The manifest's other two artifacts also match their recorded hashes: blockmap `b4fc537f...` (180812 bytes) and `latest.yml` `00c3144b...` (360 bytes).
- `product_digest` recomputed from `git ls-tree` of `a62530c` with the worktree's own `productTree` equals the manifest value `262fe0c6...` (415 tracked files).
- `git diff --name-status 6f7680a a62530c`: `package.json` and `package-lock.json` (three `version` lines, 0.18.0 to 0.19.0), `CHANGELOG.md`, and six added `Docs/` files. No code file changed since my GO.

### 2. Payload: PASS, 233/233

Extracted the actual installer with 7-Zip, never installed it: installer, then its `app-64.7z`, into new empty folders. Compared every extracted file with the manifest's `payload.files` by SHA256 and size: **233/233 match**, 0 mismatches, 0 missing, 0 extra. The 48 `runtime.files` entries (bundled Python and ffmpeg) also match the extracted payload, 48/48. The extracted `resources/backend/VERSION` reads 0.19.0.

### 3. Shipped build on an isolated profile: PASS

How: the extracted `Books Arranger.exe` was run directly. Its own private Electron profile, data folder, APPDATA, LOCALAPPDATA and TEMP, port 5214 (debug port 9336, loopback only), `--show-inactive --quiet-errors`. Port 5210 was never used and was not listening, and no `Books Arranger.exe` was running at any check before or after. A synthetic library of 8 books. First launch with `--catalog-mode=new` let the shipped build scan it (completed, 8 candidates), then I quit it. Five failed-job rows were then seeded into that scratch catalog with the app closed, through the build commit's own Python modules (read-only import, no bytecode, worktree status unchanged by it), and the shipped build was launched again on it.

| Check | Result |
|---|---|
| Renderer version | PASS: the page badge reads "v0.19.0" and the backend health and state report 0.19.0 |
| Quit control | PASS: "Quit Books Arranger" button present and enabled in the shipped window; the window did not take focus (`document.hasFocus()` false) |
| Core refused-retry screen | PASS: with Status "Output needs attention" the page reads "Showing 1–5 of 5 candidates", groups All 5, Can retry 1, Other 3, M4B not supported 1, no horizontal scroll. QK001 "Stopped — ready to retry", "Safe to retry now.", Retry. QK002 and QKR01 "Stopped — review changed", "Retry was refused" / "Repair was refused: the book's review or source files changed. Start over sends it back to automatic processing.", Start over. QK004 "Stopped — file problem", "Retry was refused: the app couldn't read or write a file. Check the folder, then retry.", Retry. QK003 "Can't convert — M4B not supported", "Retry was refused: the app doesn't support how this M4B is built...", no Retry. Screenshots: `evidence/refused-retry-screen.png`, `evidence/refused-retry-table.png` |
| Normal Quit | PASS: clicked the shipped "Quit Books Arranger" button once. The process exited with code 0, no signal, 439 ms after the click (18:18:54.389 to 18:18:54.828 UTC) |
| Process and port closure | PASS: all 7 processes of the app's tree (4 Electron, 2 Python, 1 console host) were gone, nothing listening on 5214, 9336 or 5210 |
| Real catalog untouched | PASS: before and after fingerprints identical (below) |

Real data (read-only, no connection, no copy, no write), taken 18:15:32 UTC and again 18:19:04 UTC. Real data folder `C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/data`: `inventory.sqlite3` 549404672 bytes, mtime_ns 1792403601797734200, SHA256 `1d3adb8343b002cfe840d58630643cd472c37b14fa57c747667e213a7a1e636f`; `inventory.sqlite3-wal` 6818632 bytes, SHA256 `65e31b70cff9344f600379166be18693a2957f62791b536bbe7ba65197396620b`; the shm, journal, lock and `web-instance*.json` files also identical by size, mtime and SHA256. The default Electron profile `C:/Users/AnGeLZzZ/AppData/Roaming/Books Arranger`: 83 files, 26 directories, 8433647 bytes, listing digest `2bdcf836bdb9bbff8e6661623ce0a4cae1af684e5063be449935018a57ec2073`, identical. `Z:/Audiobooks`: 8890 files, 783 directories, 741133939313 bytes, name/size/mtime digest `3dc27a677264f11844cd3e166ba609f36a6008aa1e6bb3bef9fe98a5d0f71a97`, identical. `%LOCALAPPDATA%/Books Arranger` does not exist. This is unchanged observation around the smoke, not an audit of database contents.

Observation, existing behaviour: the app's own retention sweep had already removed the seeded working files of QK001 when I read the screen (only the folder's `ownership.json` remained), so the row read "Safe to retry now." with no Clear button, as in the earlier passes.

### Not covered in this section

Installation or uninstall, the auto-updater, tray, Alt+F4 and window-close paths, a real catalog copy, conversions, Quit during a scan or a running pass (all of these were run on the unpackaged source build in the sections above, at `6f7680a`), the Python suite, and Senua's construction verdict (hers, separate). The earlier `6f7680a` behaviour pass is the evidence for behaviour. This section binds that pass to the shipped bytes: no code file changed between `6f7680a` and `a62530c`, the payload equals the manifest, and the shipped renderer, refused-retry screen and Quit work.

Worktree note: during this section `git status` shows ` M Docs/BooksArranger_CodeReview_v0.19.0_2026-10-19.md`, which is not mine (Senua's concurrent edit). My only edit to the worktree is this report.

Pattern alerts: none new in this section. PA-1 above keeps its disposition (defer, Sergei declined further work).

Evidence and scratch (Sergei deletes), about 732 MB: `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/7be0fa3c-ad7a-444a-aa4a-6a232ded8ba0/scratchpad/shared/futaba-v0190-packaged/`. It holds the extracted installer and payload, `payload-binding.json`, `evidence/` (real-before.json, real-after.json, quit-click.json, pre-quit-tree.txt, post-quit-alive.txt, the two screenshots, refused-retry-rows.json), `logs/` (launch and exit records) and `tools/`. No QA process is running.

**Verdict:** GO
