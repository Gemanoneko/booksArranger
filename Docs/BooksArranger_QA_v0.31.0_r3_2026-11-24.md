# Books Arranger 0.31.0: QA report, round 3 (Futaba, delta pass on the fourth build)

Date: 2026-11-24, about 03:03 to 04:20. Build tested: packaged, `399caea9da73ce0c6ee516105f80bc64ae2f9a56`. Left uncommitted. Round 2 is `BooksArranger_QA_v0.31.0_r2_2026-11-23.md` (NO-GO on `7023cc9`: B1, M1).

**Verdict:** GO

**Scope of this GO, read before using it.** It covers build `399caea` only (installer SHA-256 `e9add58f…59fbd`), the build I was handed and hash-checked. While I was testing, the worktree HEAD moved to `d96979d` (committed 03:33, "revert(look-up): Goodreads' firewall challenge is a try again, as before M1", Senua's delta 3, M7 and M8). I did not test `d96979d`, and no build of it was handed to me. The version label is the same (0.31.0), so nothing in the filename or the verdict line tells the two apart. A build made from `d96979d` or later needs its own hash-pinned pass from me before Sully releases (see section 6). From its diff (5 files: `public_research.py`, `series_backfill.py`, two tests, CHANGELOG; "B1 kept whole") I expect B1 and R35 to hold, but that is a reading of a diff, not a test.

No Blocker is open. B1 is fixed and I could not break it (4 books, 3 lanes, one fully automatic with nothing typed or pressed). R35 holds on the case I could build. Smoke passes. There is one new Major (M2 below): on this build a live Goodreads human check held a new standalone book for an hour at the identity stage. That is the behavior `d96979d` removes.

## 1. Hash check (compared only; the entry check was not re-run)

| Item | Handed over | Found | Match |
|---|---|---|---|
| Entry log `q031h/ender-entry.log` SHA-256 | `0a2c64d3…2b845b2bc8` | `0a2c64d329d747a54d996f57aadf1a47cec4e4d9718f723e3ab4b78b845b2bc8` | yes |
| Installer `Books-Arranger-Setup-0.31.0.exe` SHA-256 | `e9add58f…9fbd` | `e9add58f8cc0cd19cb2e42fed44c013e33585796eb3f7c16578958db6be59fbd` | yes |
| `dist/release-artifacts.json` SHA-256 | `65c36766…07cc` | `65c367661420db2c5031950a93572a36aff5bd166a340c8916bee9915bf207cc` | yes |
| Unpacked `Books Arranger.exe` SHA-256 | `c96a8d73…4801` | `c96a8d73c5f9843f871db89713518ba4d4791afb413d2d5d112b12b0a9fd4801` | yes |
| Receipt, line 3 of the log | `399caea…, dirty: N, check pass, personal-folders clean` | read in full: `books-arranger v0.31.0 @ 399caea9da73ce0c6ee516105f80bc64ae2f9a56 (dirty: N) … check pass … personal-folders clean` | yes |
| Worktree `ender-031` HEAD | `399caea` (manifest `source_head`) | `399caea` when I started (`git log`); `d96979d` when I finished | **moved, see above** |

Counts and method: Node `# tests 279 / # pass 279 / # fail 0` read from the log. Python: the log prints `Ran N tests` once per batch; I summed them (`grep -o`, 13 batches, total 3,202), equal to the hand-over figure. I ran no test myself.

## 2. How it was run

- **Engines.** The packaged python and the packaged `resources\backend` code of the tested build, started by my own launcher (`web_server.main()`), `--audiobook-output-root`, one data folder per lane, ports 5271 to 5283 (never 5210 or 5212), TEMP inside my run folder. All under `I:\AI Projects\Worktrees\Books Arranger\futaba-031d\` (now deleted).
- **The page** was read and driven through headless Edge on my own profile (no window, no focus, no mouse): `document.title`, `innerText`, and the page's own buttons clicked by script inside that headless page. The shell's native folder dialog cannot exist in headless Edge, so for Choose folder… I replaced only that dialog with a stub that returns a folder inside my run folder. The button, the request, the engine's answer and the row's wording are the page's own.
- **Network.** Real (Wikidata, FantLab, Goodreads, DuckDuckGo), except in the offline steps, where I blocked it inside my launcher (every non-loopback name lookup and connection refused). R27 recipe corrections followed: network block in the launcher, artist tag `Liu Cixin`, each lane taken offline to online by the app's own shutdown route, then restarted only after every stored host back-off had ended.
- **Fixtures.** Cuts (25 s parts, and the whole 36 min) of my own copy of `ba-mp3-fixture/fixture.mp3`, tags set with the packaged ffmpeg. Originals untouched.
- **Counts.** "N converted out of N approved" is the page's own line, checked against the engine's `audiobook_jobs.converted_total / approved_total`. "Listed under Audiobook Ready" is the list route with the Ready filter (`status=converted`), read after a fresh page load. File facts: size, SHA-256, decoded-audio md5 and audio-packet md5 (packaged ffmpeg `-f md5`), chapters and tags (ffprobe), and a full decode to null.
- **Comparison run.** To tell new from old I also ran the r2 build (`a57d5cef…`, installer SHA-256 `688799e7…`, the one on `7023cc9`) the same headless way, two lanes only. Never installed.
- **Shell smoke** used the unpacked exe with my own `--installation-config`, `--roots-json`, `--port 5280`, `--show-inactive`.
- Lanes: A (shell smoke), C2 (R35 press, 36 min book), C3 (fully automatic, 36 min book), H2 (blocked move), G2 (Goodreads check), N, N2 (series books, online), N0, N3 (same on the r2 build), M, M2 (see section 5), G (first Goodreads try, see M2).

## 3. What was checked, by the brief's items

### Item 1. B1, a book the rules renamed or moved must show as converted: PASS

All three checks hold on every book the rules touched. Same books, same recipe as r2's lane M (artist `Liu Cixin`, title `Тёмный лес`, offline conversion, online restart, English title and series found on Wikidata).

| Lane | What happened | Row on the page | Counter | Ready list |
|---|---|---|---|---|
| **C3** (fully automatic: nothing typed, nothing pressed) | Converted 03:45 under the Russian title. Online 03:48. Rules wrote and filed it at 04:02:03 to 04:02:06 into `sorted\Liu Cixin\Remembrance of Earth's Past\`. | `Audiobook Ready`, `Now in sorted\Liu Cixin\Remembrance of Earth's Past\Remembrance of Earth's Past - 2 - The Dark Forest - Liu Cixin.m4b`, `Choose folder…`, `Moved. The audiobook is now in …` | `All done · 0 need attention · 1 converted out of 1 approved books` | 1 row |
| **C2** (rules rewrite, then his Choose folder… during it, item 3) | Rewrite 03:54:28. His move to his folder done 03:54:33. | `Audiobook Ready`, `Now in …\his-folder\Remembrance of Earth's Past - 2 - The Dark Forest - Liu Cixin.m4b`, `Choose folder…`, `Use computed folder`, `Folder chosen by you` | `1 converted out of 2 approved books` at 03:55:56 (the second book was converting), `2 converted out of 2` at 03:59 | 1 row at 03:55:56 |
| **H2** (rewrite where the move was blocked: I put a regular file named `Remembrance of Earth's Past` where the series folder would be) | Rules wrote the book and renamed it in place at 04:00:36; the move could not happen. | `Audiobook Ready`, `Now in sorted\Liu Cixin\Remembrance of Earth's Past - 2 - The Dark Forest - Liu Cixin.m4b`, `Choose folder…`; read-only list `Could not be renamed or moved · 1` | `All done · 0 need attention · 1 converted out of 1 approved books` | 1 row |

- My poller read counters and list every 3 s through C3's rewrite: `ready=1 all=1 jobs=1/1` the whole time, `writes=1` at 04:02:03, back to `all_done` 04:02:06. In r2 the same step turned `1 converted` into `0 converted`.
- **Choose folder… after a rules move (C3):** pressed through the page at 04:04 (after the rules had filed it). The page's picker was asked `Choose a folder for The Dark Forest`, default folder the rules' folder, button `Move here`. The book moved to his folder: `Moved. The audiobook is now in …\C3\his-folder`, one `.m4b` in his folder, none left in `sorted`. (The first press, 04:03:59, produced no request and no note; two later presses behaved as above. See Minor 5.)
- **File integrity** (the rewrite must not change the audio). Decoded-audio md5 and audio-packet md5 before and after, identical in all three lanes:
  - C2 and C3 (36 min, one file): decoded `405dacfe…8e48`, packet `30abd3c4…a467` before and after. Both final files have the same SHA-256 (`c6bf8be6…`), size 36,646,304. Title `The Dark Forest`, album and sort_album `Remembrance of Earth's Past - 2 - The Dark Forest`, grouping `Remembrance of Earth's Past`, track 2, artist and album_artist `Liu Cixin`. Full decode clean.
  - H2 (50 s, two parts): decoded `4423a983…f360`, packet `551395a4…2e44` before and after; the same 2 chapters (`Track 01` to 25.013 s, `Track 02` to 50.027 s); same tags as above. My blocker file was untouched (SHA-256 `ea7c0355…` before and after). Only one `.m4b` for the book.
  - Cover and data stream: not checked this round (r2 checked them; the fix did not touch them).
- R27 content (the English title in the file's tags) therefore held in all three runs, so I did not need a separate R27 re-run.

### Item 2. M1, Goodreads' own human check counts as nothing found: PASS on this build, by injection; the live challenge produced a different problem (M2)

- **Live.** Goodreads answers with HTTP 202 and `x-amzn-waf-action: challenge` today: curl, third request of three (about 03:03). The app recorded real, un-injected human checks from Goodreads with the reason `Public source presented a human check; no bypass attempted` in three lanes: N (03:06:31), N2 (03:13:42), H2 (03:48:31).
- **Injected, to reach the ledger path.** I could not make a live challenge land on a look-up on demand, so lane G2 (standalone English book, converted at 03:10) had a challenge injected in my launcher for Goodreads only, exactly that status and header (one injection logged), switched on at 03:17:31 before its first look-up. Everything else was real, DuckDuckGo included (it gave its own live human check in the same try). The look-up ran at 03:20:14. Ledger: Goodreads `none` with the human-check reason, publisher `none` (DuckDuckGo's live human check), FantLab `none`, Wikidata `none`, state `none`. Page at 03:21:05: `All done · 0 need attention · 1 converted out of 1 approved books`, title `Books Arranger: all done`, `Nothing is running, queued or waiting.` No 6 h wait.
- Tests cover the rest, as the brief said.
- What the live challenge did to a new book: M2.

### Item 3. R35, Choose folder… pressed during a rewrite: PASS on the case I could build

C2, offline to online restart, **no Start pressed after the restart**, a second book (Ada Quill, 2.4 h, from four copies of the fixture) waiting in the library:

| Time | Fact |
|---|---|
| 03:54:28.77 | The engine's state shows `background.series.writing = 1` (the rewrite of the 36 min book has begun). |
| 03:54:28.777 | **Choose folder… pressed** (the page's own button). Page: `Move queued. It runs when the app is free.` then, on the row, `It runs when this book's processing finishes.` |
| 03:54:29.09 | I clicked `Start automatic processing` (so another book began converting during the rewrite). |
| 03:54:33.5 | The write ends. Jobs go `Paused`, `queued 1`, then `Running`, current book `Lantern Tides` (03:54:33.77). |
| 03:54:33.78 | Page: `Moved. The audiobook is now in …\C2\his-folder`, and `Renamed or moved by the app · 1`. |
| by 03:59 | The second book has finished converting by itself (`2 converted out of 2`). |

His move was done 4.7 s after the press, which is the length of the write plus 0.2 s, and it did not wait for the second book's conversion (it finished as that conversion started; that book then converted for about 2 more minutes). File result: one `.m4b` for the book, in his folder, none left in `sorted`; audio identical (item 1); his folder saved as the override (`Folder chosen by you`, `Use computed folder`).

**Not exercised (said plainly):** the rewrite itself only starts when nothing converts, so "a conversion running when the press lands" can only be built by starting one as the write begins, which is what I did (overlap of about 0.1 s before his move finished). I did not build a saved Pause under a rewrite, nor a Retry of another book queued beside it, nor separate runs with and without a Start (my Start came 0.3 s after the press). Tests cover them; Senua's delta covers them.

### Item 4. Smoke: PASS
- Lane A, unpacked exe, my own installation config, port 5280, `--show-inactive`: started, window title `Books Arranger: checking what is left` (one book waiting), started with `--show-inactive`; I did not look at the screen and used no mouse or keyboard.
- A second instance with `--close-window` (the close button's action): the window hid (title empty, handle 0); the shell, the host python and the engine stayed up (the recorded tray exception).
- A second instance with `--quit` (the tray's Quit): all shell processes and the engine were gone within 2 s, port 5280 closed. No process naming `futaba-031d\A` remained.
- Sergei's installed copy (PIDs 40204 and 41472, port 5210) was running and unchanged at the start and at the end.

## 4. Findings

### Blocker
None open. (B1 from r2: fixed, verified, section 3 item 1.)

### Major

**M2. On this build a live Goodreads human check holds a new standalone book at the identity stage for an hour.**
- This is the other side of M1's fix: the human check is now a one-hour pause on Goodreads (`CHALLENGE_REASON` and the one-hour host pause, per the M1 commit message), and the look-up before review waits for Goodreads.
- Live proof, nothing injected: H2's Goodreads record read `next 04:48:31, Public source presented a human check` (a live challenge at 03:48:31). At 04:02:13 I put a standalone book (`Andy Weir / The Martian`) in H2's library and pressed Start. At 04:03:04 the page read `Waiting for an online answer: The Martian · Next try 04:48. After 3 tries a book converts with the names from its files.` I did not wait it out. A series book beside such a pause is not held (N converted in 90 s: FantLab answered).
- Old against new, same live challenge: N2 (this build) and N3 (r2 build) started in the same second and hit one challenge at 03:13:42.8. N3 stored a **5 minute** back-off (next 03:18:42, reason `Public source unavailable`); N2 stored a **one hour** pause (next 04:13:42). Lane G (challenge injected from the start) showed the same hold: `Next try 04:06`, 03:06 start.
- How often: this build recorded a Goodreads human check in 3 of the 6 online lanes I ran on it inside 2 hours (N, N2, H2), and Goodreads challenged 1 of 3 curl requests.
- This is Senua's delta 3 M7 (and her M8: one challenge becomes "nothing found" for later books without a request) as I read the revert's message. `d96979d` reverts it. I did not test `d96979d`.
- Status: open on `399caea`; addressed in HEAD by the revert, unverified.

### Minor

1. **The Audiobook Ready list lags the counter for a book converted with an incomplete identity.** Series books converted automatically with original language `Unknown` (review reason `Canonical identity and original language incomplete`, lanes N, N2, N3): `All done`, `1 converted out of 1`, and the row says `Audiobook Ready` under All candidates, but the Ready filter returned 0 rows for about 5 minutes. N2 converted 03:13:55, Ready list lit 03:18:57; N3 on the r2 build, 03:13:55 and 03:18:58 (the same lag, so **not new in this build**). A standalone book with a verified language was listed within about a minute (G2), and N0 (r2 build) within about 35 s once. The fix for B1 did not cause it and did not change it. It heals by itself.
2. **`All done` shows while a rename or move is still owed** (r2 Minor 1, still there). `pending.moves 1` with `work: all_done` and the title `all done`: C2 03:47:36 to 03:54:28, C3 03:55:11 to 04:02:06, H2 03:51:26 to 04:00:37 (7 to 9 minutes each). Quit then and the rename waits for the next launch.
3. **The wording for a move blocked by a file in the way names a drive.** H2's row: `…\Remembrance of Earth's Past isn't available. Connect the drive or choose another folder. Nothing was moved.` The thing in the way was a file in the author folder, not a drive. For Judy.
4. **A look-up try is spent while the engine is offline, and the next one is 6 hours away.** Lane M converted offline at 03:25. I did not shut the engine down; its first look-up ran at 03:29:57 (network blocked), the ledger read `deferred`, next attempt 09:29:57, and going online at 03:35 changed nothing. In r2's lane M I shut the engine down 33 s after conversion, so this did not show. My recipe slip, but a real outage of a few minutes right after a conversion costs that book a 6 h wait (the stated design: three tries, six hours apart).
5. **One Choose folder… press on C3 produced no request and no page note** (04:03:59, a freshly loaded tab, my picker stub set 5 ms before the click). Not reproduced: the next two presses on the same row worked. I cannot say whether the page ignored it or my harness raced it. Logged, not claimed as a defect.
6. **Carried over from r2, not retested:** approving a book by hand while automatic processing is idle leaves the audiobook queue `Paused q 1`.

### Harness notes (not product findings)
- Headless Edge tabs left open for several minutes were frozen by the browser: the page's async requests never answered while the engine answered a curl in 0.1 s. Marking the tab active over the debug protocol fixed it. If anyone reproduces r2's "page stale" in headless Edge, check this first.
- Hand-approving a book through the page (names, language, author) did not reach the row's title in my hands (Save names said saved; the row's review title stayed empty). I dropped that route and used automatic lanes, which are also closer to what Sergei does. Not investigated.

## 5. Not verified (said plainly)
- Anything on `d96979d` or later (section 6).
- R35's saved-Pause, separate no-Start and Retry-of-another-book variants (section 3 item 3).
- M1 at the ledger stage with a live challenge (injected instead); and the one-hour wait's end (04:48) was not waited for, so I cannot say how many hours "after 3 tries" really takes under a persistent challenge.
- R34's second half (an old 0.30-era hold), the shell's own window title while automatic processing runs (the shell cannot be given an output folder with `--roots-json`), keyboard use, layouts other than headless Edge's default, cover and data stream of the rewritten files.
- Lane M2 (a second offline lane for a short book) was stopped before its conversion; lane M is spent (Minor 4). Neither is evidence.

## 6. What I need before Sully releases
A hash-pinned pass on the build that will ship: compare installer, manifest and entry log by hash (no entry check), confirm `source_head` is the commit meant, then test only what `d96979d` changed: a Goodreads 202 with `x-amzn-waf-action: challenge` is a plain try again (5 minute back-off, r2's behavior), DuckDuckGo's human check still counts as nothing found, plus one B1 spot check (a rewritten book still shows `Audiobook Ready`, `Now in`, `Choose folder…`, counted, listed) and the smoke. About 30 minutes. Note that the revert brings back r2's M1 (a Goodreads challenge in the series ledger is a try six hours later, so `All done` can wait on it); the commit message says that is Jane's ruling of 2026-11-24, so I list it as a known accepted behavior, not a new finding.

## 7. Pattern alerts
Pattern alerts:

- **P1 (open since round 1, disposition: fix or accept).** `All done` and the status lines are honest only at the edges the build tests. This round added: `All done` with a rename owed (three lanes, Minor 2) and a Ready list that lags the counter for a book with an incomplete identity (Minor 1, same on the r2 build). One rule for "what is left" and "what is converted", read from one place, would close the family. Jane to disposition: fix, accept or defer.
- **P2 (from round 2, B1 family).** The B1 shape (the page's picture of a finished book left behind by a rewrite) is fixed for rewritten books and held through the live write. The family is not gone: Minor 1 is the same kind of disagreement on another path. Disposition proposed: accept the B1 fix as closed; keep P1 open.
- **P3 (new, disposition proposed: accept with a rule).** A change to a shared client moves every stage that uses it, and the tests that came with the change covered the stage the ruling named (the series ledger), not the other (the identity wait). M1 did this; Senua found it as M7 and M8, and I found it live (M2). The revert is the fix this time; the rule would be that a change to `PublicClient` names every stage that calls it in its test list.

## 8. Personal-folder listing (list only; nothing deleted or moved)
Files or folders newer than 03:00 today in `Desktop`, `Documents`, `Downloads`, `Pictures`, `Videos`, `Music` and `OneDrive` (three levels): none. `%LOCALAPPDATA%\Books Arranger`: not present. Sergei's installed copy and Data folder, `Z:\`, port 5210, the worktree (`git status` empty, HEAD read only), `q031*` and the main checkout's code: not written to. (My write to `/tmp` was refused once by the C: guard before it ran; nothing was written there.)

## 9. Disposal
- Stopped, all by their own routes: eleven headless engines (the app's shutdown route, ports 5271 to 5283 now free), the lane A shell (the tray's `--quit`), headless Edge (`Browser.close`), my pollers (ended on their timers).
- Checked by command line: no process whose command line names `futaba-031d`, nor `3df83ec0…` (this build) nor `a57d5cef…` (r2 build), except the shells running the check itself. Sergei's PIDs 40204 and 41472 and port 5210 unchanged.
- `futaba-031d/` (905.95 MB) removed with the studio sweep (`node scripts/studio-sweep.mjs --project "Books Arranger" --path "I:/AI Projects/Worktrees/Books Arranger/futaba-031d" --apply`: removed 1, kept 54 not mine, **stuck 0**). Nothing is still locked.
- r2's `futaba-031c` and the earlier pass's orphaned engines (`futaba-031b`, ports 5242 to 5246) were already gone when I started (only 5210 listening).
- Left for others, not mine: the sweep's kept items (`q031a` and the registered worktree `ender-031`), none touched.
