# Books Arranger 0.29.0 QA, regression pass 2 (fix build)

QA: Futaba. Date: 2026-11-17. Source commit: `6e3de5f81f24b5857907283941d11d59a76d3fbc` (branch `ender/0.29.0`; Ender's commits since `50ce63c`: bcd7da6, c6e7dfd, ae34010, f5298c8, ac859c7, 34d92bc, ad60f79, 6e3de5f). Candidate, not packaged: tested from a `git archive HEAD` snapshot on the shipped embedded Python, through the real web backend and a headless browser. This report supersedes `BooksArranger_QA_v0.29.0_2026-11-17.md` (the `50ce63c` pass).

**Verdict:** NO-GO

## Read this first

All 11 findings I was asked to re-check, plus Senua's S-M2 and S-M3, are fixed and verified on the running app. **One new defect, caused by the M-4 fix, stops me from saying GO:**

**N-1 (Major, new). Every author-unclear row counts as "he is working on it", so rows that should leave the Needs attention list stay on the page, labelled `This row leaves the list when you close this editor.`, with no editor open.** Two visible effects, both on a fresh page with nothing typed:

1. The chips do not filter. Open Needs attention (23 rows: 17 Author unclear, 4 Name taken, 2 Other), click **Name taken · 4**: the list shows 21 rows (the 4 Name taken rows plus all 17 Author unclear rows, each saying `This row leaves the list when you close this editor.`). Click **Other · 2**: 19 rows. The footer reads `Showing 1–21 of 12 candidates`. Clicking **Author unclear** or **All** brings the right rows back. The stale rows were still there 6.5 s later.
2. A removed book does not leave. Delete the files of an author-unclear book (B3) and scan: the chips drop (`All · 5` to `All · 4`, `Author unclear · 2` to `· 1`) but the book's row stays on the page, with that text, for the whole 40 s I watched. So S-M2 ("removed books leave Needs attention at once") holds in the engine and the counts but not on the page, for the commonest Needs attention row (every Author unclear one).

Cause seen in the page state (flagged, not fixed): an untouched ask row gets `askDrafts` `choice: "c0"` just by rendering (its default radio). The new `namesUnsaved` (`web/app.js` ~3000-3005, commit ae34010) returns true for any `d.choice`, so `underCursor` is true for every ask row and `keepUnderCursor` (~3006) holds it whenever a list change would drop it. The old test needed `namesData(row.id) && namesChanged(row)`. Ender's page tests (`test_source_check_frontend.js`) do not build an ask row with its default choice, which is why the entry check passed.

Workaround for Sergei today: reload the page. A one-condition fix plus one page test with a real ask row state should clear it; I will re-check on the fix commit.

Why NO-GO and not "GO with a Major": the studio vocabulary calls only a broken core flow a Blocker, and conversion, approval and every other fix work. But N-1 is new in this batch, it undoes the visible result of item 1 (his own request) for the commonest row, and it is cheap to fix. If Jane and Sergei decide to ship with N-1 logged, that is their call; nothing else here blocks.

## Summary

- Build confirmed by hash (section 1). Full suite not re-run (Lean verification); my live runs are the delta.
- Fixed and verified: B-1, M-1, M-2, M-3, M-4, M-6, m-1, m-3, m-4, m-5, m-6, S-M2 (engine and counts; page: see N-1), S-M3. M-5 skipped (pending Sergei). m-2 and m-7 not in scope.
- New: N-1 (Major) and four Minor observations (section 4).
- Also covered from "Not verified": Waiting for you with the real engine flag, Manual Conversion Save As start folder (page and Electron main-side module, never the native dialog), restart after a rollback round trip.
- Pattern alert: none new beyond PA-1's disposition, see section 7.

## 1. Build identity

| Check | Expected | Found | Result |
|---|---|---|---|
| Repo HEAD | `6e3de5f81f24b5857907283941d11d59a76d3fbc` | same (`git rev-parse HEAD`), branch `ender/0.29.0` | match |
| Entry log `I:\AI Projects\Worktrees\Books Arranger\qa-6e3de5f\ender-entry.log` | SHA-256 `0fe798a0ff48d8bce7ff28ee0b298bc54969d31a9e834b90071db74004780992` | same (`sha256sum`) | match |
| Receipt line (line 8 of the log, verbatim start) | `… @ 6e3de5f… (dirty: N) … check pass …` | `Entry-check receipt v2: books-arranger v0.28.13 @ 6e3de5f81f24b5857907283941d11d59a76d3fbc (dirty: N) [source:0389389a…; harness:98263df0…; runtime:9485d78c…; checker:4bae2cde…] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a; personal-folders clean (5 subfolder notes)` | match |
| Snapshot | the committed files | `git archive HEAD` (committed content only; the tool repo has no change of mine) | match |
| Runtime | the entry-check runtime | `build-cache\builds\a8162f92…\runtime`: python.exe `434b361f…`, ffmpeg.exe `a3bf949b…`, ffprobe.exe `fe818a56…` equal `runtime-pointer.json` | match |
| Version inside the build | 0.29.0 | still **0.28.13** (`/api/health`, page badge, receipt) | m-2, process: Sully's bump; the version binding must be re-checked after it |

## 2. Method and limits

- Safety: backends started through a 3-line runner that does what `launch-web.pyw` does (the embedded runtime's `._pth` keeps the script folder off `sys.path`), always with `--roots-json` (never Z:), their own `--database` under `scratch\futaba-0290r\data\`, own ports 5292 and 5293 (Sergei's app owns 5210), TEMP/TMP/BOOKS_WORK_TEMP redirected into the scratch folder, FFmpeg only from the shipped runtime. No installer, no Electron shell, no window, no focus, no audio, no native picker ever pressed.
- Sergei's app: not running at any time I looked (no `Books Arranger.exe`, nothing listening on 5210 at the start, mid-pass and the end). I sent nothing to port 5210. My only process-affecting calls were the shutdown route on my own ports 5292 and 5293, each confirmed by its own PID in `/api/health`.
- Never touched: Z:, `Audiobooks Sorted`, `I:\Books Arranger\Data`, Sergei's app or installed copy.
- Driving: the real HTTP API with the page token (same routes as the page) and headless Edge from `scripts/qa/headless-browser.mjs` (two leases, both ended, `list` shows none). The page was driven by DOM calls (`element.click()`, setting input values, window `focus` event), never mouse or keyboard input. For Manual Conversion I defined a recording stub for `globalThis.booksDesktop` in the page (what the Electron preload would expose).
- Fixtures (generated, 3 s MP3 tracks, ID3v2.3 tags built by hand so the cp1251 book stores real cp1251 bytes declared ISO-8859-1): batch 1 (26 books: ordinary, a Light Novels folder, a `Ранобэ` author-unclear book, gone-book and leftover-folder material, cp1251, a second source), batch 2 (21 books: held author-unclear books, Name taken books with clash files at their destinations, a Light Novels Name taken book, leftover-only folders, Keep cases, second-source books), and a 6-book catalog `r3` for the upgrade and rollback runs with a `git archive` of `fac11dbb` (0.28.13).
- Real-time waits: the 10 min folder grace was waited out in real time (first sighting 22:43:42; kept at 22:54:06 by every re-check and focus call; removed by the next full pass at 22:55).
- Faked or stubbed, named so: the desktop bridge in the page (Manual Conversion), a fake `ipcMain`, dialog and `stat` for the Electron main-side picker module. Nothing else in the page was faked: the 5 min stall and the real hold were not re-run.
- Limits: the packaged app, tray and installer, a real NAS or hung drive, a real 5 min stall and a real cleanup hold were not produced.

## 3. Per-finding status

| # | Status | Method and evidence |
|---|---|---|
| B-1 | **fixed** | Page, on «Книга Без» (ordinary row): typed Series `Серия Один`, Number `1`; the Goes-to line followed (`…\Серия Один\Серия Один - 1 - Книга Без - Толстой Лев.m4b`); **Save** answered `Saved names for Книга Без.`; the durable names decision read `applied`, outcome `saved`. Light novel box on «Книга Ранобэ»: unticked, Goes-to lost `Light Novels`, Save: `Saved names…`, stored value read back; ticked again and saved: back under Light Novels. Non-ask row «Книга ЛН1» (Name taken): the Goes-to line follows the box (ticked `Light Novels\Nakamura Ken\…`, unticked `Nakamura Ken\…`, ticked again); the page sends `light_novel` only when the box differs from its proposal. API on the real server: `names-save` with the 0.28 body 200 and with `light_novel:true` 200 (was 409); `approve-preview` with `names{…,light_novel:false}` and `{light_novel:true}` 200 (was 400). **Approve with an open editor's names:** `approve` for «Книга Г7» (`light_novel:false`) and «Книга Г8» (`light_novel:true`) both 202 (was 400); both converted, Г8 to `sorted\Light Novels\Толстой Лев\Книга Г8 - Толстой Лев.m4b`, Г7 to `sorted\Толстой Лев\…`. Negative controls still refuse: `light_novel:"yes"` 409 `Light novel must be an explicit boolean`; an unknown field 409 and 400. |
| M-1 | **fixed** | Page: details panel Metadata, ticked **Light novel**, **Save**: the durable review decision `applied`, outcome `saved` (was 500). Direct `POST /api/candidate/review` with `light_novel:true` 200 and `false` 200 (was 500 both); control without the key 200. Negative controls: both Light novel and Short-story collection ticked 400 `A book is a light novel or a short-story collection, not both. Untick one of them.`; `light_novel:"x"` 400. |
| M-2 | **fixed** | Three runs, each: delete a book's audio, press Start scanning, wait: «Книга Г1» (run 1, with the pass starting at the queued scan's end), «Книга Г2» (plus the earlier «Книга Г6», run 2), «Книга Г3» (plus Name taken «Книга НТ2», run 3) all left Needs attention at the scan's end, with no start, Check again or focus call (counts `author_unclear 17 to 11`, `11 to 9`, `9 to 8`). Run 3 first looked unchanged because my helper read the counts before its scan began; a clean rescan confirmed (`files.missing=1`, `removed 10`). |
| M-3 | **fixed** | Scan variant: after the pass dropped 6 books, two more scans: counts unchanged, `removed` stayed 6, `attention_dismissals` 6 rows with 6 distinct books (was two rows per book). Restart variant: deleted «Книга Г4» and «Книга Г5», restarted, the start pass dropped both; two scans after it: nothing returned (`author_unclear 4`, `files_missing 1`), dismissals 14 rows, 14 distinct books, `removed 3`, Details lists each book once. |
| M-4 | **fixed** | Name taken row «Книга НТ1» open in Edit names, clash file deleted, window `focus`: (a) the row's line reads `The name is free now. This row leaves the list when you close this editor.` and `Already there` is gone; (b) the strip stayed empty while the row was held; (c) **Discard**: the row left at once, the chips dropped (`All · 13` to `12`, `Name taken · 3` to `2`) and the strip said `«Книга НТ1» left this list: the name is free now. The book is checked again.` Name taken rows outside the editor still re-check (see section 5). **Caveat: N-1 is a different cause that hits author-unclear rows.** |
| M-6 | **fixed** | «Книга Ранобэ» (Author unclear, `Ранобэ` folder): Edit names opens with **Light novel ticked**, help `Light novel from the folder name.`, Goes-to under `Light Novels`; an untouched editor says `Nothing to save: these are the names the app already has`, so no explicit No is stored. |
| m-1 | **fixed** | Deleted «Книга Г6» entirely, called the focus route (`/api/sources/rows`, 202): counts unchanged (`author_unclear 11`), nothing dropped; five leftover folders past their grace were left alone by the focus call; the next scan dropped it. |
| m-3 | **fixed** | Automatic `Running`, phase `waiting`, `next_retry_at` set, no research waiting: the jobs panel read `Waiting for metadata sources. Next try 21:32.` while a series update ran, and again with the panel idle: `Nothing running … Waiting for metadata sources. Next try 22:42.` |
| m-4 | **fixed** | Stop pressed: `Stopping automatic processing…` at once, state `Paused` 2.5 s later, the line was gone then and stayed gone for the 60 s sampled. |
| m-5 | **fixed** | cp1251 book «Похититель детей», converted: `ffprobe` format tags `comment=Source album: Похититель детей`, title, artist and album readable; the three chapter titles `Глава 01 Похищение`, `Глава 02 Погоня`, `Глава 03 Возвращение` readable. |
| m-6 | **fixed** | A scan pressed while automatic research ran queued as `Waiting: Start scanning: Audiobooks. It runs when the app is free.` (singular; see O-r2-2). |
| S-M2 | **fixed in the engine, not on the page for author-unclear rows (N-1)** | Name taken «Книга НТ2» with its files gone: the scan pass dropped it (`name_taken 4 to 3`, `files.missing=1`). Name taken «Книга НТ3» with its files gone and **no scan** after: the start pass after a restart dropped it at once (`name_taken` left the counts). On the page: an author-unclear book removed by a scan stays on the page (N-1). |
| S-M3 | **fixed** | Drive B away (folder renamed): the page's own 30 s `/api/sources/check` calls (seen: one about every 30 s), my explicit check, and a focus call, all after the 10 min grace had expired (22:54:06 against first sighting 22:43:42): all five srcA leftover folders stayed. Drive B back with «Книга B1» deleted and «Книга B2» partly deleted meanwhile, one check: B1 dropped at once, B2 and B3 stayed, the srcA folders still stayed (the pass ran only for the returning root). **Positive control** (they were eligible): a scan, the full pass, then removed exactly the three leftover-only folders and the two now-empty parents, kept `Сидорова Мария2` (its second book is still there), `Keep1`, `Keep2` and the library root; the manifest diff shows only those files and folders. |
| M-5 | pending Sergei | Not tested. Still true: `All candidates` lists a removed book as `Candidate changed — review required` and the jobs line still counts it (`47 book candidates found`). |

## 4. New findings and observations

| # | Severity | Status | Finding |
|---|---|---|---|
| N-1 | **Major** | open | See "Read this first". Repro (numbered): 1. Fresh page, library with several Author unclear books and at least one Name taken book. 2. Press **Needs attention**. 3. Press the **Name taken** chip. 4. The list keeps every Author unclear row, each reading `This row leaves the list when you close this editor.`; the footer reads `Showing 1–21 of 12 candidates`. Second repro: delete an Author unclear book's files, press Start scanning: the chips drop, the row stays. |
| O-r2-1 | Minor | open | **The Goes-to line flips back to the old path for about 1.6 s after Save.** Light novel box ticked, Save: line `Light Novels` (live preview), then `Толстой Лев` (the old path) at 1.6 s, then `Light Novels` at 3.2 s. On «Книга Без» the old path stayed 4 s or more. The row says `Saved names` the whole time. |
| O-r2-2 | Minor | open, not compared with 0.28.13 | **A queued Start scanning press did not run while automatic processing sat between timed retries.** It waited from 22:41 until I pressed Stop at 22:44, across a retry run, while the jobs panel read `Nothing running`; the text `It runs when the app is free` was not true in that state. |
| O-r2-3 | Minor | open | **Manual Conversion, Files mode, does not pre-tick Light novel** for files from a `Light Novels\…` folder (Folder mode does, with the help line, and Save As starts in `Audiobooks Sorted\Light Novels\`). The UX spec says "when the loaded source path has a folder named Light Novels". |
| O-r2-4 | Minor | open, design question | **Manual Conversion Save As opens at Windows' own start folder when `Audiobooks Sorted\Light Novels` does not exist yet** (Electron main-side module with a fake `stat`: folder exists, the full path is used; folder missing or drive away, only the file name is passed). Sergei's first-ever light novel will not start in his library. The output folder itself could be the fallback. |
| O-1 (resolved) | Observation | closed | The empty `I:\AI` folder from my first pass is gone: the first lease's stop listed `REMOVED  I:\AI | there at the start, gone at the end`. I did not delete it and never touched it; something else removed it. |

## 5. What works, quick regression

- Drive notices: `…\srcB isn't available. Its 7 books stay on the list. Check that the drive is connected.` with **Check again** (tooltip `Check whether … answers now. Nothing is removed while it doesn't.`); `…\srcB answers but is empty. Its 6 books stay on the list. Check that the drive is connected.` with nothing dropped; the line cleared once the drive answered.
- Drop-on-start and drop-on-drive-return: pass (S-M2, S-M3 above). Converted books stay: all 28 converted books stayed listed through every pass (`28 converted out of 28 approved books`). List-only: manifests of both libraries before and after each pass differ only by the leftover files and folders named above.
- Leftover-only folders: first sighting, 10 min grace, parents removed, never the library root, `Notes.pdf` and an `Extras\bonus.txt` subfolder keep their folders, focus never deletes. Pass.
- Name taken re-check outside the editor: «Книга ЛН1» name freed, focus: the chips dropped, the strip said why, the book was checked again and converted. Pass.
- Light Novels filing from a folder (`Light Novels\Ayatsuji Yukito\Иная`) and from typed names: pass. cp1251 chapter names: pass.
- Status naming: `Researching books: <book>`, `Converting: <book> Step 1 of 4 …`, `Cleaning up: <book>`, `Metadata: Updating series: <book>`, `Nothing running`; the word "Running" never appeared in the jobs line. Stop acts at once. A queued press names its blocker.
- Restart intent: same-version restart with automatic `Running`: back to `Running`. Same-version restart after a user Stop: stays `Paused`. Upgrade from 0.28.13 (paused with 5 jobs queued by a user Stop, opened by the candidate): `Paused`, jobs paused, nothing converted over 40 s.

## 6. Not verified items now covered

- **Waiting for you with the real engine flag:** reached. With every book checked, automatic `Completed`, nothing queued and 2 books needing attention, `/api/state` returned `needs_you_only: true` and the jobs panel read `Waiting for you: 2 books need attention. The app can't do more until you review them.` with **Review them** (106 x 41 px, tooltip `Show every book that needs you.`), 15 px text, `Waiting for you:` in weight 600, count equal to `Needs attention · 2`, no horizontal scroll. Pressing it opened Needs attention. Pass.
- **Manual Conversion Save As start folder:** Folder mode with a `Light Novels` source: Light novel pre-ticked, help `Light novel from the folder name.`, and the page passed `defaultPath` `…\sorted\Light Novels\Книга ЛН1.m4b`; an ordinary folder: not ticked, empty `defaultPath`. Files mode: not pre-ticked (O-r2-3). Ticking the box after loading files passes `…\sorted\Light Novels\Книга Г4.m4b`. The native dialog itself was never opened (O-r2-4 is the main-side module with fakes).
- **Restart after a rollback round trip:** catalog `r3` run by 0.28.13 (user Stop, 5 queued), opened by the candidate (stays Paused), run again by 0.28.13 and Quit mid-conversion, opened by the candidate again: `Paused`, jobs `Audiobook jobs paused`, `restart_paused: false`, 5 queued, nothing converted over 50 s. Positive control: the candidate's own Quit mid-conversion, reopened: `restart_paused: true` (restorable), jobs `stopped at a safety hold`, nothing resumed on its own.

Still not verified: the moved-cover hold, a real On hold block («Похититель детей»), a real 5 min stall, a slow or hung drive, a real NAS and its backlog, focus moving when a focused row leaves, Stop's deferred re-pause order (Senua S-m2), the packaged build, tray and installer.

## 7. Pattern alerts

- **PA-1 (new page-to-server fields and hooks pass the entry check but fail in the running app): disposition accepted by Ender, fix verified.** The real-server tests exist (`tests/test_http_0290.py`, run by the entry check since 6e3de5f) and my live runs through the real server found no new field or hook that the server refuses (B-1, M-1, M-2 all closed above).
- **PA-2 (new, same family one layer over): a page state the page tests never build.** N-1 passes the page tests because they never render an ask row with its default `choice`. Suggested disposition: **FIX with N-1** by adding one page test that builds a real ask row from its default state and checks that a chip change or a gone book drops it; **DEFER** the wider idea (run the page tests against real server rows) to Ender as a maintenance item. Jane and Sergei to confirm.

## 8. Cleanup and personal folders

- Backends (ports 5292 and 5293, including the 0.28.13 runs) stopped through their own shutdown route, each confirmed by PID; no listener left on 5292, 5293 or (not mine) 5210. Headless leases `0ee0da67e3c0` and `795f9e499256` stopped, `list` shows none. No installer, no Electron process of mine.
- Scratch folder `I:\AI Projects\Studio Illuminati\WIP\Books Arranger\scratch\futaba-0290r\` (snapshots of 0.29.0 and 0.28.13, fixtures, catalogs, probes, tools): removal with `node scripts/studio-sweep.mjs --apply --path <that literal path>` after this report, confirmed in my reply.
- **Superseded evidence:** this pass supersedes the first report's evidence citation of `I:\AI Projects\Worktrees\Books Arranger\qa-50ce63c` and `qa-9d05455.sweep-62492-1794936066900`; those two folders can be released. `qa-6e3de5f` is the entry log this report cites; keep it until the verdict is acted on.
- Personal-folder listings, copied verbatim, list only, nothing deleted or moved by me:

```
Lease 0ee0da67e3c0 (futaba-0290r):
STOPPED lease 0ee0da67e3c0: 0 ended by sweep, 0 left; personal folders listed (1 removed, 5 subfolder notes)
  REMOVED  I:\AI | there at the start, gone at the end
  SUBFOLDER D:\SteamLibrary | changed below the depth checked
  SUBFOLDER E:\SteamLibrary | changed below the depth checked
  SUBFOLDER F:\SteamLibrary | changed below the depth checked
  SUBFOLDER H:\SteamLibrary | changed below the depth checked
  SUBFOLDER I:\SteamLibrary | changed below the depth checked

Lease 795f9e499256 (futaba-0290r-b):
STOPPED lease 795f9e499256: 0 ended by sweep, 0 left; personal folders clean
```

- Builder's entry log: `Entry-check personal folders: clean (5 subfolder notes) (7 folders, 11 drive roots watched)`.

Regression verification is recorded against fix commits bcd7da6 (B-1, M-1, M-6), c6e7dfd (M-2, M-3, m-1, S-M2, S-M3), ae34010 (M-4, m-3, m-4, m-6; **introduces N-1**), f5298c8 (rollback round trip) and ac859c7 (m-5), all at HEAD `6e3de5f`.
