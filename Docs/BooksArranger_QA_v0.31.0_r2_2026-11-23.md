# Books Arranger 0.31.0: QA report, round 2 (Futaba, delta pass on the third build)

Date: 2026-11-23 to 2026-11-24 (overnight). Build: packaged, `7023cc9e77fb8cb528991e3ec287891787c2a7df`. Left uncommitted. Round 1 is `BooksArranger_QA_v0.31.0_2026-11-23.md` (GO on `a8b6804`).

**Verdict:** NO-GO

One Blocker (B1) and one Major (M1). B1: once the app's rules rename or move a finished book, the page shows that book as `Pending`, with its old source folder, `Open source folder`, no `Now in` and no `Choose folder…`; the default Audiobook Ready list goes empty and the line says `All done · … · 0 converted out of N approved books`. I saw it on every book the rules touched (four books in three lanes, one of them a fully automatic run with nothing typed), and it does not heal on a rescan or an engine restart. I rate it a Blocker because the rules touch most books and this is the screen Sergei works from; the data on disk is right and nothing is lost. If Jane or Sergei accept it for this release, that is their call, not mine.

The fixes you asked me to check do work: R31 passes, R32 passes for DuckDuckGo (M1 is its live gap), R27 passes end to end (with three deviations from the recipe, listed), R30 and R33 pass at the engine, R34 passes on the part I could build.

## 1. Hash check (compared only; the entry check was not re-run)

| Item | Handed over | Found | Match |
|---|---|---|---|
| Entry log `q031e/ender-entry.log` SHA-256 | `40658e25…9660c3` | `40658e250db816b6db5c280ac6e1b89ba9bbaf2c2586d48f70e5214e839660c3` | yes |
| Installer `Books-Arranger-Setup-0.31.0.exe` SHA-256 | `688799e7…749ab` | `688799e72443ca3d974108b5db82bc21f4a662532886bf1d4917ac0661f749ab` | yes |
| `dist/release-artifacts.json` SHA-256 | `d2d53f0d…c2ee` | `d2d53f0ddca32e46a5fb127c2018868d3291a48ea6160d099a74b928eed9c2ee` | yes |
| Manifest `source_head` | `7023cc9` | `7023cc9e77fb8cb528991e3ec287891787c2a7df` | yes |
| Unpacked `Books Arranger.exe` SHA-256 | manifest entry | `c96a8d73…4801`, equal to the manifest's | yes |
| Worktree `ender-031` HEAD, status | not stated | `7023cc9e…`, `git status` empty | consistent |

Receipt, line 3 of the log, read in full: `Entry-check receipt v2: books-arranger v0.31.0 @ 7023cc9e77fb8cb528991e3ec287891787c2a7df (dirty: N) […] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a; personal-folders clean`.

Counts and method: Node `# tests 279 / # pass 279 / # fail 0` read from the log. Python: the log prints `Ran N tests` once per batch; I summed them (13 batches, total 3,183), equal to the hand-over figure. I did not run any test myself.

## 2. How it was run

- **Lane A, the real shell.** The unpacked exe, my own `--installation-config` (every folder under my run folder), `--roots-json`, port 5251, `--show-inactive`, `--quiet-errors`. The shell cannot be given an output folder together with `--roots-json` (`desktop/main.js` reads the output folder only when there is no roots file, and then the default root is `Z:\`, which I must not touch). So automatic processing cannot run in the shell, and every finished-book check ran headless.
- **Lanes B to M, headless, same build.** The packaged python and the packaged `resources\backend` code, started by my own launcher (`web_server.main()`), `--audiobook-output-root`, one data folder per lane, ports 5252 to 5260, TEMP pointed into my folder. The page was read through headless Edge on my own profile (no window, no focus, no mouse): `document.title` and `innerText`. The page's own buttons were pressed with a script click inside that headless page, never on the desktop. The network was real (Wikidata, FantLab, Goodreads, DuckDuckGo) except in the offline steps.
- **Offline.** Ender's recipe says a dead `HTTPS_PROXY` blocks the network. It does not: `metadata_sources.py` builds its opener with `ProxyHandler({})` on purpose, so the first lane I ran that way looked everything up online and converted under the English name in about a minute. I blocked the network inside my own launcher instead (every non-loopback name lookup and connection refused). A harness matter, not a product defect, but the recipe needs correcting.
- Fixtures: cuts (25 s to the whole 36 min) of my own copy of `ba-mp3-fixture/fixture.mp3`, tags set with the packaged ffmpeg. Originals untouched.
- Counts: converted and approved from `audiobook_jobs.converted_total` / `approved_total` and the page's own line; finished files by listing each lane's sorted folder; the 3,183 as in section 1.

## 3. What was checked, by the brief's items

### Item 1. R31, Paused at once after "Stop automatic processing": PASS
- Lane F, offline, two books waiting for an online answer. Before Stop: title `Books Arranger: continues by itself`, `Automatic processing: Running`, `Continues by itself · …`. I clicked `Stop automatic processing` on the page. One second later: title `Books Arranger: paused`, `Automatic processing: Paused`, `Resume automatic processing`, jobs line `Paused · 0 need attention · …`, engine `work.state: paused`.
- Same with a book needing attention present (round 1's repro shape): `Paused · 1 need attention · 0 converted out of 0 approved books`, title `paused`, within 1 s.
- Still `paused` 35 s later and still `paused` about 57 min later (lane left alone).
- The title is the page's `document.title` in headless Edge, not the OS window of the shell (the shell cannot run automatic processing, see section 2). The shell's own window title I read only in smoke (below).

### Item 2. R32, a human check counts as nothing found: PASS for DuckDuckGo; live gap in M1
- Lane I, one standalone Russian book, series ledger after its real look-up: `publisher` and `litres` both `answer: none, reason: Public source presented a human check; no bypass attempted`; Goodreads, FantLab, Wikidata `none`; state `none`, `No verified narrative series found in the supported sources`. No 6 h wait recorded.
- End to end: converted 23:49:54, first look-up deferred (Minor 2), second look-up 23:59:55 settled `none`, and the page read `All done · 0 need attention · 1 converted out of 1 approved books`, title `Books Arranger: all done`, `Nothing is running, queued or waiting.` About 10 minutes after the conversion, not 12 hours.
- It is not so in every run: Goodreads answered some look-ups with its own human check, which the app counts as `unavailable` and waits 6 h for (M1).

### Item 3. R27 retest, the English title written into a finished file: PASS, with three deviations from Ender's recipe
Deviations, said first:
1. **The recipe's book does not convert on its own.** With the artist `Лю Цысинь` and no network, after Try 3 (23:24:41, 23:34, 23:44; the row read `Waiting for an online answer`, `Next try …`) the book was held `Held — Author unclear` (`english_spelling`, `odd_name`), not converted. That is ruling 39 in `public_research.py` (a foreign author credited only in Cyrillic is asked after the look-up ends) and the 0.31.0 test `test_the_author_question_waits_for_the_look_up_and_is_asked_only_after_it`. So "after 20 to 30 minutes it converts under the Russian title" is wrong for this author. When I answered only that question (typed `Liu Cixin`), the book converted under `Тёмный лес` but its manifest had `gap_search.background: []`: a typed answer closes the gap, so no English title is ever looked up (the round 1 limit, still true).
2. **I used the artist tag `Liu Cixin` (Latin)** with the title `Тёмный лес`, two parts, folder `Liu Cixin\Тёмный лес`, nothing typed in the app. That converts without a question.
3. **The online restart had to wait until the persisted host back-off expired** (Minor 3). My first lane (K) burnt its English-title try that way and is parked until 06:12; the clean run is lane M.

Lane M, step by step (times are local):
- 00:13:19 automatic processing started, network blocked. Tries 00:13, 00:23, 00:33. 00:33:25 converted under the Russian title: `Liu Cixin\Тёмный лес - Liu Cixin.m4b`. Job manifest `metadata_facts.gap_search.background` = `["original_title"]` (also `gaps: [original_title, series]`, `tries: 3`). Step 3 passes.
- Before the rewrite: size 841,541; sha256 `3d5fd8ca…`; decoded audio md5 `d126396271b055d10bc4db4d55ed42c0`; audio packet md5 `ed611e745e1b589686211f30c0e36a91`; 2 chapters ("Тёмный лес" at 0 to 25.013 s and 25.013 to 50.027 s); a png cover plus a data stream; title and album `Тёмный лес`.
- 00:33:58 engine shut down. 00:39:00 restarted with the network on (after the stored host back-off ended, 00:38:20).
- 00:42:30 the detail look-up found the English title (Wikidata Q607276). 00:43:23 the series look-up finished (Remembrance of Earth's Past, No. 2, Wikidata). 00:43:33 the page said `All done` (Minor 1: the rename was still owed). 00:51:17 the rules wrote and filed it once.
- After: `Liu Cixin\Remembrance of Earth's Past\Remembrance of Earth's Past - 2 - The Dark Forest - Liu Cixin.m4b`, one file, no other copy. ffprobe: title `The Dark Forest`, album and sort_album `Remembrance of Earth's Past - 2 - The Dark Forest`, grouping `Remembrance of Earth's Past`, track 2, artist and album_artist `Liu Cixin`. Decoded audio md5 and packet md5 identical to before; the same 2 chapters with the same times and names; cover and data stream kept; a full decode runs with no error.
- "Renamed or moved by the app · 1": one entry, kinds `series` and `title`, `written: [series, title]`, both with the Wikidata source. The row in the list reads `Canonical title: The Dark Forest`, `English title found on Wikidata. Series: Remembrance of Earth's Past · No. 2 · found on Wikidata`. A search for `Тёмный лес` and a search for `Dark Forest` each return that one row (through the list route, not the page's search box).
- But see B1: the same row says `Pending`, shows the old source folder and `Open source folder`, and the book is no longer in Audiobook Ready.

### Item 4. R30 and R33, Choose folder… pressed while the app rewrites the book: PASS at the engine; the page side is B1
- Lane C, a 36 minute book, approved by hand with a typed author, then filed by the series look-up (Wikidata, Remembrance of Earth's Past No. 2). A script polled the engine's state every 30 ms and pressed Choose folder… (`POST /api/candidate/destination`, the same request the page sends) at the first moment `background.series.writing` became 1. Log lines:
  - `00:05:50.489` write begins (`writing 1`, `pending.writes 1`)
  - `00:05:50.550` PRESSED, 61 ms later: HTTP 200, `outcome: move_queued`, `move.state: queued`, `queue.blocker: {kind: book, cause: book}`
  - `00:05:54.05` write ends; `00:05:54.2` the queued move runs; `00:05:54.35` done.
- The packaged `app.js` maps cause `book` to exactly `It runs when this book's processing finishes.` (I pressed through the API, so I read the wording from the code, not from a screen).
- Result: exactly one `.m4b` for the book, in his folder (`his-folder\Remembrance of Earth's Past - 2 - Тёмный лес - Liu Cixin.m4b`); none left in the sorted tree; no temp or partial file in the lane. Decoded audio md5 `99f4702e…` before and after; packet md5 identical; png cover kept; full decode clean; tags now carry album `Remembrance of Earth's Past - 2 - Тёмный лес`, grouping, track 2.
- The engine finds it: `output.path` is his folder, `move.state: moved`, his folder is saved as the override, the rules' record lists the series write.
- The page does not: that row reads `Pending`, source folder, `Open source folder`, no `Now in`, no `Choose folder…` (B1).
- My first attempt (an earlier book) answered `409 This book changed. Review its details and try again.` That was my script sending a stale revision; with a fresh one the press is accepted as above. Not a product fault.
- Not tried: other moments of a rewrite (the brief said tests cover the timing).

### Item 5. R34, nothing that can never finish holds back All done: PASS on the part I could build
- Lane H: a hand-approved Harry Potter book (series from FantLab). I put a regular file where the app would create the author folder (`Rowling J. K`). The app wrote the series into the file and renamed it in place, could not move it, and the page read `All done · …`, title `all done`, `Nothing is running, queued or waiting`, with `Could not be renamed or moved · 1` beneath (`Now in` / `Would be in` / `The rename or move did not finish.`). My blocker file was not touched. Still `All done` after an engine restart.
- Not exercised: an old series hold on a book converted again (needs a 0.30-era ledger). See Minor 4 for the refusal's wording and retries.

### Item 6. Smoke: PASS
- Lane A: the packaged shell started, showed its window without taking focus, window title `Books Arranger: checking what is left` (one book waiting; no sorted folder in this lane). A second instance with `--close-window` (the close button's action) hid the window (title N/A) while the shell, host python and engine stayed up (the recorded tray exception). A second instance with `--quit` (the tray's Quit) ended the shell, host python and engine; port 5251 closed within 3 s.
- Sergei's installed copy (`I:\Books Arranger\…`, PIDs 40204 and 41472) and port 5210 were running and unchanged at the start and at the end.

## 4. Findings

### Blocker

**B1. After the app's rules rename or move a finished book, the page forgets it is finished.**
- Seen on all four books the rules touched: lane M (fully automatic, nothing typed), lane H (series written and renamed, move refused), lane C (two books, one also moved by his own Choose folder…). Books the rules had not touched (lanes K, L, G, I) read normally.
- Repro, cleanest case (lane M): convert a book with background look-ups owed, let the detail and series look-ups finish, wait for the rules. At 00:45:39 the page said `All done · 0 need attention · 1 converted out of 1 approved books`. At 00:52:15, after the rewrite: `All done · 0 need attention · 0 converted out of 1 approved books`.
- The default list (`Audiobook Ready`) then reads `No candidates match these filters · Audiobook Ready.` / `No audiobooks are ready yet.` Under `All candidates` the row says `Pending` and `In I:\…\lib\Audiobooks\…` (the old source folder), actions `Edit names · View metadata · Open source folder`. An untouched book beside it says `Audiobook Ready · Now in sorted\…\… .m4b · Choose folder… · Open book folder`.
- It does not heal: a rescan changed nothing; an engine restart (lane H) changed nothing 40 minutes later.
- The data is fine: the engine's `output.path`, the move record and the file on disk are right, and `Renamed or moved by the app` lists the change. What breaks is the page: a rule-filed book has no `Choose folder…`, so R26's "to override, Choose folder… after the book has moved" cannot be used from the list; and the counter lies next to `All done`.
- Why a Blocker: the rules touch most books (series found, English title, author folder), so after one run the default list is empty, and this is the screen Sergei looks at.
- Not compared with the first build `a8b6804` or earlier: I did not run them. It may be new in 0.31.0's rules, or older. I can run the same lane on an earlier build if Jane asks.
- Status: open.

### Major

**M1. Goodreads' own human check still holds back All done for 6 hours or more.**
- R32 counts a DuckDuckGo human check as nothing found. A human check from any other host is still a try (`series_backfill.py` lines 117 to 118), and Goodreads is now answering some requests with one: HTTP 202, empty body, header `x-amzn-waf-action: challenge` (curl from this machine at 23:40, three of three; the same URL answered 200 later). The app records it as `Public source unavailable; no bypass attempted`, kind `source_unavailable`, three tries 6 h apart.
- Seen: lane G, an English-titled standalone book, deferred at 23:38 to 05:38 (the Russian book beside it settled `none`); lane L, a Russian book, deferred at 00:02 to 06:02 with FantLab, Wikidata and both DuckDuckGo sources already `none`. During that time the page reads `Background look-ups only · … · 1 background look-up left` and never `All done`. Lane I, a few minutes earlier, got a normal Goodreads `none` and reached All done.
- It is intermittent, and I cannot say whether my own parallel look-ups (up to six engines) provoked the challenge. A real library of a few dozen books will do the same.
- A product decision, not a defect against R32's wording: accept, or count Goodreads' challenge like DuckDuckGo's.
- Status: open, disposition needed.

### Minor

1. **`All done` shows while a rename or move is still owed.** After the look-ups end, the rules act at their next pass (up to 10 min later, `PASS_WAIT 600`). In between the page says `All done` and `Nothing is running, queued or waiting`, with `pending.moves: 1` (lane C: 23:57:56 to 00:05:50; lane M: 00:43:33 to 00:51:17), then `working`, then `All done` again. `background_work.py` documents this on purpose (a series found and not applied holds back no state), but the rules do apply it. Quit at that moment, and the rename waits for the next launch.
2. **The first look-up of every converted book is deferred 10 minutes.** Ledger reason `Its cleanup is not finished yet`, next try +600 s, in all 7 lanes I looked at. The look-up runs about 0.2 s before the cleanup is recorded as completed (lane G: attempt 23:28:10.30, cleanup `updated` 21:28:10.49 UTC). So `All done` for a book owing a look-up comes at about 10 min after the conversion (round 1's spec said about 2). For a large book the cleanup takes longer, so the wait would be the same or longer.
3. **A look-up try can be spent inside a stored back-off.** After a network outage the app stores a per-host back-off (`public_research_limits`, here 5 min, `Public source unavailable`) that survives a restart. Lane K, restarted online at 00:09:09, tried its English-title look-up at 00:12:09 (before the back-off ended at 00:13:42): FantLab and Wikidata `tries 1`, deferred 6 h (next 06:12), both hosts answered my curl 200 at the time. And the rules wait for that look-up (one rewrite, title included), so K's book stays under its Russian name until 06:12 (`moves: 1` the whole night). I cannot prove no request was sent; the timing says it was not.
4. **A move that cannot happen is described thinly and retried.** My blocker (a file in the place of the author folder) gave key `did_not_finish`, cause `unavailable`, `tries 1 of 3, retries: true`, text `The rename or move did not finish.` Not "refused once, with its reason". It did not hold All done, so R34's point is met; the wording says nothing about what is in the way.
5. **Ender's R27 recipe needs correcting** (dead `HTTPS_PROXY` does not block the network; `Лю Цысинь` is asked as Author unclear after Try 3). Written up in item 3; no product change implied.
6. **Carried over from round 1, still there:** approving a book by hand while automatic processing is idle leaves the audiobook queue `Paused q 1` until `Resume audiobook jobs` (lanes C, E, H, L). Not in this delta; not compared with 0.30.

Round 1's two Majors: its M1 (Paused after Stop) is fixed (item 1). Its M2 (12 h wait) is fixed for DuckDuckGo and still open in the live world for Goodreads (M1 above).

## 5. Not verified (said plainly)
- Whether B1 is new in 0.31.0 (no earlier build run).
- R34's second half (an old 0.30-era series hold on a book converted again).
- Choose folder… pressed at moments of a rewrite other than the one I caught (tests cover the timing, as the brief said); the queued wording was read from `app.js`, not seen on the screen; R26's live row of a rules-queued move (static check only).
- The shell's own OS window title while automatic processing runs (the shell cannot run it with an output folder); R31's title is the page title in headless Edge.
- Whether my own parallel load caused Goodreads' challenge.
- The 3.3a notice, the record's 200-entry cases, layouts other than 1280 px, keyboard use.
- `Rowling`-style author with a trailing period (round 1's Minor 3) not rechecked.

## 6. Pattern alerts
Pattern alerts:

- **P1 (open from round 1, disposition: fix or accept).** `All done` and the status lines are honest only at the edges the build tests: the Paused text, the DuckDuckGo wait and the Pending list are each fixed or found separately, and round 2 found three more places where the page and the engine disagree (`All done` with a rename owed, `0 converted` beside `All done`, a look-up wait that depends on which host answered). One rule for "what is left" read from one place would close the family. Jane to disposition: fix, accept or defer.
- **P2 (new, disposition proposed: fix).** Every feature that changes a finished file after conversion (the rules' rewrite, a user's Choose folder…) leaves the page's picture of that book behind: Pending, wrong counter, no folder button. Seen in lanes C, H, M. It will recur with the next feature that touches finished files unless the list reads the finished book's place from the same record the rules update.

## 7. Personal-folder listing (list only; nothing deleted or moved)
Files or folders newer than my start (23:15) in `Desktop`, `Documents`, `Downloads`, `Pictures`, `Videos`, `Music`, `OneDrive` (three levels) and `%LOCALAPPDATA%\Books Arranger`: none. Sergei's installed copy and Data folder, `Z:\`, port 5210, the worktree, `q031*` and the main checkout's code: not written to.

## 8. Disposal
- Closed: the lane A shell (by the tray's Quit), eight headless engines (by the app's own shutdown route, all ports refused), 72 headless Edge processes (by my own profile folder). A final check found no process whose command line names my run folder. Sergei's PIDs 40204 and 41472 and port 5210 unchanged.
- Also stopped, my own: two `watch.sh` polling loops and one background wait loop (found when the first removal failed).
- **Run folder NOT yet removed.** `I:/AI Projects/Worktrees/Books Arranger/futaba-031c/` (about 4 GB: engines' data, fixtures, finished files, Edge profiles, logs, my scripts) is the only thing of mine left. The sweep (`node scripts/studio-sweep.mjs --project "Books Arranger" --path "I:/AI Projects/Worktrees/Books Arranger/futaba-031c" --apply`, dry run planned exactly that one item) refuses it with `in use or locked (rename refused: EBUSY)`, four tries over about 8 minutes, and a plain rename of the folder fails the same way. Every folder inside it renames freely, and no process whose command line names it is running (checked by command line and with Windows Restart Manager, which reported nothing), so the holder is a directory handle I cannot attribute (a scanner, or a process of another session). Nothing in it is evidence I still need: this report carries the numbers. Rerun the command above when the handle is gone (the sweep also records a refusal and retries on its own schedule).
- **Not mine, left alone, for Jane:** a QA pass on an earlier build (`ender-031/dist/builds/9e900a6a…`, run folder `Worktrees/Books Arranger/futaba-031b`) left a Books Arranger shell (PID 108088, with its children) and five engines (PIDs 101612, 24040, 111176, 117500, 85920 on ports 5242 to 5246) running, plus about 9 Edge processes, still alive at 00:55. The sweep keeps `futaba-031b` as written under 48 h. Someone should close them.
