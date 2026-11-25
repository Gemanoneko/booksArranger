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

**Verdict:** RELEASE CLEAR

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
