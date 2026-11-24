# Code Review — Books Arranger v0.31.1, round 2

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-24
Tool: Books Arranger
Release: v0.31.1
Commit range: 7ed4d62..b497778ac9306353aa02bc6c324bcd7667d3fef0 (4 commits); round 1 covered v0.31.0..7ed4d62
Files changed: 16 files, +757 / -133
Stand-down dimensions: none
```

---

## Summary

This round re-reviews Ender's fixes for round 1 (`BooksArranger_CodeReview_v0.31.1_2026-11-24.md`) and for Futaba's QA findings:

- removal holds: `finished_removal.blocked`, `_removal_hold`, and the same check again inside the removal's transaction;
- a search by file ID among files of the same size, for books renamed by hand;
- corrected wording in the job reason, the log and the status line;
- the brake weighed against all finished books;
- the listing cache;
- the 30 s reference re-check;
- shared search tokens, searched in batches of 64;
- retained-run guards;
- a finished-book recheck after every Start.

**Method.**

- My two round-1 probes were run again against `b497778`, with a third for the dot-folder case.
- A randomized soundness check of the new reference search: 40 trials, up to 160 paths each. The rows included case changes, doubled backslashes, JSON wrapping, `ſ` and the Kelvin sign. A forced 200-token case exercises the batching.
- `tests/test_relink_found.py` ran in full, 26 tests including the probes. Everything passed except my dot-folder probe.
- `test_published_snapshot_lifecycle` and `test_recovery_retention` cannot run in this session. The hook puts the temp folder on `I:`, and the native file disposal refuses there (`FileRemovalRetained … could not be verified`). That comes from the environment, not from this change. For the 30 s re-check I relied on reading the code and on Ender's entry check.
- Nothing ran against Sergei's install, profile, catalog or `Z:\`.

---

## Round-1 findings: status

| # | Round-1 finding | Status at b497778 | Evidence |
|---|---|---|---|
| M1 | A book with an unfinished app move, or a replacement parent, was removed as gone | **Fixed** | `merge_service.py:6058` (`_removal_hold`), `finished_removal.py:47` (`blocked`: any non-terminal `book_moves` row, any replacement link) and `finished_removal.py:88` (checked again inside the caller's `BEGIN IMMEDIATE`, under the catalog write lock). My `rename_intent` probe now stays `completed`. |
| M2 | A book renamed in place, or moved inside a skipped dot-folder, was removed as gone | **Fixed for every folder the search enters. The skipped-folder part remains (r2-m1).** | `_namesakes` and `_with_recorded_id` (`merge_service.py:6074-6101`). My rename-in-place probe is now relinked to `Fixed Title.m4b`. The dot-folder probe is still `removed`. |
| M3 | "No files touched" while the removal triggers deletion of the copies | **Fixed** | `finished_removal.py` `REASON`; the log now says "library and source files untouched"; the status line says "library files untouched" (`web/app.js`). All three are now accurate. |
| m1 | The brake's denominator shrank after the launch pass | **Fixed** | `merge_service.py:6224`, `max(checked, _finished_total())`. |
| m2 | An incomplete listing was relisted once per missing book per pass | **Fixed** | `_output_files` caches any listing for `RELINK_INDEX_SECONDS`. A cached incomplete listing still answers "unprovable", and `_remove_missing` still lists fresh. |
| m3 | Reference check once per loop | **Fixed** | `working_lifecycle.py:811` and `:897`: the check runs again every 30 s for the files still to go, in both `_discharge_published` and `_discharge_removed`. |
| m4 | New passes lacked the retained-job guard | **Fixed** | `audio_jobs.py:653` (a retained 'needs attention' row also returns early); `_removal_hold`; `_release_removed_leftovers` and `_release_changed_copies` skip retained jobs. |
| m5 | Keep files docstrings were stale | **Fixed** | `recovery_retention.py:128`, `merge_service.py:2475`. |

---

## Red-team of the new code

- **File-ID search, wrong-file adoption: none found.** Adopting a file still goes through `_relink_matches`. That needs `S_ISREG`, the recorded `[st_dev, st_ino]` or native identity, one link, the size and the full SHA-256 on a held handle, and exactly one match. The same-size pre-filter only adds candidates, and each one still has to pass every proof. A hard link has links = 2 and is refused. A file whose ID number was reused has the wrong hash, so the book stays and is not removed.
- **Books with no recorded file ID: safe.** Any file of the same name or the same size makes `_relink_found` return False. In `_remove_missing` the book is skipped. So such a book is never adopted, and is never removed while something could still be it. Any `OSError` while reading a file of the same size answers None, which also means nothing is removed.
- **M1 transaction re-check: sound.** `blocked` reads `book_moves` and `audiobook_replacements` inside the removal's own `BEGIN IMMEDIATE`, so no move or replacement link can be written between the check and the tombstone. Two observations, neither a finding:
  1. The re-check reads holds, not location. A 'found' move recorded after `_remove_missing`'s proof is terminal and does not block. That needs the file to come back under Sorted, and a Start's check to relink it, inside one book's proof window (a Start sets `_verify_stop`, and `_remove_missing` checks it before every book). That is negligible.
  2. A replacement link of any state blocks removal for good, so a deleted book that was ever replaced stays listed. This is conservative and deliberate.
- **Shared token, batches of 64: sound. It cannot miss a reference.** The proof above `TOKEN` (`working_lifecycle.py:61-71`) holds for any TOKEN-only substring of the normalized path, not only the longest run. `search_tokens` always gives each path one of its own runs (`best in runs[index]` is list membership). Every token falls in some batch. The control-character, NUL, blob and casefold-to-ASCII conditions are rebuilt per batch from that batch's tokens. Python still decides every returned row against every wanted path. The randomized check found 0 rows that the full scan flags and the candidate search misses, over 40 trials and the forced 200-token batch case.
- **30 s re-check: correct.** It covers only the files still to go (`prepared[index:]`) and resets its clock after each run. A reference that appears mid-loop holds the rest through `discharge_published`'s existing `published_held` path. The remaining window is at most 30 s plus one removal. That is accepted in the brief's revisit column.
- **Start-triggered recheck, races with running jobs: none that remove anything.** The background pass cannot start while the converter thread is alive (`audio_jobs.py:720`). A Start, or a book queued by an approval, sets `_verify_stop`, so a pass in flight ends without removing anything, or stops `_remove_missing` before its next book. `sorting_moves` and `name_write` select only `state='completed'`, so they never touch a removed book. A replacement or a rules move started meanwhile is caught by `blocked` in the transaction. One cost was found: r2-m2.

---

## Rubric

### 1. Security
- Status: Pass. Nothing new shells out, the IPC surface is unchanged, and no secrets were added.

### 2. Correctness & Logic
- Status: Concerns
- Findings:
  - **r2-m1 [Minor]** `merge_service.py:6166` with `merge_service.py:6178`: the M2 fix does not reach folders the search never enters. Those are folders whose name starts with `.`, `#`, `@` or `$`, and hidden or system folders. Samba hides dot-folders by default, and `metadata.safe_name` keeps a leading `.` or `#`, so a series like `.hack` gets such a folder. A book renamed or moved within such a subtree is neither in the name index nor in the size index. `_absence_proof` still walks the recorded path through it and "proves" the book gone.
    - Reproduced: `.hack__Sign\Vol 1.m4b` renamed to `Volume 1.m4b` in place ended as `removed`.
    - Fix: when the recorded path passes through a folder `_output_files` does not enter, return False (never remove) or search that subtree.
    - Minor rather than Major because the trigger is now narrow: a book filed under such a folder that Sergei then renames or moves within it. The cost is the same as round 1's M2: the catalog entry, which can be restored by hand, and copies released without the audiobook being verified.

### 3. Crash / Stability Safety
- Status: Pass. `_verify_rows` now always runs `_pass_finished`, and `b497778` lets a test stand-in work without `pass_done`. The log de-duplication (`_relink_said`, `_refuse_removal`) is bounded by the number of books.

### 4. Performance
- Status: Concerns
- Findings:
  - **r2-m2 [Minor]** `merge_service.py:1672` with `audio_jobs.py:720-726`: after any Start, `_recheck_waiting` stays True until a published-check pass starts. That cannot happen while the converter thread is alive, so the recovery sweep runs every 20 s instead of 60 s for the whole conversion run, possibly all night. Each sweep reconciles one working attempt. It also runs the purge batch, the leftover passes and `_finish_temporary_cleanups`, which does two replacement lookups per completed job through `_retained_cleanup_job`. That is three times the background catalog work during conversions, on the engine's one Python core: the same contention class as the stuck-load bug. Fix: count `_recheck_waits()` toward the 20 s cadence only while the queue is idle, or have the converter's exit wake the sweep.
  - The shared-token search is a clear win: the 270 s → 2.3 s measured in the brief is plausible from the code.

### 5. State & Data Safety
- Status: Pass. Every deletion path from round 1 is unchanged except for the 30 s re-check, which narrows a window and widens none. The new removal holds only make removal stricter. A wrong removal now needs the r2-m1 skipped-folder case.

### 6. Input Handling
- Status: Pass. No new inputs.

### 7. Maintainability
- Status: Pass.

### 8. Doc/Code Drift
- Status: Pass. The brief's rows match the code. "Hidden, system, `#`/`@`/`.`/`$` folders … are not searched" is stated, but the brief does not say that such a folder's books can still be removed (r2-m1).

### 9. Build & Release Hygiene
- Status: Pass. `package.json` is still 0.31.0, as in round 1; Sully bumps it. No stray files are in the range. Untracked in `Docs/` and outside this range: the round-1 report, Futaba's QA report and Judy's UX spec.

---

## Verdict

- Total Critical: 0
- Total Major: 0
- Total Minor: 2 (r2-m1, r2-m2)

**Verdict:** RELEASE CLEAR

All three round-1 Majors and all five Minors are fixed, apart from M2's skipped-folder part, which is carried here as r2-m1. The new code adds no deletion risk. The reference search is sound, the file-ID relink cannot adopt a wrong file, and the removal holds are re-read under the write lock. Both Minors are for the next cycle; r2-m1 is a few lines if Jane wants it in 0.31.1.
