# Code Review — Books Arranger v0.16.3

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-17
Tool: Books Arranger
Release: v0.16.3
Status: FINAL; accumulated range, the startup-fix delta, the unreleased v0.16.2 delta and the actual installer artifact reviewed
Commit range: 95febcdd4f4de4ffb59a3507053c4eb86f53936a..950857617e96a0ab2ef780c3cb7b15846a5b3d67
Accumulated committed diff: 123 files, +15116 / -241
Last released clearance (v0.16.1 report): 95febcdd..78b442135b70eb2d061a8f5d3571f706a1b256ae; v0.16.1 is tagged at 5420254e79f239f7df0f737966c8652e4db30f4a
v0.16.2 (not published, never tagged): 5420254..d8349715dd03afe2cc12ea9db59cffd4c4c38fd0 reviewed in full in Docs/BooksArranger_CodeReview_v0.16.2_2026-10-17.md; d834971..be3062e1de65eced33335428a1da35c29ea4a0d0 is Docs-only
Delta reviewed in full here: be3062e1de65eced33335428a1da35c29ea4a0d0..950857617e96a0ab2ef780c3cb7b15846a5b3d67 (8 files, +239 / -19)
  efd8b8e3864d2219d01a5ce5a9ebe432422ab423 startup fix (audio_jobs.py, merge_service.py, web_server.py, tests/test_startup_published_check.py, scripts/check-desktop.mjs)
  950857617e96a0ab2ef780c3cb7b15846a5b3d67 version bump to 0.16.3 + CHANGELOG (3 files)
Stand-down dimensions: none
Release source commit: 950857617e96a0ab2ef780c3cb7b15846a5b3d67
Release product tree SHA256: 9b791328643e8f0b11691144e84811b5cdec33f6e7043380d9073f7f181ec7a1
Release artifact manifest SHA256: 299f15d6b48a280c327372debb393523ca38b56d70a813878e2cc3ceb7e6ce89
Release installer: dist/builds/f5a13513-2440-4f9e-9424-f153803ab708/Books-Arranger-Setup-0.16.3.exe
Release installer SHA256: 12c17d1efc70a4de08104734499e02fa1a8884c8daf5d9ced3ca4952806096db (172,939,487 bytes)
```

The source `95febcd..78b4421` was cleared in `Docs/BooksArranger_CodeReview_v0.16.1_2026-10-17.md`. Its findings still stand and are not re-derived here.

v0.16.2 will not be published, so its delta ships for the first time in v0.16.3:
- I reviewed it in full this morning (`Docs/BooksArranger_CodeReview_v0.16.2_2026-10-17.md`, RELEASE CLEAR at `d834971`). That analysis carries forward unchanged.
- Its only product file, `merge_service.py`, changed again in this delta, but only by the 4-line `start_published_check` pass-through (`merge_service.py:391-393`). Nothing it adds touches the v0.16.2 status logic (`_worker_active`, `_state`).
- The v0.16.2 tests were re-run at `9508576` and pass: `test_automatic_processing` and `test_status_snapshot` are inside the comparison run below.
- The new background thread is not "work" in the v0.16.2 sense. `drained()`, `_worker_active()` and `verify_idle` correctly ignore it. It never writes after Start or Quit (question 2).

## Delta be3062e..9508576

### The fix (efd8b8e)

- **Root cause confirmed against the code.** At `be3062e`, `AudioJobs._recover()` ran inside `AudioJobs.__init__`, which `MergeService.__init__` calls (`merge_service.py:96`). For every `completed` row it called `_check_output` → `MergeService._output_valid` (`merge_service.py:944-958`), which fully hashes the published `.m4b` on the share. `BrowserServer.__init__` builds the MergeService before the server answers health. The shell waits 180 s (`desktop/main.js:251`).
- **Change.**
  - `_recover` (`audio_jobs.py:106-120`) now reads only `running` rows:
    - a `publishing` row is settled synchronously through the extracted `_settle` (`:122-134`), which is the same logic as before;
    - every other running row is requeued, as before.
  - `start_published_check` (`:136-147`) starts one daemon thread, at most once per queue. It does not start if the queue is closed or a Start already happened. `web_server.py:62` calls it after `start_retention`.
  - The thread, `_verify_published` (`:149-169`), reads the completed rows once. For each row it skips exact historical retirements, runs `_settle` without the lock, then takes `_lock`. It returns if the stop is set, and writes only if the row is still exactly what it read.
  - `resume()` sets the stop under the lock before anything else (`:292`). `close()` sets it under the lock and joins the thread for at most 5 s (`:321`, `:328-330`).
- **The thread can only demote.** For a `completed` row, `_settle`'s "promote" branch can never fire, because `record` is `json.loads(row["output"])`. So its only possible write is `completed` → `needs attention`.

### Release questions

1. **Can deferring the check let a destructive path act on an unverified or changed output? No.** Every destructive path re-hashes the published output itself, holding a read handle, immediately before acting. None of them trusts the row state alone:
   - **Originals removal.** `CleanupJobs.run` hashes the output and checks its size and parent identity while holding `VerifiedFile(final)` (`source_cleanup.py:193-195`). It revalidates the boundary before each disposal (`:248`). Before every disposition it re-checks, inside a `BEGIN IMMEDIATE` transaction, that the row is still `completed` with the same output (`:251`, `:255`, through `_cleanup_guard`, `merge_service.py:308-314`). The existing case `tests/test_source_cleanup.py:42-45` covers a changed output.
   - **Recovery purge.** It runs in `RecoveryRetention.purge` inside `storage.protected_output` (`recovery_retention.py:102`), which re-hashes the output under a held handle (`storage_cleanup.py:128-142`). This matters because the retention thread starts before the published check (`web_server.py:61-62`). Covered by `tests/test_recovery_retention.py:44-45`.
   - **Working-file and temporary-file deletion.**
     - `working_files`, `run` and `run_folders` all enter `protected_output` first (`storage_cleanup.py:466`, `:525`, `:726`). So does `_discharge_published` (`working_lifecycle.py:526`). Covered by `tests/test_storage_cleanup.py:65`.
     - Unpublished-attempt retirement refuses any row that has an output (`working_lifecycle.py:220`).
     - For a completed row, `terminal()` only hands over receipts and deletes nothing (`:441-465`).
   - **Automatic or manual Start before the check finishes.**
     - Every start path goes through `MergeService.resume()`: the HTTP route at `web_server.py:356`, the automatic paths at `automatic_processing.py:322` and `:336`, and `create`, `queue` and `approve_automatic`.
     - Before `jobs.resume()` it may prune temporary files and run queued originals removal (`merge_service.py:282-287`). Both are self-verifying, as above.
     - `jobs.resume()` then stops the thread under the lock and re-hashes every finished book before the converter starts.
     - So the CHANGELOG's "before any new work begins" holds for new conversions, not for queued cleanup (s6).
   - **Ender's edge case (a crash between completion and cleanup enrolment): confirmed safe.**
     - `MergeService.__init__` (`merge_service.py:120-125`) can now enrol a `waiting` cleanup row for a book whose changed output has not been checked yet. At `be3062e` the row would already have been `needs attention` and would not have been enrolled.
     - At Start, `CleanupJobs.run` refuses at `:194-195`, or the guard refuses at `:199` if the background check already demoted the row. The cleanup row becomes `needs_attention` and every original is kept.
     - The visible difference is a cleanup-attention row instead of nothing. Until Start processes it, `_recovery_idle` (`merge_service.py:371`) defers recovery deletion. That is safe.
   - **Update and restart.** `prepare_update` → `finish_shutdown` → `merge.close()` → `jobs.close()` sets the stop under the lock. The thread is read-only until its locked stop check (`audio_jobs.py:163-165`), so nothing is written after `close()` returns, whether or not the 5 s join succeeded. The update fence (`engine-update.js`) waits up to 60 s for a clean exit, so the bounded join fits. The thread is a daemon and does not hold the process open.
   - **Quit mid-check.** Same mechanism. Measured by `test_deferred_check_never_writes_after_close` and the M1/M4 mutants below. Quit can wait up to 10 s, not 5 s (s4).
2. **Thread safety and lifecycle: sound.**
   - **Stop semantics.** Every possible write is ordered with respect to Start and Quit by `_lock`:
     - `resume()` and `close()` set `_verify_stop` inside `_lock`;
     - the thread checks it inside `_lock` immediately before its compare-and-write.
   - **The compare-and-write is atomic** against every other writer of `audio_jobs`. All writers live in `AudioJobs`:
     - `enqueue`, `retry_failed` and `resume` hold `_lock`;
     - the converter thread writes without the lock, but it only exists after a `resume()` has already stopped the check.
   - **The compare is exact.** It compares whole-row dicts, including `updated`, so a row changed and changed back still counts as changed.
   - **Exceptions.**
     - A `sqlite3.Error` on the initial read ends the thread.
     - Per-row exceptions, whether from the validator, `historical_retirement` or `_update`, are swallowed. The row stays `completed` until Start re-checks it.
     - No exception path writes.
   - **Double start.** It is guarded under `_lock` (`_verifier is not None`). It is also refused after close or after a Start. Measured: the M7 mutant is caught.
   - **Lock contention with Start.**
     - While hashing, the thread holds neither `_lock` nor `MergeService.operation_lock`, so Start acquires both at once. Measured by `test_resume_takes_over_and_the_deferred_check_never_overwrites_it`.
     - The thread holds `_lock` only for one row read and one `UPDATE`. That is bounded by SQLite's 5 s busy timeout (`audio_jobs.py:74`), so in the worst case Pause waits 5 s.
     - The real contention is Start's own synchronous re-check, which predates this release (s2).
   - **The 5 s Quit wait** is per `close()`, and `MergeService.close()` runs twice on shutdown (s4).
   - **File sharing.** The thread opens outputs for read only (share mode READ: `native_io.py:148`, `:171`, and Python's own `open`). Cleanup and protected-output holders also open for read, so neither side gets a false sharing violation from the other.
3. **Ender's `test_desktop_host` race: not caused or widened by this change. I cannot classify it without the failing assertion.**
   - **Not run.** The real-host case binds the fixed dev port 5212 and launches a real engine host. This pass excludes launches, and Futaba's QA may be live, as in the v0.16.2 review.
   - **Static.** Both of the test's catalogs (new, then existing) contain no finished books. So the new thread runs one `SELECT`, finds nothing and exits. `close()` then joins a dead thread. Nothing the test asserts reads anything the delta changed.
   - **The one candidate I found predates this release.**
     - The recovery-retention thread's first pass at startup briefly holds a recovery admission (`web_server.py:69-73`).
     - While it does, `/api/desktop/status` reports `idle: false` (`desktop_backend.py:76-78`, through `merge_admissions`, or `recovery_active` in `verify_idle`).
     - The test asserts `idle` on its very first status read (`tests/test_desktop_host.py:39`).
   - **If that is the race, it is test-only in impact.** The product effect is a momentary "not idle", which only makes the update fence refuse and re-poll.
   - Ender should capture the failing assertion on its next occurrence (s7).
4. **Test determinism and coverage.**
   - **Determinism: confirmed.** The 6 new cases use Events with 5 s bounds, and no case relies on real-time ordering. The one exception is the server-wiring case's 2 s wall-clock bound, which is generous.
     - Runs on a private `git archive` export of `9508576`, with the pinned QA runtime (`scripts/qa-runtime.json`, SHA256 `434b361f…` re-verified), `-I -B`.
     - 1 run plus 20 in a row, then 3 rounds of 8 concurrent processes (24 runs under load). No failures, errors or skips in any of them.
   - **Positive controls.** I ran 13 mutants of `audio_jobs.py` and `web_server.py` against the 6 new cases. 9 were caught:

     | Mutant | Failing cases |
     |---|---|
     | M1, no locked stop check | 2 |
     | M2, no compare-before-write | 1 |
     | M3, Start does not stop the check | 1 |
     | M4, Quit does not stop the check | 1 |
     | M5, construction hashes finished books again | 3 |
     | M6, the server never starts the check | 1 |
     | M7, no double-start guard | 1 |
     | M9, compare on state only | 1 |
     | M11, publishing row requeued instead of settled | 1 |

     4 survived, all coverage gaps (s5):
     - M10: Start no longer re-checks;
     - M8: the check ignores historical retirement;
     - M12: per-row exceptions are not contained;
     - M13: no stop check at the top of the loop. This one is harmless, because the locked check covers it.

     I then ran M10 and M8 against 15 existing queue, cleanup, storage, status and automatic test files (309 cases), with an unmutated control run alongside:
     - **Both survive there too.** Each run produced only the control's 2 environmental failures. So no test anywhere in that set shows that Start re-checks finished books.
     - **Two flakes, unrelated to the mutant.** The M8 run also hit 2 one-off errors, in `test_replacement_jobs` and `test_working_cleanup`. M8 cannot reach them: nothing outside `BrowserServer` starts the check. Neither error reproduced in 6 further runs of those two files, 3 with M8 and 3 without.
   - **Regression comparison.**
     - 32 Python test files that touch the queue, cleanup, storage, status or automatic paths and bind no listener: 472 cases.
     - They were run on private exports of `be3062e` and `9508576`. The failing sets are identical: the same 16 cases fail on both, and 456 pass on both.
     - All 16 failures are environmental to my scratch location: the longer export path trips the app's own Windows path-length guard (10 cases), plus a few fixture files outside the exported tree.
     - So the delta changes no outcome in that set. It also means those 16 cases (for example `test_working_lifecycle`'s restart case) were not independently re-verified here; Ender's gate covers them in the worktree.
   - **Not run.** `test_web`, `test_desktop_quit`, `test_status_read_contention`, `test_merge_http` and `test_desktop_host` were not run, because they bind listeners or launch hosts. `test_app_launcher` needs `tkinter`, which the QA runtime lacks.
5. **Version bump: complete. Changelog: accurate on the fix, with gaps (s6).**
   - `package.json` and both `package-lock.json` root version fields read 0.16.3, in one commit (`9508576`). No other lockfile line changed.
   - The packaged `resources/backend/VERSION` reads `0.16.3`. It is build-generated and untracked. The ASAR `package.json` reads 0.16.3, and the manifest's shell and backend versions are 0.16.3.
   - 0.16.3 is newer than the latest tag, v0.16.1. Neither v0.16.2 nor v0.16.3 exists as a tag, locally or on `origin`.
   - The worktree is clean at `9508576`.
   - The CHANGELOG cause and timing are accurate: 180 s window, about 283 s for 60 books. They match the code and Ender's commit message.

## Artifact binding (independent, 2026-10-17)

All checks were read-only on the artifact, with private scratch copies only. Nothing was installed, launched, packed or rebuilt.

- **Manifest.** `sha256(dist/release-artifacts.json)` = `299f15d6…` (full value in header).
  - It equals `manifest_receipt.sha256` in `build-cache/builds/d37cb1a4-b297-47ae-a687-4e21ba86bcfd/metadata-rotation-complete.json`.
  - That receipt archived the previous manifest as `release-artifacts.json.previous-b98b8509-…`, whose SHA256 is `03c2c9dc…347cb`. That is exactly the v0.16.2 manifest the v0.16.2 report bound.
- **Manifest contents.**
  - Schema `books-desktop-artifacts-v1`, version `0.16.3`, `source_head` `950857617e96a0ab2ef780c3cb7b15846a5b3d67`, `build_id` `f5a13513-2440-4f9e-9424-f153803ab708`.
  - `payload.verified true`, `installer_equivalent true`, shell and backend version `0.16.3`.
  - 219 payload files, 581,949,129 bytes. `payload.manifest_sha256` `c62e0559…5c94`: recomputed, equal.
- **Product digest.** I recomputed `9b791328…c7a1` with the tool's own `productTree`, through both its `-z` release-flow parser and its build-manifest parser. Both give the manifest value.
  - Controls: `efd8b8e` gives `08cce74e…`, which differs because the version files changed.
  - `be3062e` and `d834971` both give `02b31944…f0fa`, the v0.16.2 digest, as they should, because the range between them is Docs-only.
- **Release files.** The installer, blockmap and `latest.yml` SHA256 and sizes equal the manifest's three artifact entries. Both `sha512` lines in `latest.yml` equal the installer's actual SHA512, and its size line matches.
- **Installer bytes.**
  - Exactly one 7z signature, at offset 171,347, with valid start-header and next-header CRCs.
  - Physical size 172,376,271; tail 391,869. The NSIS data-block length just before the signature is equal to that size, with the compressed bit clear.
  - The carved SHA256 is `56603e4d5e437262161cab6c2e2654d89b7c593a546428f507c2a54d86596970`. It matches the producer receipt entry `nsis-archive/545f4de7-…/app-64.7z`.
- **Extracted payload.** I extracted the carve privately with the repo's own `7za`. The 219 files are **byte-identical** to `payload.files`, with nothing missing, extra or different. `win-unpacked` is likewise identical.
- **Against the 0.16.2 payload**, 51 of 219 files differ, and none was added or removed:
  - `Books Arranger.exe` and `resources/app.asar`;
  - `resources/backend/audio_jobs.py`, `merge_service.py`, `web_server.py` and `VERSION`;
  - 45 `.pyc` files.
  - The runtime map is identical.

  This is exactly what the source delta predicts. The test and the check script are not shipped.
- **Source binding.**
  - All 51 tracked backend files equal the `9508576` git blobs under git's own clean filter (`git hash-object --path`); 30 are checked out with CRLF line endings. `VERSION` is build-generated.
  - The protected data files keep their hashes (`replacement_eye_plan.json` `db493dbb…`, `public_source_leads.json` `cfa08525…`).
  - All 11 ASAR application files equal the git blobs. The ASAR `package.json` is the builder-stripped subset; every shared field is equal (0.16.3, `electron-updater` 6.8.9). The other 254 entries are bundled dependencies.
  - The shipped `desktop/main.js` keeps `contextIsolation: true`, `nodeIntegration: false` and `sandbox: true`.
  - The packaged `app-update.yml` feed is `Gemanoneko/booksArranger`, `releaseType: release`.
- **Native receipt** (`build-cache/builds/d37cb1a4-…/native-operation-result.json`): mode `build`, `root_exit_code 0`, `native_job_closed true`, `active_processes_after 0`.

Behaviour of the packaged app on the real-catalog copy is Futaba's QA and not part of this verdict.

## Summary

I reviewed every file in the delta:
- `audio_jobs.py`, `merge_service.py` and `web_server.py`, read against every destructive and lifecycle caller: `source_cleanup.py`, `storage_cleanup.py`, `recovery_retention.py`, `working_lifecycle.py`, `replacement_retirement.py`, `automatic_processing.py`, `desktop_backend.py`, `desktop/main.js` and `desktop/engine-update.js`;
- the new tests and `scripts/check-desktop.mjs`;
- `CHANGELOG.md`, `package.json` and `package-lock.json`.

Each release question was answered from the code and backed by measurements: mutants the tests must catch, a regression comparison against `be3062e`, and two probes. The installer is bound to `9508576` independently of the build's own receipts.

The fix is correct and safe. Its one new regression is cosmetic but visible on every launch (s1). The next instance of the same root cause, full hashing of the catalog over the share, is the Start path (s2). It predates this release.

## Rubric

Severity tags and the always-blocking floor are those in `Team/Docs/ProcessRules.md`, Severity definitions.

### 1. Security

Pass.
- The delta adds no route, IPC channel, shell-out, credential handling or file write. The new thread opens files for read only and writes only its own `audio_jobs` row, under the queue lock.
- The Electron flags and the update feed are confirmed in the actual artifact.

### 2. Correctness & Logic

Concerns: one new Major (s1), one Major carried, and Minor findings. The fix does what it says, and nothing destructive depends on the deferred check (question 1).

- [Major s1, new in this delta] "Audiobook Ready" and the converted count read low after every launch until the background check reaches each book.
  - **Where.** `merge_service.py:175`, `:956`; `conversion_progress.py:26`; `review_backend.py:179`, `:211`, `:227`.
  - **Mechanism.** A book counts as converted and Ready only when `_validated_outputs` holds its current file facts. Only a successful `_output_valid` fills that map. At `be3062e` the startup hash filled it for every finished book. Now it fills one book at a time as the background check progresses, or all at once at Start.
  - **Probe**, on the real `MergeService` restart fixture (`tests/test_merge_service.py`): one converted book, then the service is rebuilt as at launch.
    - At `be3062e`: `converted_total` 1, and the "Audiobook Ready" page total 1.
    - At `9508576`: both read **0** at launch, then 1 after the background check.
  - **Effect on the live catalog.** The default candidates filter is "Audiobook Ready" (`web/app.js:9`). For up to about 4.7 minutes after each launch it shows a short list, or "No audiobooks are ready yet…" (`web/app.js:199`). The job line reads "0 converted out of N approved books".
  - **Severity.** No data, queue or decision depends on it; I grepped every consumer, and automatic processing does not read it. It self-heals.
  - **Fix.** Separate "verified this session" from "eligible to show". One option: seed `_validated_outputs` from the recorded output facts (`dev`/`ino`/`size`/`mtime_ns`) as provisional at construction. The background check then evicts any book that fails, and polls still never hash.
- [Major r1, carried from v0.16.2; predates it] The lost wake-up in `AudioJobs.resume` (`audio_jobs.py:293-294` with `:358-360`). Unchanged by this delta: `resume()` sets `_verify_stop` before its existing early return.
- [Minor r2, carried from v0.16.2] `merge_service.py:197-203`: the capture order in `_worker_active` does not match its docstring. Masked by the two samples.
- [Minor n1, carried from v0.16.1] `desktop/main.js:353,358-370`: the Quit confirmation decides from a cached answer.

### 3. Crash / Stability Safety

Concerns: one Major predating this release, newly identified (s2), and Minor findings. The new thread adds no crash path: per-row exceptions are contained, and it is a daemon.

- [Major s2, predates this release (since v0.4.0); the same root cause as the startup failure] Start re-hashes every finished book while holding the queue lock and the operation lock.
  - **Where.** `audio_jobs.py:288-300`, under `MergeService.resume`'s `@operation` (`merge_service.py:275`).
  - **Cost.** On the live catalog this is the same about 283 s that broke startup, and it grows with the library. It recurs on every idle-to-busy transition: a manual Start, the automatic run's `merge.resume()` (`automatic_processing.py:322`, `:336`), or each automatic approval that finds the converter idle (`merge_service.py:757`).
  - **While it runs:**
    - `pause()` and `drain()` wait on the same lock (`audio_jobs.py:306-315`).
    - A desktop Quit calls `merge.drain()` (`desktop_backend.py:92`). The shell's 5 s request timeout then reports "Quit could not be confirmed". Minutes later the engine exits by itself.
    - A sign-out stop waits in `jobs.close()`.
    - The retention thread waits on the operation lock while holding a recovery admission, so `recovery_active` reads true.
  - **Probe.** With 3 finished books at 1 s each, `pause()` called 0.2 s into `resume()` returned after 2.8 s.
  - **Data safety.** None at risk.
  - **Fix.** Make Start's re-check incremental: re-hash only books whose file facts changed since they were last verified. Or run it outside `_lock` and the operation lock, with the same locked compare-before-write this delta introduced, and start the converter only after it finishes.
- [Minor s4, new] Quit, update and sign-out stop can wait up to 10 s, not 5 s, for a book being hashed.
  - **Where.** `web_server.py:94` and `:81`, with `audio_jobs.py:328-330`.
  - **Mechanism.** `finish_shutdown` calls `merge.close()`, and the `serve_owned` `finally` → `server_close()` calls it again. Each call joins the check for up to 5 s, and the check only notices the stop between books.
  - **Effect.** It is harmless to data and fits the update fence's 60 s. It eats into the shell's 8 s sign-out window (`desktop/main.js:403`).
  - **Fix.** Join once, for example when `self._verifier` is already stopped, or skip the second `close()`.
- [Minor n2, carried from v0.16.1] `merge_service.py:57-66`: the status computation's owner thread is not bounded.
- [Minor n3, carried from v0.16.1] `web/app.js:58-68`: a 503 goes through the generic disconnect path.

### 4. Performance

Concerns: Major only. s2 is the dominant cost and is recorded under dimension 3. The delta itself improves cold start from 286.6 s to about 3 s (Ender's measurement; the mechanism is confirmed in the code). For the first minutes after launch, the background check competes for share bandwidth with anything else that reads Z:.

- [Major, advisory, carried from v0.16.0] `working_lifecycle.py:228` (and `:411`): reference rescans scale with catalog size times disposable-file count.

### 5. State & Data Safety

Concerns: one Major predating this release, which the new check inherits. Every destructive path is still self-verifying (question 1). The new thread can only demote a row, and only while no Start or Quit has happened.

- [Major s3, predates this release; the new background check inherits it] A transient share failure permanently marks finished books "Output needs attention".
  - **Where.** `merge_service.py:958` with `audio_jobs.py:89-90`, `:126-134` and `:295-300`.
  - **Mechanism.** `_output_valid` turns any `OSError`, such as Z: unavailable or not yet reconnected, into `False`. `_check_output` reports that as "Recorded output is missing, changed, or failed validation", and the row moves to `needs attention`.
  - **No way back.** I found no automatic or one-click path from that state back to `completed`:
    - `_settle` only revisits `completed` and `running` rows;
    - `retry_failed` refuses rows that have an output;
    - `failed_m4b_retry.eligible` requires no output.
  - **Exposure.** It was the same at startup before and at every Start. The deferral moves it into the first minutes after launch, rather than widening it.
  - **Fix.** Treat "the share or folder is unavailable" (`OSError` before a hash is obtained) as "not checked; leave `completed`". Only a size or hash mismatch, or a missing file under a reachable parent, should mean "changed".

### 6. Input Handling

Pass. The delta adds no input surface.

### 7. Maintainability (no Critical findings on its own)

Concerns (Minor only). The change is small, its tests use the real `AudioJobs` under Event control, and they are enrolled in `scripts/check-desktop.mjs`.

- [Minor s5, new] The new tests miss three behaviours (M10, M8 and M12 survive).
  - **Start's own re-check (M10).** `tests/test_startup_published_check.py:105` asserts `'MainThread' in calls`. But construction's synchronous settle of the publishing row satisfies that, not `resume()`. Neither the new tests nor 309 existing cases show that Start re-checks, and the CHANGELOG's guarantee rests on that re-check.
  - **The historical-retirement skip in the check (M8).**
  - **Contained per-row exceptions (M12).**
  - **Not covered at all.** No case runs the check together with a `MergeService`-level Start or queued cleanup.
  - **Fix.**
    - Have the resume case reject the book's output only for the main thread, and assert `needs attention` after `resume()` with a stub `_work`.
    - Add a `historical_retirement` stub that returns true and assert no write.
    - Add a validator that raises and assert that later rows are still checked.
- [Minor r3, carried from v0.16.2] `tests/test_automatic_processing.py:675-731`: the `elif` branch with Stop set is not covered.
- [Minor n4, carried from v0.16.1] `tests/test_status_snapshot.py:39,67,128-131`: these cases rely on real time.
- [Minor m2, carried from v0.16.0] `scripts/check-desktop.mjs:19-23`: `tests/test_build_external_tools.py` is still not enrolled.
- [Minor s7, new; predates this release] `tests/test_desktop_host.py:39`: the real-host case fails in about 1 of 5 gate runs, and the cause is not yet classified (question 3). Record the failing assertion. If it is the startup-admission `idle` race, retry the `idle` read for a bounded time.

### 8. Doc/Code Drift (no Critical findings on its own)

Concerns (Minor only). The new docstrings and comments are accurate, except the "before any new work" nuance below.

- [Minor s6, new] Three gaps in the v0.16.3 CHANGELOG entry and docstrings:
  - **"Before any new work."** `CHANGELOG.md:7` and the docstrings at `audio_jobs.py:112` and `:139-140` say Start re-checks every finished book "before any new work begins". Queued originals removal and temporary-file cleanup run before `jobs.resume()` (`merge_service.py:282-287`). Each verifies its own book, but the sentence is broader than the code.
  - **The v0.16.2 fix is not mentioned.** The entry does not say "v0.16.2 was never released; its changes ship in this version", although the v0.16.1 entry set that precedent. Readers of v0.16.3's notes would miss the between-books pause fix.
  - **The Ready-list lag (s1) is not mentioned.**
  - **Fix.** These are CHANGELOG-only edits; see the release-path notes on what they do to the binding.
- [Minor n5, carried from v0.16.1] Three small inaccuracies remain:
  - `merge_service.py:369` says "indexed existence check";
  - `Docs/BooksArranger_Brief.md:303` omits that stop-now bypasses `engineRequest`;
  - `CHANGELOG.md` (the v0.16.1 entry) says "the whole job table".

### 9. Build & Release Hygiene

Pass, with Minor concerns carried forward.
- The version bump, the lockfile in the same commit, and the CHANGELOG are present.
- No dependency changed.
- The worktree is clean at `9508576`.
- The installer is bound to the source, and the payload was reproduced from the installer bytes (see Artifact binding).
- This review does not claim the publication run.

- [Minor m1, carried from v0.16.0] `scripts/build_phase.py:103-121`: the carve checks are partly self-consistency. I re-checked them independently for this artifact.
- [Minor m3, carried from v0.16.0] `scripts/build_phase.py:99-107`: an implicit coupling to the reduced `7zip-bin` 5.2.0 `7za`, which fails closed.

Release-path requirements in the tool's own contract (`scripts/release-contract.mjs:24-36`, `scripts/release-flow.mjs:38-46`), for Sully and Futaba. These are not findings, and each fails closed:
- **Installer reuse.** Only Docs-only or CHANGELOG-only descendants of `9508576` may be released with this installer. A CHANGELOG fix for s6 keeps the product digest.
- **`Docs/BooksArranger_ReleaseAcceptance_v0.16.3.json`** needs:
  - exactly the keys `schema` (`books-desktop-acceptance-v1`), `version`, `qa` and `review`;
  - version `0.16.3`;
  - `review` set to `Docs/BooksArranger_CodeReview_v0.16.3_2026-10-17.md`;
  - `qa` matching `^Docs/BooksArranger_QA_v0\.16\.3_\d{4}-\d{2}-\d{2}\.md$`.
- **Futaba's report** needs, like this one:
  - exactly one `**Verdict:**` line;
  - exactly one source-commit pin line naming `950857617e96a0ab2ef780c3cb7b15846a5b3d67`;
  - exactly one artifact-manifest line naming `299f15d6b48a280c327372debb393523ca38b56d70a813878e2cc3ceb7e6ce89`.
- **The v0.16.2 report and acceptance index** pin `d834971` and the `03c2c9dc…` manifest. They cannot clear v0.16.3, and v0.16.2 must not be tagged.

## Finding rollup

- Open Critical: 0.
- Open Major: 5, all advisory.
  - New in this delta: s1, the Ready list and converted count lag after launch.
  - Predating this release, newly identified: s2, Start's synchronous full re-hash under the locks; s3, a transient share failure permanently demotes finished books.
  - Carried: r1 (v0.16.2), and `working_lifecycle.py:228` (v0.16.0).
- Open Minor: 14.
  - New: s4, s5, s6, s7.
  - Carried from v0.16.2: r2, r3.
  - Carried from v0.16.1: n1, n2, n3, n4, n5.
  - Carried from v0.16.0: m1, m2, m3.
- Always-blocking floor: intact.
  - No machine harm: the Electron flags are unchanged in the actual artifact, and there are no new deletes. The only new write is a guarded row update.
  - No secret exposure.
  - No risk to repo history.

Major and Minor findings are logged for Ender's next cycle and do not gate this release.

## Verdict

- Total Critical: 0
- Total Major: 5
- Total Minor: 14

**Verdict:** RELEASE CLEAR

This clearance covers the accumulated range `95febcdd4f4de4ffb59a3507053c4eb86f53936a..950857617e96a0ab2ef780c3cb7b15846a5b3d67`. That range includes the unpublished v0.16.2 delta. It also covers the installer `Books-Arranger-Setup-0.16.3.exe` (SHA256 `12c17d1efc70a4de08104734499e02fa1a8884c8daf5d9ced3ca4952806096db`), bound by the manifest hash in the header.

It covers construction only. Futaba's packaged real-catalog-copy QA GO is the independent behaviour gate. s1 and s2 are the two things her live-catalog pass will see: an empty Ready list right after launch, and a long, unresponsive Start or Pause on a large library.

A rebuild, or any product-file change after `9508576`, voids this artifact binding and needs a fresh binding check.
