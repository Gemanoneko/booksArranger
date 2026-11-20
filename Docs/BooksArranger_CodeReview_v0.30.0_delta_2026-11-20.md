# Code Review — Books Arranger v0.30.0 (delta)

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-20
Tool: Books Arranger
Release: v0.30.0
Commit range: 5dbba45..03041ee73c8c34e222885abe2db884fc23a34c9b, 24 commits (merges included). Follows my review of
  v0.29.0..5dbba45 (BooksArranger_CodeReview_v0.30.0_2026-11-19.md, RELEASE CLEAR, 6 Major, 6 Minor). The verdict below
  covers the full 0.30.0 range, v0.29.0..03041ee.
Release source commit: 03041ee73c8c34e222885abe2db884fc23a34c9b
Files changed: 50 files, +2212 / -271 (28 code/script files +812 / -242; 21 test files +1378 / -28; the Brief)
Stand-down dimensions: none. Electron: light pass; webPreferences unchanged.
```

---

## Summary

What changed:
- Fixes for my M1-M6 and m1-m6.
- Futaba's QA fixes: F1 (held Brom cleanup re-checked on Start), F2 (freshness cue), C1-C3, D1-D3, the research row and the Approve file count.
- Sergei's damaged-parts ruling (`1a0c031`): container-only damage with the audio proven intact converts normally; damage the app can't repair says "Need to reacquire".
- Two test-isolation fixes.

How it was checked:
- I read every code hunk. The red-team focus was the five areas in the brief: F1, the audio-intact proof, M4's bound, M1/m6 persistence, and the author-merge and part-number rules.
- Ender's entry check at 03041ee is the full-suite run. I did not repeat it.
- I ran targeted tests on a private `git archive` export of 03041ee under `I:/AI Projects/Worktrees/Books Arranger/senua-030`, with TEMP pointed there. All passed:
  - `test_sorting_030_review` (24 cases)
  - `test_recovery_ancestry_moves` (4)
  - `test_quit_bound` (14)
  - `test_action_queue` (38)
  - `test_damage_ruling` (7, real FFmpeg)
  - `quit-watch.test.mjs` (17)
- I re-ran my 0.30.0 M1 probe (a safe stop while a queued action runs): 1 of 3 actions were kept at 5dbba45, 3 of 3 at 03041ee.
- I ran a rules probe on `groups._without_part_number` and `canonical_names._order_key`.

Results:
- Every Major from the first review is fixed. Nothing is on the safety floor.
- 0 Critical, 0 Major, 4 Minor.

---

## Focus areas (the brief's questions)

- **F1. Can the re-check delete originals for a genuinely different recovery set? No.**
  - `CleanupJobs._run` calls `_recovery_boundary` (relocation-aware ancestry plus root identity) before any marker change, copy or removal.
  - Each member's recorded backup path must equal the expected one ("Recovery correspondence changed").
  - Every recovery copy is fully re-hashed against the source SHA-256 before the first original is disposed.
  - A cleanup whose restore began is skipped (`_restore_begun`).
  - Nothing runs it unprompted: `_finish_held_cleanups` needs an admitted Start, and `_resume_guarded` passes no backlog without a press.
  - The test has negative controls, and they hold with every original kept: forged ancestry, a replaced recovery folder (same name, same bytes), and a begun restore.
  - One latent parity gap, not counted as a finding: the `_work` re-pick does not filter `kept_by_choice` the way the sweep does. Keep files is offered only for "Original bytes differ…", so it cannot apply to this reason today.
- **The audio-intact proof never accepts damaged audio as intact.**
  - `m4b_repair.container_only` needs every repair kind to be container-only, so any `truncated_final_frames` makes the whole file damaged.
  - `prove_audio_intact` (join) and the single-file path both require four things: equal copied-audio evidence, a packet count equal to the source's full sample table, complete `-xerror` decodes of both files, and identical native PCM.
  - The planner proves that no sample uses missing bytes.
  - Mid-stream frame corruption is not a container shape. It stays "intact", fails its decode, and becomes "Need to reacquire" (`test_every_known_shape…`).
  - The only blind spot is the one every conversion has: frame bytes that decode without an error.
- **M4. Does Quit always end? Yes, on every path where the engine answers or refuses. The worst case is about 650 s (≈ 11 min).** The parts:
  - the 15 s bound;
  - up to 300 s while a file change is named (createQuitBound; a poll with none named ends it at once);
  - stop-now;
  - 30 s;
  - up to 300 s of kill hold (endOwnEngine `holdKill`, 2 s request timeout, polled every second);
  - a 5 s kill wait.

  On the engine side, `finish_shutdown` and `_close_file_changes` are each capped at `FILE_CHANGE_BOUND` = 300 s. The engine keeps serving status through `merge.close()`, so the shell's hold can see the change. One case predates 0.30.0 and is still open: see m-d1.
- **M1 and m6. Queue persistence under a crash and another version: Pass.**
  - `close()` keeps the waiting actions, and every later save is stamped as a clean close.
  - An action that comes back to wait is saved before its admission is released.
  - The saved queue is written in one SQLite transaction.
  - The other-version check runs in the right order: `ready()` sets `previous_owner` before `start_loading()` triggers the restore, and `server.instance` exists before the queue is built.
  - A crash during a run loses only that action, by design ("never run twice").
  - One unidentified failure in 13 runs of `test_action_queue`'s persistence cases plus my probe. It did not reproduce in 12 reruns; it looks like a timing flake in a test, not in the code.
- **The author-merge and part-number rules: Pass (my probe outputs are below).**
  - Part numbers:
    - "metro 2033", "book 1984", "warhammer 40000", "agent 007" and "chapter 100" are now left whole.
    - "darwin's blade 1" and "darwin's blade 2" still form one set.
    - "fallout 76" and "harry potter 6" / "harry potter 7" are stripped by design. That is two digits, set apart by a separator. The chapters, and protected approved groups, still decide.
  - Authors:
    - "K. J. Parker" and "Parker J. K." are now two people. "A. A. Milne" and "Milne A." are two as well, a split, which is the safe side.
    - Scoped rules count in the book's own folder, and keep, not-author and collection rules leave the name as it is.
  - What still merges, by Sergei's "same words in any order" ruling, not a defect: "Ross Thomas" with "Thomas Ross", and "Jean-Paul Sartre" with "Paul Jean Sartre".

---

## Rubric

### 1. Security

- Status: Pass. No new shell strings, HTML sinks or IPC. The sorting script now confirms which app it is talking to (`/api/health`) before it does anything, and exits 1 if any named book did not move.

### 2. Correctness & Logic

- Status: Concerns (Minor only)
- Findings:
  - `audio_pipeline.py:587-590` and `manual_conversion.py:716` — **[Minor] m-d2. An internal repair error is reported as permanent damage, with no way to retry.**
    - A part repair that raises `ValueError` / `KeyError` / `TypeError` / `StopIteration` (an app defect included) becomes `PartRepairError('failed')`.
    - Under the ruling, that now shows "{file} is damaged and cannot be repaired safely. Delete the book, then get a new copy." and offers no Retry.
    - So a repair bug after an update would tell Sergei to delete a book he cannot retry. The file was diagnosed repairable, so it is damaged, but the deletion advice should come only from a proven verdict.
- Verified fixed: M2 (`sorting_follow_up` returns 'later' for passing refusals and `_follow_up` retries them), m1, m2, m3, C1 and C3.

### 3. Crash / Stability Safety

- Status: Concerns (Minor only)
- Findings:
  - `desktop/main.js:624` (`watchQuit`), `desktop/quit-watch.js:6-14` — **[Minor] m-d1. Quit can still wait forever on a hung engine.** This predates 0.30.0. `createQuitWatch` counts only refused connections, and a timeout resets its count. An engine that keeps its socket open but stops answering status leaves the shell in `watchQuit` with no window and no bound. The bound and the kill hold run only on answered polls. A cap on consecutive timeouts, after which Quit anyway goes ahead, would close it.
- Verified fixed:
  - M4: a file change is waited for on both sides, with a 300 s bound.
  - M6's deadlock risk: the join now takes the queue lock before the catalog writer, the same order as `_record_source_damage` (reviews.lock, group_lock, queue lock).

### 4. Performance

- Status: Pass.
  - M5 is fixed. The chapter plan never copies a damaged part. The conversion repairs it once per attempt, in its stage, outside the review and group locks, so nothing is left in `reviews.cache`.
  - M6 is fixed. The join plans its regroup on a read snapshot, then makes one short write, the way `presync` does.
  - Residual, not counted: when the regroup inputs change between plan and commit, the full regroup runs in the final transaction while the queue lock is held, so `live_status` polls wait for it. That path is rare (three planning attempts first).

### 5. State & Data Safety

- Status: Pass.
  - F1 is safe (see Focus areas).
  - M3: move recovery runs in retained mode. Retained jobs and retained paths are skipped (`from` / `target_path` / `temp_path` match the journal columns; an error counts as skipped), and the plan leaves retained jobs where they are.
  - The join stays all or nothing; every Refused or Busy rolls back.
  - Note for QA: the first 0.30.0 start will reconcile any move that was left unfinished on Sergei's install since 14 Nov. It uses the same reconcile path as any other mode.

### 6. Input Handling

- Status: Pass. The sorting apply answers every named job id, either "Not in the list" or the list's own refusal reason.

### 7. Maintainability (no Critical findings on its own)

- Status: Pass. `press_progress` is keyed by thread; the action queue clears its own entry at start and end. Entries left by non-press threads that rebuild a manifest are small, and are cleared when a thread id is reused for a press.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Pass. m4 is fixed (`finish_shutdown` comment, `action_queue` docstring). Each new decision row in the Brief matches its code.

### 9. Build & Release Hygiene

- Status: Concerns (Minor only)
- Findings:
  - `scripts/c-drive-guard.mjs` (`OUR_TEMP_PREFIXES`, `OWN`) — **[Minor] m-d3. The C: guard got deeper but no longer fails on Python temp names.**
    - The m5 fix walks inside every Books Arranger-named folder on C: and fails on any new or changed entry. Good.
    - But it dropped `tmp` and `etilqs_` from the names that fail a run. A Python fixture of ours that ignores the redirected TEMP and falls back to the real Temp is now only a note. That is the leak the guard was built to catch.
    - The trade-off is documented: another program's `tmp*` names in Temp. Matching the note's time against the run window would bring the positive control back.
  - `tests/test_damage_ruling.py` — **[Minor] m-d4. The join path's proof has no failing test.** The only negative control for the audio-intact proof is on the single-file path (PCM mismatch → refused). `prove_audio_intact` in the join path has none for a PCM mismatch or a packet count that differs from the sample table. The code is correct by reading; the test should prove it.
- Version: `package.json` is still 0.29.0. That is Sully's bump. The entry check passed at 03041ee.

---

## Patterns

The fixes landed with their failure-before controls named in each commit. That is the right habit. What remains sits at the edges of the Quit and damage flows: a hung engine (m-d1), and an internal error read as damage (m-d2).

---

## Verdict

- Total Critical: 0
- Total Major: 0
- Total Minor: 4

**Verdict:** RELEASE CLEAR

There are no Critical or Major findings and nothing on the safety floor. m-d1 to m-d4 are logged for Ender's next cycle.
