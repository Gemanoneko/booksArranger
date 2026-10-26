# Code Review — Books Arranger v0.22.1

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-26
Tool: Books Arranger (Electron / Python)
Release: v0.22.1
Commit range: 143b33b733a2c3dfcd86e89f5c70df9fbbe6b03c..c26bc5823baefdd77dd90f5b12e7e18f410f4a40 (tag v0.22.0 .. origin/main c26bc58, 51 commits)
Release source commit: c26bc5823baefdd77dd90f5b12e7e18f410f4a40
Release artifact manifest SHA256: 72a0f4f776158bb1b1ab37660d13a6e621d7e03e95f5a705ffe2e999654a6585
Reviewed source: C:/Antigravity Projects/Worktrees/Books Arranger/rv0221 (detached worktree at c26bc58, removed after the review); v0.22.0 compared from a git archive of the tag in my session scratch
Files changed: 92 files, +9101 / -1333 (git diff --shortstat). Product code and scripts: 39 files, +4028 / -1216. Tests: 46 files, +3787 / -113. Docs and CHANGELOG: 5 files, +1283 / -1. package.json and package-lock.json: version only.
Stand-down dimensions: none
```

Rulings checked against: `Team/Docs/BooksArranger_Rulings_2026-10-24.md` (2, 5, 6, 6a, 10, 11a, 14, 16, 19, 19b, 21, 23-28), the backlog `Docs/BooksArranger_0.22.1_Backlog.md` and the Brief's 0.22.1 section.

**Artifact pin.** Ender's manifest is `C:/Antigravity Projects/Worktrees/Books Arranger/cand-0221b/dist/release-artifacts.json`. I recomputed every value myself, read-only, with the repo's own `release-contract.mjs` and `release-flow.mjs` (`gitEntries`):
- Manifest SHA-256 `72a0f4f7…a6585` over the file's bytes (no BOM). It equals Ender's value.
- `version` 0.22.1; `source_head` c26bc5823baefdd77dd90f5b12e7e18f410f4a40; `build_id` 2f38bd9a-afe8-47b4-960a-2faa377b85e7; `latest.yml` reads `version: 0.22.1`.
- `product_digest` `42248363…41db` equals `productTree(ls-tree c26bc58)`.
- `artifactContract(manifest, {version: '0.22.1', productTree})` accepts it: three artifacts, payload 288 files with its `manifest_sha256`, runtime 48 files.
- Each artifact matches the manifest's size and SHA-256:
  - `Books-Arranger-Setup-0.22.1.exe`: 174,078,561 bytes, `b24f23a3110d278c88b54149d624f9431cb2e4c2fa913574a47d653aa583e6ab` (Ender's value);
  - the `.blockmap` (181,747 bytes) and `latest.yml` (360 bytes).
- The `cand-0221b` worktree is at c26bc58 with a clean tree. I only read and hashed it.

---

## Summary

**No Critical finding, and the safety floor is intact. Two Major findings, both worth fixing before 0.22.1 ships.**

- **W1 (Major): the folder structure files real books under wrong titles, on its own.** For a one-file book sitting in an `Author\Series` folder, the file name now beats a clean tag title. On the live library that puts the author's name into the title, and once a stray bracket: «Сергей Недоруб - Севастопольский дозор», «Марина Ясинская - Чужой Дозор )». I measured this read-only on the real tags. Nine books of that shape, and «Игры Немезиды 1», are "Waiting for source" in the live catalog today. 0.22.1 researches them again on its first run, accepts them and converts them under these names.
- **W3 (Major): Cancel update does not resume what it stopped.** Neither does the update's own bound or a failed close. The things the update still waits for are, by definition, still stopping, and each restart is refused or skipped while they are. The conversion queue stays paused. The automatic run, the scan and the background lookups stay stopped. The page then says "Books Arranger is running as before." The engine records the failures (`resume_problems`), but nothing shows them.
- **Ten Minor findings** (W2, W4-W12), listed in the rubric. Most are narrow edges of the new updater, startup and identity code. W11 is a gate gap: 23 test modules have always run outside the gate. I ran them: none fails because of 0.22.1, but 8 fail the same way on v0.22.0, so what they cover is checked nowhere.

**Answers to the nine questions.**

1. **The lock change.** No deadlock, and no stale read that leads to a wrong action.
   - Lock order:
     - `progress_books` takes `group_lock` only to rebuild stale groups, and releases it before `_progress_lock`, so the order is always group_lock, then `_progress_lock`.
     - `converted_ids` only probes `_progress_lock` without waiting.
     - The ActionQueue lock is taken under the control lock (`state()` → `view()`), never the other way round.
     - `DesktopControl.lock` is never held while the control condition is taken.
   - The lock-free reads feed display only: the book list, `converted_ids`, `describe()`'s cached location, and the to-do list's "Goes to" cache. Every action re-reads under its own lock or compare-and-set:
     - Delete and Remove this copy plan again under `operation_lock` + `group_lock` and compare the confirmed paths.
     - Scan again writes only through `snapshot(db)==initial` inside `BEGIN IMMEDIATE`.
     - Remove from list keys its record on the fingerprint it read, so a book whose files come back is listed again.
     - Open folder re-leases the location and compares the key.
   - Start's re-check now takes `operation_lock` one book at a time. An approval can start the worker between two books. The prune that follows is the same one that already runs between books after each conversion, so I found no harm in it.
2. **Approve on local identity, `_gap_fill` in the background.** A background fill cannot change a converted book's destination or name.
   - `gap_fill` writes only its own `gap_fill` table, and no product code reads it.
   - It also fills the research cache, which research later reads. That can only change books that are not yet converted, which is intended (ruling 16).
   - Only series backfill renames in Sorted, as before (ruling 17). More books now reach Sorted without a series, so it will rename more of them.
   - Fairness: each background lane gets at most 40 % of a site's hourly bound (`_lane_ready`, a sliding 1-hour window of the lane's own reservations, the Wikimedia family counted together). Research is never lane-limited.
   - One Minor: the fetch now runs outside the lock, so two threads can fetch the same uncached URL at once (W12).
3. **Folder identity and the file-name order.**
   - *Wrong order:* none found. `filename_sequence` needs one 1..N or 0..N-1 run read at the same place in every name, and two runs that disagree cancel each other. I tried disc/track swaps, constant numbers, years and bitrates by hand.
   - *Mis-filing:* yes, W1 (titles) and W2 (a book folder taken as a series).
   - *Wrong join or split:* none new.
     - The "one book folder" join needs every part's album to equal the folder title.
     - The works check is skipped only for a book folder.
     - Separate volumes of one work (Образцов, «Единая теория всего», Том 1-4) now convert as four books numbered 4, where 0.22.0 held three of them. That matches ruling 19b's volume pattern.
     - The `named_order` exemption also drops the disc-total check for any clean-named set. A lone "disc 1 of 2" would now convert as a whole book. That is W9, latent: none on the live catalog.
   - *Reader as author:* not through the folder structure. Every candidate, the folder author included, goes through `offer()`'s reader guard. No top folder of the live library is a reader. But the new "Person. Title" rule can make a character the author when no author tag exists (W8, latent on the live catalog).
   - *Odd-name guards:* `odd_identity` runs on every identity v5 book that nothing else holds. Select all (`pageSelectable`) and bulk Approve as is (`approveSelectable`) both leave out `odd_name` rows. That exclusion is in the page only: the approve route cannot tell a bulk press from a single one. The bulk dialog lists every destination path, so I count it as acceptable, not a finding.
4. **The fail-less updater.**
   - *Interrupting a file change:* no forced stop can do it. The engine never ends itself while anything waits. Every stop is a flag the worker reads between steps. The in-place tag edit, a cleanup disposal, the Delete loop and records, and a series rename each run in a `critical()` block, and a press also holds an admission.
   - *Cancel:* it does not really resume (W3).
   - *A failed install:* it reopens the old app only when the installer fails to spawn. electron-updater's own fallback can still start the installer after that (W7). A silent NSIS failure after the installer has started is not seen; that comes with Sergei's silent-install ruling (Q2).
   - *Data loss:* none. Not counting W7, the app can end half-installed only through NSIS failing after spawn. The shell can still close without installing in one narrow case (W5).
   - *Update source and checks:* not weakened. The feed URL is unchanged. The checksum and admin-installer refusal, the tamper test, the lease-loss test and the native lease are all kept.
5. **Startup.** No request can act on a half-loaded catalog.
   - Every POST is refused with 409 `loading` until `took_ms` is set, except `/api/shutdown` without data. Once the books part is up, View metadata and Open folder are allowed; both are read-only.
   - `/api/inventory` and `/api/cover` answer 503 until the books part. `/api/state` answers from the loader only.
   - No worker or queue can run before `_start_background()`.
   - Two Minors on the edges: the shell hard-kills a loading engine after 15 s (W6), and a failed close in the update path leaves a half-closed engine (W4).
6. **Queued Retry, Repair and Delete.** All three hold.
   - A queued delete runs `merge.delete_book` with the confirmed paths. That plans again with `wait=False` under both locks, compares the paths, and refuses on a new revision or a scan.
   - A stale list cannot delete: `files_changed` or `changed`, nothing touched.
   - Only the confirm request carries `paths`, so the preview cannot queue a delete.
   - A running action holds an admission, so a scan cannot start under it and the update waits for it.
7. **Busy page.** It does not hide a dead engine process. In the desktop window, an engine exit closes the app with its own message (`main.js` exit handler). An engine that stops answering shows "No answer for N min … quit from the tray" after 2 minutes. Not counted: connections refused by a live process (its listener is gone) show nothing in desktop mode. That window is at most the 20 s exit bound.
8. **E1-E5 and the Git runner.**
   - **E1** is closed:
     - The wrapper is generated into `harness/`, covered by the harness digest.
     - The gate's pass line names the runtime root, its tree digest and the fixture.
     - Ender's entry log shows `qa_runtime` = `cand-0221b/build-cache/qa-runtime`, `a3cb3b5e…`.
   - **E2** is closed: `graph.json`'s assembler SHA-256 `3bd3481b…` equals the c26bc58 script.
   - **E3** is only partly closed (W10): `checkRuntime` pins only `python.exe`, `ffmpeg.exe` and `ffprobe.exe`. By hand, all 47 files of the context's runtime tree equal the shipped `runtime.files`; the only file not in the tree is `ffmpeg/BUILD.txt`.
   - **E4** is closed: `cleanGitEnv` strips `GIT_*` and sets `GIT_OPTIONAL_LOCKS=0`, and Git runs with `core.fsmonitor=false`.
   - **E5** is closed: every path is an argument. The defaults are the studio's checker folder and `cmd.exe`.
   - **69039aa:** `assemble()` takes the Git runner as a parameter. Only the test injects one; the CLI always uses the real `gitIn`. HEAD and the clean-tree check run before and after the snapshot.
   - So the receipt is still trustworthy. Ender's receipt reads `Entry-check receipt v2: books-arranger v0.22.1 @ c26bc58… (dirty: N) … check pass`, and its context hashes to the `.sha256` beside it.
9. **The gate.** It runs everything it declared before, plus the six new suites, each once. The ten node suites are now fifteen, and the two new page scripts are syntax-checked. But "everything" is the declared list: 23 test modules sit outside it, as in 0.22.0 (W11).

---

## Rubric

### 1. Security

- Status: Pass
- Findings: none.
  - The Electron settings are unchanged: `contextIsolation`, `sandbox`, no `nodeIntegration`, and `will-navigate` keeps the window on the engine origin.
  - `trustedSender` now also accepts the first frame. It accepts only that exact `file://…/web/index.html`, and navigation away from it is refused.
  - New routes:
    - `/api/queue/cancel`, `/api/queue/ack` and `/api/author-rule/retract` take the page token and a strict shape;
    - `/api/desktop/update-cancel` takes the desktop token;
    - the queue's `title` is bounded to 500 characters and shown only through `textContent`.
  - The diff adds no `innerHTML`.
  - The update feed and the checksum, lease and admin-installer checks are unchanged.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **W1 [Major]** `local_identity.py:1805`, `:1838` (`_structured_title`), `:1793` (the author strip). **One-file books in an `Author\Series` folder take the file name as their title, over a clean tag title.**
    - For `book == 'file'` the "file names carry the folder's title" test (`files_name_title`) is always true, because the "folder title" is that file's own name.
    - So any tag title that differs is replaced.
    - The author strip only removes the *folder's* author. In a shared-universe folder, the book's own author stays in the title.
    - Nested brackets leave a dangling ")".
    - Measured on the live library (tags read read-only from `Z:`, offline research at c26bc58 against v0.22.0), in `Сергей Лукьяненко\Вселенная Дозоров - Межавторский цикл`:
      - 0.22.0: «Севастопольский дозор», «Масть», «Чужой Дозор»…
      - 0.22.1: «Сергей Недоруб - Севастопольский дозор», «Виталий Каплан - Масть», «Марина Ясинская - Чужой Дозор )», five more of the same shape, and «Валерий Пылаев - Запах Сумрака» (was «Дозоры. Запах Сумрака»).
      - They are filed as `…\Вселенная Дозоров - Межавторский\Вселенная Дозоров - Межавторский - 16 - Сергей Недоруб - Севастопольский дозор - Недоруб Сергей.m4b`.
      - Every one of them is accepted with no question.
    - The same rule turns «Игры Немезиды» into «Игры Немезиды 1», the file's part number.
    - In the live catalog these nine books, and «Игры Немезиды 1», are "Waiting for source" with no job. `standing-22-v1` researches them again, locally, on the first run.
    - Their already-converted siblings carry the clean titles.
    - No audio is lost, but the names in Sorted are wrong until the rename pass (ruling 21).
  - **W2 [Minor]** `local_identity.py:1753-1808` (`folder_structure`), `:1719` (`_series_name`). **A second-level folder that names a book, or groups several series, is taken as the series.**
    - Live: `James S. A. Corey\5. Игры Немезиды\5. Игры Немезиды 1.m4b` becomes series «5. Игры Немезиды» #5, filed under `Corey James S. A\5. Игры Немезиды\5. Игры Немезиды - 5 - …`.
    - Live: «Darwin's Blade 1» and «2» become «Dale Stewart Mike O'Rourke» #4. Darwin's Blade is not in that series.
    - Both are "Waiting for source" in the live catalog.
    - A file numbered inside its book's own folder ("Stephen King\Нужные вещи\01 Премьера 1.m4b") would read as book 1 of series «Нужные вещи» if it were ever grouped alone. Today its set is held.
  - **W3 [Major]** `desktop_backend.py:393-433` (`_resume_after_update`). **Cancel update, the engine's bound and a failed close do not restart what the update stopped.** The update waits *because* workers are still stopping, so when Cancel or the bound arrives they are still alive:
    - `merge.resume()` raises `StartRefused('busy', 'The audiobook worker is still pausing…')` (`merge_service.py:838`), so the queue stays paused once the book stops;
    - `automatic.start()` returns at once while the old thread lives (`automatic_processing.py:300`), so the run ends at its stop point;
    - `inventory.launch(resume=True)` raises 'A scan is already running' (`scanner.py:225`);
    - `series_backfill` and `gap_fill` `start()` return while their threads live.
    - The failures go into `outcome.resume_problems`, which no page reads. The Install line then says "Update cancelled. Books Arranger is running as before." (`web/desktop-ui.js:36`, and the same in the `bound` line).
    - `tests/test_desktop_update.py` cannot see this: its fakes' `start()` and `resume()` always succeed.
    - Nothing is lost. The automatic run and the queue simply stay stopped until Sergei presses Start, against ruling 27 ("says exactly why").
  - **W8 [Minor]** `local_identity.py:1920-1930`. **The new "Person. Title" rule (item 10) can make a character the author.**
    - `looks_like_person` accepts «Гарри Поттер», «Анна Каренина», «Джон Картер», «Jack Reacher».
    - A single file tagged «Гарри Поттер. Философский камень» with no author tag, in a folder that names no person, was asked in 0.22.0 (author missing). 0.22.1 files it as `Поттер Гарри\Философский камень - Поттер Гарри.m4b` with no question (synthetic probe), against ruling 11a.
    - Live catalog: 7 folders carry the shape, all with an author tag. None is authorless today. The rule rightly sets aside readers there («Генри Каттнер. Истории о Хогбенах.» read by Тихонов).
  - **W9 [Minor]** `source_identity.py:194`, `:211`. **`named_order` drops the disc-total membership check for any clean-named set**, not only when the disc tag is the series number (`series_disc` already covers that).
    - Twelve files `01..12`, tracks `N/12`, disc `1/2`: 0.22.0 holds the set ("Source membership uncertain"); 0.22.1 converts it as the whole book, and the cleanup then removes the originals (synthetic probe).
    - Live: 17 folders use the exemption. All of them are series-position disc tags (Honorverse 1/12, the Tolkien trilogy, Corey 6/9, Hobb 1/3, Pern), so none is a half book today.

### 3. Crash / Stability Safety

- Status: Concerns
- Findings:
  - **W4 [Minor]** `desktop_backend.py:368-370` with `web_server.py:384-396` and `merge_service.py:3560-3585`. **A failed close in the update path leaves a half-closed engine that reports "running".**
    - `finish_shutdown` closes the ActionQueue for good (`closed=True`) and calls `merge.close()`, which sets `_closing` and closes workers before it can raise. A typical raise is a `TimeoutError` from the retention thread or the published check, neither of which the update waits for.
    - `_resume_after_update('blocked')` then clears `closing`, but every Start and resume is refused ("closing"), and every queued press answers "Server is shutting down".
    - A second Restart to update, or a Quit, gets out of it.
  - **W5 [Minor]** `desktop/engine-update.js:55`, `:68`, with `desktop/main.js:227`. **The shell can still close the app without installing (the 0.21.1 failure, narrower).**
    - Once the engine is 'updating' (too late to cancel), the shell waits until the 3-minute bound plus 60 s. Then it throws `engine_stuck` and leaves update mode (`state.quit='none'`).
    - The engine is still in `merge.close()`. When it later exits 0, the exit handler takes it as the backend's own Stop and calls `finishExit(0)`: no installer, no reopen.
    - It needs `merge.close()` to take more than about 90 s after the waiting list emptied near the 150 s mark.
  - **W6 [Minor]** `desktop/main.js:360-370` (`endLoadingEngine`), `web_server.py:300`, `:320-321`, `:350-361`. **The shell hard-kills a loading engine 15 s after closing its pipe**, while the engine itself waits 60 s for the loader (`stop_loading`).
    - 0.22.0 never killed the engine.
    - The kill is on the child handle, so the native host's kill-on-close Job ends Python too. It is not a numeric-PID kill.
    - Only `synchronize_groups` is marked `loading.changing()`. MergeService construction also writes (`owned_artifacts`, the enrolment of finished books), and Quit while loading ignores `restart_safe` altogether.
    - `_start_background()` runs before `loading.finish()`, so the retention purge can start while the shell still treats the engine as loading.
    - Every write involved is a SQLite transaction or a journaled step, so a kill is crash-equivalent. I found no lost data.
  - **W7 [Minor]** `desktop/main.js:636-650` (`installUpdate`). **electron-updater 6.8.9's own fallback can start the installer after the shell has given up on it.**
    - `NsisUpdater.doInstall` handles a failed spawn itself: `EACCES` or `UNKNOWN` re-runs it through `elevate.exe`, and `ENOENT` opens it with `shell.openPath` (`node_modules/electron-updater/out/NsisUpdater.js:131-141`).
    - The shell has meanwhile reported `installer_blocked` and started the old engine. A UAC prompt, or the installer, can then appear over a running app, and NSIS closes it mid-load.

### 4. Performance

- Status: Pass (one Minor)
- Findings:
  - **W12 [Minor]** `public_research.py:386-400`. **With the fetch now outside the client lock, two threads (research and a background lane) can both miss the cache for the same URL and both reserve and fetch it.** That is two requests against the site's bound.
  - The gains hold in my reading:
    - `progress_books` reuses each job's lookup per `lookup_token` and receipt. `lookup_token` covers every relocation change, because each insert and generation update appends a migration event (`publication_locations.py:228, 287, 442, 592`).
    - The to-do reuse stamp covers every manifest writer: the only `UPDATE … manifest` is series backfill's, and it updates `manifest_hash` with it.

### 5. State & Data Safety

- Status: Pass (deletes); W3, W4 and W6 are listed above
- Findings: none new.
  - Delete book, Remove this copy and the empty-folder removal keep every guard of the 0.22.0 review.
  - N18: the folder check now walks subfolders, never through a link or junction, bounded at 2,000 entries, with the SOUND list.
  - N19: Remove this copy proves before it takes the locks. Under the locks, every hashed file must keep its size, mtime and native file id.
    - I checked that the NAS reports real file ids (`st_ino` 38994282, 38994286 on two `Z:` files), so the stamp and the hard-link refusal are meaningful there.
  - The critical sections close the windows the update could hit.

### 6. Input Handling

- Status: Pass
- Findings: none.
  - `queue` must be a strict boolean, and only `mode: delete` queues.
  - The cancel and ack ids are canonical UUIDs, at most 1,000 acknowledged at once.
  - `rule_id` is bounded to 1-100 characters.
  - The `title` of a queued action is display-only.

### 7. Maintainability (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **W11 [Minor]** `scripts/check-desktop.mjs:37-76`. **23 test modules have never been in the gate's declared list (the same 23 as in 0.22.0).** I ran them one at a time at c26bc58 and against the v0.22.0 tree (system Python 3.14.9).
    - None fails because of 0.22.1: every failure at c26bc58 fails the same way on v0.22.0.
    - 15 pass.
    - 8 fail on both trees: `test_merge_service`, `test_start_over`, `test_storage_busy`, `test_chapter_repair`, `test_encoding_policy`, `test_fresh_stat`, `test_output_rename`, `test_native_thread_check`. Several are long-standing fixture rot, for example "No sorted output folder is set" in `test_start_over` and `test_merge_service`.
    - So what they cover, including MergeService approval totals and Start over's pending start, is checked nowhere.
    - The v0.22.0 tree also failed `test_anthology` and `test_sort_title`, from my longer scratch path only.
    - The precedent is the gate's own comment: "Both broke unseen outside the gate".
  - `merge_service.py` passes the progress callback into the MergeService constructor, which `LoadAborted` leaves through (`progress()` → `checkpoint()`), part-built. No thread runs yet at that point, and `merge` is never assigned, so `finish_shutdown` skips `merge.close()`. That is fine, but implicit.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings:
  - The Brief's ruling-27 row says Cancel, the bound or a failed close "undo it … the app runs on as before". W3 shows they do not.
  - The Brief's E1-E5 note says the assembler fixed E3. W10 shows it is only partly fixed.
  - The Brief says the build-guard and entry-context changes are tested. They are, and they are in the gate.

### 9. Build & Release Hygiene

- Status: Pass (one Minor)
- Findings:
  - **W10 [Minor]** `scripts/qa-entry-context.mjs:76-83` (`checkRuntime`). **E3 is only partly closed.**
    - Only `python.exe`, `ffmpeg.exe` and `ffprobe.exe` are pinned.
    - The other 44 runtime files, including the codec DLLs and `python314.zip`, are trusted on first use. They are hashed into the context, but nothing compares them with a pin or with the shipped `runtime.files`.
    - For this candidate I compared them by hand: all 47 equal the shipped runtime.
  - Other release checks:
    - The version is bumped in `package.json` and the lockfile in one commit.
    - CHANGELOG has a `[v0.22.1]` entry with the manual 0.22.0 → 0.22.1 update steps (backlog item 5).
    - The artifact matches its manifest (Header).
    - `cand-0221b` is clean at c26bc58.

---

## Probes and tests run

All read-only against Sergei's library and catalog. Tags were read with ffprobe through the repo's own `metadata.read_metadata`. The live catalog was opened with a read-only SQLite URI, one read snapshot per query. Probe scripts and outputs live in my session scratch.

| # | What | Result |
|---|------|--------|
| P1 | `looks_like_person` on all 307 top folders of `Z:\Audiobooks` and on 16 character names | No reader is a top folder. "Harry Potter" and "Mark Frost" read as persons; Harry Potter's depth keeps it out of the folder structure. Character names: see W8 |
| P2 | `folder_structure` on every folder of audio files below `Z:\Audiobooks` (names only) | 147 structures; the wrong ones are W1 and W2 |
| P3 | Offline research, c26bc58 against v0.22.0, on 176 real files (24 folders, tags from `Z:`) | 120 groups; W1, W2. Clean improvements: Sigma Force/VanderMeer/Dune/Dark Tower titles and series, «Пепел Вавилона» and «Восстание Персеполя» joined, «Перерождение 2. Двенадцать» (item 10) |
| P4 | Tags of the W1 files | Tag titles clean («Севастопольский дозор», artist Сергей Недоруб); the structure title replaces them |
| P5 | Synthetic rows (no file): "Person. Title" without an author, half a two-disc set with clean names, a control without disc tags | W8, W9; the control converts in both versions |
| P6-P8 | Live catalog, read-only: title tags shaped "Person. Title"; clean-named folders whose disc tags exceed their discs; the research state of the W1/W2 books | 7 folders, none authorless; 17 folders, all series-position discs; W1/W2 books "Waiting for source", no job |
| P9 | The 23 modules outside the gate, one at a time, at c26bc58 and on the v0.22.0 tree | W11: no 0.22.1 regression |
| — | Artifact pins with the repo's helpers; the QA context's graph, harness and runtime tree; Ender's entry log | Header; answer 8 |

I ran no full gate and no mutation sweep: Futaba's entry check was running throughout. The Python probes used the system Python 3.14.9, the same minor version as the shipped runtime.

---

## Patterns

The same pattern as the 0.22.0 grouping findings (G1-G3, N1): new automatic identity or grouping evidence turns a held book into one that converts by itself, and the tests are built on the motivating names (Sigma Force, VanderMeer, Anita Blake) rather than on the library around them. W1 surfaced from a single folder of real files the tests do not hold. A one-off offline research pass over the live catalog's held and waiting books, old code against new, comparing the destination of everything that now converts, would have shown it before release. The updater tests repeat a second pattern: fakes whose restart always succeeds (W3).

---

## Verdict

- Total Critical: 0
- Total Major: 2 (W1, W3)
- Total Minor: 10 (W2, W4-W12)

No Critical finding is open, and the safety floor is intact. W1 and W3 are the closest to the line. W1 files about ten real books under wrong names on the first run; W3 leaves work stopped behind an "as before" line. I recommend fixing both before 0.22.1 ships.

| # | Sev | Dim | file:line | Finding | Fix (next cycle, or before ship) |
|---|-----|-----|-----------|---------|-----------------------------------|
| W1 | Major | 2 | `local_identity.py:1805`, `:1838`, `:1793` | One-file books in an `Author\Series` folder take the file name as their title over a clean tag title: another author's name, a dangling ")", a part number | Let the file name win only for a book *folder* (`book == 'folder'`), and strip every leading "Person - " piece and unbalanced brackets from the folder title |
| W3 | Major | 2 | `desktop_backend.py:393-433` | Cancel, the bound and a failed close cannot restart workers that are still stopping; the page says "running as before" | Wait, bounded, until each stopped worker has ended (or clear its stop flag in place) before restarting it, and show `resume_problems` in the Install line |

**Verdict:** RELEASE CLEAR
