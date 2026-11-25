# Code Review — Books Arranger v0.31.3

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-25
Tool: Books Arranger
Release: v0.31.3
Commit range: v0.31.2..db4b3667eb4fdb2e02f46ed76130e56c3824792d (13 commits, branch ender/0.31.3-late-writes)
Files changed: 20 files, +1789 / -68
Stand-down dimensions: none
```

Release source commit: db4b3667eb4fdb2e02f46ed76130e56c3824792d
Release artifact manifest SHA256 (observed, `dist/release-artifacts.json`, `source_head` db4b366, `version` 0.31.3): ea52c98f0ad1a1b582190705c060bbf54f152f96c897b00d222d0f86920d20ed

---

## Summary

0.31.3 lets the late series and name writes (`series_backfill`, `name_write`) remove files on the NAS with the remote method from Sergei's 2026-11-16 ruling (`VerifiedFile.dispose(remote_legacy=…)`, with the new `_last_checks` and `remove_owned`). It also adds:

- the one-time retry of the 115 holds from 0.31.2 (`_retry_retained_removals`);
- the proof-gated removal of the 2 leftover temporary files and one fresh try at the names for Card and Hobb (`_clear_leftover_temporaries`, `_remove_leftover`, `NameWrite._leftover_outcome`);
- the "Removing old files" row, Waiting item and done line (`cleanup_view`, `outcome_view`, `background_work`, `web/app.js`);
- the reworded hold reasons, the `old_file_kept` could-not key, and the 0.31.3 version bump.

I read the whole diff and the code around it: resume, `_protected`, `_boundary`, `catalog`, `VerifiedFile`, `DirectoryBoundary`, the close and update paths, and `media_unchanged`. Four probes ran against the existing fixtures to test the findings below.

**Wrong-file deletion holds up.** Before the old file goes:

- the catalog must name the new file by path, size and SHA-256 (`_names_rewritten`);
- the new file is re-hashed against the write's proof and stays held;
- the old file's identity and SHA-256 must match the record, with one link, and are checked twice (`_protected`, then `_last_checks` through the same handle);
- old and new must be different files (SAME_FILE);
- the folder identity is held and revalidated;
- the removal goes through the held handle, so a rename by path cannot redirect it.

Paths with Cyrillic letters, `«»`, brackets and spaces pass `ordinary()` and the fixtures. Case and normalization aliasing is caught by the identity checks.

**Selection.** The match is on the exact hold text, `removal_intended`, and all recorded proofs. A record outside the 115 or the 2 would go through the same full re-proof. The Brief records that the live copy matches exactly 115 and 2.

**"Once" is reliable** across a crash, restart or re-install: `removal_retry` and `temp_retry` are persisted with the state change. A second instance is blocked by the single-instance lock and the catalog owner.

**The temporary-file proofs are sufficient.** The temp cannot be the only good copy: the book's own file must match the catalog hash, and the temp's media must equal that file's, byte for byte.

**The Card/Hobb fresh try cannot loop.** `RETRY_KEYS` carries `temp_retry` and `names_retry` into the new record, and `_failed`'s text no longer matches the selector. It runs only for books whose hold matches exactly.

**Frontend.** Every new string reaches the DOM through `textContent`.

**What is wrong:**

- the clean-up ignores Quit's and the update's stop;
- one unreachable moment of `Z:` uses up the one-time retry;
- the retry turns "old file missing" into "removed and freed";
- a silent-refusal sibling of the root cause remains in `_discard_temp`.

None of these deletes a wrong file, loses data or crashes, so none is Critical.

---

## Verification

Probe: `WIP/Books Arranger/scratch/0313-review/probe_0313.py`. It uses the existing `Library`, `nas_library` and `as_0312` fixtures, a private support owner, TEMP and fixtures under `scratch/0313-review`, and `python -I`. Run with `timeout 600000`: 4 tests OK in 7.9 s.

| # | Check | Method | Result |
|---|---|---|---|
| P1 | Old file missing when a 0.31.2 hold is retried (spec 9.4 expects N7) | `hold_as_0312`, unlink the old file, `run_pass` on the simulated NAS | `('done', '')`; `_cleanup_counts` = removed 1, freed 18634 (= `old_size`). N7 is never raised. → M3 |
| P2 | `Z:` unreachable during the retry's pass, then back | `DirectoryBoundary.__enter__` raises `AncestorUnavailable` for one `run_pass`, then a normal `run_pass` | After the outage: held, "Series recovery could not verify the files; remaining copies kept: An inspected destination ancestor is unavailable", `removal_retry` 0.31.3. After the drive is back: still held, both files present, counted kept. → M2 |
| P3 | Stop (Quit / update) set before the pass | `backfill.stop.set()`, then `run_pass` | `('done', '')`, old file removed: the retry and the R35 loop run with stop set. → M1 |
| P4 | Count cache when a write lands during a read | A wrapped `connect` commits the book's `done` (plus `_changed()`) after `_cleanup_counts` has read, before it stores | Ledger says `done`; the cached counts still say removed 0 (one book left). → m1 |
| — | Lock pin | `git show db4b366:package-lock.json \| sha256sum` | `228bb206…a56c`, equal to `scripts/build-inputs.json` |
| — | Attribution | `git log v0.31.2..db4b366` grepped for Co-Authored / Generated with / anthropic | None |
| — | Bundled Python `Path.exists` | `desktop/runtime-pins.json` (3.14.8 embeddable), and the source of `pathlib.Path.exists` on 3.14 | It is `os.path.exists`, so any `OSError` reads as "missing" |

---

## Rubric

### 1. Security
- Status: Pass. No new shell-outs. SQL is parameterized, and the only interpolated table names are class constants. The new renderer strings and the book title reach the DOM through `textContent`. No Electron, IPC or secret change in range. Deletion validation is assessed under 5.

### 2. Correctness & Logic
- Status: Concerns
- Findings:
  - **M2 [Major]** One moment of `Z:` being unreachable uses up the one-time clean-up for every book it touches.
    - Where: `series_backfill.py:838-852` (`_retry_retained_removals`) moves every match to `cataloged` with `removal_retry` set and checks no drive. `_finish_active` (`series_backfill.py:453-466`) gates only on the library scan. `resume` (`series_backfill.py:1418-1429`) stores any `BoundaryError`/`OSError` as a hold, and the book is never retried by this version.
    - Inconsistency: `NameWrite`'s own pass treats a missing drive as "no try" (`name_write.py:473-474`, `Later(DRIVE_AWAY)`).
    - Effects: if `Z:` is offline, asleep or read-only at the first pass (about 2 min after launch), all 115 books end as "115 old files kept: a check failed". A drop mid-run burns the books still left. `_clear_leftover_temporaries` does the same to the 2 temporaries (`series_backfill.py:880-888`), so Card and Hobb also lose their fresh try. The stored reason carries the engine prefix and raw text, which spec 5.3 left unspecced; a write of names reads "Series recovery…".
    - Undo: only a later `REMOVAL_RETRY` bump.
    - Verified: P2.
    - Ender starts at: the drive check (`_answers(published_root…)`) before the move to `cataloged` and before `_remove_leftover`. Also, an unreachable ancestor during a retried book should become a `Later`, not a hold.

### 3. Crash / Stability Safety
- Status: Concerns
- Findings:
  - **M1 [Major]** The clean-up does not stop for Quit or for "Restart to update".
    - Cause: the R35 loop (`series_backfill.py:742-746`, `name_write.py:434-438`) and `_retry_retained_removals` never read `self.stop`. The candidate loop does (`series_backfill.py:759`). Before this release, active rows were rare crash leftovers. Now 115 `cataloged` rows (about 40 min of NAS reads) run in that loop.
    - Each book is a RENAME critical section with three full reads over SMB (new once, old twice).
    - Quit: `_close_lookups` joins 30 s per worker (`merge_service.py:6470-6480`). `_close_file_changes` then waits up to `FILE_CHANGE_BOUND` = 300 s (`merge_service.py:6482-6493`). The workers keep opening the next book's section, so Quit takes up to about 6 minutes. The process then exits mid-book.
    - Data stays safe on exit: the delete is the last step, and `removal_intended` resumes it correctly.
    - Update: the update waits for the live `series_backfill` thread and open sections (`desktop_backend.py:489-495`). That thread does not end before the loop does, so a "Restart to update" pressed during the clean-up hits its 150 s bound and is undone (`desktop_backend.py:534-536`). This goes against ruling 27, "updates must not fail".
    - A single book of more than about 3 GB on a slow link can also exceed the 300 s bound alone.
    - Verified: P3, plus the code cited.
    - Ender starts at: `if self.stop.is_set(): return` between books in both R35 loops, and in `_retry_retained_removals`.
  - **m4 [Minor]** A database error in the count step can stop the clean-up pass silently.
    - Where: `_finish_active`'s `finally` calls `cleanup_view` (`series_backfill.py:467-470`), which reads the database.
    - Effect: a `sqlite3` error there replaces any exception in flight and aborts the pass. `_run`'s bare `except: pass` swallows it, with no log line. The work already done is safe, and the next pass resumes.

### 4. Performance
- Status: Pass. The old file is hashed twice per book, as the 2026-11-16 ruling requires; its cost to Quit is counted under M1. Selection scans only held rows once per pass. `_kept_old_files` runs on the rules' tick, not on every poll.

### 5. State & Data Safety
- Status: Concerns. The file-delete operations are validated before executing: see the summary. No path to deleting a wrong file was found.
- Findings:
  - **M3 [Major]** The retry records a missing old file as "removed".
    - Cause: the retry keeps `removal_intended: True` from 0.31.2's refused attempt. It is required at `series_backfill.py:862` and carried at 850-852. In `_resume_protected` (`series_backfill.py:1507-1521`), an old file that is missing therefore goes to `done`. It is counted in "N old files removed, X freed" (`_cleanup_counts`), not held as N7 "The old file is missing, and the app did not remove it." That breaks spec 9 check 4 and the N7 row.
    - Worse case: the bundled Python 3.14.8 `Path.exists()` returns False on any `OSError`. A transient SMB error on that one check records `done`, and the old file stays on `Z:`. No later pass looks at a `done` row, so even a future `REMOVAL_RETRY` cannot find it.
    - Verified: P1, plus the pathlib source.
    - Ender starts at: drop `removal_intended` when moving to `cataloged` in `_retry_retained_removals`. Resume sets it again right before the delete (`series_backfill.py:1513-1514`).
  - **M4 [Major]** `_discard_temp` still swallows refusals silently. This is the same class as the root cause.
    - Where: `series_backfill.py:1719-1728`, `except (OSError, ValueError): pass`. `BoundaryError` and `FileRemovalRetained` are both `ValueError`.
    - Effect: every refusal from the new `remove_owned` / `_dispose_temporary` on the failure paths of both writes leaves the temporary file (0.5-1.2 GB) on `Z:` with no log line and its `owned_artifacts` row still present. That covers N2, row 4, N8, a refused local or non-remote removal, and an owner-location refusal. The new sentences for these cases therefore never reach the ledger or the log from this site.
    - History: this is how the 2 leftovers of 0.31.2 were born. `apply` and `resume('writing')` call it on every failure.
    - Ender starts at: at least a `_log` line with the reason and path.
  - **m1 [Minor]** The count cache can go stale after the last book.
    - Cause: `_cleanup_counts` stores its result after the read (`series_backfill.py:436-450`). A `_set` + `_changed()` that lands from the other thread during that read is overwritten with stale counts (P4).
    - Series ledger: the next `candidates()` call clears it (line 683).
    - Name ledger: only the next names write clears it. Until then the "Removing old files" row can stay at "N-1 of N", turn "No progress for 5 min", and keep "All done" away (`finished_state` `late_left`) until a restart.
    - Fix: a generation counter, or invalidate and store under one lock.
  - **m2 [Minor]** One book held in both ledgers is retried by both workers at once.
    - Case: a series hold (A→B) and a names hold (B→C) on the same book. No `_other_writer` check applies to the retry or to `_finish_active`; `_clear_leftover_temporaries` has one.
    - Effect: the sharing violation is safe but makes one hold come back spuriously. Or the series retry hits `CATALOG_MISMATCH`, and A, the oldest copy, stays for good.
    - Unknown: whether any of the 115 overlap. Ender can query the live copy for job ids present in both ledgers' retried rows.

### 6. Input Handling
- Status: Pass. Paths go through `ordinary()` (traversal, ADS, device and trailing-dot names rejected). The fixtures exercise Cyrillic paths. The hold-text match compares a stored string to a computed string; the path is never parsed out of it. The record fields used by the retry are type- and presence-checked (`RETRY_FIELDS`, `isinstance(record, dict)`).

### 7. Maintainability
- Status: Concerns
- Findings:
  - **m5 [Minor]** The selection key is human-facing English. `RECOVERY_HOLD`, `APPLY_HOLD`/`NAMES_FAILED` and `retained_text` now serve as both UI sentences and the retry's key; a future rewording silently selects nothing. The tests pin them, but a stored machine flag would be sturdier. Related: `cleanup_view` reaches into `_cleanup_counts` and both ledgers' `__dict__` (`series_backfill.py:277-308`).

### 8. Doc/Code Drift
- Status: Concerns
- Findings:
  - **m3 [Minor]** The clean-up's total can grow. Spec section 2 says the total is "fixed once the retry has queued them; it never grows". The matcher runs on every pass (`series_backfill.py:838-852`), so any new 0.31.3 hold with the same text (for example a refused removal on a volume that is not positively remote) joins the run. That raises the total, resets the done-line memo (`series_backfill.py:300-305`) and shows the row again. The retry is bounded (once per book), so it is safe.
  - **m6 [Minor]** A false sentence stays after a series leftover is removed. The series variant of `_leftover_outcome` keeps the old hold text, which ends "…The file was kept." (`series_backfill.py:895-898`). The comment says no such book exists today.
  - The N7 drift from spec 9.4 is counted under M3.

### 9. Build & Release Hygiene
- Status: Pass. `db4b366` bumps `package.json` and both root versions in `package-lock.json` together, and the lock pin matches the lockfile's SHA-256. `CHANGELOG.md` has the v0.31.3 entry. The new module is wired into `check-desktop.mjs` and the worker batches. No attribution trailer appears in any of the 13 commits. No v0.31.3 tag exists yet (Sully's step). The manifest is bound to `db4b366`.

---

## Patterns

This repeats the 0.31.2 root cause. A refusal or an environmental failure that is turned into a final state without telling anyone (M2, M3, M4) is the same failure mode as the silently kept NAS removals. Long one-shot work that ignores the stop event (M1) is new, because this is the first release that queues many R35 resumes at once.

---

## Verdict

- Total Critical: 0
- Total Major: 4
- Total Minor: 6

Earlier verdict (db4b366): RELEASE CLEAR

The release is not blocked: no finding deletes a wrong file, loses audio or crashes. Before shipping, consider:

- **M2:** it can waste the whole one-time clean-up.
- **M3:** its orphaned `done` row cannot be recovered even by a later `REMOVAL_RETRY` bump.
- **M1:** it makes "Restart to update" fail during the roughly 40-minute clean-up.

All three are small changes (a drive check, removing one record key, a stop check). Folding them into 0.31.3 is Sergei's call.

| # | Sev | Dim | file:line | Finding | Fix (next cycle unless folded in) |
|---|-----|-----|-----------|---------|-----------------------------------|
| M1 | Major | 3 | `series_backfill.py:742-746`, `name_write.py:434-438` | The clean-up loop ignores stop: Quit up to about 6 min, and an update fails at its bound | Check `self.stop` between books and in `_retry_retained_removals` |
| M2 | Major | 2 | `series_backfill.py:838-852`, `453-466`, `880-888` | `Z:` unreachable once uses up the one-time retry (and Card/Hobb's fresh try) | Drive check before the move to `cataloged`; a retried book's unreachable ancestor becomes `Later` |
| M3 | Major | 5 | `series_backfill.py:850-852`, `1507-1521` | Inherited `removal_intended` turns "old file missing" (or a transient `exists()` False) into `done`, "removed, freed" | Drop `removal_intended` on retry |
| M4 | Major | 5 | `series_backfill.py:1719-1728` | `_discard_temp` swallows every temp-removal refusal with no log | Log reason and path |
| m1 | Minor | 5 | `series_backfill.py:436-450` | Count cache stored after a concurrent invalidation stays stale | Generation counter or lock |
| m2 | Minor | 5 | `series_backfill.py:838-852`, `453-470` | No one-writer check when one book is held in both ledgers | `_other_writer` gate; check the live copy for overlap |
| m3 | Minor | 8 | `series_backfill.py:838-852`, `300-305` | Total can grow; the done line can re-arm | Spec or code |
| m4 | Minor | 3 | `series_backfill.py:467-470` | A database error in `finally` masks exceptions and silently aborts the pass | Guard the call |
| m5 | Minor | 7 | `native_io.py:13-15`, `series_backfill.py:854-862` | UI sentences double as the selection key | Stored flag |
| m6 | Minor | 8 | `series_backfill.py:895-898` | Series leftover keeps "The file was kept." after removal | Reword with the names variant |

---

## Re-review at 520ee66

```
Reviewer: Senua (Code Reviewer), a fresh agent (the first re-review was cut off by a usage limit)
Date: 2026-11-25
Tool: Books Arranger
Release: v0.31.3
Commit range: db4b3667eb4fdb2e02f46ed76130e56c3824792d..520ee66f847e867dde774fc9e5709205005d1728 (14 commits, branch ender/0.31.3-late-writes)
Files changed: 10 files, +1123 / -43 (code: series_backfill.py, name_write.py, web/app.js, web/style.css; the rest is tests and docs)
Stand-down dimensions: none
```

Release source commit: 520ee66f847e867dde774fc9e5709205005d1728
Release artifact manifest SHA256 (observed, `dist/release-artifacts.json`, `source_head` 520ee66, `version` 0.31.3): 0bb30af78499e6a4869f8c43c56843dd2a6fc1ccd071c2e02a47ba37055797f0

### Summary

The range folds in the fixes for M1–M4 and m1–m6 above, plus Futaba's B1 (= M1), m2, m3, m4, m6, m7 and m8. Line numbers below are at 520ee66.

**The delete paths hold.** The range adds no new delete call. It changes the gates around the existing ones:

- the old file in `_resume_protected`;
- the new file in `_withdraw`;
- the write's own temporary file in `_dispose_temporary` and `_discard_temp`;
- the leftover in `_remove_leftover`.

I walked each one again. The old file still goes only after all of these:

- the catalog names the new file by path, size and SHA-256 (`_names_rewritten`, `series_backfill.py:1666-1667`);
- the new file is re-hashed and stays held (`_protected(new)`, 1652);
- the old file's identity, size, SHA-256 and single link pass, then pass again through the same handle on the NAS (`_protected`, `_last_checks`);
- SAME_FILE;
- the folder is held and revalidated.

Two new pieces only decide whether a file is there: the pre-check of the new file (`_seen(new)`, 1647) and `present()`. A "not there" never leads to a removal, only to N7, row 3, `done`, or forgetting a temporary file's record. Every new wait (`Later(DRIVE_AWAY)`, and the `Later` from `_seen`) leaves the recorded state as it was, and the next pass runs every check again. No path was found where doubt fails to keep both files. **No Critical.**

**Earlier findings.** All are fixed at their stated cause (table below). Two are fixed only in part, and the open parts are new findings:

- M2's drive check is too broad: **M5**.
- M3's network half is narrowed, not closed: **M6**.

**New findings:** M5 and M6 (Major), m7 and m8 (Minor). None deletes a wrong file, loses audio or crashes.

### Earlier findings, checked by cause

| # | Stated cause | Fixed at the cause? | Evidence |
|---|---|---|---|
| M1 / Futaba B1 | The R35 loops and the retry never read `stop` | Yes. `stop` is read between books in both loops (`series_backfill.py:865`, `name_write.py:449`), in `_retry_retained_removals` (972, 982) and in `_clear_leftover_temporaries` (1012). Both Quit routes set both stops before any wait: `/api/desktop/quit` through `MergeService.stop_background` (`merge_service.py:6456-6459`), and `/api/shutdown` through `finish_shutdown` → `close` → `_close_lookups` (6477). A book in hand finishes (ruling 27), so Quit waits for one book at most. After a relaunch, `start()` clears the stop and every recorded state resumes. | P3 re-run: with stop set, the hold is untouched and both files are kept. The five `test_m1_*` cases pass, including the control: the next pass, without stop, ends `done`. |
| M2 | A drive that does not answer turns the one-time retry into a final hold | Yes, for a drive that does not answer. The drive is checked before a book is sent back (977), before each book (539), in `resume`'s error path (1573), in the leftover clearing (1024, 1032) and in the names write (`name_write.py:590`). Open: M5, m7. | P2 re-run: `done` once the drive answers. The four `test_m2_*` drive cases pass. |
| M3 | An inherited `removal_intended` reads a missing old file as removed; `Path.exists()` answers False on any `OSError` | The main cause, yes: `removal_intended` is dropped on retry (989), then set again together with `removal_version` right before the removal (1672-1673). The network half is narrowed, not closed: M6. | P1 re-run: N7, counted kept, removed 0. |
| M4 | `_discard_temp` swallows refusals | Yes. The refusal is logged and recorded as `temp_left`, and the ownership row is kept (1898-1901). Open: M6's misread at 1895. | `test_m4_a_refused_temporary_removal_*` passes. |
| m1 | A count is stored over a concurrent write | Yes: a generation token (470-472, 484, 509-513). | P4 re-run: removed 1 after the race. |
| m2 | Both writers retry one book | Yes. The series write goes first and never waits; the names write waits for it (`name_write.py:400-412`, `series_backfill.py:579-588`). Neither waits for the other in a loop. | `test_m2_one_book_*` passes. |
| m3 | The total grows; the done line re-arms | Yes. The picked books are sent back together (970-991), and `removal_version` keeps every hold this version makes out of the run (1002). | `test_m3_a_hold_this_version_made_*` passes. |
| m4 | A count error in `finally` masks the outcome | Yes: guarded and logged (557-562). | `test_m4_a_count_error_*` passes. |
| m5 | UI sentences double as the selection key | Yes. The `LEGACY_*` constants (133-136) match, character for character, what v0.31.2 stored: `git show v0.31.2:series_backfill.py` lines 1002 and 1101, `FileRemovalRetained`'s text, and `name_write.py` lines 452 and 539. | Both versions read side by side. |
| m6 | A false "The file was kept." | Yes: `SERIES_UNCHANGED`, plus where the file is when it was kept (1046-1048). | Its test passes. |
| Futaba m2, m4, m6, m8 | — | Yes: the start delay holds (388, 660); a new file already gone gives row 3 (1647-1651); the Waiting item ends with the scan (339); the total is fixed from launch (496-508). | `FutabaMinorTests` pass. |
| Futaba m3, m7 (every progress row) | — | Yes, and no regression found. `web/app.js:2082` also writes the value when the attribute is missing; a row with no measure stays indeterminate. Below 560 px (`web/style.css:24`), the head and step get a definite width and an ellipsis, and the count and time wrap. Nothing changes above 560 px. | `tests/test_late_cleanup_frontend.js` passes. |

### New findings

#### 2. Correctness & Logic — Concerns

- **M5 [Major]** A book whose folder is gone waits for ever as "The library drive is not answering".
  - **Cause.** `_drive_away` (`series_backfill.py:524-531`) returns True for any `AncestorUnavailable` without asking whether the drive answers. `DirectoryBoundary` raises that error whenever a folder on the way is not there: "the drive or share is away, or the folder is gone" (`native_io.py:82-85`, from `current.exists()` in `__enter__`).
  - **What happens.** Take a held book whose folder was renamed, moved or deleted after 0.31.2:
    - it is still sent back, because the library root answers (977);
    - `resume` then turns the error into `Later(DRIVE_AWAY)` about every 60 s, with no end (1573-1576);
    - the book stays `cataloged` and is never held;
    - "Removing old files" stays at N-1 of N, and "All done" never shows (`late_left`);
    - the same book's write of names waits behind it for good (`_waits_for_other`, `_retry_blocked`).
  - **Regression.** At db4b366 this book was held with a reason. The M2 fix introduced the endless wait.
  - **Same cause, two more places** (read in the code, not probed):
    - the names write's failure path (`name_write.py:590-594`) sets it back to pending with `Later` on every pass;
    - the leftover clearing (`series_backfill.py:1032-1033`) skips Card or Hobb on every pass with no log line.
  - **Verified:** P5 and P10.
  - **Unknown:** how many of the 115 books' folders have changed since 0.31.2. Finding out needs the live catalog, so I did not check.
  - **Ender starts at** `_drive_away`. Count an `AncestorUnavailable` as the drive only when `_answers(root)` is also False. When the root answers, hold the book with a reason (N4, or a sentence from Judy), or wait only a bounded number of times.
- **m7 [Minor]** Part of M2 remains: some short network errors still end a retried book for good.
  - **Cause.** `resume` waits only when the error is `AncestorUnavailable`, or when the root does not answer right after (1573). Any other short error becomes a final hold if the root answers a moment later. Examples:
    - `BoundaryError('Destination directory cannot be protected: [WinError 64] …')` from `DirectoryBoundary`;
    - a failed open of the old file.

    The hold reads `RECOVERY_HOLD` plus the raw error text, which spec 5.3 left without a sentence. A `Held` that a misread network error produced (M6 effect b, or row 3 from `_seen(new)` at 1647) is never checked against the drive either.
  - **Scope.** The window is narrow: one blip inside a book on a link that answers again at once. Both files are kept.

#### 3. Crash / Stability Safety — Concerns

- M1 is fixed (above).
- **m8 [Minor]** A crash just after a leftover temporary file is removed costs Card or Hobb the fresh try.
  - **Cause.** Between `remove_owned` (1126) and the `_set` that records `temp_removed` (1039), the mark exists only in memory. At the next start:
    - `_leftover_temporary` still matches the old text;
    - `_remove_leftover` cannot open the file, which is gone;
    - the root answers, so no wait applies.
  - **Effect.** `temp_kept` is stored, and the book reads "…A temporary file is still there: <path>", which is false. The write of names gets no fresh try.
  - **Scope.** The window is milliseconds (one `lstat` and one catalog write), and nothing is deleted. This code dates from db4b366 and is unchanged in this range; I missed it in the first pass.
  - **Fix.** When the temporary file is already gone and its ownership row is its only record, treat it as removed.

#### 5. State & Data Safety — Concerns

- The file-delete operations are still validated before they run (see Summary).
- **M6 [Major]** A network error can still read as "the old file is gone". This is M3's network half.
  - **Cause.** `present()` (`series_backfill.py:243-251`) treats any `FileNotFoundError` as "not there". Python raises `FileNotFoundError` for these Windows errors:

    | Code | Meaning |
    |---|---|
    | 3 | path not found |
    | 15 | drive not found |
    | 53 | network path not found |
    | 67 | network name not found |

    53 and 67 are what Windows answers when an SMB server cannot be reached. Only error 2 means "this file is not there". P7: `present()` answers False for an existing file under WinError 53.
  - **Effect a: the original M3 worst case, still reachable.**
    1. A NAS removal is lost to a drive drop. The M2 path (1573) keeps it as `Later`, with `removal_intended` True.
    2. On the next pass, the one presence check (1666) gets WinError 53.
    3. The book is recorded `done` (1678-1681) and counted removed and freed, while the old file stays on Z:.
    4. No later pass reads a `done` row.

    This now takes two network faults instead of one. Verified: P8.
  - **Effect b.** In a plain retry, one such error on that check holds the book N7 and uses up its one-time retry. Both files are kept. Verified: P9.
  - **Effect c.** `_discard_temp` (1895) forgets the record of a temporary file that may still be on the NAS, with no log line. It heals itself when the same write runs again (`_own_temporary`). Read in the code, not probed.
  - **Why the tests miss it.** The M3 tests model the network error as `OSError(64, …)`, which Python never raises as "not found" (`tests/test_late_writes_nas_0313.py:1036, 1061`).
  - **Ender starts at** `present()`. Answer False only for a `FileNotFoundError` whose `winerror` is 2 (or that has no `winerror`, off Windows); raise anything else.

#### Other dimensions

- **1. Security — Pass.** No shell-outs. The table names in `_ledger_entry` and `_cleanup_counts` are literals or class constants. The DOM writes are unchanged (`textContent`). No Electron, IPC or secret change.
- **4. Performance — Pass.** The changes add:
  - one `isdir(root)` per held candidate per pass, and one per book;
  - one parse per held row that has `removal_intended` in the count, which is cached.

  With Z: asleep, each `isdir` can wait for the SMB timeout. Stop is read between books, so Quit waits for one such check at most.
- **6. Input Handling — Pass.** `LEGACY_*.format(path)` formats only the template, so braces in a path are safe. Paths still go through `ordinary()`. A record that is not valid JSON reads as `{}` (`_ledger_entry`).
- **7. Maintainability — Pass.** The docstring of `_drive_away` reads "a folder … that is not there" as the drive. That is M5's cause, counted there.
- **8. Doc/Code Drift — Concerns.** The M3 tests' docstrings say a network error is never read as removed, but the error they use cannot reach the `FileNotFoundError` branch (M6).
- **9. Build & Release Hygiene — Pass.**
  - The version stays 0.31.3.
  - The lock pin `228bb206…a56c` equals `scripts/build-inputs.json`.
  - The manifest is bound to 520ee66, with SHA-256 `0bb30af7…`.
  - No attribution line appears in the 14 commits.
  - There is no tag `v0.31.3` yet (Sully's step).

### Verification at 520ee66

All runs used `python -I`, with TEMP and TMP and every fixture under `WIP/Books Arranger/scratch/0313-review`. Nothing touched Z:, `I:\Books Arranger\Data`, the installed app or any catalog copy. Each run took under 600 s.

| # | Check | Method | Result |
|---|---|---|---|
| P1–P6 | The db4b366 probes, run again | `probe2_0313.py` (11.9 s) | **P1:** N7, removed 0 (M3 fixed). **P2:** `done` once the drive answers (M2 fixed). **P3:** with stop set, the hold is untouched (M1 fixed). **P4:** removed 1 after the race (m1 fixed). **P5:** the folder renamed by hand → `cataloged`, "The library drive is not answering" (M5). **P6:** a root that never answers → the book is never sent back, the state is `continues`, as specced (the drive's own Waiting item, `background_work.py:537`, is where the reason shows; not checked live). |
| P7 | Which Windows errors read as "not found" | `OSError(0, …, None, code)`, then `present()` under WinError 53 | 2, 3, 15, 53, 67 → `FileNotFoundError`; 59, 64, 121, 1231 → `OSError`. `present()` answers False for an existing file (M6). |
| P8 | A drive drop during the NAS removal, then WinError 53 on the next pass's check | `probe3_0313.py` | After the drop: `cataloged`, `removal_intended` True, old file there. After the next pass: `('done', '')`, removed 1, freed 18634, **old file still on disk** (M6 a). |
| P9 | WinError 53 on the old file's check in a plain retry | `probe3_0313.py` | Held N7, both files there (M6 b). |
| P10 | P5 on one engine instance over 5 passes, one simulated hour apart | `probe3_0313.py` | `cataloged`, DRIVE_AWAY, 5 deferrals. View: active, 1 left, no Waiting item (M5). |
| T | Targeted tests | `run_targeted_0313.py`: ReviewMajor, ReviewMinor, FutabaMinor, LeftoverTemporary, CleanupView and SeriesFollowUpAfterTheCleanUp tests (79.5 s) | 34 of 36 pass. The two that do not are the SeriesFollowUpAfterTheCleanUp cases (Futaba's m1 lane). Their fixture hard-codes `scratch/s` (`tests/test_rule_filing_031.py:781`), outside my runner's removal owner: what was refused is the lane's own proof-stage `.stderr` file. That is my harness, not the build; Ender's entry check ran these cases green on this build, and Futaba settles m1 in her re-test. |
| F | Frontend | `node tests/test_late_cleanup_frontend.js` | PASS |
| — | Lock pin, manifest, attribution | SHA-256 of `git show 520ee66:package-lock.json`; `dist/release-artifacts.json`; `git log db4b366..520ee66` searched for attribution | As in dimension 9. |

### Patterns

The M2 and M3 fixes replaced "any error is final" with "an error of this type means the drive is away" and "an error of this type means not found". In both, the type says less than it seems:

- `AncestorUnavailable` also covers a folder that is gone;
- `FileNotFoundError` also covers a server that cannot be reached.

A check that decides between waiting, holding and recording a removal should ask the drive itself (`_answers`) and the exact Windows code, not the exception class.

### Verdict at 520ee66

- Total Critical: 0
- Total Major: 2 (M5, M6)
- Total Minor: 2 (m7, m8)

**Verdict:** RELEASE CLEAR

Nothing in this range deletes a wrong file, loses audio or crashes, and every doubt keeps both files. Two findings are worth considering before the one real run on Sergei's library; folding them into 0.31.3 is Sergei's call:

- **M5.** If any of the 115 books' folders changed since 0.31.2, "Removing old files" never ends and "All done" never shows. The fix is a few lines in `_drive_away`.
- **M6.** It is one `winerror` check in `present()`. It closes the last route to a `done` row that leaves the old file on Z:.

| # | Sev | Dim | file:line | Finding | Fix (next cycle unless folded in) |
|---|-----|-----|-----------|---------|-----------------------------------|
| M5 | Major | 2 | `series_backfill.py:524-531`, `977`, `1573-1576`, `1032-1033`; `name_write.py:590-594` | `AncestorUnavailable` is read as "drive away" even when the drive answers: a book whose folder is gone never settles, so the row stays up and "All done" never shows | Count it as the drive only when `_answers(root)` is False; otherwise hold with a reason, or wait a bounded number of times |
| M6 | Major | 5 | `series_backfill.py:243-251`, `1666`, `1678-1681`, `1895` | `present()` reads WinError 3, 15, 53 and 67 as "not there": a lost NAS removal can be recorded `done` with the old file left on Z:, and a plain retry can be burned as N7 | False only for `winerror == 2`; raise anything else |
| m7 | Minor | 2 | `series_backfill.py:1573-1580`, `1647` | Short network errors of other types, or a `Held` from a misread, still end a retried book for good | Check the drive for these too |
| m8 | Minor | 3 | `series_backfill.py:1126`, `1039`, `1110-1112` | A crash between the leftover's removal and its record gives a false "still there" sentence and no fresh try | Treat already gone, with its ownership row present, as removed |
