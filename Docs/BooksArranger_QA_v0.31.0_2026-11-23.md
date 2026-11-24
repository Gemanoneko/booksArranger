# Books Arranger 0.31.0: QA report (Futaba, delta pass)

Date: 2026-11-23. Build: packaged, `a8b6804a013b643412c72aedf34f1e7e00de1455`. Left uncommitted.

**Verdict:** GO

No Blocker. Two Majors (below) are logged, not gating. Four things in the brief could not be exercised and are listed under "Not verified"; the one that matters most is R27's English-title rewrite (see there). Jane decides whether to ask for a targeted check before Sully runs.

## 1. Hash check (not re-run: compared only)

| Item | Handed over | Found | Match |
|---|---|---|---|
| Entry log `q031c\ender-entry.log` SHA-256 | `cc819bc0…2f4b813` | `cc819bc0…2f4b813` | yes |
| Installer `Books-Arranger-Setup-0.31.0.exe` SHA-256 | `7f4868f4…511a845b6d` | same | yes |
| `dist\release-artifacts.json` SHA-256 | `9b8d37f1…a281c` | same | yes |
| Manifest `source_head` | `a8b6804` | `a8b6804a013b643412c72aedf34f1e7e00de1455` | yes |
| Unpacked `Books Arranger.exe` SHA-256 | (manifest entry) | `c96a8d73c5f9843f871db89713518ba4d4791afb413d2d5d112b12b0a9fd4801` = manifest | yes |

Receipt line 3 of the log, read in full: `Entry-check receipt v2: books-arranger v0.31.0 @ a8b6804a013b643412c72aedf34f1e7e00de1455 (dirty: N) [source/harness/runtime/checker pins] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a; personal-folders clean`. The log also shows Node `# tests 279 / # pass 279 / # fail 0`. The Python count (3,150) is not readable as plain text in the log; taken from the hand-over.

Note for Jane: the worktree `ender-031` moved on while I tested (HEAD `e961288` and `0375cb3`, after `a8b6804`; files such as `series_backfill.py`, `book_move.py` newer than my start). I did not touch it. I tested only the packaged build whose hashes match above, so this report covers that build and nothing after it.

## 2. How it was run, and one limit

- **Lane A, the real shell.** Unpacked exe, my own `--installation-config` (all folders under `futaba-031\A`), `--roots-json`, port 5231, `--show-inactive`, `--quiet-errors`. It started, showed its window without focus, and the page title read `Books Arranger: continues by itself` / `waiting for you` as the state moved (read from the OS window title of my own process only). The close button hid the window to the tray with the process and engine still up (the recorded tray exception); a second instance with `--quit` (the tray's Quit) ended the shell, the host python, the engine and the helpers within about 6 s, port closed. Sergei's four `Books Arranger.exe` and his two python PIDs, and port 5210, were unchanged at the end.
- **The limit.** The shell ignores `audiobook-sources.json` when `--roots-json` is given (`desktop/main.js`: `audiobookOutputRoot=(!isDev && !rootsJson)?…:null`), so in a `--roots-json` shell run there is no Audiobooks Sorted folder and automatic processing can never start ("No sorted output folder is set"). The finished-book flows (items 3 and 4) therefore ran in:
- **Lane B and C, headless, same build.** The packaged python and packaged `resources\backend` code, started by my own launcher with `--audiobook-output-root`, own data folder, ports 5232 and 5233, no window. The page was read through a headless Edge on my own profile folder (no window, no focus, no mouse; `document.title` and `innerText`, so hidden elements are not counted). The network was real (Wikidata, FantLab and Goodreads answered; DuckDuckGo answered with a human check). To make a finished book that the online look-up had not yet touched, I converted some books with a dead proxy (engine restarted with `HTTPS_PROXY` to a closed port) and then restarted with the network on.
- Fixtures: copies of `ba-mp3-fixture/fixture.mp3` cut to 20 to 40 s clips, with tags set by the packaged ffmpeg (ID3v2.4), plus two m4b volumes built from the same clip. Originals untouched.

Counts and method: candidates counted from `GET /api/inventory?view=candidates` `total` (14 after the first scan of lane B; 18 source files); finished books counted from the Audiobooks Sorted tree (21 files at the end, one of them my own decoy file, so 20 converted) and `converted_total` in `/api/state`.

## 3. What was checked, by the brief's items

1. **Series from the file's own tags, no shared destination.**
   - Pass: sort-album/grouping "Series. Книга N" on files of a book filed it by itself with no question: `Тестовая сага` 1 and 2 → `Тестов Иван\Тестовая сага\Тестовая сага - N - …`, row suffix ` · from the file's tags`.
   - Pass: title tag `Sprawl Trilogy 01 - Neuromancer` → `Gibson William\Sprawl Trilogy\Sprawl Trilogy - 1 - Neuromancer - Gibson William.m4b`, suffix ` · from the title tag`, no question.
   - Pass, Sergei's Sprawl report (two m4b volumes `02-Граф Ноль.m4b`, `03-Мона Лиза овердрайв.m4b`, shared album "Sprawl Trilogy", own title tags): the app separated them and filed `…Sprawl Trilogy - 2 - Count Zero…` and `…- 3 - Mona Lisa Overdrive…` beside Neuromancer. No shared destination.
   - Pass: two different recordings with one title and author: the second is held `Same name as another book` ("A book with this name is already in Audiobooks Sorted"), Approve disabled with `That name is already in Audiobooks Sorted. Change the title or author.` The first was already converted (known, left as it works today).
   - Observation (not a defect against the scope text): the same Sprawl shape as **mp3** files (`02-`/`03-` prefixes, or no prefixes, different sort-album numbers) stays one candidate: `Missing files — part 1 isn't here` with `Convert what's there` and one destination `Sprawl Trilogy - Gibson William.m4b`, or `Held — Playback order uncertain`. The tags' own "Книга 2" and "Книга 3" are not used there because the files disagree. If Sergei's real Sprawl files are mp3, this release does not help him.
2. **Translated books get English title and English series folder; Russian originals stay Russian.**
   - Pass: `Лю Цысинь\Тёмный лес` → `Liu Cixin\Remembrance of Earth's Past\Remembrance of Earth's Past - 2 - The Dark Forest - Liu Cixin.m4b`; row reads `English title found on FantLab.` and `Series: Remembrance of Earth's Past · No. 2 · found on FantLab · English name from Wikidata`, as the spec words it.
   - Pass: Lukyanenko "Ночной дозор" → `Лукьяненко Сергей\Дозоры\Дозоры - 1 - Ночной Дозор - Лукьяненко Сергей.m4b` (Russian stays Russian, `found on Goodreads`).
   - Pass: a book waiting on a source reads `Waiting for an online answer`; hint `No online answer yet about its series. Try 2 of 3 at 17:58. Nothing to do.`; stopped automatic: `…Press Resume automatic processing to try again.` and a button of that face is on screen; Waiting item `Waiting for an online answer: 2 books / Next try 17:58. After 3 tries a book converts with the names from its files.` The end of the wait (3 tries) was not reached.
3. **"All done" and named jobs.**
   - Pass (positive control, lane C): two series-tagged books converted, no look-up owed: after about 4 min `All done · 0 need attention · 2 converted out of 2 approved books`, window title `Books Arranger: all done`, `Nothing is running, queued or waiting.`, Running, Waiting, On hold and the Waiting-for-you block all empty.
   - Pass: add one book needing attention → badge and title `waiting for you` with `Review them`. Approve it with a typed author, it converts, its series look-up is deferred → `Background look-ups only · … · 1 background look-up left`, title `background look-ups only`, Waiting item `Finding series for finished audiobooks: 1 book / Waiting for online sources. Next try 00:40. No file is changed.` With both at once the badge is `Waiting for you` and the look-up item stays (lane B).
   - Pass: audiobook jobs paused → `Paused · 3 books waiting to convert`, title `paused`.
   - Pass (static, packaged `web/app.js`): none of `recorded and stay where they are`, `No audiobook is renamed or moved`, `next version`, `Series found for`, `Review changes`, `Leave as it is`, `Renames and moves`, `Offer again`, `Left as they are`, `Convert now` is present; `Finding English titles and author names`, `This look-up changes no file` and the series tooltip sentence are. `Nothing running` appears only inside `Nothing running that could be read`.
   - The page at 600 px wide (lane C, screenshot): no overlap seen. Other widths, zoom and keyboard not checked.
4. **Finished books filed by the rules.**
   - Pass: a flat finished book with a series found by a source is filed by itself, no question: `Задача трёх тел` → `…\Remembrance of Earth's Past\Remembrance of Earth's Past - 1 - Задача трёх тел - Liu Cixin.m4b` (Goodreads); `Гарри Поттер и философский камень` → `Rowling J. K\Harry Potter\Harry Potter - 1 - …` (Wikidata) with the author folder fixed.
   - Pass, the record: `Renamed or moved by the app · 2 · last 23 Nov, 18:29`; opened, newest first, each entry `Title · Author · date · Series: … · No. n · found on <source>` (and `· Author folder: …`), `Was in` / `Now in`, `Show in list`; the help line and `Find book` are as specced.
   - Pass, the could-not list: I put a file at the exact target of a book the rules wanted to move. The book stayed, my file was not touched, and `Could not be renamed or moved · 1` opened to `Now in …`, `Would be in …`, `A file with that name is already there.`, `Show in list`, under the record. The badge and state were not changed by it. The summary is hidden at zero. The same book also appears in `/api/filing/could-not` with key `name_exists`.
   - Pass, files after a rule write (`Задача`, `Гарри Поттер`): decoded audio packets md5 identical before and after (`706a300b…`, `788f6936…`); chapters kept (2 and 2, "Track 01/02", same times); cover kept (png attached picture); `ffmpeg -f null` decodes with no error; album/sort_album/grouping/artist tags rewritten.
   - Not seen live: R26's row of a rule-queued move (no `Cancel`, `Choose folder…` disabled with the tooltip). Static check only: the tooltip sentence is in the packaged `app.js`. My one capture caught the book while the engine still counted it as a move that then became the could-not entry above.
5. **Doubtful series no longer ask.**
   - Pass: title `Хроники Тестера 3. Ночной полёт` (series-and-number shape) is queued and converted with no `Title unclear`, no fields, no Approve; filed under its whole title, no series.
   - Pass: Foundation: Wikidata answered "Foundation series; Foundation Trilogy" and the engine dropped it as `several_series`; the book shows nothing about a series.
   - Pass: Latin author `Jiang Wei Long` (not orderable) filed as written, no question.
   - Controls still ask: two credited people (`Author unclear`, choices), bitrate-shaped title `Тестовая повесть 128` (asked; see Minor 5 for its name).

## 4. Findings

### Blocker
None.

### Major

**M1. After "Stop automatic processing" the status line, badge and window title say "Checking what is left", not "Paused".**
- Repro: start automatic processing, let it settle with some books held or waiting, press Stop automatic processing. The page says `Automatic processing: Paused` and `Resume automatic processing`, the engine's `work.state` is `paused`, but the Audiobook jobs line reads `Checking what is left · 4 need attention · …` and the window title `Books Arranger: checking what is left`, still the same 60 s and longer after.
- Cause (packaged `web/app.js`, `jobsFirstPart`): `Paused` is shown only when the audiobook queue itself is paused (`jobs.state`); the engine's `paused` falls through to the last line, `Checking what is left`. The UX table 1.1/1.5 says engine `paused` shows `Paused` / title `paused`.
- Why Major: the whole point of 0.31.0 is honest status, and here a user's own Stop is described as the app working out what is left, in the taskbar, with nothing counting. Audiobook jobs paused via the Pause button reads correctly (checked).
- Status: open.

**M2. "All done" will not show on the day a standalone book is converted; the usual wait is 12 hours or more.**
- Seen: every finished book with no series on FantLab, Goodreads and Wikidata (`Jiang Wei Long`, `Повторная книга`, `Ночной полёт`, later `Дюна`, `Основание`, …) is left `deferred` in the series ledger because the two DuckDuckGo-backed sources (publisher, Litres) answer "Public source presented a human check; no bypass attempted"; next try 6 h later, 3 tries per source (R9) → at least 12 h before the look-up gives up. During that time the badge is `Background look-ups only` or `Waiting for you`, with `N background look-ups left`. At the end of lane B: 9 books between tries, all with next try ≈ 6 h out.
- It is honest, and it is R9 as Sergei approved it. But it is the direct answer to his question "how do I know the app finished?": for any newly converted standalone book the answer is "not for half a day". Not a defect of the build; a product consequence for Sergei and Jane (accept, or ask Ender whether a source that only ever returns a human check should count as no answer on the first try).
- Status: open, disposition needed.

### Minor

1. `Checking what is left` lasts about 4 min after the last conversion (lane C: converted at once, badge came up after about 4 min); the spec says about 2 min.
2. With no Audiobooks Sorted folder set (lane A) the state sticks on `Continues by itself` for good, because the "still checking" books wait for an automatic processing that cannot start. Only a degraded configuration; the line should not promise.
3. The author name written into the file loses its final period: typed `Rowling J.K.` became folder and embedded `artist`/`album_artist` `Rowling J. K` (the folder-safe form went into the tags). The name inside the file should be the name, not the folder spelling.
4. Text on the automatic panel after a pass: `Automatic pass complete — 4 converted · 0 held Background look-ups continue.` has no separator between "held" and "Background".
5. The same bitrate-shaped hold has two names: the list status reads `Held — Title or author missing` (title clue `01`) while the attention list card reads `Title unclear · The title ends with a number that looks like a bitrate.` Probably older than 0.31.0; not compared with 0.30.
6. Approving a book while automatic processing is idle (lane C, both the direct call and the page's queued call) leaves the audiobook queue `Paused queued 1`, with the page and title saying paused, until `Resume audiobook jobs`. I did not press Pause. May be long-standing; not compared with 0.30.

## 5. Not verified (say so plainly)

- **R27, English-title rewrite of a finished book (title and author inside the tags and in the app's list).** No finished book ever got a recorded English title in this session: the detail look-up covers only books whose manifest has `gap_search.background` (read in `gap_fill.py`), and my books approved before any research ran have none (`gap_fill` showed `done 8 / total 8, found 0`; the Foundation, Harry Potter and Three-Body books were never in it). So `Основание`, `Задача трёх тел` and the Harry Potter books kept their Russian titles. What I verified instead is the same write step with `written: ["series","author"]`: audio, chapters, cover and decode intact (item 4). Consequence worth knowing: a translated book approved by hand before online research ran is never offered an English title later (a second recording of the Three-Body book, converted by automatic processing after research, did get `…1 - The Three-Body Problem…` and now sits beside the Russian-titled one). Whether that is by design is Ender's to say.
- R26 live row; the 3.3a notice (needs more than 5 finished books to file at once); the record's 200-entry cases; Quit during a backlog and the next launch.
- Doubtful shapes: a number that disagrees with FantLab (FantLab answered "unavailable" for that book), `Sources disagree` about a series only, `Series and standalone evidence conflicts`, `Series membership has conflicting author credits…`.
- The end of an online wait after 3 tries (tries are minutes to hours apart); R14 a drive not answering; layouts other than 1280 and 600 px, 200% zoom, keyboard use of the record; the tray menu by mouse (I used the same Quit by command), the set-up window.

## 6. Pattern alerts

**P1 (new, disposition proposed: fix).** `Checking what is left` is the page's fallback for any engine state it has no words for. It appeared for: the engine really counting (intended), engine `paused` after Stop (M1), a degraded configuration that can never finish (Minor 2), and for about 4 min instead of 2 after a conversion (Minor 1). One honest sentence per state, and `paused` mapped, would close the family. Jane to disposition: fix, accept or defer.

## 7. Personal-folder listing (list only; nothing deleted or moved)

Files or folders in Sergei's personal folders newer than my start (17:36): `Downloads` (the folder's own timestamp only; no file inside is newer), `Pictures\Screenshots\Screenshot 2026-11-23 174248.png` (17:42; not mine, my captures went to my own folder through a headless browser). `Desktop`, `Documents`, `Videos`, `Music` and `%LOCALAPPDATA%\Books Arranger`: nothing newer. Nothing written in the worktree, `q031*`, Sergei's installed copy or Data folder, `Z:\` or port 5210.

## 8. Disposal

Closed: lane A shell tree, lane B and C engines (by the app's own quit and shutdown; ports refused), my headless Edge instances. `futaba-031\` is deleted at the end of this pass; this report is the only thing left.
