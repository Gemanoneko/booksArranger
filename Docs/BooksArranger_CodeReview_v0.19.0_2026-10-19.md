# Code Review — Books Arranger v0.19.0

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-19
Tool: Books Arranger
Release: v0.19.0 (target per Jane's brief; package.json still reads 0.18.0 at HEAD, Sully bumps and confirms)
Commit range: adef2118ecac4d7c3202e364bbd7c5423fd7baf7..c2abd97861d6c4ba7df40f3298f784a9c0a6b986
  Base: the end of the range certified by BooksArranger_CodeReview_v0.18.0_2026-10-18.md (worktree Docs/)
Branch / worktree: codex/books-electron-m1, C:/Antigravity Projects/Worktrees/Books Arranger/electron-m1/
Files changed: 34 files, +4789 / -326 (production .py and web/: 14 files, +2159 / -279; tests: 15 files, +2473 / -21; docs: 5)
Stand-down dimensions: none. No Electron shell file (desktop/) changed in the range.
```

---

## Summary

Range covers the four exact M4B writer shapes, typed Retry/Repair refusals with their one-time startup conversions, the M4B pre-check states, the `audio-staging` fix, Start over and the set-aside table, "Let the app handle it" (single, combined, bulk), the Started over marker, leftover-working-file classification, Clear working files, clear-first on Retry/Repair/Retry all, the O12 pending auto-start, and the narrow table. I read the whole production diff, plus the unchanged code each new path leans on: `working_lifecycle.retire`, `native_io` boundaries, `desktop/main.js`, `desktop_backend.quit`, `audio_jobs` worker and retry CAS.

The delete paths hold. No new code path removes a file except through the existing verified disposal (`WorkingLifecycle.retire`). That path re-proves ownership, native identity, single link, hash and boundary, and deletes by handle. Discarding a review is catalog rows only. The M4B allowances are byte-exact.

The weak spot is the O12 pending start. It is blind to Quit and to the app's own force-stops. A probe on the worktree's own test harness confirms it fires during a desktop Quit drain and after a disk-full or working-file hold. Neither case loses data, so there is no Critical. Both are Major, and I recommend fixing them before this ships.

---

## Rubric

### 1. Security

- Status: Pass
- Findings: none. The five new POST routes sit behind the existing `trusted(token=True)` gate. They validate the request shape, take canonical UUIDs, require an explicit boolean for `discard_review`, bound selections to 1–1000 and refuse duplicates. No new shell-out; no `innerHTML`. Before `retire`, `_working_targets` (`merge_service.py:1900`) adds canonical ids, link/junction refusal from the staging root down, a realpath-in-root check, an ownership record, a receipt-in-attempt-folder rule and protection for sources, cover and library roots. Futaba's junction, hard-link, `..` and staged-source attacks agree.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **[Major] M2** `automatic_processing.py:373-380` (`stop`) with `merge_service.py:222-223`: the disk-full hold (`on_space_hold`) and the working-file hold (`on_working_hold`) call `automatic.stop(force=True)`, which does not clear `start_pending`. Within one poll (about 3 s) after the jobs worker returns, `_pending_loop` (`:343-372`) reads jobs `Paused`, which is not a block, and calls `start()`. `_work` then resumes the queued conversions (`:484-485` / `:499`), so one more book is tried on a full disk or past the working-file hold. Probe: `start_pending` is still `{'kind':'conversion'}` after `stop(force=True)`, and the pass started by itself.
  - [Minor] m1 `automatic_processing.py:306` (`request_start`): it returns `running` whenever the worker thread is alive, including while the run is `Stopping`. So the O12 `stopping` pending kind can never come from a press. The note promises "Automatic processing is running and will reach this book", but the run then pauses and nothing restarts it. This matches Futaba's first "Stop then Start over" returning `running`.
  - [Minor] m2 `retry_refusal.py:130-155` (`RESOLVED` / `convert_resolved`): the conversion runs at every startup with no version or key guard. Any *new* refusal that carries the same text gets marked `resolved` again, so it reads "ready to retry" after every restart and rejoins Retry all. `native_io.py:64` still raises that text for a genuinely unavailable ancestor. It is not "once".
  - [Minor] m5 `audio_jobs.py:819` (retry CAS) and `audio_jobs.py:927` (worker pending query): set-aside status lives in a separate table. The Retry compare-and-set only compares the `audio_jobs` row, and the worker's `state='pending'` query has no `CURRENT` filter. "A set-aside job never runs again" therefore rests on the request-time E6/newest checks alone. No race reaches it today: the page serializes presses, and Start-over rows offer no Retry. Defence in depth only.

### 3. Crash / Stability Safety

- Status: Concerns
- Findings:
  - **[Major] M1** `automatic_processing.py:343-372` (`_pending_loop`), with `desktop_backend.py:139-146` (`quit`): the pending loop calls `_current_block()` and `start()` with `server_closing=False`. It never sees the server closing or the merge draining. Quit's `automatic.stop()` (not forced) returns early when no run is Running and leaves `start_pending` set. When the scan stops, or the current book finishes under drain, the pass starts *during Quit* (confirmed by probe). From there, by code reading:
    - A new run enters discovery. With queued jobs it calls `merge.resume()`, which is a no-op while draining, then spins in `while not self._idle_jobs()` (`:485-487`). That loop exits only on `stop_event`. Nothing sets it, because `close()` comes only after `_parked()`, and `_parked()` waits for this thread. Quit hangs at "finishing" until the process is killed or Windows signs out.
    - With no queued jobs, it starts a fresh library scan and network research while "quitting".

    This is the common sequence "Start over while a book converts, then Quit after this book". It also breaks the brief's claim that the pending start "fires with exactly what Start does": a Start press during Quit is refused by the control gate.
  - [Minor] m8 `automatic_processing.py:303-317` (`request_start`, documented "Never raises") catches only `ValueError`. A SQLite error out of `start()` (`_update` and the run insert retry for at most 30 s) has two effects:
    - In a press, it surfaces as HTTP 500 "Local control failed" after the set-aside or release transaction has already committed.
    - In `_pending_loop`, it kills the daemon thread and leaves a stale "will start by itself" notice. The next `_set_pending` recovers it.

### 4. Performance

- Status: Concerns
- Findings:
  - [Minor] m9 `merge_service.py:1965-1994` / `:1996` (`_clear_working`, `_clear_first`): Clear, and Retry/Repair clear-first, run `retire` synchronously inside the press. `retire` hashes every working file and every original source (`working_lifecycle._input`). With originals on the network library, a large book can exceed the page's 15 s press bound. The page then falls back to re-reading, or "Connection interrupted", while the server keeps working. In Retry all this runs under `operation_lock` (`_retry_one`), which blocks other operations for the duration. Futaba's 0.7 s for 640 MB used local originals.

### 5. State & Data Safety

- Status: Concerns. Delete validation itself: Pass.
- Findings:
  - [Minor] m3 `merge_service.py:1992`: every `not_safe` failure is remembered in `_working_failed` against the listing signature. That includes a transient sharing violation, which native_io wraps as BoundaryError "Cannot protect exact file: [WinError 32]". A lock that is released later never changes the listing, so the row stays "can't clear working files" until restart. This is the root cause of Futaba's Minor 1. The wording also says "Some … weren't cleared" when nothing was removed.
  - [Minor] m6 `book_restart.py:117-128` (`set_aside`): a set-aside job is hidden from the attention list and from Clear, and never gets another admission. Its attempts in `attention` / `sources_retained` state (`reconcile` handles only `closed`) therefore hold their working files indefinitely, with no UI path to see or reclaim them. Keeping them was the spec's choice; the missing way back is not.
  - Verified clean: `book_restart` touches catalog rows only, in one `BEGIN IMMEDIATE` transaction with whole-row and revision compare-and-set (rollback on `Changed`/`Editing`); lock order `reviews.lock` → `group_lock` matches `approve_automatic`; no double queueing (`_requeued` and `_requeue_into` deduplicate; `approve_automatic` re-checks `candidate_status` under locks); no revived parent (every newest-job query in the retry/repair/clear/admission paths uses `CURRENT`); no auto-approval without a release (plain Start over on a saved review still holds as `Manual draft retained`; duplicate-recording holds are re-derived at approval). Startup conversions are compare-and-set on `detail` and keep the raw text; `convert_legacy` is idempotent. `LEGACY_PRESERVATION_SHA256` matches the installed v0.18.0 payload (`dist/builds/bc7ac95d…/backend/m4b_preservation.py` = `bc16d609…`).

### 6. Input Handling

- Status: Pass
- Findings: none. The M4B allowances are exact:
  - `iods`: the full 19-byte prefix plus exactly 5 profile bytes, 32-bit header.
  - Track `udta`: byte-equal to the 16-byte empty `name` form, and the whole `trak` is re-compared after the rewrite.
  - `blank()`: a 32-bit header with the type *and* payload all zero, so a zero-filled `data` box does not count.
  - `clean_items`: drops an item only when its single child is blank. Blank children are dropped only beside exactly one version-0 `data`. Any other mix is refused.

  Nothing non-blank is dropped, every drop is written into the plan, proof and receipt, and the output still passes the full packet and PCM comparison in `audio_pipeline`. Blank boxes outside `ilst` items stay refused.

### 7. Maintainability (no Critical findings on its own)

- Status: Concerns
- Findings:
  - [Minor] m7 `audio_jobs.py:620` (`AudioJobs._m4b_working_clear`), the `m4b_working_clear` hook (`merge_service.py:202`) and `MergeService._m4b_working_clear` (`:1788`): dead code, never called since working-files refusals stopped deciding the row. Remove it, or it will drift.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings:
  - [Minor] m10 `Docs/BooksArranger_Brief.md` (Pending start row) says the pending start "fires with exactly what Start does". It does not: see M1, which bypasses the closing/draining gate that Start obeys. Futaba's copy findings sit in the same bucket:
    - `web/app.js:253`: "start over" should read "started over" (her Minor 4).
    - `restartNote` promises "Let the app handle it appears once it is held" to multi-file and leased books (her Minor 3).

### 9. Build & Release Hygiene

- Status: Pass (notes for Sully)
- Findings: none in code. No `desktop/`, packaging or dependency change. Notes:
  1. package.json is 0.18.0 at HEAD; the bump and lockfile go in one commit.
  2. Futaba's GO is filed as `BooksArranger_QA_RefusedRetry_c2abd97_2026-10-19.md`, with no version in the name. `check_release_preconditions.mjs` will refuse it until a QA report names v0.19.0.
  3. This report sits in the studio checkout's `Docs/`, beside Futaba's report. Recent reviews were committed in the worktree's `Docs/`, so Sully places the copy wherever the gate runs.

---

## PA-1 (window in the foreground): what the code can and cannot explain

- **No foreground path in the reviewed range.** The diff touches no `desktop/` file. The new server paths, including `_pending_loop`, call no window, focus, sound or notification API. Renderer focus is element `.focus()` and `<dialog>.showModal()` only; neither activates an OS window, consistent with Futaba's `document.hasFocus()` false. Helper processes keep `CREATE_NO_WINDOW` / `windowsHide`.
- **The only programmatic foreground path in the shell** is `desktop/main.js:313-318` `showWindow()` (`restore` + `show` + `focus`). It is reached from a tray click or menu, and from `second-instance` → `handleCommand` (`:434-438`) for *any* argv other than `--quit` or `--close-window`. That includes a second launch carrying `--show-inactive` or `--start-hidden`, which are ignored there. This is pre-existing and outside the range, so it is not counted. It can explain an event only if a launch overlapped a running instance on the same profile.
- **Most likely mechanism (not provable from code): Windows hands activation to the top of the z-order.** `showInactive()` places the window at the top of the z-order without activating it. When the user's foreground window closes or minimizes (a toast, a popup, a closed tab window), Windows activates the next top-level window, which can be ours. This fits the pattern: "between two of the user's own windows", 1–11 s, and none while idle.
- **Suggested check for Futaba:** log the previous foreground window's destroy or minimize event in the same 100 ms window as each appearance.

---

## Verification performed

- Python 5 modules (`test_m4b_preservation`, `test_refused_retry`, `test_staging_root_retry`, `test_working_clear`, `test_start_over`): 150 tests, OK (Python 3.14, `-B`, worktree's own `scratch/`, tree clean after).
- Node frontend: `test_startover_frontend`, `test_refused_retry_frontend`, `test_precheck_frontend`, `test_attention_frontend`, `test_retry_frontend`, `test_retry_selected_frontend`, `test_automatic_frontend`: all exit 0.
- Probe for M1 and M2, on the worktree's own `Base` harness (stubbed `_work`, synthetic catalog, no app launch): `probe_pending.py` in the session scratch `shared/senua-0190/`. Results: Quit drain, pending start fired = True. Force stop: `start_pending` kept, then fired = True.
- No app launch, nothing against the real library or port 5210, no code change, no commit.

---

## Patterns

The holds the app enforces (closing, draining, disk-full, working-file hold) are checked where a *press* enters: the control gate, `request_start(server_closing=…)`. A background actor that later acts for that press does not re-read them. That covers the pending start here, and the same shape is worth checking in any future "do it later by itself" feature. The second pattern is "once" conversions keyed on text rather than on a version or marker that new records cannot carry.

---

## Verdict

- Total Critical: 0
- Total Major: 2
- Total Minor: 10

**Verdict:** RELEASE CLEAR

No Critical finding and the safety floor is intact: no new path can delete outside the app's own receipt-owned staging, no original is at risk, and nothing new is shelled out, logged or exposed. Majors M1 (pending start fires during Quit and can hang it) and M2 (pending start overrides the disk-full and working-file holds) are advisory. I recommend fixing both before this build reaches Sergei. One fix covers both: `stop()` and drain/close clear `start_pending`, and the pending loop checks closing/draining before `start()`. Each needs a regression test that drives Quit and `stop(force=True)` with a pending start.

---

## Delta review c2abd97..6f7680a (2026-10-19)

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-19
Release: v0.19.0 (package.json still reads 0.18.0 at HEAD; Sully bumps)
Commit range: c2abd97861d6c4ba7df40f3298f784a9c0a6b986..6f7680adb8711522aeea9ce93dcb9506d63bed70
  Commits: 05d08d9, f4829fc, 8fc4e8e, 10f3375, 6f7680a
Branch / worktree: codex/books-electron-m1, C:/Antigravity Projects/Worktrees/Books Arranger/electron-m1/ (clean before and after)
Files changed: 9 files, +219 / -16
  Production: automatic_processing.py, merge_service.py, native_io.py, web_server.py, web/app.js
  Tests: test_start_over.py, test_working_clear.py, test_startover_frontend.js
  Docs: Brief
Stand-down dimensions: none. No desktop/, packaging or dependency change.
```

### Summary

Both Majors are closed. `stop()` now ends a pending start on every path: Stop, Quit and both safety stops. `start()` refuses once Quit or shutdown has begun, and it checks this under the same lock that `stop()` takes. I found no window where a start slips past Quit. The new sharing-violation type weakens no delete refusal. There is no new Critical and no new Major, and there are two new Minors.

### M1 (pending start fires during Quit): closed

- **Quit order** (`desktop_backend.py:130-146`):
  1. `server.closing=True`, under `control_condition`.
  2. `merge.drain()`, which sets `draining=True`.
  3. `inventory.stop()`.
  4. `automatic.stop()`.

  Both flags are set before the stop.
- **Shared lock.** `start()` (`automatic_processing.py:255-259`) re-reads both flags through `_server_closing()` inside `self.lock`. `stop()` takes the same lock, and the pending loop calls `start()` inside it too.
- **The race in the brief** (a start firing between the closing check and the start) cannot happen: the check and the thread start are one critical section. Only two orders are possible:
  - *Start wins the lock.* The run exists when Quit's `stop()` gets the lock. It is set Stopping and `stop_event` is set, so it ends like any run that Quit finds running.
  - *Quit's flags come first.* `start()` raises, and the loop drops the pending start as `closing`, which is not in CLEARS.
- **A press admitted before Quit.** It can reach `_set_pending` after Quit's `stop()`, from a `_current_block` read taken before the flags were set. That pending start can never fire: `start()` refuses it, and the next poll drops it. The only effect is a stale notice for one poll (about 3 s).
- **Other shutdown paths**:
  - `stop_now` (Windows sign-out) sets `closing` before `_shutdown`.
  - The web shutdown route sets `closing`.
  - `close()` sets `closed`.

  The hook is wired unconditionally in `BrowserServer.__init__` (`web_server.py:151`). `merge.draining` is a plain bool, so the `is True` read holds.

### M2 (pending start overrides the disk-full or working-file hold): closed

- Both holds still go through `stop(force=True)` (`merge_service.py:222-223`), which now clears `start_pending` first.
- Each hook runs inside the jobs worker, before the worker returns (`audio_jobs.py:938`, `:1008`, `:1018`). The worker is still alive at that point, so jobs read Pausing. The pending start is therefore gone before jobs can read Paused.
- I found no other worker self-stop meant as a safety hold.
- A *new* press inside the worker's tail is not covered: see d1.

### Sharing violation (f4829fc): no delete refusal weakened

- **Where it comes from.** `FileInUse` subclasses `BoundaryError`, and so also `ValueError`. Only `VerifiedFile.__enter__` raises it, and only for `ERROR_SHARING_VIOLATION` (32). Lock violation (33) and access denied stay plain `BoundaryError`.
- **Every other consumer catches by class and still refuses or holds as before:**
  - `working_lifecycle.py:365`, `:379`, `:510`, `:634`
  - `scanner.py:406`
  - `series_backfill.py:482`, `:576`
  - `storage_cleanup.py:315`
  - the audio pipeline
  - worker admission (`_archive_attempt`, then the working hold)
- **Nothing keys on the class name.** `failure_cause` (`audio_jobs.py:61`) keys only on OperationalError, OSError and ValueError. `FileInUse` lands in the same `None` branch that `BoundaryError` did, and `retryable` stays False.
- **Only `_clear_working` treats it differently**, and only in two ways: the reported cause becomes `file_problem`, and the failure is not stored in `_working_failed`.
  - The except order is correct: `FileInUse` comes before `BoundaryError`.
  - `retire` raises before removing anything in that attempt.
  - Every re-press runs the full ownership, identity, link, hash and boundary proof again.
- **Test.** Ender's test triggers a real Windows sharing violation. It asserts that `FileInUse` is a `BoundaryError` and that nothing was removed.
- Prior m3 is closed.

### 8fc4e8e, 10f3375, 6f7680a

- **8fc4e8e (refreshed row on a 409).** `refused(error,id)` adds the refreshed row from `restart_row`, which returns None, and so omits the row, on ValueError, OSError or sqlite3.Error. Only a typed-cause refusal carries the row; the untyped 409 is unchanged and tested. The page calls `placeRow` only when a row came back. This closes Futaba Minor 2.
- **10f3375 (conditional note).** `release_expected` comes from `book_restart.py:215`: a saved review, a single M4B and no lease. Without it, the sentence ends before the button promise. This closes Futaba Minor 3.
- **6f7680a (Brief row).** The Brief row now matches the code. With 10f3375 and the line-253 copy (now "Books you start over…", grammatical), prior m10 is closed.

### New findings

- **[Minor] d1: a press after a safety stop still gets a pending start.** `automatic_processing.py:384-399`, with `audio_jobs.py:1005-1018`.
  - *What happens.* A safety stop cancels once; it does not leave a hold that later starts read. A Start over or release press can land after `on_space_hold` or `on_working_hold` returns but before the jobs worker exits (its `finally` / `after_attempt` working cleanup). That press reads jobs as Pausing and gets a `conversion` pending start. The pending start fires when the worker returns, and the new run resumes the queue. So one more book is tried on a full disk or past the working-file hold.
  - *Probe.* `test_press_after_safety_stop`: fired = True.
  - *Why Minor.* The press must land inside the tail window. A Start press right after the hold does the same today, because no start gate reads the holds. The next attempt hits the same hold again, and no data is lost.
  - *Fix, if wanted.* The hold sets a flag that the pending loop reads; an explicit Start or Resume clears it.
- **[Minor] d2: Pause audiobook jobs does not end a pending start.** `web_server.py:577`, with `automatic_processing.py:502-505`. I missed this in the first pass: O12 landed in the previous range.
  - *What happens.* While a pending start waits, Pause only pauses the jobs. The pending start survives and fires once jobs read Paused, as its note says it will. A new run's discovery then calls `merge.resume()` for the queued jobs, so the pause is undone within about 3 s. Cancel automatic start avoids this.
  - *Decision needed.* Should Pause end a pending start the way Stop now does? That is a product call for Sergei, through Judy.
- **Carried and unchanged in this range:** m1, m2, m5, m6, m7, m8, m9.

### Verification performed (delta)

- **Python**, 5 modules (`test_m4b_preservation`, `test_refused_retry`, `test_staging_root_retry`, `test_working_clear`, `test_start_over`): 155 tests, OK. Python 3.14 with `-B`, using the worktree's own `scratch/`. The tree was clean afterwards.
- **Node**, 7 frontend suites (`test_startover_frontend`, `test_refused_retry_frontend`, `test_precheck_frontend`, `test_attention_frontend`, `test_retry_frontend`, `test_retry_selected_frontend`, `test_automatic_frontend`): all exit 0.
- **`probe_pending.py`**, the original M1/M2 probe:
  - Quit: fired = False, and `start_pending` is None.
  - Space hold: `start_pending` is None after `stop(force=True)`, and fired = False.
- **`probe_delta.py`**, the interleaving stress (both probes are in the session scratch `shared/senua-0190/`). 300 iterations per stop type; in each, the blocker clears at a random moment around the stop.

  | Stop type | Start fired before the stop | Run survived the stop |
  | --- | --- | --- |
  | Quit | 67 | 0 |
  | Safety stop | 111 | 0 |

  Positive control: the same probe against `c2abd97`'s `automatic_processing.py` fails both cases, with the pending start surviving the stop (Quit at iteration 166, safety stop at iteration 3).
- No app launch, nothing against port 5210 or the real library, no code change, no commit.

### Verdict (delta, HEAD 6f7680a)

- Total Critical: 0
- Total Major: 0 open (M1 and M2 closed)
- Total Minor: 10 open (8 carried, 2 new: d1, d2)

The safety floor is intact. The delta adds no delete path, no shell-out, no logging of secrets and no new exposed route. This line supersedes the one above, which certified `c2abd97`. Both read RELEASE CLEAR, so the release check finds one consistent verdict.

**Verdict:** RELEASE CLEAR
