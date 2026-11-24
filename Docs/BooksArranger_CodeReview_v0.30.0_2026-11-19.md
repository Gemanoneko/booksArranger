# Code Review — Books Arranger v0.30.0

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-19
Tool: Books Arranger
Release: v0.30.0
Commit range: v0.29.0 (0f21134)..5dbba45336915df1cf058b3ea1550f324a95d3d5, 33 commits (main, merges of
  ender/030-features, -join, -reloc, -sorting included)
Release source commit: 5dbba45336915df1cf058b3ea1550f324a95d3d5
Files changed: 122 files, +8619 / -742 (41 code/script files +4450 / -519; 77 test files +3870 / -222; Docs)
Stand-down dimensions: none. Electron: a light pass only. desktop/main.js changes only the Quit flow, and webPreferences
  are unchanged (contextIsolation true, nodeIntegration false, sandbox true).
```

---

## Summary

What changed:
- The jobs panel: live job state on every poll (`live_jobs` / `live_state`), and `/api/state work` (`background_work.py`).
- The action queue is now saved across restarts (`QueueStore`, restore, `restored_press`).
- Item A: the background passes run in retained-runtime mode.
- Item B: the relocation-root ancestry bridge.
- sort-1: `same_value` / `data_location_match` for jobs queued before a storage move.
- Item C: damaged-part repair before a join.
- Item D: Join into one book (`book_join.py`), its undo (A15), and Cancel of a Retry or Repair (`m4b_readmission.withdraw`).
- Item E: `scope_view`.
- Item F: Quit, with its 2 s read bound and the shell's Quit-anyway bound.
- Sorting items 2-8: `sorting_moves.py`, the new endpoints and script, `canonical_names.py`, the series wait, the root series folder, trailing-number part sets, and the 30-hour cap removed.
- The C: guard in the desktop check.
- The 0.29.0 minors.

How I checked it:
- I read every code hunk in the data and file-safety areas the brief named, with the code around it at 5dbba45. I read the page diff only for new HTML sinks; there are none.
- Ender's entry receipt for 5dbba45 (`entry-030b-run`, "check pass", dirty N) is the full-suite run. I did not run the suite again.
- I ran targeted probes on a private `git archive` export of 5dbba45 under `I:/AI Projects/Worktrees/Books Arranger/senua-030`, with TEMP pointed there too:
  - an action-queue safe-stop probe that reuses `test_action_queue.PersistentQueueTests`. Its 8 inherited cases passed.
  - a regex probe of `groups._without_part_number`.

Results:
- Nothing is on the safety floor.
- No Critical findings.
- 6 Major and 6 Minor findings, mostly where Quit, retained mode and the new sorting and join flows meet.

---

## Rubric

### 1. Security

- Status: Pass
- Findings: none.
  - No new shell string: FFmpeg and FFprobe still get argument lists through `run_owned`.
  - No new `innerHTML` or other HTML sink in `web/`.
  - Both `/api/sorting-moves*` routes need the page token.
  - The sorting apply recomputes the list on the server. The client sends only the digest and a list of job ids that can only narrow it.
  - The Electron config is unchanged.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - `action_queue.py:602-623` with `web_server.py:586-588` — **[Major] M1. A safe stop throws away the saved queue.**
    - **Mechanism:** `finish_shutdown` calls `ActionQueue.close()` first. `close()` saves the waiting actions and then clears them from memory. If an action is still running at that point (`stop_now`, which covers Quit anyway, sign-out and the shell pipe closing, never waits for presses) and it ends with `None` (`RetryRefused` while closing, line 680), the worker re-inserts it into the now-empty list. It then saves with `closing=True`. That save replaces every other saved action with this one.
    - **Second path:** the `_admit()` failure path (line 606) does the same.
    - **Probe:** three queued Retry presses, the first one running.
      - Control (the action ends before `close()`): 3 of 3 saved.
      - Safe stop: 1 of 3 saved.
    - **Effect:** the lost presses get no outcome line. Sergei's Q4 "remember" fails silently.
  - `series_backfill.py:206-226, 313-317` — **[Major] M2. One refused follow-up move strands an approved series move for good.**
    - **Mechanism:** after the series is written, `_follow_up` records any refusal of the move once. The pass retries only rows whose `follow_up IS NULL`, so it never comes back.
    - **Quit hits it every time:** Quit waits for the RENAME section and lets `resume` finish. `_follow_up` then runs at once. `_queue_move` → `ActionQueue.enqueue` refuses ("Server is shutting down"), so the refusal is recorded permanently.
    - **End state:** the book stays in its old folder under its new series name. By my reading, the plan then lists it only as "Its name does not follow the app's naming". The page shows nothing about it.
    - **Fix direction:** a transient refusal (closing, draining, a move already running, queue full) should leave `follow_up` empty.
  - `groups.py:389` — **[Minor] m1. `_TRAILING_PART_NUMBER` strips the last 1-3 digits of any longer number.**
    - The lazy prefix may contain digits. Probe results:
      - "metro 2033" and "metro 2034" → "metro 2"
      - "book 1984" and "book 1985" → "book 1"
      - "warhammer 40000" → "warhammer 40"
    - So two different novels in one folder, with the same artist, become one part-set cluster.
    - `part_sets.decide` and the protection of approved groups still keep them apart in the cases I traced. Anchor the number with a non-digit before it (`(?<!\d)`).
  - `canonical_names.py:71-91` with `author_rules.py:37-40` — **[Minor] m2. Two author-merge edges.**
    - The "same words in any order" key sorts initials too. "K. J. Parker" and "Parker J. K." get the same key, so they file into one folder. That is a false merge between two different initial orders.
    - `author()` asks only `same_as` with `folder=''`, so only library-wide rules count. A scoped rule is ignored, and so is a `keep` rule for a Latin credit: a kept Latin spelling is still turned surname-first, at research time (`public_research.py:1587`) and in the sorting plan.
    - No seed conflicts today. Grading this Minor because a false merge is worse than a split.
  - `sorting_moves.py:212-216` — **[Minor] m3. The plan does not catch two listed items with the same target.** It checks only whether the target already exists on disk. The second move fails at run time with `target_exists`. book_move's no-replace publication means nothing is overwritten, but the digest Sergei approves certifies a list that cannot fully run.

### 3. Crash / Stability Safety

- Status: Concerns
- Findings:
  - `desktop/quit-watch.js:86-98`, `desktop/main.js` `watchQuit` / `quitAnyway`, `web_server.py:584-597` — **[Major] M4. Quit anyway kills the engine regardless of an open file change.**
    - **Mechanism:** `createQuitBound` starts its 15 s clock on any named work except the chosen conversion. That includes `critical` (ruling 27's DELETE / CLEANUP / RENAME / TAG_EDIT sections), `press` and `cleanup`.
    - **What follows:** `stop-now`. `finish_shutdown` then raises after 30 s for a press still running. `endOwnEngine` terminates the host 30 s after the pipe closes.
    - **Before:** a `blocked` close left the engine running. The update path still lets "a file change finish by itself".
    - **What this relies on:** each section's crash recovery, which mostly exists (journaled intents, restartable series rename). But it gives up ruling 27's "finishes once begun" guarantee for Quit. Where no recovery runs (M3), nothing repairs the result.
    - **Suggested fix:** exempt `critical`, or extend its bound, the way the update path does.
  - Quit's 2 s read bound: Pass.
    - Status computations, book pages, repair checks (`diagnose_path` is read-only) and gap fill (catalog only) are abandoned only as reads or as atomic SQLite transactions.
    - Series backfill's unbounded write phase is journaled (`writing` → its temporary file is discarded at the next pass). Its RENAME is still waited for.

### 4. Performance

- Status: Concerns
- Findings:
  - `audio_pipeline.py:567-585`, `review_backend.py:913-920, 988` — **[Major] M5. The repair before a join re-copies a damaged part again and again.**
    - **Mechanism:** `part_chapter_plan` makes a full repaired copy of every damaged part that has chapters: it streams the whole source, re-reads it to verify, decodes, and deletes the copy. It is called from `build_manifest`, and the converter's guard runs `build_manifest` up to 4 times per book under `group_lock` (the F31 comment). The attempt then repairs the part again in `check_working_space`. Nothing is cached.
    - **Cost:** for a 1-2 GB part on the NAS, that is minutes of reads and writes while scans, regroups, Keep separate and joins wait for `group_lock`.
    - **Disk leak:** a kill (M4, a crash) leaves `reviews.cache/part-repair-<hex>/` with a full copy inside, and nothing sweeps it. The `storage_cleanup` and `working_lifecycle` patterns match only stage files.
  - `book_join.py:497-568` — **[Major] M6. Join holds the catalog writer too long, with an inverted lock order.**
    - **Mechanism:** `join` holds the catalog writer (`BEGIN IMMEDIATE`) across a full in-transaction `groups.sync` of the root. It then waits up to 5 s for the queue lock. That order is the reverse of the converter's: it holds the queue lock across catalog I/O, so it cannot let go while waiting on the writer that join holds.
    - **Result of a collision:** the full 5 s stall, a wasted regroup, `Busy`, and a retry. 0.22.2 measured about 10 s for a regroup under one writer and saw other writers time out (`groups.presync`).
    - Keep separate already does the in-transaction regroup. The extra 5 s wait while holding the writer is new.
    - **Suggested fix:** take the queue lock before `BEGIN IMMEDIATE`, or use the `presync` pattern.

### 5. State & Data Safety

- Status: Concerns
- Findings:
  - `sorting_moves.py:170-220`, `merge_service.py:317-318` — **[Major] M3. A sorting move in retained-runtime mode is never recovered if interrupted.**
    - **Mechanism:** Sergei's portable install is always in retained-runtime mode, and move recovery never starts there (Ender's decision row: "not reviewed").
    - **What 0.30.0 adds:** an approval that moves many books at once, and the Quit-anyway kill (M4).
    - **Exposure:** a move interrupted after its publication or rename and before its location commit stays `unfinished` for good. The catalog points at the old path; two copies or a temp file stay in Sorted.
    - **Plan does not skip retained jobs:** `plan()` also lists retained jobs (no `retained_job` check), unlike `series_backfill.candidates`.
    - **Mitigation:** Sorted to Sorted moves are mostly same-volume renames, which keeps the window small.
  - Pass on the rest of the brief's list:
    - **Digest guard:** recomputed on the server and signs job, from, to and items.
    - **Verified move and no overwrite:** book_move, with no-replace rename and publication; `name` is checked to be a bare `.m4b` name.
    - **Partial failure:** each item is reported separately and the others go on.
    - **Item B (relocation-root ancestry):** keyed exactly; no other loosening.
    - **sort-1 (`same_value`):** bridges only paths inside the bound data namespace. Library paths, hashes and other strings fail `_root` / `_inside` and compare exactly.
    - **Item A (retained mode):** the gone-source check never decides a book that has a job. Recovery purge, working, finished-book and regroup passes skip retained jobs and fail closed on an unreadable record.
    - **Join:** one transaction, rolled back on Refused or Busy; the parts' jobs are set aside under the queue lock. The withdraw race is handled by `_withdrawn_meanwhile`.
    - **Undo:** refused once the joined book is approved or has a job.
    - **`part_chapter_plan`'s `rmtree`:** removes only its own fresh uuid folder.
  - `action_queue.py:534-566` — **[Minor] m6. Two gaps in queue restore.**
    - A saved press for a book that got a new press while loading is dropped without an outcome line.
    - The stale check depends on the older version writing `desktop_shutdown`. An older version that crashed or was killed in between is not detected, so its presses come back. They re-check revisions, so this is low risk.

### 6. Input Handling

- Status: Pass. Join items are bounded (2-200, unique, typed ids and revisions). `job_ids` is limited to 1-2000 strings of at most 100 characters. The digest must be a 64-character string. Titles and authors are bounded to 1000. Progress `file` is bounded to 260.

### 7. Maintainability (no Critical findings on its own)

- Status: Pass. `_running` gives `state()` and the live read one shared wording. Fixtures in `tests/test_action_queue.py` reuse cleanly. `retained_job_ids` has a caller.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings:
  - `web_server.py:588` and the `action_queue.py` docstring — **[Minor] m4. Stale comments.**
    - `web_server.py:588` still says "queued actions are dropped, never run (Q1)". Since 0.30.0 `close()` saves them.
    - The module docstring says "a queued move is cancelled at the next start". `drop()` cancels it at Quit, and in retained mode there is no move recovery at all (M3).

### 9. Build & Release Hygiene

- Status: Pass, with one Minor.
  - Ender's entry receipt covers exactly 5dbba45 (dirty N, check pass).
  - `package.json` is still 0.29.0. That is Sully's bump.
  - `.gitattributes` makes the hashed files LF.
  - `c-drive-guard.mjs` has a positive control (`tests/test_c_drive_guard.js`, case 2), and each child gets its own TEMP.
- Findings:
  - `scripts/c-drive-guard.mjs` `list()` — **[Minor] m5. The C: guard looks only at the top level of each place.** A write inside a folder that already exists is invisible, for example under `%LOCALAPPDATA%\<existing app>\`, `%APPDATA%\npm-cache` or a `C:\Users\<name>` subfolder. That covers any writes into an installed app's data folder on C:. Ender's comment covers create-then-delete but not this.

---

## Patterns

Quit keeps trading waits for kills (0.22.3, 0.29.0 S-m4, now item F). Each round makes some writer's crash path load-bearing (M1, M2, M4), and retained-runtime mode switches off one of those paths (M3). Before the next Quit change: list every writer, its crash recovery, and whether that recovery runs in retained mode.

---

## Verdict

- Total Critical: 0
- Total Major: 6
- Total Minor: 6

**Verdict:** RELEASE CLEAR

There are no Critical findings and nothing on the safety floor. M1-M6 and m1-m6 are logged for Ender's next cycle. My suggested order:
1. M1 and M2: small, local fixes.
2. M4: exempt `critical` from the Quit-anyway bound.
3. M3: review move recovery for retained mode, or exclude retained jobs from the plan.
4. M5 and M6.
