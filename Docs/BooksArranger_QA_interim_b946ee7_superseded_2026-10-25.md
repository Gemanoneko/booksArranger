# Books Arranger 0.22.0 - INTERIM QA on candidate b946ee7 (Futaba)

Pass run 2026-10-25. Tester: Futaba. Behavior only; construction is Senua's. Stopped early on the coordinator's instruction: the b946ee7 build will not ship because of the Blocker below, and a fixed candidate is coming. This report records what was verified on b946ee7, what failed, and the exact checks still pending for the fixed build. It is not a release clearance.

Version under test: **0.22.0**. Installer: `Books-Arranger-Setup-0.22.0.exe`, SHA-256 `6e7fd42079a25a0d55e93e036ad787e1fe781585386df80bc8dcbbeb7ceb0fd5` (173,883,415 bytes), build `8747da8c-8d36-41c2-9fc3-8959ef6a3978` in `C:/Antigravity Projects/Worktrees/Books Arranger/cand-0220b/dist/builds/`.

Release artifact manifest (`cand-0220b/dist/release-artifacts.json`) SHA-256: `7d52a8949e3750c5830c63f9de31bf70f112470cab9d1d38c1b4f8a2a26dd21a`.

Release source commit: b946ee732be82acdbd56efa351bd1dce96d9880e

Blockers: 1. Majors: 3. Minors: 8. Data loss found: none. Pattern alerts: 2 (section 6).

**Verdict:** NO-GO

**Why NO-GO.** The eight new "Needs your answer" chips (and the old "Need to reacquire" chip) do not work in the packaged build: clicking one sends a request the server refuses (HTTP 400, "Unknown attention group") and the list stays on "Loading...". Sergei can still work every book from the "All" view, and nearly everything else I tried behaves as specified, but the chip filters are how he works a list of 140 to-dos, and bulk "Approve as is" lives only inside two of those chips. Two more Majors (a book that never continues after Sergei's "Same author" answer, and a Scan again that reports a false success) also break a promise the row makes.

## 1. Build identity and the entry receipt

- Installer SHA-256 recomputed from the file: equal to the handoff. Manifest SHA-256 recomputed: equal to the handoff. Manifest `version` 0.22.0, `source_head` b946ee73..., `payload.verified` true. `cand-0220b` HEAD b946ee7, tree clean, nothing in it written by me.
- The installer was **not run** (Sergei has Books Arranger installed per-user on this machine; running it would overwrite his install entries). I extracted it with the repo's pinned `7za.exe` 21.07 (SHA-256 `b0cfdeaf429f5cc53f85123dd8f5a5feb92c19d31aa34df257edf9a26be05f95`) into an isolated folder: **277 of 277 files hash to the manifest** (0 missing, 0 mismatched, 0 extra), and the `win-unpacked` tree in the build folder also hashes 277 of 277. 80 of 80 text files under `resources/backend` equal the committed blobs of b946ee7 once CRLF is ignored. Backend `VERSION` 0.22.0. 7-Zip reports "data after the end of archive" (the installer's own tail), nothing else.
- Step 1, the identical entry check: `run-entry.sh` SHA-256 `2bf8f16be958ec8fc692fb80f1724e4e3659b1284ba5bc72fc58f6fb518fa5c7` (as required); port 5212 free and no process of ours running when I started; Bash timeout 600000; exit 0 in 385 s; log `qa-run-0220b/logs/futaba-entry.log`. Counts from the gate's own pass line: **1,591 Python cases, 64 node cases (64 pass, 0 fail, 0 skipped), 20 frontend scripts, 8 syntax files**, as expected.

Ender's receipt (from the handoff):

`Entry-check receipt v2: books-arranger v0.22.0 @ b946ee732be82acdbd56efa351bd1dce96d9880e (dirty: N) [source:f555e63791094c202f7398a455d57415299904af67a9fa692561c2bd83eb54c8; harness:fc2d9cbf2878ea8e87833ec6a37261fc92c426fe302e5c74036e17907ad751c2; runtime:7aa29336e78db6ca9f9fb408ca334f72c0425bb18432792614fcd14587db4f49; checker:8af6c2583c60cdef7b610f2161010394aa7ad45fafe7584f69e98fc5c131ce6a] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a`

Futaba's receipt (printed by my run):

`Entry-check receipt v2: books-arranger v0.22.0 @ b946ee732be82acdbd56efa351bd1dce96d9880e (dirty: N) [source:f555e63791094c202f7398a455d57415299904af67a9fa692561c2bd83eb54c8; harness:fc2d9cbf2878ea8e87833ec6a37261fc92c426fe302e5c74036e17907ad751c2; runtime:7aa29336e78db6ca9f9fb408ca334f72c0425bb18432792614fcd14587db4f49; checker:8af6c2583c60cdef7b610f2161010394aa7ad45fafe7584f69e98fc5c131ce6a] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a`

The two lines are **byte-identical** (compared with `cmp` against the handoff text and against Ender's own log; SHA-256 of the line `1699ddded7def9fb63c639927a96fc9d21b2ec33a1a53c437fadff8e9a2145d2`). Limit: the receipt covers the pure-node gate (`check`); `pre-qa`, `post-build`, `check-electron` and `test:smoke` are undeclared, so n/a. It is not a behavior test, and it did not catch the Blocker (section 4, B-1).

## 2. Method and isolation

Three lanes, all from the extracted payload, all with a private environment (own TEMP, APPDATA, LOCALAPPDATA, USERPROFILE) and fixture libraries I generated (58 to 78 small MP3 and M4B files made with the packaged FFmpeg, plus a 100-book catalog):

- **Lane A, the real packaged shell** (`Books Arranger.exe` from the payload): `--shell-profile`, `--data-dir`, `--roots-json`, `--port=5214`, `--show-inactive`, `--quiet-errors`. Used for launch, window, close, Quit and the first-run screen. Screenshots with `PrintWindow` (no focus change; the foreground window was the same before and after).
- **Lane B, the packaged backend** started by the packaged Python, with the public-source transport closed (HTTP 503 to every request, as `tests/test_local_admission.py` does; nothing else patched), the UI loaded in a leased headless Edge (`scripts/qa/headless-browser.mjs`, driven over DevTools: no OS input, no focus, no audio). This lane carries every to-do check, with an output folder set.
- **Lane C, the packaged desktop backend** (the process the shell starts, with the shell's own token mechanism), for the book-list speed numbers.

Why the to-do list is not driven inside the real Electron window: with `--roots-json` the shell passes no output folder (`desktop/main.js`, the `audiobookOutputRoot` line is null when a roots file is given), the app then reads "No sorted output folder is set. Set the Audiobooks Sorted output folder to start automatic processing.", Start is blocked, and nothing can reach the list. The only alternative was to point the shell at the real `Z:` roots, which is forbidden. So the to-do UI is the packaged `web/` served by the packaged backend, rendered by Chromium in a headless browser at the exact content size of the real window (1264 x 821, from lane A). Same HTML, CSS and JS; not the Electron frame.

- Never installed or run on Sergei's profile. His install (`%LOCALAPPDATA%\Programs\Books Arranger`), his profile (`%APPDATA%\Books Arranger`) and his data folder show no change since this session began (modification times checked at the end). His app was not running. `Z:\`, `Y:\`, the live `data/` and the real catalog were never opened. My ports: 5212 (lane B), 5214 (lane A), 5215 and 5216 (lane C), one engine at a time per port; 5210 (his) never used.
- Check for real OS input: none used. Clicks, keys and typing in lane B are DevTools events inside the private browser. In lane A the only OS-level actions were `WM_CLOSE` posted to my own window, my own `--quit` second-instance command, and the first-run window, which ignores `--show-inactive` and held the foreground for the few seconds it was open (known, 0.21.2 m-2; the brief allowed focus-taking visual checks). The tray icon's own right-click menu was **not** used.

## 3. What was verified on b946ee7

### (a) The "Output needs attention" list

Fixture state at the first look: 18 rows. Chips seen: Missing files, Missing title or author, Author unclear, Same author?, Name taken (hidden at zero, shown at 1 later), Part of a bigger book, Files unclear, Order unclear, Can retry (always shown), Other; the other Stopped chips hidden at zero; Retry all hidden at zero.

| Check | Result |
|---|---|
| Counts agree | All chip = shortcut "Needs attention . N" = Jobs line "N need attention" at every observation (25, 24, 23, 22, 21, 19, 18 ... 15). Within one poll after an action. Exception: see m-5. |
| Copy, rows, sentences | Every status line and sentence I compared is verbatim against Judy's sheet and her three review sections, including the late fixes: "Author missing / No author in the tags, file name or folder name.", "Tags unreadable / The tags show garbled text, so they aren't used.", "Two people are credited. The app can't tell who wrote it.", "The only name credited may be the reader. The app can't tell who wrote it.", "Is "Alder Corvel" the same author as "Alder Corvell"?", "Spelled almost like an author you have (1 book).", "No choice files it as written. Nothing is remembered.", "No choice files it under Без автора.", "A choice is remembered for other books with these names. Applies to 2 books.", "N of M files is missing.", "All 2 files are missing.", "The track tags say there are 3 parts, but part 2 isn't here." with "Part 2 of 3", "Season or episode numbers in the names or chapters suggest separate books.", "The names or chapters number the files as books, so they may be separate books.", "Together these 2 files run 32 hours, which is long for one book.", "The tags say 5 tracks, but 3 files are here.", "Some files share a track number.", "Track numbers skip or don't start at 1.", "Name taken / A book with this name is already in Audiobooks Sorted.", "Needs you / This book needs your decision. Reason: ...", "Tags/Names/Goes to / As one book / Already there" labels, "Still checking 1 book. More may appear here.", "On hold - see Needs attention". |
| Goes to line | On every Missing-title, Author, Same-author, Part, Files, Order and Missing-files (some present) row; label "As one book" on the set rows, "Already there" on a taken name, "Goes to" elsewhere. Absent on the all-files-missing row (as in the mockup) and on the Stopped row for the damaged MP3 (see m-3). Never "Unknown". |
| Tooltips | Every control in the chips and the row types I dumped (each distinct title and accessible name read from the page): all verbatim, including chip tooltips (with N6 "Show books that may be parts of a bigger book."), shortcut "Show every book that needs you.", Approve (both versions, the set version with the re-encode sentence, N3), Approve this order / these files, Change order, Choose files, Keep as separate books, Scan again (both versions), Convert what's there, Remove from list, field tooltips, radio tooltips "Use {name} as the author." and "Type a different author.", the inert Approve "That name is taken. Change the title or author." and "Save or discard the edits in the details panel first.". Technical details summary "Show the technical message.", Copy "Copy the technical message to the clipboard." |
| Layout, 6 sizes | 1440x900, **1264x821 (real default content size)**, 1024x768, **934x611 (real minimum content size)**, 700x800, and 200% zoom (720x450 at 2x): **0 overlapping pairs of elements in every row, no horizontal scroll (page or list), no clipped cell, no clipped button text**. Chips 40.5 px high; inputs 37.5 px high and 203 px wide at the narrowest; radios 24x24 with a 32 px label row (52 px when the label wraps); row buttons at least 96 x 37.5. The list window grows with the viewport (740 px at 900 high, 661 at 821, 608 at 768, 640 at 800, 451 at 611, 430 at 450). **At 1440x900, 3 full rows are visible**, as specified. Exception: m-1 (Convert what's there is 140 px wide, target 152). |
| Keyboard | Tab order from the row: row, Select, fields or radio group (one stop), primary, second action(s), View metadata, Source folders, as in section 9 of the spec, on five row types. Arrow keys move inside a radio group and never approve. A space typed in a field does not select the row. **Enter in a field does not approve and refreshes the Goes-to line; Ctrl+Enter approves.** Focus ring: 3 px solid on every stop, not clipped. Esc cancels the dialog. Focus after Approve: the next row's first working control (but see m-3). |
| Pending state | "Approving..." with `aria-disabled` and focus kept, row size unchanged, then the "Queued" flip with the verbatim hint "Approved. Converts if needed, then renames and moves it to Audiobooks Sorted.", disabled "Queued" button, strip line "Approved 1 book. Track it under Queued / creating.", row gone at the next refresh. |
| Technical details | Closed by default on every row I selected (all 25 rows in one pass, plus repeats). Region: `pre`, tabindex 0, aria-label "Technical message", max height 240 px, `overflow-wrap:anywhere`. Space opens and closes it; mouse opens it; Copy details writes the text and shows "Copied.". It stays closed on the next selection. (Enter on any `summary` does nothing in my driver, including the old Manual review one, so Enter on it is not judged.) The raw ffmpeg text appears there in full and is not in the row, the panel status or the Jobs panel, which reads "Audiobook on hold: Broken Lantern / On hold - see Needs attention". Leaks: m-2, m-6. |
| Names and rule numbers on screen | No "Sergei" or "ruling" in any row, panel status, Jobs panel, grouping line or tooltip. Present in the opened "Accepted evidence" JSON of a finished book: m-4. |

### (b) Title + author from one source, readers, no author

- **One source converts:** a single file `x1/01.mp3` whose only evidence is the tags (album, title, artist; the folder name is junk) converted automatically to `Вельская Алина\Тихий Омут - Вельская Алина.m4b`. A two-file book whose tags and folder agree converted too.
- **A suspected reader is never filed as the author:** a book whose only credit is a name the catalog knows as a reader of three other books is listed as "Author unclear / The only name credited may be the reader...", the radio shows "artist tag . reader on 1 other book", **nothing is preselected**, the line "No choice files it under Без автора." shows, and an untouched Approve filed it under `Без автора\Чужая Тень.m4b`. Bulk exclusion of that row was **not** tested (the row was approved before the simulated bulk run; section 7).
- **A no-author book asks first:** four no-author books were listed as "Author missing" with the title basis line ("Title from the folder name." / "Title from the file name.") and the empty-Author placeholder "Empty files it under Без автора.". Approve as is with nothing typed on `Утро снайпера` filed it at `Без автора\Утро снайпера.m4b`, which equals the Goes-to line shown before the press; the job records "Approved by you".
- Tags garbled (UTF-8 read as Latin-1): "Tags unreadable", title from the folder name, destination `Без автора\Mojibake.m4b`.

### (c) Approve as is, typed values, merge rules, saved order

- Typed author "Терри Пратчетт" on a no-author book: the Goes-to line followed after 546 ms (debounce 500) to `Pratchett Terry\Шляпа полная небес - Pratchett Terry.m4b` (the seeded merge rule). Enter alone did not approve; Ctrl+Enter did. Output exactly there, the sources gone once the job completed (the event order itself was checked on the joined-parts job, section (d)); job actor `user`, "typed: author", evidence provider "Entered by you".
- Author unclear: picking the album-artist candidate moved the line to `Пухин Сергей\...`; choosing did not approve; Approve filed it there.
- Same author?: arrow keys through the radios never approved; choosing "Same author: use Alder Corvell" and pressing Approve filed `Alder Corvell\Salt Road - Alder Corvell.m4b` and showed "Remembered. 2 books continue." (but see M-1). Near-spellings of authors already converted were asked ("Marcus Reed" vs "Marcus Read", "Андрей Белова" vs "Андрей Белов"); a translation pair was asked with "Same name in another language.".
- Name taken: a new book whose planned path is occupied by a file the catalog does not know was listed with Title and Author fields, label "Already there", an inert Approve with the exact tooltip, Ctrl+Enter inert; typing a new title freed it (label back to "Goes to"), Approve worked, and the older 39-byte file in Sorted was untouched. (A duplicate of a recording the catalog already holds takes the "Needs you" duplicate route instead: m-3.)
- **Saved order:** Change order focuses the "Included audio files" heading; moving files in the panel makes Approve inert with the exact tooltip; after Save track review the row list shows the saved order (04, 01, 02) and **the output's chapters follow it** (Глава 4, Глава 1, Глава 2; and Глава 2, Глава 1, Глава 2 for the tied book). Save needed a typed note first ("Record the membership and order review basis" otherwise); see m-7 and M-3.

### (d) Parts

| Set | Result |
|---|---|
| Explicit "Часть 1 / Часть 2" M4B pair | Joined automatically into one M4B, 24.009 s, **6 chapters at 0, 4, 8, 12.005, 16.005, 20.005 s** (titles Глава 1 to 6 in order); the second part starts at 12.005 s, equal to the first part's recorded re-encoded length (12.0047 s in the job journal). |
| Bare-numbered "Геном 1/2", chapters continue | Joined automatically, same chapter layout. |
| Volume pattern "Торадора 1/2", every file starts at Глава 1 | Stayed two separate books, each 12 s, 3 chapters, track tag kept. |
| Season markers (3 files, s01e01 ...) | Asked: "Part of a bigger book / Season or episode numbers ...", Playback order list, "Approve as one book" + "Keep as separate books". |
| Book words (2 files "Книга 1/2") | Asked; "Approve as one book" joined it: 24.009 s, 6 chapters at 0, 4, 8, 12.005, 16.005, 20.005. |
| Over 30 hours (2 x 16 h) | Asked with the verbatim sentence. Approve was refused with "The audio format needs a decision the app can't make yet..." (my 8 kHz, 8 kbps fixture is outside the encoding policy; correct refusal copy). A real 32 h re-encode was not run. |
| Missing part (tracks 1/3 and 3/3) | "Missing files / The track tags say there are 3 parts, but part 2 isn't here. / In ...\Strangers\ / Part 2 of 3". After the part was restored and a library scan ran, the set of three **joined automatically** into `Лесная Анна\Незнакомцы - Лесная Анна.m4b`. |

**Originals are removed only after the joined book is verified:** in the job journal of the joined book "publishing" is stamped 00:22:25.22 and the source-cleanup record is created 00:22:26.93, after it. No source remained for any converted book in any run.

### (e) Keep as separate books

On the 3-file season set **with saved panel values** (original language, canonical title, author folder, author credit and an evidence note saved through "Save preview metadata"; the panel said "Metadata source saved."), pressing Keep as separate books gave "Kept as 3 separate books. Each is checked again.", the row left, the candidate count rose from 41 to 43, the three sources kept their exact size and modified time, nothing new appeared in Sorted at the press, and the three files became three candidates that the app then researched and converted on their own as `Вик Орлов\Сериал 1 / 2 / 3 - Вик Орлов.m4b`, none of them returning as "Part of a bigger book". So the N1 fix really splits. With unsaved panel edits open, both Approve as one book and Keep went inert (as specified).

### (f) Missing files rows

Names and folders exactly as specified: the folder on an "In" line, each missing name on its own line, "Part 2 of 3" for a missing part. A missing cover alone adds no row. Scan again with the file still missing: "Checked 02:46. Not found." Remove from list: row hint "Removed from the list. No files were touched.", strip "Removed 1 book from the list. No files were touched.", count 19 to 18, no file touched; when the files returned and a scan ran, the book came back as a normal book. Scan again on a missing **part**: M-2.

### (g) Book list speed (packaged desktop backend, local disk, 100 generated 2-file books, one run)

| Measure | Result |
|---|---|
| List (candidates, All), idle, before any conversion | median 21 ms (n=12) |
| List during the run, all samples | median **1.29 s**, p95 **4.64 s**, max **5.76 s** (n=317) |
| List by converted books | 0-24: median 0.87 s, p95 1.82 s; 25-49: 1.22 s, 2.60 s; 50-74: 1.42 s, 4.22 s; **75-99: 1.67 s, p95 5.48 s, max 5.76 s** |
| `/api/state` during the run | median 520 ms, p95 772 ms, max 898 ms |
| List, idle, all 100 converted | median 51 ms (the first call 1.35 s, then about 50 ms); the "Audiobook Ready" filter the same |
| Whole run | 100 of 100 converted in 1,007 s, 0 failed |

The changelog line "on a 200-book test with 50-99 books converted, the median wait fell from 13.3 s to 3.4 s" is not reproduced or refuted: my catalog has 100 books, not 200, and I had no 0.21.2 build to run beside it. On this catalog the list still waits seconds while books convert and the wait grows with the converted count (p95 5.5 s at 75-99). The status call is unchanged from the 0.21.2 figures (0.53 / 0.80 / 0.95 s there).

### (h) Regression: scan, approve, convert, verify; close and quit

- **Scan to verified output:** on the 100-book catalog (scan 100 candidates, automatic approve, convert): all 100 outputs have 2 chapters, a duration of 0.6 to 1.2 s, title and artist tags and an audio stream; 20 sampled outputs fully decode with no errors; **0 source audio files left**. On the UI catalog I probed the chapters of the joined, kept-separate and reordered outputs (sections c and d) and confirmed every output exists in Sorted with its source gone; I did not decode-test each one.
- **Shell, launch:** engine listening about 6 s after launch, window "Books Arranger" 1280 x 860 (content 1265 x 823), header **v0.22.0**, the page says "Closing this window keeps Books Arranger running in the tray.". 6 processes. Foreground window unchanged.
- **Close button:** a real `WM_CLOSE` (what the title-bar X sends) hides the window; all 6 processes stay and port 5214 stays held: the recorded tray exception, not a defect.
- **Quit:** the tray's own command path (`--quit` to the running copy, same `--shell-profile`) exited 0; every Books Arranger process was gone on my first poll (under 1 s), the launch command exited 0, port 5214 free.
- **First-run "Choose data folder" window:** renders; `WM_CLOSE` ends every process (exit 0). It took the foreground while open (known).
- **Start racing Quit: NOT VERIFIED.** My three-iteration harness failed to create its fixture folders (a `spawnSync` call returned silently), so the catalogs were empty and the runs recorded a discovery failure that has nothing to do with the product. Discarded. Pending for the fixed build.

## 4. Findings

### B-1 - Blocker - the eight new "Needs your answer" chips return HTTP 400 and leave the list on "Loading..."
**Repro** (packaged build, any catalog with listed books): View = Book candidates, Status = Output needs attention, click any new chip, for example "Missing title or author". **Seen:** the line "Loading Output needs attention . Missing title or author..." stays, the table stays empty, the page message reads "Unknown attention group". The page's request is `GET /api/inventory?library=Audiobooks&offset=0&search=&view=candidates&status=output_attention&group=title_author` and the server answers 400 for `files_missing`, `title_author`, `author_unclear`, `same_author`, `name_taken`, `part_of_book`, `files_unclear`, `order_unclear` and also `reacquire`; `all`, `retry`, `repair`, `checking`, `changed`, `audiobook`, `other` and `unsupported` answer 200.
**Cause (read from the code, not verified by a fix):** `web_server.py` line 354 checks `group` against the fixed set `{'all','retry','repair','checking','changed','audiobook','other','unsupported'}`; that line is identical at v0.21.2 and at b946ee7. `review_backend.py` line 323 accepts the new keys, so the Python tests, which call it directly, pass.
**Why it matters:** Sergei cannot filter his to-do list by reason, and bulk "Approve as is (N)" exists only inside two of these chips, so it cannot be used. The "All" view still works for every row.
**Status:** open. Surfaced to Jane during the pass. (`reacquire` has been broken since 0.21.2.)

### M-1 - Major - a book answered by "Same author?" never continues, and drops out of every list
**Repro:** two books with the same new spelling ("Alder Corvel", two files in two folders), both asked. Choose "Same author: use Alder Corvell" on one and press Approve. **Seen:** the strip says "Remembered. 2 books continue.", the pressed book converts, and the partner ("Tin Lantern") disappears from the to-do list but stays "Held - Same author?" in All candidates. It was still there 30 minutes later, across **three** more Stop / Scan / Start automatic cycles and a scheduled "Next automatic retry check". The research record still holds the old question and the old rules generation; the API counts it as `todo_still_checking: 1` while research shows 0 researching, 0 waiting; the strip's "Still checking 1 book." line showed at first and later went hidden.
**Why it matters:** Sergei believes both books continue; one sits in limbo, listed nowhere, the exact "silent wait" he rejected. Nothing is lost (the source is untouched).
**Status:** open.

### M-2 - Major - Scan again on a "Missing files" row for a missing part reports a false success and does not catalogue the restored part
**Repro:** a set with parts 1 and 3 present (tracks 1/3 and 3/3). (1) Press Scan again with part 2 still absent. **Seen:** the strip says "Files found. The book is checked again.", the row shows that line with Scan again and Convert what's there disabled, and it stays that way until the page reloads. (2) Put part 2 in the folder and press Scan again. **Seen:** the same "Files found" line, the new file is not catalogued ("Files cataloged" unchanged), and the row returns unchanged with "Part 2 of 3". The spec check (part-sets 8.4: "Scan again with the part restored removes the row") fails.
**Cause (read):** `merge_service.scan_again` sets `found` for any state `refreshed` or `unchanged` of the book's known members; a part that was never catalogued is not among them.
**Workaround that works:** Stop automatic processing, Start scanning, Start automatic processing: the three parts joined into one book.
**Status:** open.

### M-3 - Major - after a successful "Save track review" the row's Approve stays inert
**Repro:** Order unclear row, Change order, move a file, tick the two confirmations, type a note, Save track review ("Track review saved. Source files unchanged."). **Seen:** the row's list shows the saved order but "Approve this order" stays inert with the tooltip "Save or discard the edits in the details panel first." for at least 33 s (watched every 2.5 s). Selecting another row and coming back clears it; a fresh page load shows it enabled.
**Why it matters:** the workflow the button promises ("Save it there, then approve") does not work on the live page, and the tooltip tells him to do what he just did.
**Status:** open.

### Minor findings

- **m-1 - "Convert what's there" is 140.3 px wide, target at least 152 x 32.** `style.css` has `.row-actions .ask-convert{min-width:152px}` and the later, more specific `.row-actions .row-retry[aria-label^="Convert"]{min-width:104px}` wins. The label is not clipped. All the other ask buttons are at or above 152.
- **m-2 - raw OS text outside Technical details** for the two missing-file books: the All candidates status cell reads "Needs attention - Cannot protect exact file: [WinError 2] The system cannot find the file specified." and the details panel's "Automatic result" lists the same sentence as a bullet (`#automatic-reasons`), under a status that is already plain ("All files missing / All 2 files are missing."). The panel also says "Automatic retry after ..." for a book whose files are gone.
- **m-3 - duplicate-recording rows are dead ends.** "Needs you / This book needs your decision. Reason: Identical verified recording already arranged - duplicate sources preserved" (and "Possible duplicate recording - original sources preserved") show an inert Approve whose tooltip says "That name is taken. Change the title or author.", but the row has no title or author field and no other action. Judy's offer 3 (Keep existing) covers this, not built. After approving the previous row, focus landed on that inert Approve (the rule is "next row's first working control"). The Stopped row for the damaged MP3 has no "Goes to" line (the spec asks for one on every row).
- **m-4 - names and rule numbers in opened "Accepted evidence".** On a finished book the raw JSON contains "(Sergei 2026-10-24, ruling 6b)" and "Sergei's rule (ruling 12)". Closed by default; the stored note is part of the recorded evidence. Judy's part-sets must-fix 1 set the standard for the grouping line only.
- **m-5 - the page lags its own counts.** After "Same author" the partner row stayed on screen for more than 6 s while the shortcut had already dropped; after Scan again the "Files found" row stayed (M-2). A fresh load agreed with the count every time.
- **m-6 - spec conflict, build follows one side.** Each row cell's tooltip begins "Technical detail:" and carries the server's raw reason (up to 200 characters; the damaged MP3 row carries a local path and "Full audio decode failed"). Spec 4.6 says that is intended; spec check 3 says a search of the page for `decode` must find it only inside the open Technical details and that the tooltip shows none. One of the two needs to change.
- **m-7 - "Save track review" demands a typed note** ("Record the membership and order review basis") before it saves a reordered list; the Change order tooltip does not say so. Judy's call whether the note stays on this path.
- **m-8 - "Part of a bigger book / This file is named as one chapter." on a four-file book** (the title ends in a number). The sentence says "This file". Spec'd verbatim; the cause is wider than the sentence.

### Observed, not diagnosed (no finding without a realistic repro)

- Three books credited to "Автор Номер1", "Автор Номер2" and "Автор Номер3" in one research pass were all filed under the folder `Автор Номер1\`, silently. Names that differ by a trailing digit are synthetic; realistic near-pairs ("Белов"/"Белова", "Reed"/"Read") were asked as specified. Ender may want to know that digit-different credits merge.
- "Name taken" only appears when a file the catalog does not know sits at the planned path. A different recording of an already-converted book (same title and author) goes to the "Needs you" duplicate route instead, as does one whose sanitized name differs ("The Hollow Harbor?" files as `The Hollow Harbor_`).
- A tags-versus-folder disagreement (folder "Пухин Сергей", tag "Ирвин Мальц") converted under the tag author without a question. Accepted under "title + author from one source is enough"; the "Tag and folder differ" sentence was not produced by my fixture.
- "Title and author missing" was not produced: the file or folder name always supplies a title, so every no-author row read "Author missing".

## 5. Evidence and cleanup

- Evidence kept: this report; my entry log `qa-run-0220b/logs/futaba-entry.log` and the child copy my run made, `qa-run-0220b/entry-run-DOPgAG/` (106 MB, mine; Ender's is `entry-run-D5bHbz`). `cand-0220b` and `qa-run-0220b` are kept for Sully, untouched by me.
- Screenshots used (all in `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/d530e8cb-ee7c-4c79-8efe-d38719ffe367/scratchpad/futaba-0220/shots/`, deleted after this report): `00-initial.png` (the packaged page, v0.22.0, "0 need attention"); `m-w1440-all.png` (the list at 1440x900: chips with counts, Missing files rows with In lines and buttons, an Author-missing row with Title and Author fields); `09-chip-diag.png` (**B-1**: the chip pressed, "Loading Output needs attention . Missing title or author..." twice, empty table, the Jobs panel line "On hold - see Needs attention"); `05-iron-details.png` and `06-all-iron-row.png` (**m-2**: the WinError text in the panel and in the All status cell); `10-ready-details.png` (a finished user-approved book: Author "Pratchett Terry", Cover "Neutral artwork", destinations); `26-bulk-dialog-1440.png` (simulated chip: the dialog, five paths, "14 selected books are left out."); `28-name-taken.png` (page top only; the row itself was read from the DOM); `30-shell-window.png` (the real Electron window, v0.22.0, tray sentence, "No sorted output folder is set..."); `31-chooser.png` (the first-run window). Others in that folder were captured for the measurements and read through the DOM values quoted above, not looked at one by one.
- Removed at the end with `studio-sweep.mjs --apply --path`: the extracted payload, all fixture libraries and catalogs, outputs, logs, private profiles, the headless browser lease, my scripts and screenshots (see the final message for what the sweep reported). No process of mine remains and no port is held.
- **Slips of mine, none a product result:** (1) I wrote `python -I - ... <<< ""` once (empty input, exited at once) and, by a leftover line in a command, `python - <<'EOF'` with an empty heredoc once, which hung until I stopped the task; no orphan was left (checked by process list). Both break the brief's "no stdin python"; every other script was a file or `-c`. (2) The first 100-book run held 99 books because my fixture titles ended in a number (numbered parts); redone with digit-free titles and well-separated author names. (3) The Start-vs-Quit harness slip in section 3. (4) The first-run window took the foreground for the seconds it was open (a window with no show-inactive path, launched inside the brief's visual-check allowance). (5) Several driver slips that cost reruns (wrong selectors, an invalid language value in my first panel save).

## 6. Pattern alerts (dispositions proposed; Jane confirms)

1. **A list of keys kept in three places, and the check looks at one** (B-1; also `reacquire` since 0.21.2, and Judy's own note about `attentionKeys`). The UI list, `review_backend` and the `web_server` whitelist must agree and nothing tests the route. Proposed: **fix** (one source for the key list) and **add** a test that requests every chip key over HTTP.
2. **A message reports intent, not outcome** (M-1 "Remembered. 2 books continue." with one not continuing; M-2 "Files found." when nothing was found). Two instances this pass. Proposed: **fix** both, and **add** a test per answer that asserts the partner book's next state and the scan's real result.

## 7. Checks still pending for the fixed build (exact list)

Everything below is either untested on b946ee7 or was tested only through a workaround, and must be run on the new candidate (committed build, isolated, same method):

1. **Chips (B-1):** every one of the nine chips returns 200, shows its rows, its count equals its rows, zero-count chips are hidden, a selected chip that reaches zero falls back to All with focus on All, counts update in place on each poll, `reacquire` works.
2. **Bulk Approve as is, through the real chips (only simulated here with a page shim):** the button exists only in Missing title or author and Author unclear, never in All, Missing files, Same author?, Name taken, the three hold chips or the Stopped set; Retry selected is hidden in every "Needs your answer" chip and present in All; the dialog lists exactly the eligible paths, Cancel has focus, Esc cancels, a double press runs once, a forced refusal reads "Approved N-1 of N. 1 stays listed with its reason." and keeps the row; **a reader-only row is excluded from bulk (never tested, even in the simulation)**; a row with unapproved typed text is left out and counted; the dialog at 1440, 1024, 700 and 200% (it measured 560 x 363 with no overlap at all four in the simulation).
3. **Stopped set:** Can retry, Can repair, Need to reacquire, Original changed, M4B not supported rows with the "Goes to" line and the typed-cause copy for a decode failure (the damaged MP3 read "Source audio needs replacement", with no Goes-to line); Retry all and Retry selected never include a superseded book (stale rule); a Stopped row for an "Original changed" job (I could not make one: Pause is disabled when nothing runs).
4. **Start racing Quit** on the packaged desktop backend with the tray's drain route, at least 3 iterations (my attempt was invalid), and the same 100-book speed run on the fixed build.
5. **Real tray right-click Quit and real clicks inside the Electron window:** not done (no real OS input; the relayed "away" statement carried no stated window).
6. **A real over-30-hour join** (a fixture that passes the encoding policy; mine was refused).
7. **Ender's two grouping fixes:** rerun the explicit "Часть 1/2" join, the bare-numbered "Геном" join, the "Торадора" volume split, the season set asked then Keep (with and without saved panel values), the book-words join, the missing-part rows, and the "Сериал 1/2/3" books not returning as "Part of a bigger book".
8. **Re-verify the findings that get fixed:** M-1 (the partner book converts or is listed, and the sweep line is true), M-2 (Scan again with part 2 absent says "Checked ... Not found." and with it restored the row leaves), M-3 (Approve works right after Save track review), m-1, m-2, m-3, m-4.
9. **Same author? choices not exercised:** Approve with no choice files the book as written and records nothing (compare `author_rules` before and after); "Different author" records a keep rule and clears every book with that pair; the row's "Applies to N books." matches.
10. **Not exercised at all on this build:** the details panel's "Names found" list and the "Not found" marks in the included-source list; the empty-list sentences ("Nothing needs your attention." and the "... yet. N books are waiting to be checked." variants) and both states of the sweep line; the activity line "On hold - see Needs attention" for a multi-line reason (seen once, for the damaged MP3); the "Couldn't copy..." line with the clipboard blocked; the "Also:" line on a two-reason book; the refusal "The destination changed. Check the Goes to line and try again."; the panel check that one Title shows in both the row and the panel after a panel save; a "Needs you" row count of 0 on a copy of the live catalog (read-only, no research) and the per-chip coverage numbers (D5 in Judy's review); a second launch of the Same author? rows after an app restart.

Pass ends here. No fix was made or attempted by me.
