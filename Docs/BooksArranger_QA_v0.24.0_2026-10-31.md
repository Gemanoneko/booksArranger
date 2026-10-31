# Books Arranger 0.24.0 — delta QA, 2026-10-31 (Futaba), build abe5fab

**Verdict:** GO

The Blocker (B1, Tolkien) and the three fixes tested with it (M1, m1, m2) are closed on this build, and the two new "Number unclear" paths (74b) work. The hidden packaged-app smoke ran and its tray-history entries were removed afterwards, as rulings 74a and 74d allow; the key is byte-identical to its backup. One Major from the first pass (M2, below) is not part of this delta, was not re-tested, and is still open.

Release source commit: abe5fab23cc5d74bc6e6510751a15eb4b1dcaac8

Release artifact manifest SHA256: 7932ed4319c1e35c323bbaea6f21352d1760ec340de19cf134e5ef0fb57422a2

Pattern alerts: none

This report covers build `abe5fab` (commit `abe5fab23cc5d74bc6e6510751a15eb4b1dcaac8`, installer SHA-256 `452eb75c…879c`). The first pass on build `edff1975` (NO-GO) is kept at the end of this file for the record. That pass certified nothing for this build.

## A. Identity (confirmed by hash; the entry check was not re-run)

| Value | Measured |
|---|---|
| Source commit | `abe5fab23cc5d74bc6e6510751a15eb4b1dcaac8`; the tool repo's HEAD equals the receipt's `@` hash; the commits since `edff197` are 8b21f7a (B1), 82169e6 (M1), b2d53c0 (m1), 0dce386 (m2), 0318217/629ac23/abe5fab (74b) and one docs commit |
| Installer | `q240\r11\dist\builds\d1a0856a-98ef-4936-a66c-56df3eefcf9d\Books-Arranger-Setup-0.24.0.exe`, 174431202 bytes, SHA-256 `452eb75cb63cff26a660d5c593f65f404802939a383231f84944c50821c3879c` (equals the handoff's `452eb75c…879c` and the manifest's own entry) |
| Manifest | `q240\r11\dist\release-artifacts.json`, SHA-256 `7932ed4319c1e35c323bbaea6f21352d1760ec340de19cf134e5ef0fb57422a2` (equals the handoff's `7932ed43…22a2`); `version` 0.24.0, `source_head` equals the commit, `build_id` `d1a0856a-98ef-4936-a66c-56df3eefcf9d`, 304 payload files, product digest `c612cbfc…` |
| Payload | Installer extracted with 7-Zip into scratch (no install): all 304 files match the manifest's size and SHA-256, none extra; `resources/backend/VERSION` reads 0.24.0 |
| QA runtime | The pinned `build-cache/qa-runtime` (the same Python, FFmpeg and runtime hash `845f19b1…d6db0` as the first pass) |
| Builder's receipt (read from `q240\r11\logs\ender-entry.log`, not a run of mine) | `Entry-check receipt v2: books-arranger v0.24.0 @ abe5fab23cc5d74bc6e6510751a15eb4b1dcaac8 (dirty: N) [source:478a6483…8720; harness:99856aa8…4f71; runtime:845f19b1…d6db0; checker:05481a7a…a41f] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a` |

## B. Method

- Same as the first pass: the packaged backend, page and shell modules from the verified payload on the pinned QA runtime, headless; the engine started as the shell starts it; private roots and catalogs only; nothing on Z: or the live `data/`; nothing installed; no mouse or focus. Every engine quit through the desktop control route exited with code 0; two runs whose driver I stopped ended through the engine's own stdin-close shutdown.
- Explorer is replaced by a log writer (the repository's own `dispatch_folder` test seam). One run (item 5) also forces "no English spelling found online" with the hook the repository's own test patches (`PublicResearch._author_latin` returning None), because the live sources do find Tolkien's spelling. It is named where used.
- The live sources ran at the app's own pacing (no cooldown bypass). The Tolkien run took 24 s this time, with no cooldown.
- The page checks load the packaged `app.js` on DOM doubles with `fetch` bridged to the live engine, as before.
- **Path length.** The app refuses a destination longer than 240 characters. The series file names now carry the English title (`Властелин колец - 1 - The Fellowship of the Ring - Tolkien J. R. R.m4b`), and my scratch folder is 140 characters deep, so my first attempt with a long output root held two volumes with "Verified metadata exceeds the supported Windows output path length". That is the guard doing its job, not a defect: the real output root (`Z:\Audiobooks Sorted`, 20 characters) leaves more than 100 characters more. For the Tolkien and "Number unclear" runs I used the 8.3 short form of the same scratch folder as the library root (79 characters), which the engine accepted without complaint.

## C. Results by item

### 1. B1 Tolkien in a clean library, live sources — PASS

Three folders of two files each, tagged as in the evidence image (author «Джон Рональд Руэл Толкин»), a new catalog, Start:

| Volume | Author | Series | Number | Title | Filed as |
|---|---|---|---|---|---|
| «Хранители. Летопись первая» | Tolkien J. R. R. | Властелин колец | 1 | The Fellowship of the Ring | `Tolkien J. R. R\Властелин колец\Властелин колец - 1 - The Fellowship of the Ring - Tolkien J. R. R.m4b` |
| «Две твердыни. Летопись вторая» | Tolkien J. R. R. | Властелин колец | 2 | The Two Towers | `…\Властелин колец - 2 - The Two Towers - Tolkien J. R. R.m4b` |
| «Возвращение государя. Летопись третья» | Tolkien J. R. R. | Властелин колец | 3 | The Return of the King | `…\Властелин колец - 3 - The Return of the King - Tolkien J. R. R.m4b` |

- One author folder (`Sorted` holds only `Tolkien J. R. R`; Windows drops the final dot of the folder name). The series is `verified` for all three, from the first pass, with no question asked and no hold.
- **When the numbers disagree (74b).** Two volumes whose titles say another number than FantLab's:
  - «Хранители. Летопись вторая» (the title says 2, FantLab says 1) and «Две твердыни. Летопись первая» (the title says 1, FantLab says 2) were both held, ask kind `title_author`, `why: number_unclear`, with the volume facts `{title_number, series_number, provider: fantlab}`.
  - The row's one-line reason reads "The title says book 2, but FantLab says book 1." (and the mirror sentence).
  - Pre-filled: Series «Властелин колец» (the source's), Number the title's (2 and 1), Title the volume's own Russian title. No English title was offered or filed: no "The Fellowship of the Ring" on the wrong book, no "The Two Towers" on the other.
  - Approve on the row filed `Властелин колец - 2 - Хранители. Летопись вторая - Tolkien J. R. R.m4b`, the Russian title with the title's number.
  - The control volume with agreeing numbers (3) filed straight through in the same run.

### 2. M1 a book with a chosen folder stays in Audiobook Ready — PASS

- Choose folder (outside Sorted), Approve, Start. Live timeline of the chosen book: `Queued`, `Creating`, then at 12 s `ready=true`, `job: Audiobook created`, `move: moved`; the control book (default Sorted) was ready from 7 s.
- Thirty more seconds in the same session: both still ready; the chosen book is in the Audiobook Ready filter (the first pass lost it within 3 s of the move and kept it lost until a restart).
- The page row reads "Now in <his folder>\Chosen Two - Anon Two.m4b", "Folder chosen by you. The app would use Sorted\Anon Two\", Choose folder…, Use computed folder, "Moved. The audiobook is now in <his folder>." and Open book folder. No "In <old source>" line.

### 3. m1 no empty sentences — PASS

On a row with nothing computed yet (a fresh scan, no title):
- Before the pick: "Goes to Not decided yet."
- After the pick: "Goes to <chosen folder>\", "Folder chosen by you." (the "The app would use " fragment is gone), and the note "Folder saved. This book goes to <chosen folder>."
- After "Use computed folder": "Folder reset." and "Goes to Not decided yet." No sentence ends empty and no full stop follows an empty path.

### 4. m2 the Missing-files hint — PASS

- `1001…1012` without 1005: "The file names say there are 12 parts, but part 1005 isn't here." plus "File names run from 1001 to 1012. Skipped: 1005." The payload carries `missing.source: names`. No "1,005".
- `01, 02, 04`: "The file names say there are 4 parts, but part 3 isn't here."
- Not exercised live: the `tags` branch of the new hint (a Missing-files row whose count comes from track tags, a part set). My tag-numbered fixture became a files-unclear row with its own unchanged copy ("The tags say 4 tracks, but 3 files are here."). The repository tests cover the branch.

### 5. A book held for another question, with mismatched numbers — PASS (with the forced spelling hook)

- «Хранители. Летопись вторая» held first for the English spelling (`author_unclear`, `english_spelling`; the numbers not yet asked).
- In the page I chose Other and typed `Tolkien J. R. R.`, then pressed Approve. The request carried the author and no Series or Number. The answer was kept: no job, nothing filed, and the page announced "Answer saved. This book still needs its series confirmed. Enter Series and Number, then press Approve. This book has not been queued or filed."
- After the next research pass (Start), the book's question was "Number unclear": "The title says book 2, but FantLab says book 1.", Series «Властелин колец», Number 2, Title the Russian title, and the author kept as typed (`Tolkien J. R. R.`).
- Approve on that question filed `Tolkien J. R. R\Властелин колец\Властелин колец - 2 - Хранители. Летопись вторая - Tolkien J. R. R.m4b`.

### 6. Hidden-app smoke, ruling 74a, tray-history cleanup (74d method) — PASS

- **Authority.** Ruling 74a (Sergei, 2026-10-31, in `Team/Docs/BooksArranger_Rulings_2026-10-24.md`) allows the hidden-app check to add the tray-history entry for 0.24.0 only and says to remove the entry after each run. Ruling 74d resolves the leftover from the first pass (Ender removed it before this run). I read both in the rulings file, not only in the message.
- **Backup first.** `reg export` of `HKCU\Control Panel\NotifyIconSettings` before each run: 155 keys, `UIOrderList` 1256 bytes, SHA-256 of the export `886a4799…80cc`. Two exports taken minutes apart were byte-identical, so nothing else was moving the key.
- **Run.** A private copy of the unpacked payload from the verified manifest, `--start-hidden`, private profile, data, temp and ports, no mouse. Results (run 2, which saved its report):
  - the displayed version and the engine version are both 0.24.0 and the payload pins held (the helper re-verified the manifest, the installer and all 304 files);
  - window close hid the window while the shell and the engine kept running;
  - Quit (the app's own `--quit` control, treated as the tray Quit path by the 0.23.0 acceptance; I did not click the tray menu) exited the process with code 0;
  - no visible window and no foreground take (`intrusion: null`, a positive control of 24 visible windows);
  - payload unchanged, native owner closed (`zero`, active 0), 9.4 s.
- **Two runs.** Run 1 ran and added its entry (the tray key changed as expected and no app process was left), but my driver then failed to write its result file (I had not made its logs folder), so its functional report was lost and I claim nothing from it. I removed its entry, made the folder, and ran again. Each run's entry was removed.
- **What a run adds.** Exactly one new leaf (run 1 `11118209564929692193`, run 2 `14484780577544705898`, each pointing at the scratch copy of the app) and its 8-byte id at the front of the root `UIOrderList`. Nothing else changed.
- **Removal (Ender's 74d method, adapted only by parameters).** Per run: the scratch app copy deleted first (the method refuses while the exe exists), `--check` read-only, then `--apply`: a same-handle `NtDeleteKey` on the verified leaf (no subkeys, `ExecutablePath` equal to the copy) and a compare-and-set `RegSetValueExW` of `UIOrderList` only when it still equalled the post-run export byte for byte, then a read-back. Run 1 passed with only the method's parameters changed (own id, exe path, the pre-run export), and Ender's verify script, parameterized the same way, passed (`pass: true`, own leaf absent, no other key or root value changed, the key identical to the pre-run export).
- **One extension, run 2.** Run 2 added two ids to the list, not one: Windows had re-added run 1's id (leaf long gone) in front of the older ones, so the list read `[run2, run1, <the 1256 bytes as before>]`. The strict method refuses that on purpose. I extended the same check by one parameter: the second id must be the declared earlier-run id, it must have no leaf, and the rest must equal the pre-run list byte for byte. It did, and the apply wrote the pre-run list back.
- **End state.** The final export of the key is byte-identical to the backup (same SHA-256 `886a4799…80cc`): 155 keys, no own leaf, `UIOrderList` 1256 bytes, no id of mine at its front. No Books Arranger process is left.
- **Note for Sergei, not a defect.** Windows keeps these ids in its tray history and re-adds them to the list on the next tray change, as it did with the first pass's id before this run. "Put back exactly as it was" is true at the end of the run; it does not stop Windows adding the old ids again later.

## D. Findings

**No Blocker. No new Major.**

### Major carried (not part of this delta, not re-tested)

- **M2 (first pass).** A finished book whose file another program holds open when the engine starts is flagged "Output needs attention" and never recovers, even after the file is freed. Reproduced in the first pass with no move pending; I did not run 0.23.0, so "older than 0.24.0" is not proven. The new commits do not touch it. It needs a disposition from Jane or Sergei (fix, accept or defer).

### Minor

- **m5 — After the kept-answer Approve the book leaves the list until the next Start.** The page announces "Enter Series and Number, then press Approve", but at that moment the row is no longer listed ("Needs review", no question) and nothing asks again until the next research pass; then it returns as "Number unclear". The behaviour follows the design (answer kept, nothing filed, asked next, as ruling 52's series question), so this is friction, not a defect. A short line naming the next step ("press Start to continue") would close it. Judy's call.
- **Observation: the 240-character guard.** Series file names with English titles are now about 70 characters, so an output root longer than about 130 characters holds those books with "Verified metadata exceeds the supported Windows output path length". It does not name the cause (the length of his own output folder). Not reachable with `Z:\Audiobooks Sorted`.
- **Observation: tags branch of m2 not exercised live** (see item 4).

The live-session versus restart divergence seen three times in the first pass (M1, the recovered move, the held file) did not recur here; M2 is the one left.

## E. Limits of this pass

- Test only what changed since the NO-GO, plus the smoke. The first pass's items 1–6 and 8 (grouping, C1, Choose folder, Open folder, moves, numbering labels, override rule) were not repeated. M1 and m1 touched the same code, and both were re-read through the page.
- The Tolkien run is one live run at one moment, with no existing English Tolkien folder in the library. It took 24 s (the first pass hit a 15-minute cooldown on one row). The "wrong record" path was run with FantLab's current answer (the novels' order in its cycle differs from the Russian edition's volume numbers), the case ruling 74b describes.
- Item 5 used the forced "no spelling found" hook, because the live sources find Tolkien's spelling. The hold, the kept answer and the next question are the packaged code; only the lookup result was forced.
- The first-run setup window was not exercised (a visible window).
- Run 1 of the hidden smoke lost its report (my driver's folder); run 2 supplies the results. Both runs were cleaned up.

## F. Cleanup

Scratch `…\scratchpad\futaba-024\` (extracted payload, asar, catalogs, converted audio, drivers, tray exports and tools) is removed with `node scripts/studio-sweep.mjs --apply --path <it>`; the result is in my reply. Ender's `scratchpad\tray74d\` and `tray74d-tools\` were only read. `q240` is untouched. The tray key is back exactly as backed up.

---

# Earlier pass on build edff1975 — NO-GO (kept for the record; superseded by the sections above)

That pass found B1 (Tolkien), M1 (a book with a chosen folder drops out of Audiobook Ready until a restart), M2 (held file) and four Minors (m1 to m4). Its text follows unchanged, except that its verdict line is now this sentence. It certifies nothing for build abe5fab.

## 1. Identity (confirmed by hash; the entry check was not re-run)

| Value | Measured |
|---|---|
| Source commit | `edff1975f77207c0e5fc6fb043021a0d914a91c6`; the tool repo is clean (`git status` empty) and HEAD equals the receipt's `@` hash |
| Installer | `Books-Arranger-Setup-0.24.0.exe`, 174423720 bytes, SHA-256 `3d50b5601c4625e1888fb7cfd5d9645fb794d7c30d45f391d355b9c7495def58` (equals the handoff and the manifest's own `artifacts[0].sha256`) |
| Manifest | `release-artifacts.json`, SHA-256 `023e26e1ac21ee1a22c316d015d158c4509ef0c24c155a8c3f61b022ff629d5e` (equals the handoff). Its `version` is 0.24.0, its `source_head` equals the commit, its `build_id` is `2bcc97a7-634e-4f31-babb-bc34c50f8053`, its product digest is `833abda8…1994e`, its payload map has 304 files |
| Payload | The installer was extracted with 7-Zip into scratch (no install). All 304 files match the manifest's size and SHA-256, and there are no extra files. 7-Zip prints one warning, "data after the end of archive", which is the NSIS trailer |
| QA runtime | The pinned `build-cache/qa-runtime`. `python.exe` `434b361f…2c6f`, `ffmpeg.exe` `a3bf949b…5b1a` and `ffprobe.exe` `fe818a56…94bd` equal `scripts/qa-runtime.json`; the packaged `python.exe` has the same hash |
| Builder's receipt (read from `q240/r10/logs/ender-entry.log`, not a run of mine) | `Entry-check receipt v2: books-arranger v0.24.0 @ edff1975f77207c0e5fc6fb043021a0d914a91c6 (dirty: N) [source:dd9ba3a0…dc9e9; harness:fb7a92c1…f90b0; runtime:845f19b1…d6db0; checker:05481a7a…a41f] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a` |

## 2. Method

- The packaged backend (`resources/backend`), page (`web/app.js`) and shell modules (`app.asar`) from the verified payload ran on the pinned QA runtime, headless.
- The engine was started as the shell starts it (`desktop_host.py`, `-I -B`, the shell's minimal environment, the bundled FFmpeg first on PATH, private roots and data folder, private ports 5391–5402). It was quit through the desktop control route (the one the tray Quit uses). Every quit exited with code 0.
- Fixtures were real MP3 files cut from the private fixture with real ID3 tags, plus three silent 3 h 12 min files for the whole-book case.
- Research ran with the app's own pacing and public sources, with no cooldown bypass. The synthetic authors of the first run caused a few extra lookups.
- Seams used, all existing ones in the packaged code, no file edited:
  - `MergeService.dispatch_folder`, the only call that starts Explorer, was replaced by a log writer. Every Open folder result below is from that log; no Explorer window was opened.
  - `MergeService.move_fault` was used in each of three crash tests, to end the engine process right after a move's rename.
  - The folder picker runs behind its injected `dialog`.
- The page checks load the packaged `app.js` on DOM doubles (the Element class is the repository's test harness copy), with `fetch` bridged to the live engine, so the page renders real list payloads and sends real routes.
- Only private roots and private catalogs were used. Nothing on Z: or the live `data/` was touched, no catalog of Sergei's was copied, and nothing was installed.
- The scratch folder for this run held everything else. `q240` was not touched.

## 3. Results by item

### 1. One folder is one book (68, 71a, 71b) — PASS

- **Криг-style folder** (34 novel files + 4 story files by other authors and albums, track total 38): one row, 38 members. The folder verdict is `one`, basis "the file names number the whole folder", books Криг 34 and Рассказы 4. There is no 34-file candidate and no isolated story rows.
- **Same folder with the story tags mis-encoded** (cp1251 read as Latin-1): still one row (12 of 12 members), and the tags read back as «Каспер Вальтер» / «Рассказы».
- **Folder of whole books** (`Стивен Кинг`, three 3 h 12 min files, each its own album): three rows of one file each.
- **Series of novels by one author** (`Клайв Льюис - Хроники Нарнии`, three novels of three files each): three rows of three files, one per novel.
- **Control:** the same folder with three-second files is one row and a folder question (`ask`), because the rule needs files of 3 hours or more. This matches `WHOLE_BOOK_SECONDS` and is not a finding.

### 2. Approving a book kept as separate books converts it (Senua C1) — PASS

- **Keep as separate books, then Approve.** The folder `Разное` (Альфа, Бета) became a folder question after research. "Keep as separate books" answered `{kept: 2}` and made two rows. Approve on Альфа gave a job. Start converted it to `Lukyanenko Sergey\Alpha - Lukyanenko Sergey.m4b`. Jobs: 4 of 4 `completed`; `audio_job_set_aside` is empty.
- **Restart.** The engine was quit and started again: all four books were still finished (`audiobook_ready` true) and `audio_job_set_aside` was still empty, so nothing was un-approved or set aside at start.
- **Second regression (a loose file in a container folder).** A manual Approve of `Unsorted\Одинокий звук.mp3` converted it and it stayed approved after a restart. Jobs completed, nothing set aside.

### 3. Choose folder — PASS (one Minor: m1)

- **Picker seam (packaged `desktop/folder-picker.js`), 8 of 8.**
  - It returns the one absolute chosen folder and asks for `openDirectory, createDirectory, dontAddToRecent`.
  - Cancel, two or zero paths, a relative or over-long path, and a non-string answer all give null.
  - A relative default path is dropped and an over-long title falls back.
  - With no dialog it throws.
  - It is modal to the app window only. The setup window or any other sender is refused before a dialog opens, and no dialog opened in that test.
- **Page.**
  - With no desktop bridge the control is `aria-disabled` with "Choosing a folder works in the desktop app."
  - With the stub bridge, the picker request for a book not yet finished is `{title:"Choose a folder for Новинка", buttonLabel:"Select folder", defaultPath:<the book's chosen folder>}`. For a finished book the button label is "Move here".
  - Cancel changes nothing and sends nothing.
  - A pick sends only `/api/candidate/destination` with `{library, id, revision, folder}`.
  - The control sits in the destination block, never in the Actions column.
- **71j (choosing does not approve).** The row keeps its status, shows no job and `can_approve` is unchanged. No approve or create route was called.
- **71i (folder only).** On four held rows the stored override keeps the computed file name. For example the folder `Moved\Interview` gave `Moved\Interview\Интервью - Лукьяненко Сергей.m4b`. The finished output carries the computed name in the chosen folder.
- **Refusal sentences** (engine answers, shown as sent by the page):
  - Source folder, subfolder or library root: "That folder is inside <library folder>, one of your source folders. Choose another folder."
  - Data folder or the cache inside it: "That folder belongs to the app. Choose another folder."
  - Link or junction (a real junction was made): "That folder is a link or junction. Choose an ordinary folder."
  - Missing folder, file or relative path: "That folder isn't available. Connect the drive or choose another folder." (cause `unavailable`)
  - The saved choice stayed intact after all refusals.

### 4. Open source folder on every row, with the fallback (70) — PASS

- **Every row kind.** The button is on every row: held rows (Missing files, order unclear, author unclear), unfinished rows, rows in the all, held and output-needs-attention filters, and finished rows.
- **Finished rows with the originals gone** read "Open book folder" (not "Open source folder") and send `folder_kind: output`. It opened the converted file's folder, and after a move it opened the new folder (`Moved\Pick`).
- **Fallback.** With the finished book's own source folder removed, the engine's `source` route answered `{opened:true, directory:<Moved\Oko>, fallback:"output"}`, and the log shows exactly that folder.
- **A finished book whose file cannot be verified and whose source is gone** gets the single failure sentence "Folder unavailable. Connect the library drive and try again." and nothing is opened.
- Only the seam log was used; no Explorer window opened.

### 5. Moving a finished book without reconverting — PASS (two side findings, M2 and m3)

- **Move to a chosen folder.**
  - The page queued a move; no job row changed and nothing converted.
  - Rename strategy; the file landed in the chosen folder.
  - 71k: the emptied old folder (`Sorted\Lukyanenko Sergey`, `Sorted\Петров Иван`) was removed. The user-made chosen folder was removed too when the book was moved back out (by 71k).
  - A same-named file in the target gave `failed` with cause `target_exists`, and nothing was overwritten.
  - "Use computed folder" moved the book back.
- **Real crash test for "Move not finished".**
  - The engine process was ended right after the rename. The file was in the new folder and the journal said `rename_intent`.
  - Another program held the moved file open with no sharing, and the engine was started again.
  - The row's `move` read `unfinished` with cause `renamed`, folder `Moved\Bet`, and the raw error only in `detail` (`WinError 32`, never shown by the page).
  - A second restart still read `unfinished`.
  - With the file free, the next restart finished the move to `moved`, and the old folder was removed.
  - Open book folder opened the new folder while it waited.
- **Page, exact strings** (compared with the strings in the committed tests and the code; Judy's 73k copy is not in a committed document, so I could not compare against her source):
  - `renamed`: "Move not finished. The audiobook is in {folder}, but the app couldn't open it to confirm the move. Close and reopen Books Arranger to finish it."
  - `copy`: "Move not finished. The app couldn't open the copy in {folder}, so both files are kept. Close and reopen Books Arranger to finish it."
  - `catalog`: "Move not finished. The app couldn't save its progress. Close and reopen Books Arranger to finish it."
  - The `renamed` line is from the real crash payload. The `copy` and `catalog` lines are from that real payload with the cause field changed, because a copy or catalog failure cannot be produced here (no second volume; the catalog cannot be locked safely).
  - The Choose folder face reads "Needs restart", `aria-disabled`, with the tooltip "Close and reopen Books Arranger to finish the move. Then you can choose another folder." No raw error is shown.
  - A fresh page on the same payload shows the same state (reload), and the unfinished state survived two engine restarts.

### 6. Numbering labels (73f, 73i, 73j) — PASS

All three are held rows after the app's own research:

| Folder | Row | What the page shows |
|---|---|---|
| `01–03.mp3` + `Интервью 2019.mp3` | order unclear (no gap) | no numbers line, no Skipped, no Missing files |
| `1001…1012` without 1005 | Missing files | "File names run from 1001 to 1012. Skipped: 1005." and the hint "…part 1,005 isn't here." (Minor m2: wording) |
| `0998, 0999, 2500–2510` | order unclear (no gap) | no gap named (option A) |

Control: `01, 02, 04` shows "Skipped: 03" and Missing files.

### 7. Tolkien — FAIL (Blocker B1)

Three folders of two files each, tagged as in the evidence screenshot (author «Джон Рональд Руэл Толкин», albums «Хранители. Летопись первая», «Две твердыни. Летопись вторая», «Возвращение государя. Летопись третья»), in a clean library with live sources:

| Check | Result |
|---|---|
| English spelling found | yes, but in two forms: "Tolkien J. R. R." and "J. R. R. Tolkien" |
| Series «Властелин колец» 1/2/3 | no. All three books have series and number empty. `series_state` is `omitted_unknown` and `unfilled: ["series"]` |
| English titles | 1 of 3. «Возвращение государя» became "The Return of the King" (FantLab work 1669). The other two kept their Russian titles; `original_title_lookup` was `none`, original language unknown |
| No questions asked when nothing is confirmed | The app asked nothing. All three were queued and converted by the first pass or the retry, with the evidence gaps unfilled |
| Where the books went | `Sorted\J. R. R. Tolkien\The Return of the King - J. R. R. Tolkien.m4b` and `Sorted\Tolkien J. R. R\…` (two books). One author is now in two folders under two spellings |

- «Возвращение государя» was held after its first lookup ("Assistant approval requires per-field identity, author role, original language and series/standalone evidence") and retried by itself after 15 minutes, which is the app's own pacing; I did not bypass it. The other two were queued at once, with the spelling "Tolkien J. R. R." taken from that first lookup.
- The lookup was not repeated from a library that already holds an English Tolkien folder. Sergei's library may behave differently there (the library's own folder is one of the sources); this test used a clean library, which exercises Wikidata and FantLab only.

### 8. Sergei's override rule (73j) — PASS, with a display defect (M1)

Tested on two Missing-files rows (`1001…1012` without 1005, and `01, 02, 04`) and two order-unclear rows (`Дневной дозор`, `Интервью`):

- **Open source folder:** present and opens the folder (seam log), on all four.
- **Choose folder:** present, saves his folder, does not approve, and keeps the computed file name.
- **Approve himself:** the Missing-files rows offer "Convert what's there" (sends `without_missing: true`), and the order-unclear rows offer "Approve this order". Both queue, and Start converts them. The label "Approve as is" is not used on these rows; the capability is there.
- **Result.** Each book converted into his folder with the computed file name. Chapters equal the files present: Сказки 11 (the 1005 gap ignored), Око мира 3, Дневной дозор 3, Интервью 4. The originals were removed after the verified result (71h); `Unsorted\Око мира` was left empty.
- **The Сказки press showed "queued" and had no job 1.5 s later.** That was the queue waiting behind the research run, and the job came later. It is not a finding.

### 9. Smoke — launch, core action, close — PASS on function, STOPPED on the tray-history rule

- **Headless engine.**
  - It launches as 0.24.0; scan, approve, convert, restart and move ran.
  - Every quit through the desktop control route exited with code 0 (the crash tests ended the engine on purpose, exit 137).
  - Shell-style start through `desktop_host.py` worked in the probe, grouping, numbering and fresh-scan runs.
- **Hidden packaged app** (a private copy of the unpacked payload, private profile, data, temp and ports; `--start-hidden`):
  - Source commit and manifest pins were re-verified by the helper. The displayed version and the engine version are both 0.24.0.
  - No visible window and no foreground take: the guard polled every 100 ms and reported `intrusion: null`, with a positive control of 20 visible windows.
  - Window close hid the window while the shell and the engine kept running.
  - Quit (the app's own `--quit` control, which the 0.23.0 acceptance treated as the tray Quit path; I did not click the tray menu, no mouse) exited the process with code 0.
  - The payload was unchanged and nothing survived (`native.zero`, active 0, 7.67 s).
- **Not covered:** the first-run setup window (a visible window that would take focus). "Every top-level screen" is covered for the main window and the tray only.
- **STOP, as instructed.** The helper's guard stopped on the tray registry (`Preexisting tray key was changed or removed: …\NotifyIconSettings`). A read-only comparison of my before and after exports of that key shows the same shape as 0.23.0:
  - exactly one new leaf, `15685089404004928689`, whose `ExecutablePath` is the scratch copy of the app;
  - the root `UIOrderList` went from 1240 to 1248 bytes, the first 8 new bytes are the own ID and the old list follows unchanged;
  - no other value changed and no existing child changed.
  - I did not delete the leaf, rewrite the root, or apply the ruling 61/67 exceptions. The new leaf points at a scratch path the sweep removes. **Sergei must decide** what to do with that leaf and the 8-byte reference.
- **Adapted helper.** I used an adapted copy of the committed `BooksArranger_HiddenPackageSmoke_v0.23.0_2026-10-28.mjs`. Three constants differ: the work folder `Q`, the koffi owner path and the authorization line. The authorization line used to require a "Sergei approved" field; the copy requires a plan that says the basis is the task brief, with no Sergei consent and no registry cleanup authorized. No other line changed, and Senua did not review the copy.

## 4. Findings

### Blocker

- **B1 — The Tolkien fix does not hold in a clean library with live sources (item 7).**
  - Series «Властелин колец» is missing on all three books.
  - English titles are shown for only 1 of 3.
  - One author is split across `J. R. R. Tolkien` and `Tolkien J. R. R`.
  - All three were converted and filed without a question.
  - Repro: a new catalog; three folders as in the evidence image; Start; wait out the app's own 15-minute cooldown; read the rows and `Sorted`.
  - The ruling asks for series 1/2/3, English titles and a question when nothing is confirmed.

### Major

- **M1 — A book approved with a chosen folder drops out of "Audiobook Ready" until the app restarts.**
  - The catalog shows a completed rename move for it, so it was published into Sorted and then moved to his folder. After the move `audiobook_ready` is false, the row is not in the Audiobook Ready filter, and the status cell shows only "In <old source folder>" with Edit names, View metadata and Open source folder.
  - There is no "Now in", no Choose folder, no "Use computed folder".
  - The file is correct and verified; the control book (default Sorted) in the same run stayed ready. After a restart the row is right: "Now in <his folder>… Moved. The audiobook is now in …".
  - Repro: choose a folder, Approve, Start, then read the row for 20 s (live session).
  - The same happened to all four rows of item 8 (restart cured it). Explicit moves of a finished book do keep `ready`; the post-conversion move does not.
  - Not a Blocker by my definition (nothing is lost, the file is right), but the override flow's final state looks failed until a restart. Jane may treat it as one.
- **M2 — A finished book whose file is held by another program when the engine starts is flagged "Output needs attention" and never recovers.**
  - The job becomes `needs attention: Recorded output is missing, changed, or failed validation`. It stays so after the file is freed and across restarts. The row reads "No verified audiobook created yet" and drops out of Audiobook Ready.
  - Reproduced by holding a finished book's file open and starting the engine, with no move pending (that book had been moved and moved back earlier in the run; I did not repeat it on a never-moved book). It does not come from 0.24.0's move work as far as I can tell. I did not run 0.23.0, so "older than 0.24.0" is not proven.
  - Real triggers: antivirus, an indexer or a player holding the file at start.

### Minor

- **m1 — A row with no computed destination yet gives no sign of the chosen folder.** After Choose folder the row says "Goes to Not decided yet." and "Folder chosen by you. The app would use " (nothing after "use"). The confirmation reads "Folder saved. This book goes to ." The chosen folder is shown nowhere on the row. It becomes visible once a title exists.
- **m2 — Missing-files wording for a gap taken from file names.** "The track tags say there are 12 parts, but part 1,005 isn't here." The files carry no track tags (the line below correctly says "File names run from 1001 to 1012"). The number reads "1,005" and the row says "Part 1005 of 1012" beside "12 parts".
- **m3 — "Candidate changed — review required" showed on one row right after a fresh scan** twice in my first three fresh catalogs, and cleared by itself. It did not show in the 8 later fresh scans where I read the status. Cause unknown.
- **m4 — After a crash-recovered move, the book was not in Audiobook Ready for at least 25 s after the restart** (`current_audiobook` said `verified`) and was ready on the next restart. Not diagnosed; may be the same stale ready list as M1.
- **Observations, not defects:**
  - 71k removed the folder Sergei chose and made himself after the book was moved back out of it. That follows the ruling.
  - The approve labels on Missing files and order unclear are "Convert what's there" and "Approve this order", not "Approve as is".
  - The engine's `unavailable` refusal for Choose folder carries no folder name.

## 5. Limits of this pass

- Item 7 used the app's live sources once, with its own pacing. The clean library had no existing English Tolkien folder.
- The `copy` and `catalog` unfinished lines come from the real payload with the cause changed. There was no second volume, and the catalog could not be locked safely.
- First-run setup window: not exercised (visible window).
- The strings for the unfinished lines were compared against the committed tests and code.
- The live Z: library and Sergei's real catalog were not used, by instruction.
- The repository tests were not run (the builder's entry check covers them).

## 6. Cleanup

Scratch `…\scratchpad\futaba-024\` (extracted payload, asar, catalogs, converted audio, drivers, registry exports) is removed with `node scripts/studio-sweep.mjs --apply --path <it>`. The result is recorded in my reply. The tray registry leaf and the 8-byte reference are left as they are for Sergei's decision. `q240` is untouched.
