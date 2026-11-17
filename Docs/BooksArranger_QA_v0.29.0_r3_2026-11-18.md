# Books Arranger 0.29.0 QA, regression pass 3 (final build)

QA: Futaba. Date: 2026-11-18. Source commit: `edf974f7a109c30ae4e186d8c0d592bcdc4ad473` (branch `ender/0.29.0`). Commits since my r2 build `6e3de5f`: 12e60cc (N-1), 96e1573, 16398a7 (M-5), 0533218, 1e44e39, 5b83c5e, a5bc01b, f48f142, 736dfc4, 23f54cb, edf974f, plus doc commits b527230 and 92e8fb3. Candidate, not packaged: tested from a `git archive HEAD` snapshot on the shipped embedded Python, through the real web backend and headless Edge. This report supersedes `BooksArranger_QA_v0.29.0_r2_2026-11-17.md` (the `6e3de5f` pass).

**Verdict:** GO

## Read this first

**N-1 is fixed on the page.** With my r2 repro, on a fresh page: Needs attention shows 13 rows (11 Author unclear, 2 Name taken); the **Name taken** chip now shows exactly the 2 Name taken rows (`Showing 1–2 of 2 candidates`, r2 showed 21 rows and `1–21 of 12`), unchanged 6.5 s later, no row reads `This row leaves the list when you close this editor.`. The **Author unclear** chip shows 11, **All** 13. A removed Author unclear book now leaves: two books deleted, scan: the chips dropped at 1.3 s and both rows left the page at 3.3 s (r2: still there after 40 s).

Everything else I was asked to check also holds: a book whose folder is moved out and back is listed again (after a scan, and after a restart with no scan); gone books leave All candidates and the candidate count; a book with a job is never hidden; the drive-return retry works; the Goes-to line keeps the saved path after Save; Files mode pre-ticks Light novel; Save As falls back to the nearest parent. No new Blocker or Major. Two Minor observations (section 4), neither a regression, neither mine to fix.

Version inside the build is still **0.28.13** (receipt, `/api/health`): Sully's bump has not happened; the version binding must be re-checked after it (open since r2, m-2, process).

## Summary

- Build confirmed by hash (section 1). No full suite run (Lean verification); my live runs are the delta.
- Verified fixed: N-1, D-M1 (96e1573), M-5 (16398a7), D-m3 (5b83c5e), O-r2-1 (736dfc4), O-r2-3 and O-r2-4 (23f54cb), the registry race (edf974f), D-m1 and D-m4 (0533218, 1e44e39) as far as a live run can reach them (section 3).
- r2's verified list re-run: B-1, M-1, M-2, M-3, M-4, M-6, m-1, m-3, m-4, m-5, m-6, S-M2, S-M3: all still hold.
- New: two Minor observations (O-r3-1, O-r3-2). Still open from r2: O-r2-2.
- Pattern alerts: none new, see section 7.

## 1. Build identity

| Check | Expected | Found | Result |
|---|---|---|---|
| Repo HEAD | `edf974f7a109c30ae4e186d8c0d592bcdc4ad473` | same (`git rev-parse HEAD`), branch `ender/0.29.0`, not switched | match |
| Builder's entry log | SHA-256 `273c7fb5d36e2da161d410d3c9ade1820f2e8f288a089960f8d99798901fd62f` | same (`sha256sum`); entry exit code 0 | match |
| Receipt line (line 3 of the log, verbatim start) | `… @ edf974f… (dirty: N) … check pass …` | `Entry-check receipt v2: books-arranger v0.28.13 @ edf974f7a109c30ae4e186d8c0d592bcdc4ad473 (dirty: N) [source:9eda3dd0…; harness:e3b598d2…; runtime:9485d78c…; checker:4bae2cde…] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a; personal-folders clean` | match |
| Snapshot | the committed files | `git archive HEAD` (committed content only; the tool repo has no change of mine except the two path-string edits to my earlier reports, section 8) | match |
| Runtime | the entry-check runtime | python.exe `434b361f…`, ffmpeg.exe `a3bf949b…`, ffprobe.exe `fe818a56…` equal `runtime-pointer.json` (runtime hash `9485d78c…` as in the receipt) | match |
| Version inside the build | 0.29.0 | **0.28.13** | open, Sully's bump (m-2) |

## 2. Method and limits

- Safety: backend started through a 3-line runner (`web_server.main` from the snapshot, the shipped runtime's `._pth` keeps the script folder off `sys.path`), always with `--roots-json` (never Z:), its own `--database` under the scratch folder, two source folders plus an output folder inside the scratch folder, own port 5294 (Sergei's app owns 5210), TEMP/TMP/BOOKS_WORK_TEMP redirected into the scratch folder, FFmpeg only from the shipped runtime. No installer, no Electron shell, no window, no focus, no audio, no native picker.
- Sergei's app: no `Books Arranger.exe` and nothing listening on 5210 at the start or the end. I sent nothing to 5210. My only process-affecting calls were the shutdown route on my own port, each confirmed by the listener going away.
- Never touched: Z:, `Audiobooks Sorted`, `I:\Books Arranger\Data`, Sergei's app or installed copy. The registry was only read (section 3, registry race); every write path of that module ran against winreg doubles.
- Driving: the real HTTP API with the page token (same routes as the page) and one headless Edge lease (`scripts/qa/headless-browser.mjs start`, ended at the end). The page was driven by DOM calls (`element.click()`, setting values, a window `focus` event), never mouse or keyboard input. For Manual Conversion I defined a recording stub for `globalThis.booksDesktop` before the page script ran (what the Electron preload exposes); the Electron main-side module ran with a fake dialog and IPC and the real file system.
- Fixtures: generated 3 s MP3 books (ffmpeg, tags set so two people are credited for Author unclear), a hand-built cp1251 ID3v2.3 book, Name taken books with clash files at their destinations, a Light Novels folder, and a second source folder. Automatic processing researched them with no network answer ("Waiting for metadata sources" as in r2).
- Real-time waits: the 10 min folder grace was waited out in real time (section 3, D-m1).
- Faked or stubbed, named so: the desktop bridge in the page, the fake dialog/IPC for the main-side module, winreg doubles. Nothing else in the page was faked.
- Limits: the packaged app, tray and installer, a real NAS or hung drive, a real 5 min stall, a drive leaving in the middle of the folders phase (D-m4, race), and a real cleanup hold were not produced.

## 3. Per-commit status

| Item | Commit | Status | Method and evidence |
|---|---|---|---|
| N-1 | 12e60cc | **fixed** | The r2 repro on the page, see "Read this first". Held side kept: a row whose author choice I changed (c0 to c1) stayed on the page with `This row leaves the list when you close this editor.` when its files were deleted and a scan ran, while the untouched row beside it (files deleted too) left; a Name taken row with Edit names open stayed (`The name is free now. This row leaves the list when you close this editor.`) and left 0.5 s after **Discard**, the chips dropped (`Name taken · 2` to `1`) and the strip said `«Книга НТ3» left this list: the name is free now. The book is checked again.` Sibling kind: Title or author rows (two authorless books): the **Title or author** chip shows exactly those 2, a removed one left within 2 s, nothing held. |
| D-M1 | 96e1573 | **fixed** | Folder moved out, scan: the book left All candidates (`27 to 24`, three gone books listed once in Details); moved back, scan: back (`24 to 25`) and out of the removed list; out again, scan, back again, **no scan, server restarted**: listed again at once by the start pass (`24 to 25`), still listed after a further scan, never reported as removed again. The two books whose files stayed gone stayed hidden through the restart. |
| M-5 | 16398a7 | **fixed as scoped** | All candidates and the count: the page reads `22 book candidates found · 6 not approved` and `Showing 1–24 of 24 candidates` with the engine's total equal each time; gone books leave both. A book with a job is never hidden: one approved but not converted (job queued) with all its files deleted, scan: still listed, not in the removed list; 16 of 16 converted books stayed listed through every pass. Beyond the scope (Sergei's answer was All candidates and the count): the **Held** and **Candidate changed** filters still list gone books, O-r3-1. |
| D-m3 | 5b83c5e | **fixed** | Drive B away (folder renamed), `/api/sources/check` recorded it (`available: false`), a book's files deleted meanwhile, drive back, scan started, `/api/sources/check` (`checking: true`) and scan Stop within 0.3 s: the stopped scan ran no pass; **about 15 s after the stop the retry pass dropped the book**, with no further action; the scan state still read stopped. |
| O-r2-1 | 736dfc4 | **fixed** | Page, an ask row (Author unclear «Книга Ранобэ»): Edit names, Light novel unticked, **Save**: the Goes-to line sampled every 150 ms for 9 s held one value (`sorted\Толстой Лев\Книга Ранобэ - Толстой Лев.m4b`); ticked again and saved: held `sorted\Light Novels\Толстой Лев\…` for 9 s (r2: flipped back to the old path at 1.6 s). |
| O-r2-3 | 23f54cb | **fixed** | Page, Manual Conversion, Files mode, real files: from `Light Novels\Ayatsuji Yukito\Иная2\`: Light novel pre-ticked with `Light novel from the folder name.`; from an ordinary folder (control): not ticked. |
| O-r2-4 | 23f54cb | **fixed** | Page: Save As request carries `defaultPath` `…\sorted\Light Novels\Иная2.m4b` and `remembered` the sorted root. Main-side module, real file system, fake dialog: Light Novels exists: opens there; Light Novels missing, library exists: opens in the library, nothing created; Light Novels is a file: the library; library is a file or missing: the name only; his own export path wins when its folder exists; an unreachable UNC library answers after 1.5 s with the name only. |
| Registry race | edf974f | **fixed** | Own probe (winreg doubles, 9 cases): stale count no longer fails (the entry-check failure); an entry removed between listing and open is skipped; an entry removed mid-listing never hides a persistent overlapping one (3 reads); an ever-changing list is refused (`kept changing`); a real overlapping cleanup is still refused; this installation's own pending cleanup still holds; an access-denied error (not 259) still raises; more than 512 entries refused. A read-only call against the real key: nothing pending, nothing written. |
| D-m1 | 0533218 | **fixed as far as live reaches** | Positive control with the real guards: a watched folder past the grace (leftover `cover.jpg`) lost its leftover and went (listed once, `files: ["cover.jpg"]`); folders inside the grace stayed; an empty parent went; the library roots never. The race itself (an Approve that names a leftover between the check and the delete) was not produced; the unit tests cover it. |
| D-m4 | 1e44e39 | **not produced live** | A watched folder survived a drive-away and a restart and went at the next pass after the drive came back (grace passed). The mid-phase drive loss itself is a race I could not produce. |
| Tests only | a5bc01b, f48f142 | not exercised | Test-only commits (jobs-queue guard, fake-.git fixture cleanup). |

r2's verified list, re-run on this build (live, not re-explained):

| # | Status | Evidence in this pass |
|---|---|---|
| B-1 | holds | Edit names Save carries Light novel both ways on the real routes: `names-save` `light_novel:true` 200, the 0.28 body 200; `approve-preview` `{light_novel:true}` gives `Light Novels\…`, `false` and no key give the plain path; negatives refuse (`"yes"` 400 `Light novel must be an explicit boolean`, an unknown field 400). |
| M-1 | holds | Details panel, Light novel ticked, **Save preview metadata**: `Saved.`; the durable `review` decision `applied`, outcome `saved` (was 500). |
| M-2 | holds | Deleted books left Needs attention at the scan's end with no start, Check again or focus call (3.3 s on the page). |
| M-3 | holds | Over repeated scans and two restarts each gone book is listed once in Details (`removed` grew by exactly the new books). |
| M-4 | holds | see N-1 row. |
| M-6 | holds | «Книга Ранобэ» (Author unclear, `Ранобэ` folder): Edit names opens with **Light novel ticked**, `Light novel from the folder name.`, Goes-to under Light Novels, `Nothing to save: these are the names the app already has.` |
| m-1 | holds | A book's files deleted, window focus (route called, 202): 23 candidates before and after, no folder removed although two folders were past the grace; the next scan dropped the book and removed those folders. |
| m-3, m-4 | hold | Jobs panel: `Researching books: <book>`, `Converting: <book> and 1 more`, `Cleaning up: <book>`, `Waiting for metadata sources. Next try 00:45.`, `Nothing running`; Stop: `Stopping automatic processing…` at once, `Paused` 1.6 s later, the line gone by 2.1 s. |
| m-5 | holds | cp1251 book «Похититель детей» converted: `ffprobe` tags title, artist, album, comment readable; chapters `Глава 01 Похищение`, `Глава 02 Погоня`. |
| m-6 | holds | A scan pressed while automatic ran queued as `Waiting: Start scanning: Audiobooks. It runs when the app is free.` |
| S-M2 | holds | Name taken «Книга НТ4» with its files gone and **no scan**: the start pass after a restart dropped it at once (`candidates 23 to 22`, automatic stayed `Paused` after the user Stop). |
| S-M3 | holds | Drive B away (folder renamed, recorded by Check again) from 00:46:46 to 00:51:47 with the page open the whole time and a window-focus call every 30 s: the srcA leftover folder that passed its 10 min grace meanwhile (and two inside it) stayed. Drive B back, Check again: the pass ran for B only, the srcA folders still stayed (reported folders unchanged). **Positive control** (it was eligible): the next scan removed exactly that folder («Книга АУ1», empty) and left the two still inside the grace, and no library root. |

Also seen working: drive notice `…\audioB isn't available. Its 3 books stay on the list. Check that the drive is connected.` with **Check again** (tooltip `Check whether … answers now. Nothing is removed while it doesn't.`), cleared one second after the drive answered; a root that answers empty keeps its books and is never removed itself.

## 4. New findings and observations

| # | Severity | Status | Finding |
|---|---|---|---|
| O-r3-1 | Minor | open, design question | **Gone books still show under the Held and Candidate changed filters.** With ten books taken off by the passes, All candidates reads `24 of 24` and leaves them out, but **Held** lists 5 rows, 3 of them gone books (two ordinary books and a Name taken book, files deleted), and **Candidate changed** lists 11 rows: all ten books the passes took off, plus the one with a queued job (correctly never hidden). Read on the page and through the same route. Sergei's M-5 answer (and Ender's fix) covers All candidates and the count, so this is the edge of that scope, not a regression. Repro: delete two books' files, scan, Status = Held. Disposition for Jane and Sergei: extend M-5 to those two filters, or accept. |
| O-r3-2 | Minor | open, not compared with 0.28.13 | **Saving the details panel on an Author unclear row takes the row out of Needs attention with the author still blank.** Seen with two different edits (Light novel ticked; a Series typed): **Save preview metadata** answers `Saved.`, the book becomes `Needs review` and leaves Needs attention; it stays in All candidates. It is not caused by Light novel and not by this delta. A book that still needs his author answer is no longer in the list that asks for it. For Judy if it is UX-shaped. |
| O-r2-2 | Minor | open, unchanged | A queued Start scanning press names `It runs when the app is free` while the jobs panel reads `Nothing running` and automatic processing sits between retries (seen again in this pass, not timed). Not in this delta. |
| O-r3-3 | Observation | no action | The `Saved names for …` line shows twice for about 0.2 s (the row hint and the status line) on each list poll after a Save; the persistent status line never flickered. Cosmetic. |

Also noted, not findings: a raw API scan press (without the page's queue flag) was refused twice with `Pause audiobook work before starting a scan` while the engine was briefly busy after a focus call or a stop; the page's own press queues instead (m-6 above) and the same press succeeded seconds later. A page error `api.onStatus is not a function` appeared only because my stub of the desktop bridge is incomplete.

## 5. What works, quick regression

- Name taken re-check outside the editor and the held row inside it (M-4, N-1 rows). Drop-on-scan, drop-on-start, drop-on-drive-return and listing-again (D-M1) on the real engine. Converted books stay (16 of 16 approved converted, every pass). List-only: nothing but the named leftover files and empty folders was removed from the source folders, and no library root.
- Restart intent: a restart after a user Stop stays `Paused` (automatic), jobs still `Audiobook jobs paused`; nothing started on its own.
- Light Novels filing from folder and from the typed box; Light novel on the details panel and in Edit names; Manual Conversion Light novel in Folder and Files mode.

## 6. Not verified

Still not verified: the packaged build, tray and installer; a slow or hung drive; a real NAS and its backlog; a real 5 min stall; the moved-cover hold; a real On hold block; Waiting for you with the real engine flag (verified in r2, not re-run: nothing in this delta touches it); upgrade and rollback round trips (verified in r2; nothing in this delta touches the catalog schema); focus moving when a focused row leaves; the mid-phase drive loss (D-m4) and the Approve-versus-cleanup race (D-m1).

## 7. Pattern alerts

Pattern alerts: none new. PA-1 (page-to-server fields pass the entry check and fail in the running app) and PA-2 (a page state the page tests never build; N-1 was the instance) keep their r2 dispositions; this pass found no further instance: the two sibling ask kinds I could build (Title or author, Name taken in an editor) hold, and a row whose default radio is untouched no longer counts as his work.

## 8. Cleanup and personal folders

- Backend (port 5294, three runs) stopped through its own shutdown route; no listener left on 5294 or (not mine) 5210. Headless lease stopped, `list` shows none. No installer, no Electron process of mine.
- Scratch folder `I:\AI Projects\Studio Illuminati\WIP\Books Arranger\scratch\futaba-0290r3\` (snapshot, fixtures, catalog, probes, tools): removed with `node scripts/studio-sweep.mjs --apply --path <that literal path>` after a dry run that planned exactly that one item (129.79 MB); the sweep reported it REMOVED and the folder is absent from `scratch\`. Nothing else of mine is on disk: TEMP/TMP were redirected into that folder, and the headless lease's own folder went with `stop`.
- **Released evidence folders:** the earlier reports' folder citations `qa-50ce63c`, `qa-9d05455.sweep-62492-1794936066900` and `qa-6e3de5f` are superseded by this report and released. In my two earlier reports (`BooksArranger_QA_v0.29.0_2026-11-17.md` and `BooksArranger_QA_v0.29.0_r2_2026-11-17.md`) only those path strings were replaced by `(superseded evidence folder, removed)`; nothing else in either report changed. This report cites the builder's log by hash and commit only, never by folder.
- Personal-folder listings, copied verbatim, list only, nothing deleted or moved by me:

```
Lease cf36063d29db (futaba-0290r3):
STOPPED lease cf36063d29db: 0 ended by sweep, 0 left; personal folders clean (5 subfolder notes)
  SUBFOLDER D:\SteamLibrary | changed below the depth checked
  SUBFOLDER E:\SteamLibrary | changed below the depth checked
  SUBFOLDER F:\SteamLibrary | changed below the depth checked
  SUBFOLDER H:\SteamLibrary | changed below the depth checked
  SUBFOLDER I:\SteamLibrary | changed below the depth checked
```

- Builder's entry log: `Entry-check personal folders: clean (7 folders, 11 drive roots watched)`.

Regression verification is recorded against the fix commits 12e60cc (N-1), 96e1573 (D-M1), 16398a7 (M-5), 5b83c5e (D-m3), 736dfc4 (O-r2-1), 23f54cb (O-r2-3, O-r2-4) and edf974f (registry race), all at HEAD `edf974f`.
