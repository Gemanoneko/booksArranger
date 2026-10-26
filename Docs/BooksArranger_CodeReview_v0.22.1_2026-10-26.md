# Code Review — Books Arranger v0.22.1

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-26
Tool: Books Arranger (Electron / Python)
Release: v0.22.1
Commit range: 143b33b733a2c3dfcd86e89f5c70df9fbbe6b03c..b03eea75cd9c51e366ae0cdd3fd3a8f8582d232a (tag v0.22.0 .. origin/main b03eea7): first pass to c26bc58 (51 commits), then the delta c26bc58..b03eea7 (15 commits)
Release source commit: b03eea75cd9c51e366ae0cdd3fd3a8f8582d232a
Release artifact manifest SHA256: db44ec92fb9d3aa795d75857caaffd91d3a9d388f0be029a4c36a66fd7c6eec6
Reviewed source: first pass, C:/Antigravity Projects/Worktrees/Books Arranger/rv0221 (detached at c26bc58); delta, C:/Antigravity Projects/Worktrees/Books Arranger/rv0221b/wt (detached at b03eea7) and a git archive of c26bc58's *.py beside it. Both removed after the review.
Files changed, first pass: 92 files, +9101 / -1333 (git diff --shortstat). Product code and scripts: 39 files, +4028 / -1216. Tests: 46 files, +3787 / -113. Docs and CHANGELOG: 5 files, +1283 / -1. package.json and package-lock.json: version only.
Files changed, delta: 20 files, +1207 / -104. Product code and scripts: 11 files, +339 / -92. Tests: 6 files, +536 / -10. Docs: 3 files, +332 / -2 (this report, Judy's section 12, the Brief).
Stand-down dimensions: none
```

Rulings checked against: `Team/Docs/BooksArranger_Rulings_2026-10-24.md` (2, 5, 6, 6a, 10, 11a, 14, 16, 19, 19b, 21, 23-28), the backlog `Docs/BooksArranger_0.22.1_Backlog.md` and the Brief's 0.22.1 section.

**Artifact pin (b03eea7).** Ender's manifest is `C:/Antigravity Projects/Worktrees/Books Arranger/cand-0221c/dist/release-artifacts.json`. I recomputed every value myself, read-only, with the repo's own `release-contract.mjs` and `release-flow.mjs` (`gitEntries`) from my b03eea7 worktree:
- Manifest SHA-256 `db44ec92fb9d3aa795d75857caaffd91d3a9d388f0be029a4c36a66fd7c6eec6` over the file's 57,041 bytes (no BOM). It equals Ender's value.
- `version` 0.22.1; `source_head` b03eea75cd9c51e366ae0cdd3fd3a8f8582d232a; `build_id` 8c8cd155-0648-4085-9443-7f52e66528ae; `latest.yml` reads `version: 0.22.1`.
- `product_digest` `ff53722a…d744` equals `productTree(ls-tree b03eea7)` (c26bc58's is `42248363…41db`, so the old pin no longer matches this product).
- `artifactContract(manifest, {version: '0.22.1', productTree})` accepts it: three artifacts; payload `backend_version` and `shell_version` 0.22.1, `verified` and `installer_equivalent` true.
- Each artifact matches the manifest's size and SHA-256:
  - `Books-Arranger-Setup-0.22.1.exe`: 174,087,620 bytes, `c1b385219e62c39b7f3388d66d44db2744903ff993805162620fbd75cbe6a3d5` (Ender's value);
  - the `.blockmap` (181,629 bytes) and `latest.yml` (360 bytes).
- The `cand-0221c` worktree is at b03eea7 with a clean tree. I only read and hashed it.

The first pass pinned the earlier candidate (`cand-0221b`, c26bc58, manifest `72a0f4f7…a6585`, installer `b24f23a3…e6ab`). That pin is superseded.

---

## Delta c26bc58..b03eea7

**Scope and method.** 15 commits on origin/main after c26bc58, starting with this report's first commit (fa55b0f). I read every product and script hunk in full, and the tests where a question turned on them. This pass ran under ProcessRules § Lean verification: no full suite and no mutation sweep. I ran three targeted unit tests and three read-only probes (P10-P12 below), lightly, because Futaba was testing at the same time.

**Status of the first pass's findings at b03eea7.**

| # | Was | Now | Evidence |
|---|-----|-----|----------|
| W1 | Major | **Closed** | `files_name_title` is set only for a book folder (`local_identity.py:1838`). Leading pieces that are only people are dropped (`:1822-1827`). Nested and unpaired brackets go (`_balanced`, `:1747`, and `:1896` for a title that equals the folder's). P10: the live «Дозоры» and «Городские легенды» titles are now clean. |
| W2 | Minor | **Closed** for a second-level folder named "N. Title" (`:1787`). Open for the second shape («Darwin's Blade» in "Dale Stewart Mike O'Rourke"), as the Brief says | P10: 10 structures go (the 5 Corey book folders, and the 5 parts of Lindqvist's «146. Впусти меня (Светлана Смелова)», which c26bc58 read as books 1-5 of a series «146. Впусти меня»). Both are right. |
| W3 | Major | **Closed** | Question 2 below. 3 targeted tests pass. |
| W5 | Minor | **Closed**, with a narrow race left (W16) | Question 3 |
| W7 | Minor | **Closed** | Question 3 |
| W10 | Minor | **Closed** | `checkRuntime` (`scripts/qa-entry-context.mjs:85-88`) and the gate (`scripts/check-desktop.mjs:155`) both refuse a runtime whose file count or `treeDigest` differs from `scripts/qa-runtime.json` `tree` (47 files, `a3cb3b5e…`, the tree I compared by hand in the first pass). |
| W12 | Minor | **Closed**, with a narrow leftover (W13) | A second reader waits for the request in flight, then reads the cache (`public_research.py:382`, `:406`). |
| W6 | Minor | **Accepted** by Judy's ruling (section 12.3): no change needed | — |
| W4, W8, W9, W11 | Minor | Open, unchanged (the Brief's "Not fixed" list) | W8 gains one latent shape, see question 1. |

**Answers to the four questions.**

1. **W1/W2 are closed. On today's library the title cleanup damages no legitimate title, but three latent shapes can.**
   - *Live library (P10, names only, all 13,502 catalogued audiobook files, 5,351 book units, c26bc58 against b03eea7):*
     - 20 structure titles change, and every change removes a credit:
       - the 16 «Дозоры» of the shared-universe folder, «Чужой Дозор» without its ")" among them;
       - the four «Городские легенды» ("Лена Обухова - Хозяйка старого дома" → «Хозяйка старого дома»).
     - 10 structures go (W2 above).
     - One lone file meets the new whole-book rule: «Игры Немезиды».
     - This agrees with Ender's measurement of whole identities: 22 books change, none between accepted and held.
   - *Synthetic rows (P11, through the full test pipeline: catalog, lookup, Approve, destination; b03eea7 against c26bc58):*
     - **W14 (Minor, latent).** A lone numbered volume in its set's own folder loses its number and converts with no question. `whole_in_book_folder` cannot tell a set folder from a book folder when the set folder's name is the file name without its number.
       - "Takemiya Yuyuko\Торадора!\Торадора! 6.m4b" with title tag «Торадора!» or «Торадора! 6» shows «Торадора!» and goes to `Takemiya Yuyuko\Торадора! - Takemiya Yuyuko.m4b`. At c26bc58 it was «Торадора! 6».
       - "Анджей Сапковский\Ведьмак\Ведьмак 3.m4b" with no title tag shows «Ведьмак».
       - The ruling row itself rejects this outcome: "a volume would lose its number". The test's volume control is "Торадора! Том 5", which has a volume word, not a bare number.
       - None on the live library today. A later volume alone in the same folder would get the same name, and the destination check then asks: nothing is overwritten.
     - **W15 (Minor, latent; worse than c26bc58).** A single file in an `Author\Series` folder with no title tag loses the first half of a title with " - " in it, when that half is no person.
       - "Clive Barker\Books of Blood\3. Сын целлулоида - Ревущий мясник.m4b" shows «Ревущий мясник». At c26bc58 it was «Сын целлулоида - Ревущий мясник».
       - Cause: with `files_name_title` off for single files, identify's file-name fallback wins. That fallback reads "X - Y" as "Author - Title". The structure's own reading keeps the dash, but it no longer wins.
       - The new test asserts `folder_structure`'s title, not what the row shows, so it does not see this.
     - **W8 gains a latent shape.** The people strip uses the same `looks_like_person`, so a title that opens with a person-like name loses it. "Стефан Цвейг\Биографии\03 - Жозеф Фуше - Портрет политического деятеля.m4b" with no title tag shows «Портрет политического деятеля».
     - *Brackets: no damage.* `_balanced` removes only what `clean_title` already removed, plus nested and unpaired brackets. A bracket note in a tag title equal to the name («Пикник на обочине (Сталкер)») shows «Пикник на обочине» at both commits. A title with a dash and no person ("Сын целлулоида - Ревущий мясник" in `folder_structure`) keeps its dash.
2. **W3: the bounded wait cannot hang, and a worker that never ends is named.**
   - *Bounded.*
     - `_ended` joins each thread for at most min(time left, 0.25 s) against one 25 s deadline shared by every kind (`desktop_backend.py:447`, `:469-477`).
     - The update's own thread is never joined (`live`, `:431`).
     - No lock is held while waiting. `closing` is cleared first, so presses work during the wait.
     - A kind whose threads did not end is skipped, so no restart waits on the stuck worker. The others use their normal starts.
     - Outside the engine: Cancel's request joins the update thread for 30 s (`:505`); the shell waits 35 s per try, three tries (`desktop/engine-update.js:12`, `:15`). The engine's bound plus the resume (150 s + 25 s) stays inside the shell's 180 s.
   - *Never ends.*
     - It is recorded as `{kind, cause: 'still_stopping'}` (`:451`) and logged to stderr.
     - The shell types it (`problemsOf`), and the Install line names it: "Update cancelled (tried HH:MM). The audiobook jobs didn't start again. Press Resume audiobook jobs to continue." (`web/desktop-ui.js:41`).
     - "Running as before" appears only when nothing is listed.
     - Ran `MatrixTests.test_work_that_has_not_stopped_in_time_is_named_and_not_started`, `MatrixTests.test_the_bound_cancels_and_keeps_the_app_running` and `RealWorkerResumeTests.test_work_still_stopping_at_the_bound_is_named_never_as_before`: 3/3 pass, 2.2 s.
   - *One edge, below a finding.* Suppose the workers end only in the last seconds of the 25 s and a start then takes more than about 5 s. Cancel's 30 s join then returns before the outcome exists, and the line shows the plain "running as before". The engine still records the problems and logs them.
3. **W5/W7 cannot start an installer when they should not, and skip none they should start.**
   - *W7.*
     - `holdInstallerSpawn` (`desktop/update-controller.js:51`) hands electron-updater a promise that never rejects. So `NsisUpdater.doInstall`'s own fallback never runs: elevate.exe on EACCES/UNKNOWN, `shell.openPath` on ENOENT (`node_modules/electron-updater/out/NsisUpdater.js:131-141`, 6.8.9).
     - The shell keeps the real attempt. I checked that `doInstall` calls `spawnLog` synchronously inside `quitAndInstall`, so `hold.spawned()` is set by the time the shell reads it.
     - No spawn, or a failed one, is installer_blocked. A spawn that succeeds still ends in `finishExit(0)`.
     - The admin-installer refusal is unchanged.
   - *W5.*
     - `lateUpdateExit` is set only when the shell gives up after the engine was already ending (`engine-update.js:81`).
     - The exit handler then starts the old engine again (`desktop/main.js:224-226`, `lateEngineExit`) and never installs.
     - The installer still runs only on the normal path: exit 0 while `quit` is 'updating'.
     - The flag can also be left set on a running engine, after a failed close that came after 'updating'. The next status read clears it (`main.js:715`). Before that, a crash would restart the engine instead of closing the app, which is harmless.
     - New **W16 (Minor):** `lateEngineExit` returns at once while `busy.install` is true (`update-controller.js:183`), and `updateExit` has already cleared the flag. `restart()` keeps `busy.install` true until `await lease.close()` in its `finally` (`:178`). An engine exit landing in that await is never followed by a restart. The Install line still shows engine_stuck's "Choose Quit Books Arranger in the tray, then open it again", which is the right instruction there, so nothing is hidden.
4. **Nothing new can delete or move a file wrongly.**
   - The delta adds no file operation:
     - W3 restarts the existing workers through their own guarded starts (`merge.resume(recheck=False)`, as before);
     - W5 and W7 only decide between restarting the old engine and spawning the installer;
     - W10 is gate-side;
     - W12 touches the research cache only.
   - Identity changes only change names. Every destination is still refused when anything exists there (`merge_service.py:355`, `:1250`, `:2507`, `:3421`, unchanged).
   - A lone numbered file that now converts as a whole book has its original removed by the cleanup afterwards, like any converted book. All of its audio is in the converted file.

**New findings in the delta.**
- **W13 [Minor]** `public_research.py:406`. **The in-flight marker for a URL is set inside the `with connect()` block, before that block commits the reservation.**
  - If that commit raises, the URL stays marked with an Event that is never set.
  - Every later read of the URL then waits until its stop is set (Pause, the update), or for ever with no stop.
  - It needs a failed commit in WAL mode on the local catalog, so it is rare.
- **W14 [Minor]** `local_identity.py:1847` (`whole_in_book_folder`), `:2040`. A lone bare-numbered volume in its set's folder loses its number (question 1).
- **W15 [Minor]** `local_identity.py:1838` with identify's file-name title fallback. A tagless single file in a series folder loses the first half of a " - " title (question 1). This is worse than c26bc58, though it is the 0.22.0 file-name reading.
- **W16 [Minor]** `desktop/update-controller.js:183`, `:178`. An engine exit during `restart()`'s lease close is never followed by a restart (question 3).

**Delta rubric.**
1. Security: Pass. No new route, IPC channel, `innerHTML` or shell string. `holdInstallerSpawn` narrows the updater's spawn behavior.
2. Correctness & Logic: Concerns (W14, W15; W8 extended).
3. Crash / Stability Safety: Pass (W16 Minor). The W3 wait is bounded, and the shell's exit handling never installs on a late exit.
4. Performance: Pass (W13 Minor). W12's duplicate request is gone.
5. State & Data Safety: Pass. No new delete, move or overwrite path; destinations are still never overwritten.
6. Input Handling: Pass. `resume_problems` kinds and causes are allow-listed in the shell (`problemsOf`, `stoppedProblems`).
7. Maintainability: Pass. The weight entries for `test_desktop_update.py` (21 s, then 23 s) match the longer suite.
8. Doc/Code Drift: Concerns. The Brief's item 10(b) row says a volume keeps its number. It does only with a volume word (W14). The ruling-27 and E3 notes the first pass flagged now match the code.
9. Build & Release Hygiene: Pass. The artifact matches its manifest and b03eea7 (pin above), and W10 is closed.

**Delta probes and tests.** All read-only against the live catalog (read-only SQLite URI); no file under `Z:` was opened. Probe scripts and outputs lived in the rv0221b folder and were removed with it.

| # | What | Result |
|---|------|--------|
| P10 | `folder_structure` and `whole_in_book_folder`, c26bc58 against b03eea7, on every catalogued audiobook path (names only) | 20 titles changed, all credits removed; 10 structures dropped, all right; 1 whole-book candidate («Игры Немезиды») |
| P11 | Synthetic rows through the test pipeline (catalog, lookup, Approve, destination) at both commits | W14, W15, the W8 shape; the bracket and "no person" controls keep their titles |
| P12 | Artifact pin with the repo's helpers | Header and pin above |
| T1-T3 | The three W3 tests named in question 2 | 3/3 pass |

---

## Summary

*This summary, the nine answers and the rubric below are the first pass, at c26bc58. W1 and W3 are closed at b03eea7; the delta section above has the current status.*

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

The delta repeats the first pattern on a smaller scale. The W1 fixes were checked on the live names (P10 and Ender's catalog copy both agree), and the live library is clean. The new rules' edges sit just beside the motivating names, though: a volume numbered without "Том" (W14), and a tagless title with a dash (W15). The tests hold the controls next to those shapes, not the shapes themselves.

---

## Verdict

At b03eea7, first pass and delta together:
- Total Critical: 0
- Total Major: 0 open. W1 and W3 are closed.
- Total Minor: 9 open: W2 (second shape only), W4, W8, W9, W11, and the delta's W13, W14, W15, W16. W5, W7, W10 and W12 are closed; W6 is accepted by Judy's ruling.

No Critical finding is open, and the safety floor is intact. The candidate's manifest and installer match b03eea7 and version 0.22.1. The new Minors are latent: none of them occurs on the live library today.

| # | Sev | Dim | file:line | Finding | Fix (next cycle) |
|---|-----|-----|-----------|---------|------------------|
| W13 | Minor | 4 | `public_research.py:406` | The in-flight marker is registered before the reservation commits; a failed commit leaves the URL waiting for ever (or until Pause) | Register the marker after the commit, or set and remove it on any error |
| W14 | Minor | 2 | `local_identity.py:1847`, `:2040` | A lone bare-numbered volume in its set's own folder ("Торадора!\Торадора! 6.m4b") loses its number and converts with no question | Treat the folder as the book's only when it carries a book position or uploader number ("5. Игры Немезиды"), or ask otherwise |
| W15 | Minor | 2 | `local_identity.py:1838` | A tagless single file in a series folder loses the first half of a " - " title (the file-name fallback reads it as "Author - Title") | For a single file, let the structure's title win over a title whose basis is `file_name` |
| W16 | Minor | 3 | `desktop/update-controller.js:183`, `:178` | An engine exit during `restart()`'s lease close is never followed by a restart (the engine_stuck line still says what to do) | Keep the late-exit request until `busy.install` clears, then restart |

**Verdict:** RELEASE CLEAR
