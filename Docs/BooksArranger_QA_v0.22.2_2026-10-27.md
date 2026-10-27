# Books Arranger 0.22.2 - lean QA on candidate 7dcb4bc (Futaba)

Pass run 2026-10-27, about one hour. Tester: Futaba. Behavior only; construction is Senua's. Lean verification (ProcessRules, Lean verification, including item 7): I did not re-run the entry check; each changed behaviour was checked once, plus a short smoke. Sergei was at the machine: no mouse, keyboard, tray click or focus. Everything ran headless or in a hidden window, in a private profile, a private LOCALAPPDATA, APPDATA, TEMP and USERPROFILE, on ports 5231 to 5233 and random free ports (never 5210 or 5212). Sergei's profile, live data and Z: were not touched. No outbound network: the engine ran through a driver that fails every non-loopback name lookup.

Release source commit: 7dcb4bc1c6217406c883c91bc87397630a9e2fe5
Release artifact manifest SHA256: 3b7d119897d2a1d422f93c3a54b7d4f8214c0bbc3231cc8b47269944e940128a

## Result in plain words

- **GO as scoped. Blockers: 0. Majors: 1 open (M-1). Minors: 1 new (m-1). Data loss found: none. Pattern alerts: none.**
- **M-1 is the one to decide on.** Answering the app's own "which spelling of this author?" question with the Cyrillic spelling still files the book under the Latin one (ruling 33). It is not a Blocker by the vocabulary ruling (the scan, approve, convert flow works and nothing is lost), but it is a changed behaviour that does not work end to end, and it regresses a path I verified on 0.22.1. Jane and Sergei can ship with it, or batch it first.
- Passed: the updater's failed install, the queued busy presses, Edit names, the delete, the identity cases, both Xtra boxes, the slow media check, the first-run window, and the smoke test.

## 1. Build identity (compared by hash, entry check not re-run)

- Installer `cand-0222b/dist/builds/6d611429-0003-4a2a-bfd3-d2f71cb7025c/Books-Arranger-Setup-0.22.2.exe` SHA-256 `3ace03a087a014ae91eb0a4a556938e1c3728e7d0ff26b9fa4602b3b3a3e883a`: equals the handoff.
- Manifest `cand-0222b/dist/release-artifacts.json` SHA-256 `3b7d119897d2a1d422f93c3a54b7d4f8214c0bbc3231cc8b47269944e940128a`: equals the handoff. `payload.verified` and `payload.installer_equivalent` are true, shell and backend 0.22.2.
- `cand-0222b` HEAD `7dcb4bc1c6217406c883c91bc87397630a9e2fe5`, 0 changed paths.
- Ender's receipt, last line of `qa-run-0222b/logs/ender-entry.log`: `Entry-check receipt v2: books-arranger v0.22.2 @ 7dcb4bc1c6217406c883c91bc87397630a9e2fe5 (dirty: N) ... check pass`. Receipt reads `check pass`, dirty N.
- Payload extracted from the installer with the repo's pinned 7-Zip (SHA-256 `b0cfdeaf429f5cc53f85123dd8f5a5feb92c19d31aa34df257edf9a26be05f95`, the same as in my 0.22.1 pass): **292 of 292 files hash to the manifest** (0 missing, 0 mismatched, 0 extra); `resources/backend/VERSION` reads 0.22.2. The installer was not run (Sergei has Books Arranger installed); every check ran from the extracted payload.

## 2. Method and limits

- Engine: the packaged `python.exe -I -B` with the packaged backend, started through a small driver that only blocks non-loopback DNS. One extra stand-in, for the slow media check only (section 3, item 8): the same driver with the media deadline set to 0.
- Shell: the packaged `Books Arranger.exe`, hidden, driven over DevTools, with the repo's own fake-GitHub method (self-signed HTTPS, host rules), the same way the repo's PA-1 test drives its source-built copy.
- Fixtures: real tagged M4B files made with the packaged FFmpeg in the live folder shapes of the repo's `test_live_cases_0222.py` and `test_identity_0222.py`; 19 named books and 120 fillers (139 files).
- Presses are sent in the page's own request form (`queue: true` and the page's fields, read from `web/app.js`). A bare call without `queue: true` is the old refusing form the page no longer sends.
- **Probe that failed and was replaced:** my first first-run probe read `document.visibilityState` and said `visible` for both `--start-hidden` and the `--show-inactive` control, so it could not tell them apart and I discarded it. The OS window title of the shell process (`tasklist /V`) does: `N/A` hidden, the form's title shown in the control (item 9).
- **Lab slip, not a finding:** my first lab used forward-slash roots. The engine's sibling lookup then fails closed and every book reads "One part of a bigger book". Sergei's roots are Windows paths with backslashes; I redid the lab with those.
- **Fixture slip, not a finding:** my first rating-box fixture wrote the 8-byte rating big-endian. The engine refused it ("Unsupported structural box"), correctly: Windows writes it little-endian and the engine reads it that way. This is also a seen-to-fail control for the rating gate (verified fails on a big-endian rating). The fixture was rebuilt little-endian.

## 3. Changed behaviours, each checked once (packaged 0.22.2)

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Updater: a failed install keeps the app open | **Pass** | Packaged shell, hidden. Positive controls first: the real updater read the fake feed (0.22.3 available), downloaded and verified sha512. Update now with an installer Windows cannot start: phases starting, pausing, installing, then `failed` with cause `installer_blocked` **2.1 s after the press**; the shell was **still running 6 s later**; the old engine answered again (health version 0.22.2); the update was still ready (`ready: true`, available 0.22.3). A second copy with `--quit` ended the shell in 0.6 s. Not read: the tray tooltip and the Install line's path text (the tray is not readable headless; the status object carries no tooltip). |
| 1b | Updater: Cancel answers at once | **Pass on the answer; see m-1** | `cancelUpdate()` pressed at phase `pausing`: answered `true` in **1 ms**, twice. Not run: Cancel with a conversion or approval running and the "slow to resume" line. |
| 2 | Busy presses queue | **Pass** | A scan pressed while automatic processing ran: 202 `queued`, blocker `automatic`, listed in `queued_actions`. During a scan: **Approve, Save names, Delete book and Retry** each answered 202 `queued`, blocker `scan`, positions 1 to 4 in `queued_actions`. Cancel on the queued Retry answered `cancelled` and the list shrank to approve, names, delete. The other three ran to `done` after the scan ended (queue outcomes). The packaged backend holds the words "Another operation is in progress" only inside code comments; every "not accepted" text carries its reason (no bare one). Not run: how the page draws the queued face and its Cancel button (needs a browser). |
| 3 | Edit names: saved, survives a rescan | **Pass (engine)** | Book `Анна Орлова\Пртоколы SCP 1.m4b`: Save queued then `done`; `entered` lists title, series, number; Goes to `Орлова Анна\Протоколы SCP\Протоколы SCP - 1 - Протоколы SCP 1 - Орлова Анна.m4b`; after a full rescan identical. Control, another author's book with the same text: unchanged, `Седов Олег\Пртоколы SCP 1 - Седов Олег.m4b`, `entered` empty. Not proven: "Applies to N books" over separate books (my three files read as one three-part book, so it applied to 1). |
| 4 | Save shows Saving…, then Saved | **Not run in a browser** | Page text. Engine side: the Save press answered 202 and finished `done`. The strings are in `web/app.js` (lines 778, 813, 2998). |
| 5 | Delete: the row leaves at once | **Pass (engine)** | A book with all files missing: Delete book preview during a scan answered `blocked: scan`; the Delete press queued; after the scan the book is **not in the candidate list**. The page's own removal is not run in a browser. |
| 6 | Identity | **Pass, except M-1** | See the list below. |
| 7 | Boxes: the empty Xtra box and the Explorer-rating box | **Pass** | Both books approved and converted (state `verified`). Decoded audio MD5 of both outputs equals the template they were remuxed from (`a5cce5e966d9eb19be4b1e8fd189e9de`; the sources are removed after conversion, so the template is the reference). The live moov/udta of the output holds no Xtra box; the old bytes sit inside a dead `free` box left by the in-place rewrite (observation). |
| 8 | Media retry: a slow check retries, not Needs you | **Pass (stand-in)** | Every owned media call with a deadline of 60 s or less was given deadline 0, on a one-book library. The row went to **"Waiting for source"** with "The library drive answered slowly while the app checked this book. It tries again automatically." and a scheduled retry about 2 minutes out; never Held or Needs you. Control: the unpatched engine converts the same kind of book. Not run: waiting through the 2, 4, 8 and 16 minute ladder and the hold at the fifth. |
| 9 | First-run window: `--start-hidden`, `--quit` | **Pass** | `--start-hidden` with no saved data folder: window title `N/A` at every 0.5 s sample for 4 s. Positive control `--show-inactive`: title "Books Arranger - Choose data folder". `--quit` from a second copy: **0.1 s**, both processes ended, 0 left (two runs, plus the ready-state run in item 1). |
| 10 | Smoke: scan, approve, convert, verify | **Pass** | Scan of 139 files: 20 and 22 s, 0 errors. Automatic processing researched all rows offline; first pass approved 11, converted 10, and refused 1 (the wrong-endian fixture above). The rebuilt rating book was approved (queued during a scan) and converted. **14 outputs in Sorted, 0 decode errors** (`ffmpeg -f null`). Engines closed their port in 1.05 s and 0.32 s after the quit call. Closing the app: `--quit` ended the shell from the ready state and from the first-run form; the window's X button and the tray's Quit item are real input and were not run. |

### Item 6, identity (each in the packaged engine; converted unless noted)

- **Вселенная Дозоров:** `Вселенная Дозоров\Межавторский цикл\Межавторский цикл - 16 - Севастопольский дозор - Недоруб Сергей.m4b` and `... - 27 - Дозоры. Запах Сумрака - Пылаев Валерий.m4b`; the unnumbered book `Вселенная Дозоров\Корона - Каплан Виталий.m4b`. Converted.
- **Ruling 29, waiting for an English title:** Голиаф, Левиафан, Мизери and Джек из Тени all sit at "Waiting for source" and none is converted; Approve's preview for each is the Russian-title path, so Approve ends the wait. I did not read the row's hint sentence.
- **Latin names surname-first:** `Matheson Richard\I Am Legend - Matheson Richard.m4b` (converted). `Ilya Marchenko` previews as `Marchenko Ilya`; a Latin credit with a Russian title is asked "Author unclear" (`name_language`) with both spellings, `Marchenko Ilya` and `Марченко Илья`. **A Russian-writing author in Cyrillic: see M-1.** (Russian credits do file in Cyrillic: `Петров Иван\...`, `Иванов Пётр\...`, `Орлова Анна\...`.)
- **Желязны to Zelazny:** the Cyrillic credit `Роджер Желязны` in a `Roger Zelazny` folder previews `Zelazny Roger\Джек из Тени - Zelazny Roger.m4b` (the row waits for its English title).
- **1408 to King Stephen:** artist tag `sk 1408` in `Stephen King\1408.m4b`: `King Stephen\1408 - King Stephen.m4b`. Converted.
- **Shirley Jackson:** `Jackson Shirley\The Haunting of Hill House - Jackson Shirley.m4b`. Converted.

## 4. Findings

### Blocker (0)

### Major (1)

- **M-1. Choosing the Cyrillic spelling for a Latin-credited author is ignored; the book is filed under the Latin spelling.** Repro: `Unsorted\Ilya Marchenko - Zvezda.m4b` (tags: title «Звезда», artist `Ilya Marchenko`). The row asks "Author unclear" and offers `Marchenko Ilya` and `Марченко Илья`. Approve with the author set to `Марченко Илья` (what the page sends when that radio is chosen: `values.author`, `web/app.js` line 2517) queues, converts, and files `Marchenko Ilya\Звезда - Marchenko Ilya.m4b` (seen in Sorted). The Goes to preview says the same before the press. Controls on a second book with the same credit: a typed `Иван Петров` files `Петров Иван\...` (typed values are honoured), but typed `Марченко Илья`, `Илья Марченко`, `Ilya Marchenko` and `Marchenko Ilya` all file `Marchenko Ilya\...`. So the explicit answer to the app's own question has no effect, and the second book by the same credit stays asked and previews Latin. **Regression:** on 0.22.1 I verified that typed «Марченко Илья» filed `Марченко Илья\Звезда - Марченко Илья.m4b` (0.22.1 report, M-2). Ruling 33 says a Russian-writing author is filed in Cyrillic; the repo's tests assert the question and the join to an existing Cyrillic folder, not that the Cyrillic answer is used. No data loss (the book converts and verifies; only the folder name is wrong). My reading, flag only: the folder is resolved from the person's canonical spelling after the typed value is read.

### Minor (1 new)

- **m-1. Cancel update, pressed during the first second, is acknowledged but the install goes on.** Repro (2 of 2): packaged shell, idle engine, update downloaded; press Update now, then Cancel at phase `pausing`. `cancelUpdate()` returns `true` in 1 ms, yet the flow continues to the installer and ends `failed / installer_blocked` (with a real installer it would quit and install after "Cancelling"). `canCancel` is true in `starting`, `pausing` and `forcing`; `cancelRequested` is set; the park step apparently does not read it again once the engine is idle. A window under one second; not tested with a conversion or approval running (where the wait is long and Cancel matters most).

### Observations, not defects

- The dropped Xtra bytes remain in the output file's `free` padding after the in-place rewrite; there is no live Xtra box. Harmless.
- The wrong-endian rating fixture was refused as "Unsupported structural box" with no way for Sergei to see why; the real Windows rating is little-endian and passes.

## 5. Not run

- **Real-input checks: not run (Sergei present).** Every real click, the window's X button, the tray's Quit item and tray tooltip, the real Edit names editor typing.
- Page text and drawing, which need a browser: Saving… then Saved, the queued face and Cancel button on a row, the deleted row leaving the page, the editor's layout (Judy's list item 13), the "Applies to N books" line.
- The real NSIS install, the real installer's silent install, Restart to update with a conversion and an approval running (the confirm's approval line), Cancel update with work running, the slow-resume line, and the 2/4/8/16 minute media-retry ladder with its fifth-in-a-row hold.
- Speed or large-catalog checks (not asked; lean rule).

## 6. Disposal

All of my output lived in `%LOCALAPPDATA%\Temp\baqa22` and in this session's scratchpad. Both are removed with the studio sweep at the end of the pass; the Windows tray-icon record for the extracted exe was removed by the shell test itself. This report is the only file left, uncommitted.

## 7. Pattern alerts

Pattern alerts: none.

**Verdict:** GO
