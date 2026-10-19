# Books Arranger: QA report, build `c2abd97` (Start over, release, working files, pending start, narrow table)

Date: 2026-10-19. Futaba (QA). Scope: pre-release behaviour pass on the committed build. It covers everything since the interim GO on `de3e2b2` (Judy's Follow-ups 2, 3 and 4 as built), plus a regression check of that build's scope. Not covered: Senua's construction verdict, installer, packaged build.

Summary: no Blocker and no Major. The delete-safety attacks all failed to remove anything outside the app's own staging folder, and every original stayed byte-identical. Four Minor findings, one pattern alert, and one leg I could not run (a fixture converted end to end through the pass; see section 2). Details below. The machine-readable verdict is the last line of this file.

## Build under test

| | |
|---|---|
| Tool / version | Books Arranger, package.json 0.18.0 |
| Commit | `c2abd97861d6c4ba7df40f3298f784a9c0a6b986`, branch `codex/books-electron-m1` |
| Worktree | `C:/Antigravity Projects/Worktrees/Books Arranger/electron-m1/`, `git status` empty before, during (checked after every seed and test batch) and after |
| Entry-check receipt | **Not produced.** qa-handoff needs a reviewed protocol-2 context from Ender; none was supplied (same as the interim pass). Identity is pinned by full HEAD hash and a clean tree only. Not a substitute for the release receipt. |
| Run on | Electron, unpackaged, bundled Python and ffmpeg, isolated profile, port 5212 only, about 50 launches, each quit with `--quit` (every quit freed the process and the port within 1 s) |
| Sergei's live instance | Never touched. Port 5210 was not listening and no `Books Arranger.exe` was running at any check, before or after |

## How it was run

- Ender's launch command, with the same three scratch-only changes as last time (`env -u ELECTRON_RUN_AS_NODE`, `--catalog-mode=new` on first launches of new scratch catalogs only, `--remote-debugging-port=9334` loopback on most launches so I could read the real window). A second launcher takes the roots file as a parameter (`launch2.sh`, `quit2.sh`) so each catalog has its own synthetic library. Nothing read from or written to Z: or the real library.
- Seven scratch catalogs, all synthetic: `fu234` (the interim build's 63-book regression set, reseeded), `fuB` (82 books, the new-feature rows), `fuA`, `fuA2`, `fuA3` (delete-safety attacks), `fuP` (small, with a real 213 MB audiobook copy taken from scratch, plus a 40 s ffmpeg-made M4B, for the pass), `fuS` (2,502 tiny books, so a scan lasts long enough to block the pass).
- Seeds were written with the app closed, through the worktree's own modules (read-only import, no bytecode). Working folders were made by the app's own lifecycle code (real receipts), then tampered for the attacks. Every state was read from the live window (DOM, `title` attributes, `getBoundingClientRect`, `elementFromPoint`, `document.activeElement`) and from the API.
- A foreground-window watcher ran through the whole pass (read-only Win32 query, 100 ms).
- Copy exactness: every tooltip, hint, note and dialog line I read matches Judy's text unless listed under Findings.

## 1. Delete safety (priority 1): PASS

Method: snapshot (sha256 of every file, no junction or link followed) of the library originals, a `victims/` folder, a folder outside the data dir and the staging tree, before and after every call. Every call went through the real server (HTTP), and the attacks were sent whether or not the page would offer the button.

| Attack | Through | Result |
|---|---|---|
| Control: ordinary receipt-owned attempt | Clear, Retry (clear first), Repair (clear first), Retry all | Cleared exactly its own two files each time; originals identical |
| A receipt `path` names the original source | Clear, Retry | 409 `not_safe`, nothing removed, original identical |
| A receipt `path` names a victim file outside the folder | Clear, Retry | refused, victim identical |
| A receipt `path` names another book in the library | Clear, Retry | refused, identical |
| A receipt whose name and path climb out with `..\..\..\..` | Clear | refused, victim identical |
| Job folder is a junction to an outside folder holding a complete valid layout | Clear, Retry | refused ("The working folder is a link"), outside folder identical |
| Attempt folder is a junction | Clear, Retry | refused, identical |
| A recorded file replaced by a junction to a folder with a sentinel | Clear, Retry | refused, sentinel identical (a symlink variant could not be seeded: no privilege) |
| **The whole `audio-staging` root is a junction** to an outside copy of everything | Clear, Retry, Repair, Retry all (3 jobs) | refused, "No books can be retried right now", outside tree identical |
| Job id `..`, `../../victimsA09` (with forged ownership and receipts for a trap file), upper-case form of a real id | the HTTP boundary | 400 "Identity must be a canonical UUID"; the tampered rows read "M4B not supported" with no controls, and the trap file stayed identical through about 15 minutes of runtime and a restart, background cleanup included |
| `ownership.json` names another job; attempt not closed; unknown extra file; attempt folder renamed to a non-UUID; loose file in the job folder; attempt state published | Clear, Retry | refused or never offered, files identical |
| Two attempts, the second with an escaping receipt | Clear | refused for both, the good attempt was **not** partly removed |
| Source copy replaced by a hard link to the original | Clear, Retry | refused, original identical |
| Original moved away / original changed | Clear, Retry | blocked ("original files cannot be reached" / "changed"), the working copies kept |
| The job's manifest names the **staged copy as its source**; the manifest names a staged file as its **cover** | forced Clear, Retry, Repair | refused, staged files identical |
| Retry all across 3 safe rows and 1 escaping row | Retry all | the 2 safe rows cleared, the escaping row refused and now blocked, victim identical |
| A file held open (Windows sharing violation) during Clear and during Retry | Clear, Retry, from the page and the API | nothing removed, nothing queued, texts below (finding 1) |

Totals: `libA` (77 entries), `victims` (15), `victimsA09` and `victims2` (the junction target) identical after every step; `libB` and `libP` originals identical at every checkpoint (several per catalog); the only files that left the staging trees were the files of the positive controls. Start over and "Let the app handle it" removed no file either (checked on a book with a leftover folder: folder, ownership receipt, job row and journal intact).

The page and the server agree on one limit: a row seeded with a receipt that points outside its folder still reads "cleanable" (Retry and Clear offered) until the first refused press, then blocks. Only a hand-edited catalog gets there; recorded as an observation.

Timing of the real case: a 640 MB working folder cleared through the page in 0.7 s ("Cleared 640 MB of working files. Safe to retry now."), well inside the 15 s press timeout (Judy's open item l).

## 2. Start over, then the automatic pass (priority 2): PASS for the hand-over, one leg not run

Done with the real pass (research on live public sources, pass state read every 0.5 s from the server and the window):

- Pass idle, press **Start over and let the app handle it** on a book with a saved review: dialog title and focus (Cancel) as specified; note "Started over. Review discarded. Automatic processing has started. It scans the library first, so this may take a while. Find it under Status: Started over."; row at once "Started over — waiting its turn"; then "researching", then the real research answer ("Held — Collection page identity unverified", with a retry time).
- Presses while the pass runs: "...Automatic processing is running and will reach this book..." exactly. While paused: "...continued where it paused...". Bulk release of 2 held books while paused: "Discarded 2 of 2 saved reviews. Automatic processing continued where it paused. Find them under Status: Started over." with "Discarding…", focus on the result line, window unfocused.
- **A book stuck as "Manual draft retained", then released:** plain Start over by API (prediction `manual_draft`) put the book at "Held — saved review kept" with the release button; pressing "Let the app handle it" and confirming discarded the review and the context, reset the automatic record, and the pass took the book on its own ("researching", then the research answer). Old job row, journal, set-aside record and the audio file all intact (file identical by sha256).
- A second press from an outdated view, and Start over twice: 409 "This book's status changed. Check the updated status above.", nothing changed. Release on a non-held book, non-boolean `discard_review`, an unknown field: refused (409 / 400).
- Prediction `automatic`, a saved review lands before the press: the note follows the answer (`manual_draft`), in the warning colour, and the row reads the "hold" hint. A lease landing before the combined press: "This book is being edited. Finish editing, then try again.", job not set aside, review and lease untouched (all or nothing).
- **Not run: the book converted end to end.** The pass researched every fixture and the real book but the live public sources did not approve any of them ("Sources disagree on the title or author" for a clean synthetic "The Hobbit", "Collection page identity unverified" for the real book, and a DuckDuckGo human check paused that host). Without an approval the pass never queues, so no job and no conversion ran. That is the public side, not the build. What is proven: after Start over the book's current job is empty (creation shows `job: null`) and the new automatic record reaches a real research outcome. The approve, queue and convert half needs a stub-research run (Ender's tests) or an approved fixture.

## 3. The O12 auto-start and focus (priority 3)

The pending start was exercised with a **scan** as the blocker (a 2,502-book catalog, so the scan lasts 17 to 40 s):

| Moment | Scan ended | Pass Running | Page |
|---|---|---|---|
| Start over (plain) | 15:51:40 | 15:51:43 | row "Started over — waiting to start" then "waiting its turn"; notice and Cancel gone; Cancel had been visible |
| Start over and let the app handle it | 16:13:54 | 16:13:56 | note "Started over. Review discarded. A library scan is running, so automatic processing will start by itself when the scan ends or is stopped. Find it under Status: Started over." |
| Bulk release, 2 of 3 (one changed meanwhile) | 16:16:52 | 16:16:53 | "Discarded 2 of 3 saved reviews. Automatic processing will start by itself when the library scan ends or is stopped. Find them under Status: Started over. 1 were not changed. Check their status.", warning colour |

Also checked: the notice, the disabled Start with its tooltip and the Cancel tooltip are the spec's words; two presses leave one pending start; **Cancel automatic start** returns the notice to the server's block sentence, the rows read "waiting for you" with the blocked hint, focus moves to the notice (`tabindex=-1`), and the pass does not start when the scan ends; a quit with a pending start leaves the pass Paused after the relaunch and the rows read "waiting for you" (marker kept, nothing starts by itself); a window **hidden to the tray stays hidden** (page visibility `hidden` before and after) and the pass still starts; no sound, notification, dialog or toast anywhere.

The window never took focus inside the app: `document.hasFocus()` was false at every sample, the active element changed only inside the page, and none of the three start moments above has a foreground event of the QA window at the moment of the start (16:13:56 had no event of any kind in 30 s; the 15:52:06 and 16:16:37 appearances are 23 s after and 16 s before a start, 12 s after my Stop click and during my dialog confirm). A fourth start with the window hidden in the tray (16:35:27) logged no QA-window event in a second watcher. Not exercised: the conversion and "stopping" pending kinds (a conversion cannot run without an approved book, and the Stopping window was too short to catch in 3 tries; the first "Stop then Start over" returned `running`, the second returned `continued`), and the "cannot clear" blockers.

**Foreground log: see pattern alert PA-1.** The watcher recorded 18 brief appearances (1 to 11 s) of the QA window in the foreground between 15:25 and 16:30, each between two of the user's own windows (Slack, Chrome, WhatsApp, VS Code, Explorer). They did not reproduce under control: 0 events in 6 idle launch and quit cycles, 0 in 3 cycles with automation attached, 0 in a 4.5-minute idle run during which the user switched apps 5 times, 0 for each of 8 isolated automation actions (reads, element focus, clicks, filter changes, viewport emulation, an Escape key, scans, pass start and stop, dialog open and close), 0 over 5 dialog opens. I cannot attribute them to the app or to the user. Treated as unproven, filed as a pattern alert because it is the second pass in a row.

## 4. Counts, filters, geometry (priority 4): PASS

- Counts conserved: Start over press: Other 22 to 21, Started over 16 to 17, all candidates 82 to 82; attention group sums constant through Retry all, Retry selected and the pre-check pass in the regression catalog (63 at every sample); the Started over summary line counts (16 books: 11 waiting, 4 held, 1 stopped on an error) match the list and the server's counts.
- Rects, `elementFromPoint` per button, `scrollWidth` against `clientWidth`, at 1440, 1000, 950, 800, 720, 700, 640, 600, 475, at 200% zoom of 950 and of 1440, and at the table box widths 801, 799, 601, 599: Output needs attention (37 rows), Started over (16), Held (6), All candidates (82) and the Files view (90): **no horizontal scroll (table box or page), 0 intersecting rects, 0 buttons under 96 x 32, 0 covered buttons, Retry and View metadata on screen without scrolling at 950 and 700.**
- The three bands: wide (a box of about 785 px and up) shows 6 columns, medium folds Author and Audio files into "Author · N audio files" under the title (the fact appears once), compact (below a box of about 585 px) is a block per row with the header visually hidden (`position:absolute`, 1 px, clipped) and still in the tree. Explicit roles `table / rowgroup / row / cell / columnheader` are present at every width. Files view: wide above a box of about 1000, block rows below it.
- Details panel toolbar (Retry or Repair, Clear working files, note): 96 x 40 and 143 x 40, no overlap, both hit-testable, inside the viewport at 1440, 950, 700, 475 and 475 at 2x. Discard dialog at 475 and at 200% zoom: 424 x 277, fits, Cancel 96 x 40 and Discard 136 x 40, nothing covered; the batch bar wraps with no overlap.
- Contrast measured in the live window on every hint: warning 11.18, muted 8.92 on `--surface` (row-hover and row-selected pairs follow from the same tokens: 8.31 / 6.23 and 6.63 / 4.97). All at least 4.5.

## 5. The `audio-staging` bug fix (priority 5): PASS

A catalog with no `merge-cache/audio-staging` folder (`fu234`, folder confirmed absent before and after): Retry all on 26 rows gave **25 "Stopped — review changed" and no new file problem** (the interim build gave 24 file problems on 25 rows in the same setup); a single Retry and a single Repair press take the same path. The one-time conversion works: rows whose record carries the exact old text ("Prior working-file ownership requires attention: An inspected destination ancestor is unavailable", cause `file_problem`) read ready again after the relaunch ("Retry was refused in v0.18.0. The app was updated, and this M4B now passes its check.", in Can retry); a control with different text stays "Stopped — file problem". The folder is not created by the fix.

## 6. Judy's acceptance checks

Follow-up 2, section 6 (Start over, working files, Checking), with Follow-up 3 and 4 where they replaced it:

| Check | Result |
|---|---|
| Seeded `source_changed` rows: Start over (not Retry) in the row and the panel, hints and tooltips exact; `manual_draft` second wording | Pass (automatic, saved review, lease, multi-file, Repair-kind, combined) |
| After the press: job row, journal, working folder kept; held row reads its Started over state, never "Pending" or "Needs attention"; leaves Output needs attention, Other one lower | Pass |
| Cleanable row: hint clause, Retry and Clear tooltips, group Can retry, Retry all dialog "{k} of them have leftover working files, which are cleared first." | Pass (also "3 of them" with two Repair rows ticked) |
| Clear: folder emptied, originals identical, job row intact, "Cleared {size} of working files. Safe to retry now.", button gone, focus on Retry, row held in place | Pass (753 B, 3 MB, 640 MB) |
| Clear with the files already gone: "Working files were already cleared." | API answers `already`; the page string exists; the page row had already updated before I could press, so the on-screen text was not seen |
| Retry (A) on a cleanable row: "Clearing working files, then checking this book…", then "Queued — runs next", nothing said about the files | Pass |
| Forced clear failure: nothing queued, "Retry was not accepted: the working files weren't cleared. Nothing was queued." (warning) | Pass for text and queue; see findings 1 and 2 |
| Blocked row: status, hint (both variants), group Other, no Retry, no Clear, Technical detail with reason and absolute folder | Pass |
| Never disabled: Clear is absent or enabled; the only `aria-disabled` state is its own "Clearing…" | Pass |
| Old `working_files` record with no folder reads "Stopped — ready to retry" / "Safe to retry now." (Minor 3) | Pass |
| Timing (Minor 2): files removed outside the app | server read natural after 6 s (was 4 min 53 s); the app's own background cleanup showed on the next poll |
| Checking follows each check (Minor 1) | Pass: server count 57, 53, 50, 29, 0 over 38 s, the strip label one sample behind, no focus move |

Follow-up 3, section 8 and Follow-up 4, section 6 (Start over and the pass, marker, filter, summary, Repair clears first, release, narrow table, O12, O13, O14):

| Check | Result |
|---|---|
| Start over `started`, `continued`, `running` notes; row hint; no "Pending" | Pass |
| Started over entry after Output needs attention, its tooltip; ordering failed, waiting, working, held; summary line exact (waiting, being processed, held, stopped on an error; tails for "press Start", "can't start yet", release); singular forms not seeded | Pass |
| Every seeded state reads exactly: waiting, waiting its turn, researching, waiting for a source, waiting for you, waiting to start, held other, held saved review (release allowed, lease, multi-file), failed, failed with start blocked, expect-hold with and without the release clause | Pass (queued by automatic processing: not reachable, no job) |
| A row whose "changed" flag is set reads its marker state, not "Candidate changed" | Pass |
| Marker survives an app restart, rows read "waiting for you" | Pass |
| Empty Started over text exact | **Differs by one word, finding 4** |
| Repair clears first: tooltip, hint clause, "Clearing working files, then repairing this book…", then "Queued — runs next"; Retry selected k counts it | Pass |
| "Let the app handle it": button first in the cell and panel, tooltip exact; negative controls (multi-file, lease, row with a job, held for another reason, approved and not held, never visited) show no button | Pass |
| Release dialog: nothing happens on open, Cancel focused, Esc returns focus to the button, confirm shows "Discarding review…" then the note; refusals (lease, outdated, bad request) | Pass |
| Rescan evidence (an app-approved single M4B, only its modified time changed, rescan, pass visit) | Reproduced: "Held — saved review kept" with no hand edit (observation) |
| Combined button replaces plain Start over on single-M4B `manual_draft` rows only; multi-file, lease and automatic keep plain Start over; dialog and tooltip exact; confirm sets aside and discards in one transaction (a lease refuses the whole press) | Pass |
| Bulk "Let the app handle selected": counts in Held and Started over ("2 left out"), button label and tooltip, disabled at 0 with its tooltip, hidden elsewhere, dialog "Discard 3 saved reviews?" with the "2 other selected books are not included" line, Cancel focused, one changed book refused alone ("Discarded 2 of 3 … 1 were not changed. Check their status."), focus on the result | Pass |
| O12 sequence, Cancel, restart, hidden window, single pending start | Pass (scan blocker only) |
| Narrow table, three bands, no sideways scroll, Files view, dialogs at 475 and 200% | Pass |

## 7. Regression of the interim build's scope (`de3e2b2`)

Same fixtures, same checks: 61 of 63 settled states identical to the interim run (the other two are my stale expectations for the two rows seeded with Repair refusals; unchanged since then); 7 of 7 allowed M4B shapes ready and 15 of 15 near-misses "Can't convert — M4B not supported"; refused rows, stale, legacy and pre-check rows, the Checking group, the forced-press 409 on refused rows, "3 selected · 2 can be retried or repaired · 1 left out" and "9 selected · 6 can be retried or repaired · 3 left out" exact; Retry all on 26 rows (accepted; 25 later refused by the worker as "review changed", zero new file problems); counts 63 conserved; close and Quit from Audiobooks (candidates and files), Podcasts and Ebooks: the close button hides to the tray (documented exception, process alive, page hidden) and Quit ended every Electron process and freed 5212 within 1 s on each screen. The six pure-node frontend test files of the changed pages (attention, automatic, pre-check, refused-retry, retry, Start over) pass at this commit. Closed from last time: Minors 1, 2, 3 (section 6), the sideways table (section 4), the missing `audio-staging` folder (section 5).

## Findings

| # | Severity | Finding | Repro / evidence |
|---|---|---|---|
| 1 | Minor | A temporary file lock makes a row stick as "Stopped — can't clear working files" until the app is restarted, and the message is the wrong one. A file held open without delete sharing (an antivirus scan can do this) fails Clear and Retry with cause `not_safe`: "Some working files weren't cleared. The app keeps any file it can't confirm is safe to delete." Nothing was removed, so "Some" is untrue, and Judy's text for a lock is the `file_problem` one ("A file couldn't be removed; try again in a moment."). The row then loses Retry and Clear and **stays blocked after the lock is released** (checked 25 s later, past the 20 s re-check) because a failed clear keeps its folder blocked until the folder changes; it recovered only after a restart. Judy's rule: a blocked row re-reads live. | Hold `checked.m4b` of a cleanable row open (`tools2/hold.py`), press Clear or Retry, release it, wait. API and page agree. Reason shown: "Working files were kept: Cannot protect exact file: [WinError 32]…". `fuB` QB045, `fuA` QA021. |
| 2 | Minor | After a Retry or Repair whose clear step fails, the details panel keeps offering the old state. The 409 for that case carries no refreshed row (the Clear and Start over answers do), so the panel of the selected book still reads "Stopped — ready to retry" with Retry and Clear enabled for more than 10 s while the list row says "can't clear working files". A second press is refused by the server ("This book's status changed…"), so it is a wrong offer, not a loop. | Hold a file open, press Retry on a cleanable row with its panel open, read `#retry-block` and the row. `fuB` QB041. |
| 3 | Minor | The result note after a plain Start over promises a button that never appears for some books. For a multi-file book or one with an editing lease (neither can be released), the note says "...Let the app handle it appears once it is held." The row hint was corrected by Follow-up 4, section 2 (it stops at "...because it has a saved review."); the note was not. | Start over on a stuck multi-file book with a saved review, or one with a lease: note vs row hint. `fuS` QSM01, QS013. |
| 4 | Minor (copy) | The empty Started over text reads "Books you start over appear here until automatic processing queues them." Judy's text is "Books you **started** over appear here…". | Open the Started over filter in a catalog with no markers (`web/app.js` line 253). |

Observations (no severity, no action requested):

- A row whose receipts point outside the folder, or whose original changed, still reads "cleanable" until the first refused press; only a hand-edited catalog reaches it.
- Judy's finding about how often the saved-review hold appears is real: a book approved by the app, with no job, whose only change is a file modified time, becomes "Held — saved review kept" after the next rescan and pass visit, with no hand edit. The new release button and its wording ("including any hand edits") cover it.
- After Start over on a running pass that is sleeping between research retries, a book waited 55 to 60 s ("waiting its turn", "Nothing to do") before being researched. The worker looks for put-back books once a minute while it sleeps.
- The band thresholds (800 and 600) are applied to the table box including its 15 px scrollbar, so the layouts switch at a `clientWidth` of about 785 and 585. Nothing overflows (design minimums 746 and 566 still fit).
- In the Files view the "Open folder" button is 90 x 37, under 96 wide; older behaviour, not changed here.
- The Clear button and the panel's Clear button reappear for about 0.1 s while a pressed row reads "Queued" (the press has already cleared the folder). Cosmetic.
- The disabled "Let the app handle selected (0)" uses the native `disabled` attribute where the spec says `aria-disabled` (the neighbouring Retry selected does the same).
- Two spec sentences read oddly because they follow the spec literally: "these 1 selected books" and "1 were not changed".

Pattern alerts (separate channel, disposition needed from Jane: fix, accept or defer):

- **PA-1, unattributed foreground appearances of the QA window, second pass in a row.** Last pass: 1 event of 3 s. This pass: 18 events of 1 to 11 s (list and neighbours in the scratch log below). Each sits between two of the user's own windows, the QA window was launched `--show-inactive`, and under control nothing reproduced it (section 3). The studio rule is that our tooling never steals focus, so an unproven appearance has to stay open until it is attributed. Proposed disposition: **defer to a packaged-build check in a hands-off window** (Sergei states an away window; I run the same flows with the user's input idle and the watcher on). If Sergei knows he was clicking the QA window or its taskbar button, that closes it.

## Not covered

- The approve, queue and convert half of the pass for a fixture (section 2): the live public sources declined every fixture.
- Pending-start kinds "conversion", "stopping" and the "cannot clear" blockers; `visit: next_run`; the "disconnected" answer; the "Queued by automatic processing after Start over" state.
- A symlink variant of the junction attack (no privilege on this account).
- Setup screen (every launch passed `--data-dir`), `--show` (it focuses by design), packaged build, installer, Senua's review, the Python unit suite (it writes under the worktree's `scratch/`; Ender's own run stands).
- Entry-check receipt (see Build under test).

## Evidence and scratch (Sergei deletes)

Folder: `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/7be0fa3c-ad7a-444a-aa4a-6a232ded8ba0/scratchpad/shared/futaba-precheck/`, about 883 MB (two copies of one real book at 213 MB each, seven catalogs, libraries, drivers in `tools/` and `tools2/`, evidence in `evidence2/`, the foreground logs `focus3.log` and `focus4.log`). Key files: `evidence2/A_clear1.txt`, `A_clear2.txt`, `A_retry1.txt`, `A_retry2.txt`, `A_retryall.txt`, `A2_attacks.txt`, `A3_attacks.txt` (attack runs with tree diffs), `P1_watch.txt`, `P2_watch.txt`, `S1_watch.txt`, `S2_watch.txt` (pass and pending-start timelines), `layout_*.json` (rects). No QA process is running; both watchers are stopped.

**Verdict:** GO
