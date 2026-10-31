# Code Review — Books Arranger v0.24.1

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-31
Tool: Books Arranger
Release: v0.24.1
Commit range: v0.24.0 (f7317a43486d1de8e1289bd0fa3781328d16a3b9)..765a6fed1bbba5662522898af011158e56c8e9a3 (13 commits)
  First pass: v0.24.0..1f48bebdcb611d7cd427f8c213019ee89cc3bd5d (12 commits)
  Delta (r2): 1f48beb..765a6fe (1 commit, ruling 77: Senua's M2, M4, M5)
Files changed: 35 files, +1745 / -134 (delta: 5 files, +205 / -48)
Stand-down dimensions: none
```

Release source commit: 765a6fed1bbba5662522898af011158e56c8e9a3

Release artifact manifest SHA256: 5c23fe856d8df656793af93f5e6e897727d1e8726f6696e42d9c676b9e9c8832

---

## Summary

The range ships rulings 74e, 74f, 74g, 75a, 75b, 76a, 76b and 76c. The first pass read the full diff, red-team style, starting with the paths that can lose data:

- 74e/76b folder deletion: `fd4416c`, `ec1ac07`.
- 75a after-conversion check moved into SQL: `0efa330`.
- 76a revision bypass by fingerprint, and the automatic job set aside and restored: `0dd9ce7`.
- 75b Start over on a changed source: `ff8187d`.

**What holds:**

- The 74e deletion machinery is sound. The library root and its direct children are never candidates. A probe ran `_folder_candidates` over drive roots, a trailing `\`, a root in different case, Cyrillic, `[]`/`()`/spaces, UNC, `..` and an out-of-root source: zero violations, and the last two were refused.
- Leftover files go through `book_delete.remove`, which uses an exact handle inside the root, held ancestry, one link and the listed size. The folder goes with a non-recursive `os.rmdir`, which can only remove an empty directory (or the link itself, if one was swapped in), so a late arrival makes it fail safe.
- The 75a SQL prefilter is a strict superset of the old full scan. A differential fuzz compared 24,000 rows, 17,548 of them flagged by the old scan, and found 0 misses. Both degraded controls failed as expected: with the casefold arm removed, 1,125 misses; with the control-character/NUL arm removed, 333 misses.
- 76a's set-aside happens under the queue lock, which the worker's `_claim` also takes, so a claim and a set-aside cannot interleave.

**Delta (765a6fe, ruling 77).** It closes M2, M4 and M5, each verified on the repo's own disposable fixture:

- **77a:** deletion now uses a known-safe allowlist. `.aaxc`, `.pdf`, `.zip`, `.m4v`, `*.mp3.!qb`, `cover.jpg.mp3` and a name with no extension each keep the whole folder, with nothing deleted and nothing recorded as removed.
- **77b:** an unreachable drive or a failed run returns `later`, restores the folder job's prior state and records no outcome. Once the drive is back, the next sweep clears the folder.
- **77c:** `source_folder_removed_files` keeps one full, never-blanked row per file, with path, size and mtime. `Delete book`'s `forget()` does not list the table, so the record survives forgetting a book.
- I also suspected a vanished published audiobook would loop forever as "transient". The probe disproved it: that failure is recorded, not retried.

**Still open (not in the delta's scope):**

- M1: a paused queue or a scan starting mid-sweep strands a book. Re-probed at 765a6fe: still reproduces.
- M3: Quit cannot stop a sweep in the middle of a book.
- The Minors below.

None of the open findings meets the Critical bar; every failure mode found keeps folders rather than losing them.

**Tests run (targeted, per Lean verification):**

- First pass:
  - Passed: `test_source_folders` (33), `test_working_lifecycle` (8), `test_approve_as_is` (23), `test_backup_rule` (13).
  - `test_start_over` (32): the six new 75b tests pass. Eleven pre-existing automatic-start tests fail when the module runs alone (see m8).
- Delta at 765a6fe: `test_source_folders` (37) and `test_backup_rule` (14) pass, plus probes Q1–Q7.
- Probes and fuzz ran in a session scratchpad, since removed.
- The r2 build was verified read-only:
  - `C:/Antigravity Projects/Worktrees/Books Arranger/q241/r2/dist/release-artifacts.json` hashes to the pin above and names `source_head` 765a6fe and version 0.24.1.
  - All 86 packaged engine and web files are byte-identical to 765a6fe, ignoring line endings.
- Nothing touched Z:, the live `data/` folder, the repo's `dist/`, or the app.

---

## Rubric

Line numbers are at 765a6fe.

### 1. Security

- Status: Pass. No new shell-outs. No `desktop/` (Electron) change. The new SQL builds identifiers only from internal table names and `""`-quoted column names, with values bound; the new 77c table is written with bound parameters only. The new UI writes via `textContent`. The fingerprint is validated as 64 lowercase hex (`web_server.py` `fingerprint_value`).

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **[Major] M1 (open)** — `storage_cleanup.py:977-982`, `:1018-1020`; `merge_service.py:953-956`, `:1211-1228`. **The 76b sweep strands books whenever the queue is paused or a scan starts mid-sweep.**
    - The sweep's guard is `_storage_guard`. It raises `InterruptedError` whenever `jobs._stop` is set, which is true after any Pause or any stop-on-hold until the next Start, and it raises `ValueError` once a scan starts.
    - `run_folders` then rewrites the folder job from `completed` to `needs_attention`. 77b's `FOLDER_RETRY` and the prior-state restore both exclude `InterruptedError`, and a scan's `ValueError` is not "on the drive".
    - On `InterruptedError`, nothing is recorded, against the docstring's "the next start resumes it". `old_folder_jobs` only selects `completed`/`unsupported`, so the book is never selected again, and `_settle_folder_jobs` retries only busy, already-gone or `FOLDER_RETRY` reasons.
    - While paused, every retention pass (60 s) strands the next book. Over about 10 h of an idle paused app, the whole ~600-book backlog can be stranded.
    - On `ValueError` (a scan), `needs_attention` is recorded as the book's one-time outcome.
    - Either way, `series_backfill.py:321-324` then treats the book's cleanup as unfinished, so `Later` repeats forever and its series fill never runs.
    - Probes P1, P2 and (at 765a6fe) Q7 reproduce it on the repo fixture.
    - Fix direction: skip the sweep (do not start a book) while `jobs._stop` is set or a scan is alive. Restore the prior state on *every* sweep exception, as 77b already does for drive failures.
  - **[Major] M2 — Fixed in 765a6fe (ruling 77b).** Previously, `os.path.isdir` False while Z: was offline recorded `gone`, and a listing `OSError` recorded `kept`, both permanently. Now:
    - `_root_reachable` gates the sweep (`:964`).
    - `_might_clear` returns `None` on `OSError`, which means `later` (`:933-943`, `:971-972`).
    - A run that fails on the drive restores the prior folder-job state and returns `later` (`:978-981`).
    - Probe Q1: offline gives `later`, no marker, the job is still selected; once the drive is back, `completed` and the folder is cleared. Probe Q5: a mid-run `OSError(64)` restores `unsupported`.
  - **[Minor] m11 (new, delta)** — `storage_cleanup.py:964-973`. Reachability is checked once, on the library folder, and then each kept folder's `os.path.isdir` is trusted. `isdir` returns False for any error, including a network blip after the root check or access denied on that one folder, so a kept folder that merely could not be read can still be recorded `gone` for good. Distinguish "not found" (`lstat` → `FileNotFoundError`) from other errors, or check `_root_reachable` again just before recording `gone`/`kept`.
  - **[Minor] m1** — `merge_service.py:3370`, `:3405`. `APPROVE_CONVERTING` ("…it will finish with the automatic names…") is raised for any running or claimed current job, before `_approved_automatically` is checked. When the running job is his own earlier Approve, the sentence claims automatic names that are not the ones in use.
  - **[Minor] m2** — `merge_service.py:3373-3380`. `_his_revision` moves to the current revision on *any* record-only change with the same files: research, backfill and so on, not only the two causes the docstring names. When no "Goes to" path was sent (preview not loaded), an Approve-as-is files under values the row never showed, where it used to be refused as `changed`. This is reversible (rename/move), and it is within "my approval is the highest authority", but the m1 "path shown is path used" guard now protects only when a path was shown.

### 3. Crash / Stability Safety

- Status: Concerns
- Findings:
  - **[Major] M3 (open)** — `merge_service.py:1224-1225`, `:4738-4741`; `storage_cleanup.py:197`. **Quit cannot stop a sweep in the middle of a book.**
    - Each sweep book re-hashes the published m4b in full over Z: under `operation_lock`. The guard checked per chunk (`_storage_guard`) never looks at `_retention_stop`.
    - `close()` sets `_retention_stop` and joins the retention thread for 30 s *before* `jobs.close()` sets the flag the guard does read. A large book on a slow link (over ~30 s to hash) therefore makes `close()` raise `TimeoutError('Recovery cleanup is reaching its safe file checkpoint')`, and the close button does not quit promptly.
    - The same hold blocks Approve (`approve_automatic` and `queue` are `@operation`) for the whole book. The 20 s `OLD_FOLDER_BUDGET` is checked only between books, and Python's `RLock` gives a waiting press no turn between back-to-back books.
    - 77b adds `_root_reachable`, an `os.scandir` of the library folder, inside the same lock, so an offline Z: can also hold Approve for an SMB timeout.
    - `_finish_temporary_cleanups` already passes a `_retention_stop` flag; the sweep does not.
    - Fix direction: give the sweep's `protected_output` a guard that also raises on `_retention_stop` and `_closing`, and run the reachability check before taking the lock.

### 4. Performance

- Status: Concerns
- Findings:
  - **[Minor] m3** — `storage_cleanup.py:789-813`. `_held` is called per own folder. Each call reads every non-superseded `catalog_group_members` row and `json.loads` every unfinished job manifest and reacquire snapshot. Across the ~600-book sweep, that is a full catalog pass per folder; a `WHERE path IN (…)` lookup would do.
  - **[Minor] m4** — `storage_cleanup.py:933-943`, `:971-975`. `_might_clear` does not know which folders are the book's own. A book whose only kept folder is a non-own ancestor holding a safe leftover (for example a series cover) can never be cleared, yet it still triggers the full re-hash of its published m4b over Z: before ending `retained`.
  - **[Minor] m5** — `web/app.js:665`, `:797-799`. The 5-minute list re-ask aborts only the client fetch. The engine's `/api/inventory` handler keeps computing, and `cached_page` does not share in-flight reads, so after a re-ask two identical heavy reads compete for the engine's one core, which is exactly when it is already slow.

### 5. State & Data Safety

- Status: Concerns (deletion bounds verified; the 77 fixes verified; the Minors below remain)
- Findings:
  - **[Major] M4 — Fixed in 765a6fe (ruling 77c).** Previously the names of deleted leftovers lived only in a receipt cut at 1,000 characters and blanked on success. Now `source_folder_removed_files` gets one row per file (job, candidate, folder, full path, size, `modified_ns`), written `removing` *before* the file goes (`:900`) and then set to `removed` or `not_removed` with the full cause (`:902`). Nothing updates or deletes these rows except their own outcome, and `book_delete.forget()` does not list the table. Probe Q2: three files, one with a long name, each recorded in full as `removed`. **Note for 77a:** the ruling says Sergei sees the final `SAFE_LEFTOVERS` list. That cannot be checked from code; Jane confirms it before the release.
  - **[Major] M5 — Fixed in 765a6fe (ruling 77a).** Previously "no audio left" was judged by an extension denylist. Now `leftover_verdict` (`:50-63`) deletes only a known-safe allowlist, judged on the last extension, plus `Thumbs.db`, `desktop.ini` and `.DS_Store`.
    - A file is kept if any of its extensions is audio (`cover.jpg.mp3`, `x.mp3.!qb`), if it has no extension, or if its extension is not on the list.
    - One rule now serves both the run and the sweep's pre-check, which resolves m9.
    - Probe Q3: `.aaxc`, `.pdf`, `.zip`, `.m4v`, partial download, double extension and no extension each return a keep reason. A folder with `cover.jpg` and `booklet.pdf` is kept intact with no removal rows.
    - Probe Q4: `Cover.JPG`, `Book. Part 1.jpg`, `desktop.ini`, `.DS_Store`, `Thumbs.db`, `rip.log` and `v1.0.png` are safe, as intended.
  - **[Minor] m12 (new, delta)** — `storage_cleanup.py:900-902`. A row written `removing` stays `removing` for good if the app dies, or the catalog write fails, between `remove()` and `_record_outcome`. Nothing later reconciles it against the disk, so the record cannot tell "deleted" from "still there" for that file. A later run reconciling `removing` rows by `lexists` would close it.
  - **[Minor] m6** — `storage_cleanup.py:801-806`. A job set aside by 75b Start over or 76a Approve stays in `audio_jobs` as `needs attention`. `_held` counts every non-completed job's cover, so a book that was ever started over or replaced keeps a `cover.jpg` in its folder, and that folder is retained forever ("Another book or job uses a file"; probe P5). This fails safe, but 74e/76b silently do nothing for exactly the books 75b/76a touch. `_held` should skip `audio_job_set_aside` rows.
  - **[Minor] m7** — `storage_cleanup.py:706-720`, `:995`. Candidates are bounded by the root frozen in each old manifest, not by today's configured library folders. Source 1 is immutable and sources cannot overlap (`source_config.py:98-106`), so this is defence in depth only. Still, for 76b's months-old manifests a check that no candidate is a current library folder or a direct child of one costs nothing.

### 6. Input Handling

- Status: Pass. New request fields are whitelisted by `shape()`. The fingerprint is validated at enqueue and on the direct route. Bulk and queued paths pass it through unchanged. 77a's name matching is case-insensitive on the last extension and treats any audio extension anywhere in the name as audio. Lookalike or unknown extensions fall to "keep".

### 7. Maintainability (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **[Minor] m8** — `tests/test_start_over.py`. The module is not self-contained. Run alone, 11 pre-existing automatic-start tests fail ("No sorted output folder is set", `KeyError: 'pending_kind'`). With `sorted_fixture.patch_merge_service()` applied, 5 still fail. The module passes the gate only because some other module in the same worker batch patches `MergeService` at import. This is pre-existing (none of the six new 75b tests fail), but a gate rebalance like 72f can break it silently.
  - m9 (the audio/link rule written twice in `_leftovers` and `_might_clear`): **resolved in 765a6fe**. Both now call `leftover_verdict`.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **[Minor] m10** — These docs say what the code does not do (still true at 765a6fe):
    - `Docs/BooksArranger_Brief.md` (76b row) and `merge_service.py:1212-1215` say "closing stops it and the next start goes on". It stops only between books (M3), and a book interrupted by Pause is never resumed (M1).
    - `storage_cleanup.py:963` says "an InterruptedError (closing) records nothing". True, but the folder job is left in `needs_attention`, outside what the sweep selects (M1).
    - The docstrings say "only while … no scan holds the catalog". A scan can start mid-book (M1).
    - The "durable receipt" drift is gone with 77c.

### 9. Build & Release Hygiene

- Status: Pass.
  - The version moves 0.24.0 → 0.24.1 together with `package-lock.json` in `44e84f6`.
  - 765a6fe is a fix on the same version, and the r2 build is made from it.
  - The r2 manifest hashes to the pin above and names `source_head` 765a6fe, version 0.24.1 and build `c8f9f07a-1004-4119-8b29-51587040e331`.
  - All 86 packaged `resources/backend` engine and web files are byte-identical to 765a6fe, ignoring line endings.
  - No test, scratch or secret files are in the backend listing.
  - Tag `v0.24.1` is not yet created; that is Sully's.

---

## Patterns

Two patterns recur:

- **One rule written twice:** `_leftovers` and `_might_clear` (fixed in 765a6fe); in 0.24.0 (C1), `folder_unit.verdict` with two input sets.
- **Housekeeping that writes a terminal or one-shot state on a transient failure.** 77b now applies "transient means retry later" to drive failures (M2), but not yet to Pause or a scan (M1). Since 74e this housekeeping deletes user files and its failure states feed `series_backfill`, so every exit path needs the same discipline.

---

## Verdict

- Total Critical: 0
- Total Major: 2 open (M1, M3); 3 fixed in 765a6fe (M2, M4, M5)
- Total Minor: 11 open (m1–m8, m10, m11, m12); m9 resolved

**Verdict:** RELEASE CLEAR

No Critical finding is open and the safety floor is intact. Ruling 77 closes the three findings that bore on what the folder cleanup may delete and how it is recorded. M1 and M3 keep folders and stall housekeeping or Quit; they never lose data, and they are logged for Ender's next cycle. One release precondition sits outside the code: ruling 77a says Sergei sees the final `SAFE_LEFTOVERS` list before the cleanup runs on Z:.
