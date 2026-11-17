# Books Arranger 0.29.0 QA

QA: Futaba. Date: 2026-11-17. Source commit: `50ce63c37a0e4a3bf2502922c79e46686a370dff` (branch `ender/0.29.0`, tool repo clean). Candidate, not packaged: tested from a pinned snapshot of that commit on the shipped embedded Python, through the real web backend and a headless browser.

**Verdict:** NO-GO

## BLOCKER (read this first)

**B-1. Edit names Save is refused for every book, and Approve is refused while an Edit names editor is open.** The page puts `light_novel` into the names it sends whenever a row's Edit names editor is open (any book, ticked or not). The server's names check does not know that field and answers `400`/`409`. The entry check passed anyway, because its tests mock the page-to-server hop.

Repro (UI, ordinary book, no light novel involved):
1. Start the build on a fixture library, scan, open Needs attention, press **Edit names** on «Книга Тета».
2. Type Series `Серия Один` and Number `1`. The Goes-to line updates to `…\Серия Один\Серия Один - 1 - Книга Тета - Волкова Ольга.m4b`.
3. Press **Save**. The row says: `Names not saved: Edit names takes title, author, series, number, universe, collection` (no "light novel" in that list). Nothing is saved.

Repro (API, positive control in the same run):
- `POST /api/candidate/names-save` with the names the 0.28 page sent (no `light_novel`): **200**. The same names plus `"light_novel": true`: **409** `Edit names takes title, author, series, number, universe, collection`.
- `POST /api/candidate/approve-preview` and `/api/candidate/approve` with `names:{series,number,universe,collection,light_novel:false}` (what an open editor sends): **400** `Edit names takes series, number, universe, collection`. Without `light_novel`: 200.

Where to look (flag, not fixed): `web_server.py:180` (`NAME_FIELDS`) and `names_value` (`web_server.py:904-912`, the `partial` list) do not include `light_novel`. On the page, `askNamesPayload` (`web/app.js` ~4014) and `askPreview` (~3511) send it; the non-ask `namesPreview` (~4221) never sends it, so the Goes-to line cannot follow the Light novel box there either. Seen in the page: after unticking Light novel on «Иная» the Goes-to line stayed `Light Novels\…`.

Effect for Sergei: he cannot save a name change from Edit names at all, and cannot Approve a row whose editor is open. Light Novels filing from a source folder still works (see item 4), but the box that is supposed to show and undo it does not work.

## Summary

- Build confirmed by hash: HEAD, entry-log hash and receipt line match (section 1). Full suite not re-run (Lean verification).
- 1 Blocker, 6 Major (M-5 is a question for Sergei), 7 Minor, 1 unexplained observation. Details in section 4.
- Works as specified (section 5): the unavailable/empty/back drive notices and Check again, drop-on-start and drop-on-drive-return, converted books stay, list-only (no file touched), leftover-only folder removal with the 10 min grace, parent folders, never the library root, Light Novels filing from a folder, cp1251 chapter names, "Converting:"/"Cleaning up:"/"Researching books" status naming, Stop acting at once, the Waiting line naming a queued press, no auto-start on upgrade, Name taken re-check outside the editor.
- Not reproduced end to end (section 6): the moved-cover hold, the real «Похититель детей» On hold block, the 5 min stall, a slow-drive wait, the NAS backlog.

## 1. Build identity

| Check | Expected | Found | Result |
|---|---|---|---|
| Repo HEAD | `50ce63c37a0e4a3bf2502922c79e46686a370dff` | same (`git rev-parse HEAD`), branch `ender/0.29.0`; the tool repo had no change of mine (only Senua's untracked review file appeared during my pass; I did not open it) | match |
| Entry log `(superseded evidence folder, removed)\ender-entry.log` | SHA-256 `e2dc43373e388bb143175c35bd161de9ae5a2f8c1092d6a7ff773756bf6214b0` | same (`sha256sum`) | match |
| Receipt line (line 3 of the log, verbatim start) | `… @ 50ce63c… (dirty: N) … check pass …` | `Entry-check receipt v2: books-arranger v0.28.13 @ 50ce63c37a0e4a3bf2502922c79e46686a370dff (dirty: N) [source:fc37370c…; harness:e895fb43…; runtime:9485d78c…; checker:4bae2cde…] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a; personal-folders clean` | match |
| My snapshot of HEAD | the committed files | `git archive HEAD`, 2816 files = `sourceFiles` in the entry `context.log`. 2769 equal their git blob hash; the other 47 differ only by line endings (`core.autocrlf` on export; equal after removing CR) | match |
| Runtime used | the entry-check runtime | embedded Python and FFmpeg from `build-cache\builds\a8162f92…\runtime`; python.exe, ffmpeg.exe, ffprobe.exe SHA-256 equal `runtime-pointer.json` | match |
| Version inside the build | 0.29.0 | **0.28.13**: `package.json`, `/api/health`, the page badge `v0.28.13`, the receipt `books-arranger v0.28.13` | see finding m-2 |

## 2. Method and limits

- Safety: every backend was started with `--roots-json` (never Z:), its own `--database` under `scratch\futaba-0290\data\`, its own port (5290, 5291; Sergei's app owns 5210), and TEMP/TMP/BOOKS_WORK_TEMP redirected into the scratch folder. FFmpeg only from the shipped runtime. No installer, no Electron shell, no window, no focus, no audio. Native pickers and the real "Open folder" were never pressed on an available folder.
- Sergei's app was untouched by me: the same four `Books Arranger.exe` PIDs (96212, 22996, 68412, 72200) and the python listener on 5210 (PID 63352) were present at the start and at my last check during the pass (about 20:08). At 20:12 they were gone, and a read-only listing of `I:\Books Arranger\Data` shows writes at 20:08:54 (a normal exit). I sent nothing to port 5210 or to any of its processes (my only process-affecting calls were the shutdown route on my own ports 5290 and 5291, each confirmed by its own PID and port), so I take it he closed it himself. Flagged in case it was not him. Z:, `Audiobooks Sorted` and `I:\Books Arranger\Data` were never written by me. My fixture output folder is `lib\r1-sorted`, not `Audiobooks Sorted`.
- Fixtures (generated, 3 s MP3 tracks with ID3v2.3 tags; one set with cp1251 text declared as ISO-8859-1): source roots `r1-A`, `r1-B` (two sources), an output root, covers and leftover files (`Notes.pdf`, `folder.nfo`, `desktop.ini`, `Thumbs.db`, `info.txt`, `readme.nfo`, an `Extras\bonus.txt` subfolder), Light Novels folders (`Light Novels`, `light novels` nested, `Ранобэ`) and substring negatives (`My Light Novels`, `Light Novels Extra`, `Ранобэшки`). A second catalog (`r3`) for upgrade and restart tests, first run by a `git archive` of the 0.28.13 commit `fac11dbb…` on the same runtime, then opened by the candidate.
- Driving: the real HTTP API (page token, same routes as the page) and a headless Edge from `scripts/qa/headless-browser.mjs run` (leases ended, `list` shows none). The page was driven by DOM calls (`element.click()`, setting input values, a window `focus` event), never by mouse or keyboard input.
- Real-time waits: the 10 min folder grace was waited out in real time (first sighting 19:32:29 and 19:42:46, deletion at the next pass after 10 min each).
- Faked in the page, named so: the 5 min stall (`Date.now` moved +301 s in the page, rendering only) and the Waiting-for-you block (`needs_you_only` forced on the page, rendering only; the engine decision was checked separately).
- Limits: item 2's moved cover (needs a data-folder storage move), a real NAS, a hung drive, a real 5 min stall and a real cleanup hold were not produced.

## 3. Item-by-item results

### 1. Books whose source is gone leave the list

| Check | Result |
|---|---|
| Drive does not answer (source 2 renamed away), Check again | books stay (3 of 3 stay), line `…\r1-B isn't available. Its 3 books stay on the list. Check that the drive is connected.` + **Check again** (102x41 px, tooltip `Check whether … answers now. Nothing is removed while it doesn't.`), `role=status`, `aria-live=polite`. Click gives `Checking …` then `… still isn't available. Its 3 books stay on the list.` Pass. |
| Root answers but is empty | `… answers but is empty. Its 3 books stay on the list. Check that the drive is connected.` Books stay, no dismissal written. Pass. |
| Drive back with a book gone meanwhile (Q4 "then") | after `Check again` with the drive back, «Книга Икс» (all files deleted while away) dropped at once, its partial neighbour «Книга Игрек» (2 of 3 files) stayed. Pass. |
| App started with the drive away | `library_roots` shows source 2 unavailable with its 2 books; `attention_dismissals` count 15 before and 15 after the start. Drive returned: the gone book dropped. Pass. |
| Page clears the line by itself | a page opened right after the drive came back showed `Waiting for … r1-B to answer.` and the line was gone at the 29 s sample (30 s poll). Pass. |
| Converted book whose source is gone | three converted books (sources removed by their own cleanup) stayed in the converted list after a pass (3 of 3, `status=converted`). Pass. |
| List-only, no file touched | manifests (SHA-256 of every file and folder of both libraries) before and after the drive-back pass: identical. Pass. |
| Partly gone book | «Книга Гамма» (2 of 4 files) stays as `Missing files`. Pass. |
| Renamed folder | old book dropped, `Книга Тета (новая)` listed as a new book by the next scan; Details names the dropped one. Pass. |
| Removed line, Details, Dismiss | `Removed 5 books whose files are gone. Deleted 1 source folder that held only leftover files.`; Details lists `Title — path`; tooltips match the spec; Dismiss hides the line, notices stay. Pass. |
| Open source folder, root unavailable | row says `…\r1-B isn’t available. Check that the drive is connected.` Pass. |
| Layout | `#library-notices` starts below the Source lines at 1280, 960, 760, 600 and 640 px (200% zoom), no horizontal scroll, no overlap (rects measured). Pass. |
| Load step | `/api/state` while loading reports step 4 of 5 `sources` with the book count (`12 of 12`), then step 5 of 5 `books`; the page's own labels (`load-state.js`) read `Checking source folders` and `Loading your books`. Pass. |
| Triggers | start: pass. Drive back: pass. **Scan end: never ran** (M-2). **Window focus drops gone books** (m-1). |
| After a scan | **dropped books come back** (M-3). |
| All candidates view | **still lists the removed books** (M-5). |

### 2. Cleanup cover and cp1251 chapter names

- cp1251 book (title, artist, album stored as cp1251 bytes declared ISO-8859-1), approved and converted: `ffprobe` chapter titles `Глава 01 Похищение` … readable; title and album readable. Pass.
- **The comment tag is not repaired**: `Source album: Ïîõèòèòåëü äåòåé` (m-5).
- The moved-cover hold itself: not reproduced (needs a data-folder move). An ordinary conversion plus cleanup with a source cover worked end to end (3 books). Positive control only.

### 3. Stale Name taken rows

- Two books held `Name taken` by a file I placed at their destination. I deleted one clashing file, then called the focus check: the book left Needs attention (`name_taken` 2 to 1, `cleared: [Книга Альфа / name_taken]`) and was re-checked: automatic processing later approved and converted it. Pass.
- Row open in Edit names: the row stayed and the chips kept the book (`Needs attention · 7`, `Name taken · 1`). But (M-4) the row's own text did not change, the strip already said "left this list", and after closing the editor the row stayed while the counts dropped.
- Focus move when a focused row leaves: not tested (the row never left).

### 4. Light Novels

| Check | Result |
|---|---|
| Folder `Light Novels` (book «Иная») | Goes to `r1-sorted\Light Novels\Ayatsuji Yukito\Иная - Ayatsuji Yukito.m4b`; converted there, the file exists. Pass. |
| `light novels` (lower case, below an author folder) | filed under Light Novels (preview and converted). Pass. |
| Substring folders `My Light Novels`, `Light Novels Extra`, `Ранобэшки` | editor data says no pre-tick, basis empty. Pass. |
| `Ранобэ` folder | `basis: folder_name` but the box is **not ticked** while the author is unresolved (M-6). |
| Edit names box | right place (after Collection of stories), tooltip text as specified, help `Light novel from the folder name.` for «Иная». Ticking Collection unticks Light novel and the reverse. **Save and Approve fail (B-1).** |
| Details panel Metadata box | exists, but saving with it ticked returns 500 (M-1). With both boxes ticked: 400 `A book is a light novel or a short-story collection, not both. Untick one of them.` Pass. |
| Manual Conversion window box | markup exists; Save As start folder needs the native dialog: not tested. |

### 5. Source folder removed when no audio is left

- «Книга Эпсилон» (leftovers `cover.jpg`, `desktop.ini`, `info.txt`, `Thumbs.db`): kept at the first pass (grace), removed by the next pass after 10 min. Its parent `Мария Сидорова` stayed (it still held other books). Pass.
- «Книга Зета» (`cover.jpg`, `readme.nfo`): folder and its now-empty parent `Павел Орлов` removed; the library root stayed. Pass.
- «Книга Эта» directly inside the library folder (Q6): removed at the first pass after its grace. Pass.
- «Книга Дельта» with `Notes.pdf`: folder kept, silently, book gone from the list (Q7). «Книга Йота» with an `Extras\bonus.txt` subfolder: kept. Pass.
- Nothing else touched: manifest diff after the Зета pass shows exactly its two files and two folders. Each removed file has a `source_folder_removed_files` row with state `removed`. Pass.
- Not on focus: the focus check left the leftover folders alone (watch rows stayed, files stayed). Pass.

### 6. Restart intent

- Upgrade: 0.28.13 started automatic processing, Sergei-style Stop (Paused), two conversions left queued, jobs paused. Candidate opened the same catalog: still `Paused`/jobs paused, 2 queued, nothing converted over 45 s (three samples). Pass.
- Same-version restart with automatic processing `Running` (timed retry scheduled): comes back `Running`, same `next_retry_at`. Same-version restart after a user Stop: stays Paused. Pass.
- Quit during a conversion, restart: jobs `Paused`, 2 queued, reason `Audiobook jobs stopped at a safety hold`, nothing resumed (not a defect, noted because "safety hold" reads strange for an ordinary quit).
- No restart after rollback and the NAS backlog: not tested (no rollback harness, no Z:).

### 7. Status area

- Seen in the jobs line and rows across 3 conversions, a cleanup, a scan, a research pass, a series update and a check: `Nothing running`, `Converting: <book>`, `Cleaning up: <book>`, `Removing originals: <book>`, `Researching books: <book>` with `N of M books`, `Scanning files: Audiobooks`, `Metadata: Updating series: <book>`, `Checking pending audiobook work`, `Paused`. The word "Running" never appeared in the jobs line. The row reads `Converting: Иная 0:00 of 0:09 audio Step 3 of 4 - Encoding audio 0:01 elapsed`. Pass.
- Stop acts at once: pressed during research, message `Stopping automatic processing…` within 200 ms, state `Paused` 0.8 s later, even with another press queued. Pass. (Stale line afterwards: m-4.)
- Queued press names its blocker: a queued scan shows `Waiting: Start scanning: Audiobooks. They run one at a time.` Pass (wording m-6). The `Stop automatic processing queued. It runs when Converting: … finishes` form is no longer reachable because Stop never queues (Q8).
- `No progress for 5 min`: rendering verified with a +301 s clock in the page (`Converting: Книга Тета No progress for 5 min 5:02 elapsed`, row class `stalled`). Real stall detection not run.
- On hold block / «Похититель детей» wording: not produced. I held a source cover open at cleanup time; the cleanup went through, so no hold arose.
- A scheduled retry is not shown in the jobs panel (m-3).

### 8. Waiting for you

- Engine flag `needs_you_only` was false in every state I could reach, correctly: books still to be checked, a paused or running automatic pass with a timed retry, a queued action, a drive that does not answer. I could not reach the true case (every full pass left a timed metadata retry).
- Rendering with the flag forced on the page: `Waiting for you: 6 books need attention. The app can't do more until you review them.` with **Review them** (106x41, tooltip `Show every book that needs you.`), `Waiting for you:` in weight 600, line 15 px, count equals `Needs attention · 6`, no horizontal scroll at 1280/760/600, no overlap with Pause/Resume. Pressing it opens Needs attention. Pass (rendering only).

## 4. Findings

| # | Severity | Status | Finding |
|---|---|---|---|
| B-1 | **Blocker** | open | Edit names Save and Approve-with-editor-open refused, Goes-to preview stuck on the Light novel box. Repro and pointers above. |
| M-1 | Major | open | **Details-panel Light novel box cannot be saved: HTTP 500.** Repro: `POST /api/candidate/review` for any audiobook with `review.light_novel` true or false: **500** `Local control failed; inspect saved job and source cleanup status`. The same review without the key: 200. In the page this is ticking the box in the details panel's Metadata form and saving. Pointer: `Handler.review_data` (`web_server.py` ~1663) reads `source['kind']`, and `source` is not defined in that method. |
| M-2 | Major | open | **A finished scan never runs the check pass.** Repro: delete a book's audio, press Start scanning, wait; repeat 3 times: the book stayed in Needs attention (`files_missing`) all 3 times. It dropped only when I used start, Check again or the window-focus call. So Name taken rows (item 3) and leftover folders (item 5) also miss their "a scan finishes" trigger, and a book Sergei deletes stays until the next start. Pointer: the scan hook starts the pass on a new thread from the scan's own worker thread, and `MergeService.check_sources` returns `None` when `inventory.worker.is_alive()` (`merge_service.py` ~1052); the worker is still alive at that moment. |
| M-3 | Major | open | **A scan resurrects the books the pass dropped, and Details counts them twice.** Repro: delete a book's audio, restart the app (the start pass drops it; its dismissal is stored with the fingerprint from before the scan saw it missing), press Start scanning: `files_missing` goes up again (2 to 4, later 2 to 5, 6 to 7 in different runs); the next pass drops the same books again and the line reads `Removed 9 books` with `Книга Эпсилон`, `Книга Икс`, `Книга Йота` listed twice in Details (in another run `Книга Тета` and `Книга Зета` twice). Cause seen in the catalog: `attention_dismissals` holds two rows per such book with different fingerprints (e.g. `…c0e46e50f5e7` then `…d2a51da41951`). With M-2 this means the ghosts Sergei asked to lose come back after every scan until the next start. |
| M-4 | Major | open | **A Name taken row open in Edit names ends in an inconsistent list.** Repro: Needs attention, Name taken, open Edit names on the row, delete the clashing file in Explorer, bring the window back (focus). (a) The row's status line stays `That name is already in Audiobooks Sorted. Change the title or author.`; the spec says `The name is free now. This row leaves the list when you close this editor.` (b) The strip above the list already says `«Книга Тета» left this list: the name is free now. The book is checked again.` while the row is still there. (c) After **Discard** the chips drop (`Needs attention · 6`, `Name taken · 0`) but the row stays with its `Approve` button and `Already there …` path, under `Showing 1–7 of 6 candidates`. |
| M-5 | Major, **needs Sergei's answer** | open | **"Removed from the list" removes books from Needs attention only.** Status `All candidates` still lists every dropped book as `Candidate changed`, `3 files`, and the jobs panel still counts them (`21 book candidates found`). This is how the existing Remove from list behaves (it writes the same record), so it may be by design. If "leave the list" means every list, the pass needs more than the dismissal. |
| M-6 | Major | open | **Edit names does not pre-tick Light novel for a book whose author is still unresolved.** For «Книга Ранобэ» in a `Ранобэ` folder (Author unclear) the editor data is `{"proposal": false, "basis": "folder_name"}`: box unticked, help line hidden. Opening Edit names to fix the author shows "No"; saving that (once B-1 is fixed) stores an explicit No that beats the folder. This is the trap the spec names ("a pre-tick Sergei cannot see or undo"). «Иная» (author known) shows ticked. |
| m-1 | Minor | open | **Window focus also drops gone books.** The spec table says focus checks rows only (item 1: no). The focus call (`/api/sources/rows`) dropped «Книга Эта» (no folders touched). List-only, so low risk. |
| m-2 | Minor | process | **The candidate still says 0.28.13** (`package.json`, health, page badge `v0.28.13`, receipt). Sully's bump will change it; this report is for the 0.29.0 candidate at `50ce63c`, and the version binding must be re-checked after the bump. |
| m-3 | Minor | open | **A scheduled automatic retry is invisible in the jobs panel.** With automatic processing `Running`, `phase: waiting`, `next_retry_at` set and `research.waiting = 0`, the jobs panel reads `Nothing running · 6 need attention …` with no Waiting line. The retry time shows only in the Automatic block. |
| m-4 | Minor | open | **`Stopping automatic processing…` stays after the state is `Paused`** (the `#message` line, still there 40 s later). |
| m-5 | Minor | open | **Comment tag of a cp1251 book stays unrepaired** (`Source album: Ïîõèòèòåëü äåòåé`) although the brief says the comment of new conversions is repaired. Chapter names, title and album are readable. |
| m-6 | Minor | open | `Waiting: Start scanning: Audiobooks. They run one at a time.` says "They" for one queued action. |
| m-7 | Minor | note | `Stopping automatic processing — Stopping automatic processing — saving pending work` repeats itself. Same strings exist in 0.28.13: not new. |
| O-1 | Observation | open, for Jane | **An empty folder `I:\AI` appeared at the root of drive I:** at 19:53:28, inside one of my headless runs (the browser's end-of-run check listed it as NEW). It is empty and not mine to delete unproven. I found nothing in the candidate's diff that creates folders or starts processes (no `mkdir`, `makedirs`, `subprocess`, `Popen`, `shell=True` in the added Python), the other runs ended `clean`, and other agents work on this machine, so I cannot attribute it. I left it in place. It looks like what an unquoted `I:\AI Projects\…` path produces; worth one look. |

Regression checks: none (first QA of this candidate).

## 5. What passed, in one place

Item 1 drive notices, Check again, Q4, startup, converted-stay, list-only, layout; item 5 grace, parents, root, Q6, Notes.pdf and subfolder keeps, no extra file touched; item 3 clear and re-check outside the editor; item 4 folder pre-tick routing and both-ticked refusal in the panel; item 2 cp1251 chapter names; item 6 upgrade and same-version restarts; item 7 names and Stop; item 8 rendering.

## 6. Not verified

- The moved-cover hold (item 2): needs a data-folder storage move. Unit tests only.
- Real On hold block, «Похититель детей», the `Show in list` button: no real hold produced.
- Real 5 min stall, a slow or hung source drive wait text, a real NAS (`remote_legacy` file removal on Z:), the NAS backlog restart, restart after rollback.
- Manual Conversion window: pre-tick and Save As start folder (native dialog).
- Waiting-for-you with the real engine flag true.
- Focus moving when a focused row leaves.
- Packaged build, tray, installer: not part of this lean pass.

## 7. Cleanup and personal folders

- Backends (ports 5290, 5291) stopped through their own shutdown route; no listener left; the lock helper released its handle. No installer, no Electron process of mine.
- Scratch folder `I:\AI Projects\Studio Illuminati\WIP\Books Arranger\scratch\futaba-0290\` (snapshots of 0.29.0 and 0.28.13, fixtures, catalogs, probes, screenshots): removed with `node scripts/studio-sweep.mjs --apply --path <that literal path>` (dry run first: exactly one item planned; applied: `REMOVED 258.26 MB`), and confirmed gone (`ls` finds nothing). Headless leases: `list` shows none. The tool repo shows only two untracked files, Senua's review and this report; I committed nothing and did not switch the branch. One unrelated leftover seen in the sweep, not mine: `(superseded evidence folder, removed)` reported STUCK (needs an ACL fix or administrator).
- The browser's personal-folder check ended `clean (7 folders, 11 drive roots)` in all runs but one. The one that listed something (run `futaba-0290-you`, 19:53:22 to 19:57:27), copied verbatim, list only, nothing deleted or moved by me:

```
NEW      I:\AI | created 2026-11-17 19:53:28, inside the run window (2026-11-17 19:53:22 to 2026-11-17 19:57:27)
```

- Builder's entry log: `Entry-check personal folders: clean (7 folders, 11 drive roots watched)`.

## 8. Pattern alerts

- **PA-1: new page-to-server fields and hooks pass the entry check but fail in the running app.** This build has three instances: the names check that refuses `light_novel` (B-1), the review check that reads an undefined name (M-1), and the scan-end hook that the pass refuses to run from (M-2). In each the entry tests use mocks, a direct call or a fixture that skips the real hop. Suggested disposition: **DEFER to Ender** after this fix batch, as a maintenance item: one HTTP-level test per new field and hook (post the exact body the page sends; start a real scan and check the pass ran). Jane and Sergei to confirm the disposition.
- Other patterns: none.
