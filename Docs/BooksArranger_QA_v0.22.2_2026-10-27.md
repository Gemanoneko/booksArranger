# Books Arranger 0.22.2 - final delta QA on candidate 4b9fdba (Futaba)

Pass run 2026-10-27 on candidate 4b9fdba, checking only the delta 7dcb4bc..4b9fdba and carrying over the rest of my 7dcb4bc report. Tester: Futaba. Behavior only; construction is Senua's. Lean verification (ProcessRules, Lean verification): I did not re-run the entry check; each changed behaviour was checked once, plus a short smoke. Sergei was at the machine: no mouse, keyboard, tray click or focus. Everything ran headless or in a hidden window, in a private profile, a private LOCALAPPDATA, APPDATA, TEMP and USERPROFILE, on ports 5231 to 5236 and random free ports (never 5210 or 5212). Sergei's profile, live data and Z: were not touched. The installed Books Arranger on his machine kept running throughout and was not touched.

Release source commit: 4b9fdba5ebf3a3825348e118b1b44918af9b9cca
Release artifact manifest SHA256: 9c7867859a47800b70c67844b66870bd4fe97b6cec5047bbc9b620497fe5c37d

## Result in plain words

- **GO. Blockers: 0. Majors: 0 open. Minors: 1 new (m-2, carried over from 7dcb4bc, not caused by the delta). Data loss found: none. Pattern alerts: none.**
- Both items I raised on 7dcb4bc are closed: **M-1** (his Cyrillic answer is now used: «Марченко Илья» files under Cyrillic) and **m-1** (Cancel in the first second really cancels, checked at both `starting` and `pausing`, 2 of 2 each).
- Senua's M1, M2 and M4 and rulings 38 and 39 all behave as the briefs say in the packaged build.
- One thing for Jane to decide, not a gate: m-2 below (a cached FantLab record gives an English title but leaves a Cyrillic author folder).

## 1. Build identity (compared by hash, entry check not re-run)

- Installer `cand-0222c/dist/builds/4f1680bc-4970-4273-aa32-41970cd702cf/Books-Arranger-Setup-0.22.2.exe` SHA-256 `e19fefe1fcf747ff0c7f72144f8d18dcc96e8a09f66a51ef97b69f744cb4f4ab`: equals the handoff.
- Manifest `cand-0222c/dist/release-artifacts.json` SHA-256 `9c7867859a47800b70c67844b66870bd4fe97b6cec5047bbc9b620497fe5c37d`: equals the handoff.
- `cand-0222c` HEAD `4b9fdba5ebf3a3825348e118b1b44918af9b9cca`, 0 changed paths.
- Ender's receipt, last receipt line of `qa-run-0222c/logs/ender-entry.log`: `Entry-check receipt v2: books-arranger v0.22.2 @ 4b9fdba5ebf3a3825348e118b1b44918af9b9cca (dirty: N) ... check pass`. Reads `check pass`, dirty N.
- Payload extracted from the installer with the repo's pinned 7-Zip (SHA-256 `b0cfdeaf429f5cc53f85123dd8f5a5feb92c19d31aa34df257edf9a26be05f95`, the same as in my earlier passes): **292 of 292 files hash to the manifest** (0 missing, 0 mismatched, 0 extra); `resources/backend/VERSION` reads 0.22.2. The installer was not run; every check ran from the extracted payload.

## 2. Method and limits

- Engine: the packaged `python.exe -I -B` with the packaged backend and FFmpeg, started through a small driver. Fixtures are real tagged M4B files made with the packaged FFmpeg, in Windows-path library roots with a separate Sorted folder. Presses are sent in the page's own request form (`queue: true` and the page's fields).
- **No outbound network:** the driver makes the research client's name resolution fail (the client resolves names in a child Python, so the block is applied to that resolver). Positive control: with it, one lookup per source was attempted and failed at the resolver (FantLab, Wikidata, Goodreads: 1 each, all "Public source unavailable").
- **Lab slip, not a product finding:** my first identity run blocked name lookups only inside the engine process, which the research client does not use. Two GET requests reached the public FantLab API for the made-up title «Голиаф»; nothing of Sergei's was sent. I fixed the driver, threw that run away and redid the whole identity lab offline. The only thing I kept from it is the observation under m-2.
- **Stand-ins:** (a) for M4 only, the driver makes the engine's `approve_book` or `delete_book` sleep 7 s first, so an admission stays open (a real Delete or Approve is too fast to catch headless). (b) For the cached-name case only, two FantLab answers were written into the engine's own research cache table, the way a fetched answer is stored. (c) For m-1, the repo's own fake-GitHub method (self-signed HTTPS, host rules) against the packaged shell in a hidden window, driven over DevTools.
- **Control run:** the 7dcb4bc source (`git archive`) on the same packaged Python, for m-2 only.

## 3. The delta, each item checked once (packaged 4b9fdba)

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Senua M1: a correction for "01" or "Книга 1" no longer touches «1408» or "Книга 12" | **Pass** | King, three books: "01", "01 (second edition)", «1408». Preview with title "Misery": `applies` 2; Save: `applies` 2; after: both "01" books read "Misery", «1408» still "1408". Глуховский: "Книга 1", "Книга 1 (другое издание)", "Книга 12": `applies` 2 both times; after: "Первая книга" twice, "Книга 12" unchanged. Still the same after an engine restart and a full rescan. |
| 2 | Senua M2: typing the original text clears the fix; no older fix comes back | **Pass** | "01" saved as "Misery", then "Second", then the files' own "01": the book reads "01", `entered` empty, `remembered` empty, basis "tag" (not "Misery" or "Second"). The other book of the author keeps "Second" (press B's fix still reaches it). Then "Third" in force; Forget of "Third" goes back to "01", not to an older value. |
| 3 | Senua M4: a queued scan waits while a Delete or Approve runs | **Pass (stand-in)** | Approve (the queue worker's run) and Delete (the request's run), each held open 7 s. Scan pressed 1.6 s in: 202 `queued`, blocker `operation` (both). 4 s in: scan state unchanged (generation 1, then 3), `queued_actions` lists the scan with `operation`. After the Approve and its conversion ended, and after the Delete (row removed, the other book untouched), the queued scan ran (generation +1, outcome `done`). Without the stand-in, an Approve pressed alone gets blocker `jobs` once its conversion starts, which is the older path. |
| 4 | My M-1: «Марченко Илья» files under Cyrillic | **Pass** | `Unsorted\Ilya Marchenko - Zvezda.m4b` asked "Author unclear" (`name_language`, candidates "Marchenko Ilya" and "Марченко Илья"). Preview with typed «Марченко Илья»: `Марченко Илья\Звезда - Марченко Илья.m4b`; Approve; the file in Sorted is exactly that (positive control: the same preview with no typed author reads `Marchenko Ilya\...`). Control, second book by the same credit, typed "Ilya Marchenko": previews `Marchenko Ilya\Луна - Marchenko Ilya.m4b`. |
| 5 | Ruling 38: no "Waiting for the original title"; a translation with no English title converts at once, author folder English | **Pass** | `Roger Zelazny\Джек из Тени.m4b` (Cyrillic credit «Роджер Желязны») and `Девять принцев в Эмбере` (Latin credit): both converted in the first automatic run to `Zelazny Roger\<its own title> - Zelazny Roger.m4b`. No row carries "original title" in its status, reasons or wait; none listed under Held. The packaged page (`web/app.js`) no longer holds the string. Observation: `original_titles.py` still holds the dead constant text; no code shows it. |
| 6 | Ruling 39: a Cyrillic-only foreign author with no English name found gets Judy's question | **Pass** | Offline, «Скотт Вестерфельд» (Голиаф, Левиафан) and «Томас Квелл» (a second author): Held, "Author unclear"; the to-do row carries `kind author_unclear`, `why english_spelling`, one candidate (the Cyrillic name, source `spelling`), `odd_name` true (never in a bulk Approve), proposed author still Cyrillic, nothing transliterated. Research tried FantLab, Wikidata and Goodreads first. The packaged page holds the hint ("The app found no English spelling of this author's name online. Type one under Other, or keep this name if the author writes in Russian.") and shows the tag "Russian spelling" for that question's one candidate (`app.js` 2429 and 2570). Not read: how the page draws them (needs a browser). |
| 7 | Ruling 39: typing the English spelling files it there and is a rule for the next book | **Pass** | Approve «Голиаф» with typed "Scott Westerfeld": `Westerfeld Scott\Голиаф - Westerfeld Scott.m4b`; rule `same_as` "Westerfeld Scott", actor `user`. The other book of the credit previewed `Westerfeld Scott\Левиафан - Westerfeld Scott.m4b` before any rerun and, after a rerun of automatic processing, converted there with no question. |
| 8 | Ruling 39: a cached English name found files under English | **Pass for a rule or the library's English spelling; see m-2 for a cached FantLab record** | A name already in the library or a rule files English (items 5 and 7). A cached FantLab record is the one case that does not: m-2. |
| 9 | My m-1: Cancel in the first second really cancels | **Pass** | Packaged shell, hidden, fake GitHub. Positive controls: the real updater read the fake 0.22.3 feed and verified the download. Update now, then Cancel from the page the moment the phase is `starting` (answered `true` in 16 ms) or `pausing` (the window of the old defect; answered `true` in 145 ms): phases `starting` or `pausing`, then `cancelled` (cause `cancelled`), **never `installing`**, no "Installer did not start" in the shell output, the old engine answers again (health 0.22.2), the update is still ready. 2 of 2 at each phase. |
| 10 | Smoke | **Pass** | Scan, automatic processing, Approve, convert, verify through the packaged engine over three labs: 9 outputs in Sorted in the identity lab plus 3 and 2 in two smaller ones, **0 decode errors** on the 9 (`ffmpeg -f null`). Engines quit through the quit call in 0.3 to 0.9 s and freed their port. The shell's `--quit` from a second copy ended it in 0.5 to 0.7 s in three runs. No process or tray-icon record of mine is left. |

## 4. Carried over from the 7dcb4bc report

Re-run because the delta touches the same files:

- **Updater: a failed install keeps the app open** (the delta edits that branch): shell still running, phases `starting, pausing, installing, failed`, cause `installer_blocked`, old engine answers, update still ready. Pass.
- **Edit names saved and survive a rescan**: pass (item 1 above, after restart and rescan).
- **Delete: the row leaves the list**: pass (item 3: row gone, the other book kept).
- **Identity cases through the engine**: `Jackson Shirley\The Haunting of Hill House - Jackson Shirley.m4b`, `King Stephen\1408 - King Stephen.m4b` (tag `sk 1408`), `Matheson Richard\I Am Legend - Matheson Richard.m4b`, Zelazny and Marchenko as above, a Russian author in Cyrillic converted with no question: all as in my 7dcb4bc report.

Carried as reported, not re-run (the delta does not touch their code): the empty Xtra box and the Explorer-rating box, the slow media check retrying instead of "Needs you", the first-run window (`--start-hidden`), Edit names' "Applies to N books" over separate books (the engine's count of 2 was re-checked above), and the other queued presses (Approve, Save names, Delete book, Retry) during a scan (the delta changes only the scan-start branch of the queue's blocker). Not re-run either: the Вселенная Дозоров cases (series and universe handling is not in the delta).

## 5. Findings

### Blocker (0)

### Major (0 open)

M-1 and m-1 from 7dcb4bc are closed (items 4 and 9). No new Major.

### Minor (1 new)

- **m-2. A cached FantLab record for a Cyrillic-only foreign author gives the English title but leaves the author folder Cyrillic, and no rule is learned.** Repro (2 of 2, on 4b9fdba): library `Fantasy\Волшебники.m4b` and `Fantasy\Волшебная страна.m4b`, both artist «Лев Гроссман»; the research cache holds FantLab's answer for «Волшебники» (language `en`, original title "The Magicians", author name `Lev Grossman`). Automatic processing converts to `Гроссман Лев\The Magicians - Гроссман Лев.m4b` and `Гроссман Лев\Волшебная страна - Гроссман Лев.m4b`; `author_rules` gains nothing. **Control: the 7dcb4bc source gives the identical result, so the delta did not cause it.** In the same packaged engine, `canonical_author("Lev Grossman", ..., "en")` returns the English name, so the name is known and not used. My reading (flag only): the cache-only first pass already supplies an English title, so the book no longer looks like a translation and ruling 39's own lookup is skipped; the lookup runs when the cache is empty (online). Narrow: it needs the record cached before the book's first research. Jane and Sergei decide whether ruling 39's "found files under English" is meant to cover it.

### Observations, not defects

- In my discarded un-isolated run the online lookup did the right thing (FantLab found the author for «Голиаф»; rule `same_as "Westerfeld Scott"`, actor `assistant`, source cited; «Левиафан» followed it and converted at once under its own title). But «Голиаф», the book whose lookup learned the name, ended that run Held with "Local identity evidence changed" and no question. I did not follow it up (I redid the lab offline); a rerun of automatic processing probably converts it. Worth a look in real use.
- `original_titles.py` still holds the text "Waiting for the original title" (dead constant); nothing in the engine or page can show it.

## 6. Not run

- **Real-input checks: not run (Sergei present).** Every real click, the window's X button, the tray's Quit item and tooltip, the real Edit names editor typing.
- Page text and drawing, which need a browser: Saving… then Saved, the queued face and Cancel button on a row, the deleted row leaving the page, the editor's layout, the "Applies to N books" line, and how the ruling 39 question and its "Russian spelling" tag are drawn (the strings and the code that picks them are in the verified packaged page).
- The real NSIS install, Restart to update with a conversion and an approval running, Cancel update with work running, the slow-resume line, the media-retry ladder.
- Speed or large-catalog checks (not asked; lean rule).

## 7. Disposal

All of my output lived in `%LOCALAPPDATA%\Temp\baqa22c` (extracted payload, labs, a 7dcb4bc source copy) and in my folder of this session's scratchpad. Both were removed with `node scripts/studio-sweep.mjs --apply --path ...` (578.9 MB removed, +583.9 MB free on the Temp drive). Checked after: the folder is gone, no process runs from it, no tray-icon record for it remains. I left alone the Worktrees folders `cand-0222c` (the candidate build and its installer) and `qa-run-0222c` (Ender's entry log), `b0222` and `w22c`: they are Ender's and Sully's, and release still needs them. This report is the only file I changed, uncommitted.

## 8. Pattern alerts

Pattern alerts: none.

**Verdict:** GO
