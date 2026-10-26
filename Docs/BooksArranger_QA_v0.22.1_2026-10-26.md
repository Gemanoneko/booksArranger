# Books Arranger 0.22.1 - QA on candidate b03eea7 (Futaba)

Pass run 2026-10-26. Tester: Futaba. Behavior only; construction is Senua's. This report certifies the build named here and no other.

Version under test: **0.22.1**. Installer: `C:/Antigravity Projects/Worktrees/Books Arranger/cand-0221c/dist/builds/8c8cd155-0648-4085-9443-7f52e66528ae/Books-Arranger-Setup-0.22.1.exe`, SHA-256 `c1b385219e62c39b7f3388d66d44db2744903ff993805162620fbd75cbe6a3d5` (174,087,620 bytes, recomputed from the file).

Release artifact manifest (`cand-0221c/dist/release-artifacts.json`) SHA-256 `db44ec92fb9d3aa795d75857caaffd91d3a9d388f0be029a4c36a66fd7c6eec6`, recomputed from the file; its `source_head` is the pin below, `payload.verified` and `payload.installer_equivalent` are true, backend and shell version 0.22.1.

Release source commit: b03eea75cd9c51e366ae0cdd3fd3a8f8582d232a
Release artifact manifest SHA256: db44ec92fb9d3aa795d75857caaffd91d3a9d388f0be029a4c36a66fd7c6eec6

## Result in plain words

- **NO-GO.** Blockers: 0. Majors: 3 open (two reproduced on this build by me, one found on c26bc58 by the shell stream and untouched by the delta). Minors: 11. Data loss found: none.
- The delta c26bc58..b03eea7 works where I could reach it headless: the wrong titles (W1) and the book-folder-as-series (W2) are fixed on real files, «Игры Немезиды» is a whole book, and Cancel update now says what did not start again, in Judy's exact words (check 22).
- **The fix for a failed install is not enough.** An installer that cannot start still closes the app with no message and no relaunch (M-1). That is one of the cases you named in (e), and it is ruling 27's own promise.
- Not cleared: the speed check (a) and the busy page (h) were not run; the real-input and focus checks were not run (Sergei present); a changed book cancelling a queued Delete was not proven; the real NSIS silent install was never run (it would overwrite Sergei's install entries).
- A GO needs M-1 and M-2 fixed and a re-check of the items in section 9 on the next build.

## 1. Build identity and the entry check (Lean verification: I did not re-run the gate on b03eea7)

- Installer and manifest SHA-256 recomputed: both equal the handoff. `cand-0221c` HEAD is b03eea75cd9c51e366ae0cdd3fd3a8f8582d232a, tree clean (0 changed paths).
- Ender's receipt, read from `C:/Antigravity Projects/Worktrees/Books Arranger/qa-run-0221c/logs/ender-entry.log` (line 2; the log is 515,613 bytes, SHA-256 `08725442b9bcfabef5ffb0cfcc729cab6d6eedd9e0b982cfb2e045970a1399f2`; the gate ran 527 s and closed cleanly, `ok`, `closed`, not forced, not timed out):

`Entry-check receipt v2: books-arranger v0.22.1 @ b03eea75cd9c51e366ae0cdd3fd3a8f8582d232a (dirty: N) [source:c59702b3a21c6ec312fdf332fe955d4690b41e8941f6b41e7a41021c5686fb7f; harness:8a87e9b89aa44ca20f2c0abeb185d76c2ba0a524d1884f88b79024929bbee5f6; runtime:885cd18256232009d94becca8d4ce31b3e9e73971768dd1a24e7490468b41adf; checker:a448c08c150e63019cfd6e49ceed5ec5b8652a97078abde197e7a50882b759cf] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a`

- Counts in Ender's log: 1,757 Python cases, 119 node cases, 25 page scripts, 10 syntax files. `check pass` at b03eea7, dirty N, as required.
- Futaba's receipt: not re-run on b03eea7 (the Lean rule). On the earlier candidate c26bc58 I did run the gate (first thing, nothing else of ours running, port 5212 free, script SHA-256 `ee218f77ec8f16008408907516147e7ec0020c566a2f93c51a4211e9a0711f2a` as required) and my receipt was byte-identical to Ender's (`cmp` of the two lines: no difference; counts 1,745 / 112 / 25 / 10). That receipt certifies c26bc58 only. Limit: the receipt covers the pure-node gate; it is not a behavior test.
- Payload of this installer: extracted with the repo's pinned `7za.exe` (SHA-256 `b0cfdeaf429f5cc53f85123dd8f5a5feb92c19d31aa34df257edf9a26be05f95`): **288 of 288 files hash to the manifest** (0 missing, 0 mismatched, 0 extra). 86 of 86 tracked text files under `resources/backend` equal the committed blobs of b03eea7 once CRLF is ignored (the other files are 79 `.pyc` and the generated `VERSION`, which reads 0.22.1). On c26bc58 both the installer payload and its `win-unpacked` tree matched the manifest 288 of 288.
- The installer was **not run** (Sergei has Books Arranger installed: its registry keys, InstallLocation and Start menu entry would be overwritten). Everything ran from the extracted payload with a private profile, private `LOCALAPPDATA`/`APPDATA`/`TEMP`/`USERPROFILE`, ports 5231 and 5241 to 5249 only, never 5210.

## 2. Method and limits

- Sergei was awake at the machine from the middle of the pass. From then on: no mouse, keyboard, tray click or focus. Headless Edge was leased (job-object owned, CDP events only); the real shell ran with `--start-hidden` and was driven over CDP; every public-source transport answered HTTP 503 (optionally after a delay), so no fixture book reached the Internet in my engine runs.
- Fixtures: 394 real tagged audio files (MP3, M4A, M4B made with the packaged FFmpeg) in Sergei's folder patterns, built from Ender's `tests/test_folder_structure.py` shapes, plus the delta's W1/W2 shapes. Scan, research, approve, convert and verify ran in the packaged engine.
- The shell stream (a second tester under my direction) ran the real packaged shell against a local fake GitHub (HTTPS, `--host-resolver-rules` and `--ignore-certificate-errors` on the shell's command line) and a fake installer. Its first pass was on c26bc58 with visible windows before Sergei arrived. I then re-ran three of its scenarios on b03eea7 with hidden windows. Anything from c26bc58 is marked "carried" below, with whether the delta touches its code.
- Two payloads, never mixed: c26bc58 (shell stream pass 1, my gate run) and b03eea7 (everything marked "b03eea7").

## 3. Delta c26bc58..b03eea7: result by item (all on b03eea7)

Files changed by the delta that reach the product: `desktop/engine-update.js`, `desktop/main.js` (exit handler, `installUpdate`, `books:status`), `desktop/update-controller.js`, `desktop_backend.py`, `local_identity.py`, `public_research.py`, `web/desktop-ui.js`. Not changed: `web/app.js`, `web/index.html`, `web/style.css`, `web/load-state.js`, `desktop/startup.js`, the scanner and merge code.

| Item | Result | Evidence |
|---|---|---|
| W1 titles: «Сергей Недоруб - Севастопольский дозор» | **Pass** | Row title «Севастопольский дозор» (tag), author Недоруб Сергей, series «Вселенная Дозоров - Межавторский» #16, goes to `Недоруб Сергей\Вселенная Дозоров - Межавторский\Вселенная Дозоров - Межавторский - 16 - Севастопольский дозор - Недоруб Сергей.m4b`; converted, the file exists. No "Недоруб - " in the title or path. |
| W1 stray bracket: «Марина Ясинская - Чужой Дозор (2017 (с 1932)).m4b» | **Pass** | Title «Чужой Дозор», no `(` or `)`; `Ясинская Мария\...\Вселенная Дозоров - Межавторский - 25 - Чужой Дозор - Ясинская Мария.m4b`. Also «Масть» (#19) and «Дозоры. Запах Сумрака» (#27, the tag title kept) are clean. |
| W1 control: two people in the file name | **Pass** | «С. Лукьяненко, И. Кузнецов - Печать сумрака» is still asked: Held, Author unclear, two people. |
| W2: a book folder is no series | **Pass** | `James S. A. Corey\5. Игры Немезиды\5. Игры Немезиды 1.m4b`: title «Игры Немезиды», no series, no number; converted to `Corey James S. A\Игры Немезиды - Corey James S. A.m4b` (never `...\5. Игры Немезиды\...`). `Joe Hill\930. Коробка в форме сердца (...)` and the Harry Potter folder `62. Книга 1 - ...` file as whole books by their tag titles, not as series. |
| «Игры Немезиды» as a whole book (item 10(b)) | **Pass** | Title «Игры Немезиды», reasons none, one converted file, no part number. Controls as designed: `Разное\Игры Немезиды 1.m4b` (folder names no book) stays «Игры Немезиды 1»; `Торадора! Том 5.m4b` becomes «Торадора! 5» (ruling 13); the lone-bitrate file «Антитела 128» is still asked, never cut. In `...\The Expanse\5. Игры Немезиды 1.m4b` the identity reads series The Expanse #5, title «Игры Немезиды», but my three Corey files carry identical audio, so the app held it as a "Possible duplicate recording": my fixture, not a defect. Series from the lookup after conversion (The Expanse #5 by series backfill) was not run (no network). |
| W3: Cancel update restarts what it stopped, and says what did not | **Partly proven** | With a conversion held in its stopping phase by an external SQLite write lock, Cancel update (pressed at 8.3 s) was answered at 33.7 s; the engine reports `closing=false`; the Check button answered at once and the book list answered HTTP 200 in 17 ms. The Install line, in the warning tint, reads exactly Judy's row 10: "Update cancelled (tried 09:47). The audiobook jobs didn't start again. Press Resume audiobook jobs to continue." Not proven: that Resume audiobook jobs then works (the lock outlasted the job's retries; it ended "Needs attention", failed 1, so there was nothing to resume). The normal case (Cancel while a conversion runs freely) passed on c26bc58; not re-run on b03eea7. |
| W5: a late engine exit never closes the app | Not run | Needs a stalled engine that exits after the shell gives up. |
| W7: the updater's own fallback never runs, and the shell reopens the old app | **FAIL** | See M-1. The new log line "Installer did not start" appears (the fallback hold works), yet the shell still exits with code 0, 1.68 s after "Update now", with no window, no engine and no message. |
| W12: one request for a URL two threads ask for | Not run | Needs concurrent research and series lanes with a counting transport. |
| Judy section 12, check 22 | **Pass for the conversion pair** | As in the W3 row. The nothing-stuck line ("Update cancelled. Books Arranger is running as before.") passed on c26bc58 and its code path is unchanged in text. The other eleven strings of section 12 (automatic, scan, lookups, bound line, generic line, engine-ended tails) were not run on b03eea7. |
| Smoke: scan, approve, convert, verify | **Pass** | Section 4. |

## 4. Smoke and folder identity (checks c, j) on b03eea7

Scan of 394 files: under 10 s, 0 errors (8.5 s for the second scan, which reused all 394). Candidates page of 40 rows: 333 to 384 ms. Automatic processing researched all 40 (offline), approved on local identity, converted and verified in order. 24 books were converted by it; a manual Approve on a held row (title typed «Антитела», press 1.2 s, converted by 11.7 s) made 25. Every output (25 of 25) decodes with no error (`ffmpeg -f null`), and the sources of converted books were removed only after their output stood in Sorted (the manual one: 0 files left). Later four more manual approvals (section 6) brought converted to 29; failed 2 (the two multi-part VanderMeer books, below).

| Fixture (Sergei's pattern) | Row identity | Destination in Sorted (file exists) | Order |
|---|---|---|---|
| **Map of Bones**: `James Rollins\Sigmа Force\2. Map of Bones`, 240 files `001..240`, most tags `N/-1`, 20 with plain `N` and the mtime 2020-03-07 | Title «Map of Bones» (folder), author Rollins James, series Sigma Force #2; no "Order unclear" | `Rollins James\Sigma Force\Sigma Force - 2 - Map of Bones - Rollins James.m4b` | **1..240, verified in the output**: 240 chapters titled Kosti_001..Kosti_240 in sequence, starts 0.000, 0.302, 0.604 s, duration 72.446 s; the odd-tag files sit at their numbers. |
| **Black Order**: 96 files, swapped tags, album «чит. Кирсанов С.» | Title «Black Order», author James Rollins, series Sigma Force #3; the reader is neither title nor author | `Rollins James\Sigma Force\Sigma Force - 3 - Black Order - Rollins James.m4b` | file-name order |
| **VanderMeer** `477. Книга 1. Аннигиляция (Сергей Пухов)`, disc tag 1/3 | Title «Аннигиляция», author VanderMeer, series Annihilation #1; no "tags say 3 discs" question; Пухов not an author | `VanderMeer Jeff\Annihilation\Annihilation - 1 - Аннигиляция - VanderMeer Jeff.m4b` | n/a (single file) |
| VanderMeer books 2 and 3 (3 and 2 chapterless M4B parts) | Held "Candidate changed - review required" (grouping needs stronger evidence); both jobs failed "Source changed - review required" | not filed | my fixture parts carry no chapter markers: not judged; Ender's catalog-row test joins them |
| **Cronin** `Перерождение 2. Двенадцать` (reader Смелова) | Title «Двенадцать», author Cronin Justin, series The Passage #2 | `Cronin Justin\The Passage\The Passage - 2 - Двенадцать - Cronin Justin.m4b` (books 1 and 3 likewise) | n/a |
| **JESPER ERSGARD - 1986** (tag credits the reader «Илья Сланевский») | Title «1986», author JESPER ERSGARD from the file name and folder; not "Part of a bigger book" | `Ersgard Jesper\1986 - Ersgard Jesper.m4b` (not "Без автора"); Season 2 and Book 3 beside it filed under Ersgard Jesper too | n/a |
| **0 Those Who Seek Forgiveness** | Title «Those Who Seek Forgiveness», author Hamilton Laurell K., series Anita Blake #0; the order is not asked | `Hamilton Laurell K\Anita Blake\Anita Blake - 0 - Those Who Seek Forgiveness - Hamilton Laurell K.m4b` | n/a |

Other fixtures filed as designed: clean names (Matheson, Sapkowski, Мецрих «Кожа128»), «Червь 1. Созревание», «Сын целлулоида - Ревущий мясник» (Books of Blood #3) kept whole with its dash, Гарри Поттер by its tag title, «Торадора! 5».

## 5. Odd-name questions (check d, spec checks 19 to 21) on b03eea7

Rendered by the real page in headless Edge, 1440 x 900.

| Check | Result |
|---|---|
| The chip is named **"Title or author"** (count 8), beside "Author unclear" (4) | Pass |
| Status word and sentence, exactly Judy 11.1 | Pass for all four: "Title unclear" + "The title ends with a number that looks like a bitrate." / "...starts with what looks like a series name and number." (3 rows: «Сновидения Ехо #3», «Мертвый ноль 7», «Профессия: инквизитор 7», «Оттенки магии 03») / "...looks like Russian written in Latin letters." ; "Author unclear" + "The author's name has underscores and may include more than a name." No second sentence, "Check it" nowhere. |
| Fields: Title unclear rows show the Title field only, prefilled with the title as read; the folder row shows the Author field only, prefilled; Approve with nothing typed is available | Pass. Two-people rows (Good Omens, Гибсон/Стерлинг, Лукьяненко/Громов, Лукьяненко/Кузнецов) offer each person as a choice, plus Other. |
| No "missing" word on these rows (check 21) | Pass for the status cell, the sentence, the row text and every `title` tooltip in the list. The details panel was not opened. |
| Excluded from **Select this page** and bulk | Pass. In both chips "Select this page" selects 0 ("0 selected · 0 can be approved as is", Approve as is (0) disabled). On the All chip (16 rows) only the 4 ordinary rows were selected; the 12 odd-name rows were skipped. |
| Controls | Clean names are not asked: Мецрих, Matheson, Sapkowski, «Червь» were filed by themselves. «Комната ужасов 2 - 01.mp3 / 02.mp3» is held as "One part of a bigger book", not as an odd-name question. |
| Destination of the underscore row | **FAIL, see M-2.** |

## 6. Approvals, speed, queue and Delete (checks a, b, g, i)

- **(b) Approvals do not wait for optional lookups. Pass, measured.** My engine's two public-source transports answered 503 only after **8 s**. Four manual approvals on local title and author: press 1,456, 1,857, 1,815 and 1,695 ms (preview 159, 54, 52, 56 ms); all four presses done in 7.1 s, which is **2,016 approvals an hour by the press**; all four converted and verified by 50.5 s (**285 an hour end to end** with tiny files, so encode-bound). During the run the state and list polls had median 502 ms, max 3,433 ms (32 samples). The transport log shows 1 lookup call in the whole run: nothing waited for one. Limit: a small catalog (40 books), not the large one.
- **(a) Speed on a large synthetic catalog with research and a series pass running: not run.** It needs a quiet machine and a large cloned catalog; Sergei was at the machine. Small-lab numbers only (not the asked measurement): Scan again on 394 files 8.5 s; delete preview 44 ms and delete 43 ms; approve preview 39 to 159 ms.
- **(i) Delete book on "All files missing": pass.** A held 2-file book, files removed outside the app, rescanned: the preview lists 0 files (`kind files_missing`, `present` 0) in 44 ms; the delete (nothing to remove, the record forgotten) answered 200 in 43 ms; the row left the list; the Sorted tree was unchanged (53 entries before and after). The dialog copy of spec 5.2 was not rendered (no desktop page in headless).
- **(g) Queued Delete.** Preview while a scan runs: `blocked {kind: scan}` (78 ms), no refusal. Confirm queued: 202, position 1. Cancel: 200, the queue empty, the row still listed after the scan ended. A second one, left to run: the queue was empty 1.5 s after the confirm (the 30-file scan had ended), outcome `done`, the row gone. **Not proven:** a changed book cancelling a queued Delete. My change (a new, unrelated file in the folder) is not a change of the book's record, so it ran, and left the new file untouched; a real change (an original file coming back) needs a longer blocker than my small lab gave. Queued Retry and Repair: not run.
- **(h) Busy page: not run** (the desktop page and a loaded engine; not reachable in headless Edge).

## 7. Updater (check e), startup (check f) and close/quit (check j)

### 7.1 Re-run on b03eea7, real shell, hidden window, fake GitHub and fake installer

| Case | Result |
|---|---|
| Installer cannot start | **FAIL, M-1.** |
| Cancel update with a stalled worker | Line exact (section 3); 33.7 s to answer; no feedback meanwhile (m-2). |
| Restart to update with a conversion and an approval running | The update reaches the new version, but **99.1 s** after "Update now" (the conversion waited the whole 90 s safe-point window and was forced at 90.8 s; the fake installer then ran with `--updated /S --force-run` and relaunched). The conversion alone stopped in 1.4 to 1.9 s on c26bc58. m-1. |
| Close: a second instance with `--quit` | All processes of the install gone 982 ms later, none left (cancel scenario). |

### 7.2 Carried from c26bc58 (shell stream, real windows, before Sergei arrived)

Carried means: measured on c26bc58, and not re-run on b03eea7. "Untouched" means the delta does not change the code behind it.

| Item | Result on c26bc58 | Delta touches it? |
|---|---|---|
| Check states: up to date 108 ms, available about 110 ms, error 503/404/500 ("GitHub returned an error, N"), black-holed GitHub "try 2 of 3" at 30.1 s, "try 3 of 3" at 65.0 s, final line at 110.05 s, no internet 117 ms; "Request timed out" never shown | Pass | Untouched |
| Check for updates while the engine is busy (conversion and 150-file approval running) | Pass: answered in 4 ms | Untouched |
| Download: progress to 100%, verified; reset mid-download "connection dropped"; bad sha512 "failed its checksum check, so it was discarded"; appended byte "doesn't match its checksum" | Pass | Untouched |
| Restart to update, idle: no dialog, installer started with `--updated /S --force-run`, relaunch, new copy shows 0.22.2 | Pass (old app gone in 250 ms) | `installUpdate` changed (the hold) |
| Restart with a conversion: dialog text exact, stopped in 1.4 to 1.9 s, sources' SHA-256 unchanged | Pass | engine-update.js changed |
| Restart with a scan running: scan stopped, Resume enabled | Pass (1.5 s) | engine changed |
| Quit during update, first M1 sentence "An update is in progress. Press Cancel update first if you want to quit." (message line and tooltip, `aria-disabled`, 8 of 8 processes kept) | Pass | desktop-ui.js lines changed elsewhere |
| M2 bound line without a number | Pass under a declared test hook that stalls a worker (waiting at 0.5 s, forced line at 90.5 s, bound line at 150.4 s); a real stall that long could not be made | **The delta rewrote the bound line (`asBefore`); re-check** |
| Tray: Check and Restart open the window and show their result in the panel, 0 dialog windows; menu during loading "Restart to update (after loading)"; tray tooltips "loading, step 3 of 4", "waiting", "updating" | Pass (real mouse events on Sergei's screen; stopped when he arrived) | Untouched |
| First frame: window visible 371, 373, 449, 449, 450, 453, 493, 513 ms (min 371, median 449.5, max 513; machine busy). Two of eight runs showed one poll with near-white pixels (about 12%): a desktop-behind frame or an unpainted one, not told apart | Pass with caveat | Untouched |
| Hand-over: strip, Quit and window rects unchanged; the running clock never reset (1,466 samples) | Pass | Untouched |
| Stopped (engine killed at 3.3 s: shown by 4.5 s, Try again returns to Step 1); port taken by a fake Books Arranger names its process; Try again then Ready | Pass | Untouched |
| Stuck from a real silence on a 24,000-book synthetic catalog: Waiting at 16.7 s, Stuck at 36.7 s with Restart engine, Copy details, Technical details; announcement exact | Pass | Untouched |
| `--start-hidden` shows nothing; the close button hides to the tray; a second launch shows the window in 74 to 83 ms; first-run setup (a folder inside the install or a folder with no catalog refused on the form) | Pass | Untouched |
| Process tree gone, port freed: setup Quit 969 ms; first frame 970 ms (no prompt); loading Quit button 4,448 ms; loading tray Quit 15,421 ms (the 15 s bound); ready Quit button 968 ms, tray Quit 949 ms | Pass, with m-9 | Untouched |
| "last load took": absent on the first start, present on the next (13 s, 2 min 8 s) | Pass | Untouched |
| Settle line and shift: "Ready · Loaded in 2 s"; Quit moved 53 px against the 48 px limit | **Minor** (m-6) | Untouched |

### 7.3 What the real update flow proved, and did not

- **Proved (c26bc58, and the three scenarios above on b03eea7):** the real packaged shell with the real electron-updater 6.8.9 talked to a local fake GitHub over HTTPS: check, download, sha512 verification, the installer lease, the engine's bounded stop, the installer spawn with `--updated /S --force-run`, a relaunch, and a new copy (0.22.2) loading to Ready. The candidate payload was never modified; the "next" copy used for the relaunch had its version set to 0.22.2 in its own `package.json` and `VERSION`; two install copies carried declared test hooks (a stall hook; an `elevate.exe` replaced by the fake so no UAC prompt could appear).
- **Not proven:** the real NSIS silent install (never run: it would overwrite Sergei's InstallLocation, uninstall key and shortcut), "no installer window" and "focus not taken" for the real installer (my fake has no window), a real `--force-run` relaunch (the real one relaunches with no arguments and would open Sergei's profile), Windows or antivirus blocking, differential download (the blockmap fell back), the disk-full line, the verify-timeout line, the in-place M4B critical section, and the research-stub matrix case 3.
- Sergei's own folders, taken before and after: install dir 280 files, 585,289,813 bytes, newest 2026-10-25T14:50:46Z, **identical**; updater cache 5 files, 348,268,295 bytes, newest 2026-10-25T19:05:36Z, **identical**; `%LOCALAPPDATA%\Books Arranger` absent before and after. His profile (`%APPDATA%\Books Arranger`) went from 8,029 to 8,027 files and 2,607,407,908 to 2,607,251,335 bytes, newest `ShaderCache\data_1` at 05:21:47Z: that is his own app's GPU cache while it ran (every run of mine used a private `--shell-profile`).

## 8. Findings

### Major (3)

**M-1. An installer that cannot start still closes the app (ruling 27, spec 2.6). Reproduced on b03eea7; also on c26bc58.**
Repro: real shell, idle engine, local fake feed serving a "download" that is not a program but has a matching sha512; Check, Download, Restart to update, Update now. Seen on b03eea7: `[update] Installer did not start: Error: spawn UNKNOWN`, `[update] Update did not install: Error: spawn UNKNOWN`, then the shell exits with code 0 **1.68 s** after Update now; no window, no engine, no relaunch, no line. Spec: "The installer couldn't start (tried HH:MM). Windows or your antivirus may have blocked it. Books Arranger is running again on 0.22.1. ... Run the installer yourself:" with the path and Show installer file, and the old app reopened.
Cause as I read `desktop/main.js` (flag only, not a fix): electron-updater queues `app.quit()` with `setImmediate` right after `quitAndInstall`. The failed spawn is handled inside the same turn, and `restartEngineAfterUpdate` resets `state.quit='none'` at once; the old engine is still marked exited until its `loadURL` finishes, so the queued quit reaches `requestQuit`, sees the exited engine and calls `finishExit(0)`. W7's hold stops the fallback, not this quit.
Why Major, not Blocker: it needs an installer that fails to spawn (an antivirus block); no data is lost and Sergei can open the app again. It is the exact failure ruling 27 exists for.

**M-2. The Author-unclear question for an underscore-named folder files the book under the folder name whatever Sergei confirms.**
Repro: `Sbornik_Astronomikon\Richard_Ford_Labirint\Mp3\Ричард Форд - Лабиринт - NN - unknown title.m4a` (artist tag «Ричард Форд»). The row says "Author unclear: The author's name has underscores and may include more than a name.", the Author field is prefilled «Ричард Форд», and the "Goes to" line reads `Sorted\Richard_Ford_Labirint\Лабиринт - Richard_Ford_Labirint.m4b`. Approve with nothing typed, with «Ричард Форд» typed, with «Форд Ричард» typed: the preview path is the same underscore path (the preview's own `author` field says «Ричард Форд»). Only a Latin spelling typed ("Richard Ford") changes it, to `Ford Richard\...`. I approved it: `Sorted\Richard_Ford_Labirint\Лабиринт - Richard_Ford_Labirint.m4b` now exists.
Expected (Judy 11.3): Goes to follows the Author field. The "local English spelling" lookup (ruling 3) takes the underscore folder name as the English spelling of the confirmed name: the junk the question was asked to prevent. Present on c26bc58 and b03eea7 (not in the delta). Severity Major: a wrong destination after the explicit author answer (rulings 6b and 12 say Sergei's answer is final); visible before Approve and recoverable by the later rename pass (ruling 21). Judy should look at the field/Goes-to pairing; the cause is in the engine.

**M-3. A hard-killed engine can leave a catalog the app refuses to open (shell stream, c26bc58; not re-run).**
Repro: the app tree ended with `taskkill /F` while the engine wrote after load on a 24,000-book synthetic catalog (5 times live size), then relaunched. Seen: Stopped, Technical details ending "ValueError: Catalog integrity check failed; folder retained"; Try again fails the same way. The catalog itself was healthy: a normal open gave `quick_check` ok and a checkpoint cleared the 33.6 MB WAL. The guard (`desktop_catalog.py`, `inspect_folder`) opens `?mode=ro&immutable=1`, which ignores the WAL, and runs `PRAGMA quick_check`; I confirmed that line in the b03eea7 payload. A torn checkpoint at kill time makes the stale main file "malformed". The update's last-resort engine end and a Windows sign-out can do the same. Seen once; unchanged by the delta. Needs triage before it is graded: if it reproduces at live size it is a Blocker.

### Minor (11)

- **m-1 (b03eea7).** Restart to update with a conversion and an approval running takes **99.1 s** (forced at 90.8 s) against 1.4 to 1.9 s for the conversion alone; the approval in flight keeps the conversion from reaching its safe point. After relaunch both books are paused and queued (c26bc58).
- **m-2 (b03eea7).** Cancel update gives no feedback while it waits: pressed at 8.3 s, the button vanishes, the status line still shows the waiting sentence, the answer comes at 33.7 s (35 s limit in code).
- **m-3 (c26bc58).** Update soon after start on a large catalog waits on the engine's own recovery pass: at 8,000 books (3,000 finished) it hit the engine's 150 s bound; 43 s after 5 min idle; 12.5 s at live size (1,572 books, 508 finished). The final Install line was not captured.
- **m-4 (c26bc58).** A download cut by `ERR_CONTENT_LENGTH_MISMATCH` reads the generic "Couldn't download version 0.22.2 (tried HH:MM). Press Download update to try again." instead of "the connection dropped".
- **m-5 (c26bc58).** Pressing the inert Restart to update while loading writes nothing to the message line; the spec sentence is "Not yet: Books Arranger is still loading. You can update when it finishes, or if loading gets stuck."
- **m-6 (c26bc58).** The settle shifts Quit by 53 px; the limit is 48 px.
- **m-7 (c26bc58).** While loading, `#jobs-status` and `#book-candidate-counts` are not shown; between the library part and the jobs part the page says "status unavailable" (902 to 1,681 ms at live size), words 3.5 says are gone.
- **m-8 (c26bc58).** Restart engine at Stuck: the old engine kept answering for 15 s (the shell's bound), the strip stayed on Step 3, and a false "Stuck · Step 1 of 4: The engine hasn't answered for 15 s" flashed for about 1 s with its announcement.
- **m-9 (c26bc58).** At 24,000 books the page lagged the engine by 80 to 93 s after Ready (Waiting/Stuck with a silent Restart engine meanwhile); Quit after Ready did not finish in 90 s; tray Quit while loading took 15.4 s (the shell's bound). Scale artefact of a 5x synthetic catalog.
- **m-10 (c26bc58).** The first-run form's refusal shows the raw prefix "Error invoking remote method 'books:select': Error: Keep data outside source libraries and installation folders".
- **m-11 (c26bc58).** The update dialog says a conversion "stops and starts again from the beginning", but it returns Paused/queued and needs Resume audiobook jobs. I did not check whether the page hints at it.

Observations, not defects: the quiet stretch from step 3 to 4 is about 5 s at live size, 28 s at 8,000 books, 78 s at 24,000 (Judy's N5); my VanderMeer parts have no chapter markers; carried Minors m-10 (focus after Delete on Stopped rows), m-14, m-15 of the 0.22.0 report were not examined.

## 9. Not run, and what the next build must re-check

Not run (Sergei present): every real-input check (clicking the tray's Quit item during an update, real tray right-clicks, real mouse events inside the window), focus-taking checks, a visual look at the strip, the real-installer "no window, no focus" check.
Not run (other reasons): (a) speed on a large catalog; (h) the busy page; queued Retry and Repair; a changed book cancelling a queued Delete; W5; W12; Judy's remaining section 12 strings; join of "Часть N" parts, Keep, Remove this copy (0.22.0's results stand only for 0.22.0).

On the next build, re-run: M-1 (installer cannot start, and a non-zero exit after start), M-2 (the underscore row's destination with the answer typed and untyped), W3 with a free conversion (Cancel restarts it) and with a stalled one (Resume audiobook jobs then works), the bound line and the generic and engine-ended lines of section 12, the install line for W5, then (a) and (h) on a quiet machine.

## 10. Pattern alerts

**PA-1 (disposition proposed: fix; Jane to confirm).** The update flow's failure paths pass their unit tests and fail in the real shell, twice: M-1 was found on c26bc58 and survived the W5/W7 fix. Real-shell behavior (the exit race with electron-updater's queued quit) is invisible to mocks. Proposal: add one hidden-window real-shell update test with a fake feed and a non-starting installer to the gate (the harness exists, see section 11).

## 11. Cleanup and what remains

- Removed with `node scripts/studio-sweep.mjs --apply --path`: my work folder `%LOCALAPPDATA%\Temp\bq221` (extracted payload, lab, catalog, outputs, logs: 588.54 MB) and the shell stream's folder `%LOCALAPPDATA%\Temp\bq221s` (install copies, runs, 24,000-book catalogs, fake feed: 30.73 GB); both confirmed gone. Free space on the Temp drive 86.23 GB to 117.59 GB.
- Also removed: the 47 tray-icon records under `HKCU\Control Panel\NotifyIconSettings` that my hidden runs and the shell stream's runs created (all with a path inside `bq221s`; two others, `Temp\fq22\outer\Books Arranger.exe` and Sergei's `Programs\Books Arranger\Books Arranger.exe`, are not mine and were left).
- No engine of mine is running (the 5231 engine quit cleanly, exit 0); nothing of mine on any 52xx port (5230 and 5293 are another project's Vite servers). No headless-browser lease left (`headless-browser.mjs list`: no leases). My shell-stream processes were ended by PID and by path inside their own folder.
- Kept for Sully, as told: `cand-0221b` and `qa-run-0221b`; I did not touch `cand-0221c` or `qa-run-0221c` (Ender's candidate and gate run). Inside `qa-run-0221b` the child folder `entry-run-On8Ag6` is my entry-check run of c26bc58 (Ender's `entry-run-kTzTeh` is his); it stays with the folder.
- Session scratch folder (agents never clean it): receipts and the c26bc58 entry log are in `C:\Users\AnGeLZzZ\AppData\Local\Temp\claude\c--Antigravity-Projects-Studio-Illuminati\d530e8cb-ee7c-4c79-8efe-d38719ffe367\scratchpad\`; the reusable harness (fixture lab, engine launcher, page driver, fake feed, hidden-window update scenarios, about 520 KB) is in its `shared\futaba-0221-harness\`, with a `README.txt`. Jane gives Sergei that folder to delete.
- Slips of mine, none a product result: my first entry-style scan wait read the wrong key (`scan` instead of `status`) and ran 5 minutes for nothing; one heredoc with doubled quotes failed to parse and was rewritten with the file tool; a scan test failed with 409 because automatic processing owned discovery (I stopped it first). The shell stream's earlier tray tests used real mouse events on Sergei's screen after he had arrived (Jane stopped them; I ended its still-running hidden scenario by PID); it also hard-killed engines several times (M-3 came from one) and could not confirm outbound traffic of its real engine, which ran the real public transports on invented titles.

**Verdict:** NO-GO
