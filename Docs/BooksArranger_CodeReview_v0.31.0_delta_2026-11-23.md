# Code Review — Books Arranger v0.31.0 (delta)

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-23
Tool: Books Arranger
Release: v0.31.0
Commit range: a8b6804a013b643412c72aedf34f1e7e00de1455..8cc8c5a59dd40c30df708762a1d4fe3093586935 (branch ender/0.31.0)
Files changed: 14 files, +766 / -49 in 5 commits (no merges); product code outside tests and *.md: 6 files, +223 / -29
Stand-down dimensions: none
```

Counts: `git diff --numstat` and `git rev-list --count [--no-merges]` on the two endpoints. The full review (`BooksArranger_CodeReview_v0.31.0_2026-11-23.md`) certified `v0.30.1 (50c4d4b)..a8b6804`. `a8b6804` is an ancestor of `8cc8c5a`, so the two reports together cover `50c4d4b..8cc8c5a` with no gap. This report certifies the range through `8cc8c5a`.

---

## Summary

The range has five commits:
- `0375cb3`: the fix for M1 and M2. Both writes now share one move check (`book_move.begun`); the Mover gets a write-lock barrier and a backstop.
- `e961288`: the fix for M3. A series found by 0.30.x is looked up again, and counts as not found until it is.
- `fc7771c`: R30. `MergeService.choice_after_write` re-points his Choose folder… move after a rewrite.
- `bac371e`: R31. The page shows Paused.
- `8cc8c5a`: R32. DuckDuckGo's human check counts as "nothing found".

I read every line of the product changes. I re-ran my earlier M1, M2 and M3 probe shapes, which are now Ender's tests. I added three probes of my own (P1–P3) for the windows the new tests do not reach.

**Answers to the brief's four attacks:**
1. **M1, M2 and M3 are fixed.** The probe shapes from my last review now resolve. The book is no longer lost to "history does not link", and a 0.30.x series is judged doubtful.
   - The barrier and the backstop add no deadlock and no stuck move. No Python lock is taken inside a write transaction. The barrier's wait is bounded by the 10 s busy timeout, and a timeout fails the move with nothing moved.
   - **A book can still end up as two copies.** When the move wins, the write is held and its rewritten file stays in Sorted, untracked (M5). Ender's own test asserts this outcome. It contradicts R30 and the CHANGELOG.
2. **R30 works only when his press lands after the write's catalog step.**
   - If he presses during the retag, his move fails "in use", and the rules then file the book in their own folder (M4, probe P1). In other words, it goes to the wrong place.
   - It never re-points a move that is not his.
   - There is no unbounded loop. A lasting refusal, though, is retried every pass and keeps the rules' entry open (m9).
   - A Quit between the write and its follow-up drops his queued move (m10).
3. **M3: yes, in one shape.** Take a 0.30.x hold whose job is no longer its book's current, eligible job (re-converted, replaced or retained). It is counted as a look-up to do but never looked up, so "All done" never shows (m11, probe P3).
   - Holds on eligible jobs are looked up once and settle.
   - Ender's count on the live copy says all 55 holds are eligible today.
4. **R32: yes.** The match needs the exact `CHALLENGE_REASON`, the host `html.duckduckgo.com`, and the source names `publisher` or `litres`.
   - A human check from Goodreads stays a try, and so does DuckDuckGo not answering.
   - When Wikipedia's wait is re-raised in its place (`_series_publisher`), that also stays a try.

**Construction verdict.** No audio can be lost. Every new path either moves nothing, or keeps both copies. The defects are that R30 does not hold in a write's two longest phases, and that the fixed M1/M2 window still leaves a stray full copy in Sorted.

### Tests run (targeted, lean verification)

Runtime: the gate's pinned QA runtime at `WIP/Books Arranger/build-cache/qa-runtime` (the entry harness's `BOOKS_QA_RUNTIME_ROOT`). Its `python.exe` SHA-256 is `434b361f…`, `ffprobe.exe` is `fe818a56…` and `ffmpeg.exe` is `a3bf949b…`, all matching `scripts/qa-runtime.json`.

Every run used a `git archive 8cc8c5a` copy under `I:/AI Projects/Worktrees/Books Arranger/senua-031b-scratch/`. TEMP, TMP and TMPDIR all pointed into the copy's own scratch. Each run went through the gate's `support_dispositions(runroot/'scratch', [runroot/'scratch'])` wrapper. Counts are the runner's `testsRun`.

| Run | Modules | Result |
| --- | --- | --- |
| 1 | `test_name_write_031.py`: `MoveWindowTests`, `ChoiceDuringWriteTests` | 13 tests, OK (31 s) |
| 2 | `test_name_write_031.py`, `test_rule_filing_031.py`, `test_series_moves_031.py`, `test_series_lookup_ends_031.py`, `test_series_backfill.py`, `test_sorting_030.py` | 178 tests, OK (192 s) |
| 3 | `node tests/test_window_title_frontend.js` (R31) | PASS |
| Probes | Senua's `test_senua_probe_031b.py`: P1 (write of names, series write), P2, P3 (with its control) | 5 cases ran; outputs quoted under M4, M5 and m11. The loader also picked up `PreRuleSeriesTests` through the import, so the run total is 9, all OK |

**Runner note.** My first pass of run 2 left TMPDIR at the session default, outside the copy's scratch.
- Under it, `test_rule_filing_031.SafetyTests.test_a_copy_cut_before_it_was_placed…` failed. The QA disposition owner refused to remove the move temporary (`FileRemovalRetained`).
- The same case failed the same way on an `a8b6804` copy.
- With TMPDIR inside the copy, 178 of 178 passed.
- That failure came from my runner, not from the product.

The entry check on `8cc8c5a` (`q031d`) reads `check pass`. The full suite was not run here.

The probe file was in the scratch copy. The method for each probe is given below, so Ender can rebuild any of them from the `MoveWindow` and `PreRuleSeriesTests` fixtures.

**Disposal.** The scratch folder (`I:/AI Projects/Worktrees/Books Arranger/senua-031b-scratch/`, 253.85 MB: two `git archive` copies, `8cc8c5a` and `a8b6804`, plus the probe and runner files) is not removed yet.
- I tried the studio sweep twice, 90 s apart: `node scripts/studio-sweep.mjs --project "Books Arranger" --path "<that folder>" --apply`. Both times it kept the folder: `in use or locked (rename refused: EBUSY)`.
- No running process names the folder in its command line, and none runs from the QA runtime.
- The folder holds nothing to keep. It needs the same sweep line again once the lock clears.

---

## Rubric

Severity tags `[Critical]` / `[Major]` / `[Minor]` are defined in `Team/Docs/ProcessRules.md` § Severity definitions. New findings continue the numbering of the full review (M4 onward, m9 onward).

### 1. Security

- Status: Pass
- Findings: none.
  - No new shell-out, route or `innerHTML`.
  - Nothing in `desktop/` changed.
  - The `web/app.js` change is one boolean term.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **[Major] M4 — R30 does not hold when he presses Choose folder… during the retag. His move fails "in use", and the rules then file the book in their own folder.**
    - Where: `merge_service.py:6547`. Only a move that stopped with cause `'changed'` is queued again.
    - Why it fails: the write holds the old file through `VerifiedFile(old)` for its whole retag and proof (`series_backfill.py:953`, `name_write.py:521`). That handle shares read only. The Mover's `VerifiedFile(old, delete=True)` therefore meets a sharing violation and fails `'in_use'` (`book_move.py:620-623`).
    - After the write, `choice_after_write` finds no live move of his. The failed move's cause is not `'changed'`, so it returns None, and the follow-up queues the rules' own move.
    - Probe P1 (method): the real Mover runs his move from inside the write's `_write` (the retag), using `MoveWindow.choose_folder`/`run_move`. The pass then goes on with the real catalog, follow-up and queue. Output:
      - Write of names (author folder changes): `his move: failed in_use`. Moves: `[('failed','user','his','in_use','Mine'), ('queued','rules',None,None,'Obukhova Lena')]`. Book now in: `Obukhova Lena\…`.
      - Series write: `his move: failed in_use`. Moves: `[('failed','user','his','in_use','Mine'), ('queued','rules',None,None,'Normal Abnormal')]`. Book now in: `<author>\Normal Abnormal\…`.
    - The retag and its proof are the longest phase of a write (minutes per book on the share), so this is the most likely moment for "a Choose folder… pressed while the app rewrites that book".
    - The R30 tests press only after the write has reached `renamed` with its catalog step blocked, so they never reach this window.
    - Fix direction (shared with M5): while a write of the book is in hand, his move should wait, not run. Then `choice_after_write` can re-point it (rebase) or queue it again. Alternatively, queue again any of his moves that was created after the write's approval and stopped at its start, whatever the cause (`'in_use'` as well as `'changed'`).
  - **[Minor] m9 — `choice_after_write` gives its edge outcomes no lasting/passing split.**
    - The stopped branch (`merge_service.py:6549`) can raise a refusal that will never pass. Examples: his folder plus the longer new name goes over 240 characters (`book_move.plan`), "newer version", or no completed publication. The refusal becomes `'later'` on every pass.
    - `rule_filing.py:383` then keeps the entry open ("still to be asked for"). It holds one of the two FEED slots, and `to_file` stays above 0, so "All done" never shows.
    - `sorting_follow_up` already splits lasting refusals from passing ones (`:6498-6502`); this path does not.
    - The rebase branch catches the same too-long refusal (`:6542`). But it then leaves his move pointing at the old file, where it fails `'changed'`. The follow-up is already recorded as `'none'`, so nothing queues his move again. The book stays in its old folder under its new name, in neither his folder nor the rules' folder.
    - Narrow: it needs his press during a write plus a long path.
  - **[Minor] m11 — a 0.30.x hold on a job that is not a look-up candidate is counted as "to look up" for good, and "All done" never shows.**
    - Where: `series_backfill.py:333-335`. `summary()` counts every `pre_rule()` hold as `'due'` without checking eligibility.
    - `candidates()` skips the same row: not the book's newest job (`:486`), not completed, retained, already given a series, or missing a title or author. `unsettled()` skips it too.
    - Probe P3 (method): `PreRuleSeriesTests`' 0.30.x-shaped hold, plus a newer `audio_jobs` row for the same book (`needs attention`, no output). Three passes, then the finished state through `background_work` as in `HumanCheckTests.finished_state`. Output:
      - Superseded job: `ledger=held pre_rule=True asked=[] summary due/left=1/1 unsettled=[] finished_state=background_only`.
      - Control (current job): `ledger=held pre_rule=False asked=['goodreads'] summary due/left=0/0 finished_state=all_done`.
    - Ender's count on the live copy (all 55 holds are in `unsettled()`) says no live book is in this shape today. Any 0.30.x `MOVE_WAITS`/`WRITE_WAITS` row whose job is re-converted, replaced or retained before its first 0.31.0 pass will be.
    - Before `e961288` such a row counted as `moves_waiting`, which holds back no state.
    - Fix direction: count `again` only for a row that `candidates()` would take.
  - Still open from the full review: m3 (a doubtful source does not make the book doubtful) and m4 (the 0.30.0 approval route bypasses the write of names). This range does not change either.

### 3. Crash / Stability Safety

- Status: Pass
- Findings: none new.
  - **Barrier** (`book_move.py`, `_run`): it opens a `BEGIN IMMEDIATE` on a closing connection and commits nothing. A writer's transaction holds no Python lock (`_move_running` is a plain set read), so there is no lock-order deadlock with `run_move`'s `operation_lock`.
  - **Barrier timeout:** a timeout (10 s busy) is an `sqlite3.Error`. `run()` settles it as a queued move that failed with nothing moved.
  - **A move taken back meanwhile:** it returns without running.
  - **Backstop:** a `'changed'` failure after `rename_intent` or `copy_intent` is recorded through `run()`'s `Failed` branch. At that point nothing has been renamed and no temporary exists.
  - **Write lock in `choice_after_write`:** it holds the write lock only for the running check and `rebase()`.
  - Still open from the full review: m1 and m2. This range does not change them.

### 4. Performance

- Status: Pass
- Findings: none. A move does one more `resolve()`. `summary()` parses JSON only for `held` rows with `MOVE_WAITS`/`WRITE_WAITS`.

### 5. State & Data Safety

- Status: Concerns
- Findings:
  - **[Major] M5 — when his move wins the window, the rewrite is abandoned and its rewritten file stays in Sorted as an untracked full copy.**
    - Where: `series_backfill.py:1142`, raised from `_no_move_begun` at `:1248`.
    - The window is a move that starts after the retag and before the catalog step (the temporary renamed, the new file proven).
    - The guard now holds the write (correct for the catalog), but `_resume_protected` keeps the published new file, by design ("copies kept"). Nothing removes it later: the write is `held` for good.
    - Probe P2 (method): the M1 shape, with the real Mover mid-hash. Output:
      - `move: complete`. `write: held`, reason `The catalog could not record the series; copies kept: The audiobook was moved meanwhile…`.
      - Files under Sorted: `['Mine\<old name>.m4b', '<author>\White Nights Ghosts - <author>.m4b']`. The catalog names only the first.
    - Ender's own test asserts this outcome (`tests/test_name_write_031.py:786`, "the proven new copy is kept").
    - Against R30: his folder gets the old file with the old names and tags, not the rewritten one. Sergei has to find and delete the second copy by hand. `CHANGELOG.md:28` says this case "no longer leaves two copies".
    - No bytes are lost, and the catalog now resolves. That is the real gain over `a8b6804`, whose M1 and M2 chain break is closed.
    - Fix direction: as in M4, keep his move from starting while a write of the book is in hand. Or, when the guard fires, dispose of the proven new file through its held, hash-checked handle; the catalog never named it.
  - **[Minor] m10 — a Quit or restart between a write and its follow-up drops his choice.**
    - At close or at the next start, a queued move is cancelled (`book_move.py:886-888`, and ActionQueue `_forget_move`).
      - If his move had not been re-pointed yet, `choice_after_write` finds no live move of his, and the follow-up runs the rules' move.
      - If the rebase had already committed, the follow-up is recorded as `'none'`. The book stays in its old folder under its new name.
    - A second, narrow case: while startup recovery runs, `_move_running` reads every move as running (`merge_service.py:6626`). A write resumed then, for a book whose queued move recovery has not cancelled yet, is held as in M5.
  - **Verified sound:**
    - The M1 and M2 shapes (move mid-hash under `'queued'`; move completed before the catalog step; both writes) keep a catalog that resolves.
    - A writer that committed before registration is caught by the barrier: the Mover reads the book after the commit and stops before it holds the file.
    - An unregistered Mover is stopped by the backstop at its first journal write, on both strategies.
    - `rebase()` acts only on a queued move, under the write lock, and only while nothing runs it. The Mover reads its move only after that lock.
    - R30 re-points only moves that carry his override, are of this job, are queued, and were planned from exactly the receipt the write replaced (`replaced()`: path and SHA-256). A rules move is never touched.
    - M3: `judged()` cannot be satisfied by a 0.30.x record. `number_from` did not exist in 0.30.0 or 0.30.1 (`git grep` on both tags: 0 hits). A stored doubtful shape stays doubtful in `certain()`.

### 6. Input Handling

- Status: Pass
- Findings: none.
  - R32 matches only on the exact reason constant, host and source names (see attack 4).
  - A DuckDuckGo limit row whose stored reason is a 403/429 pause keeps that reason and stays a try.
  - Note, not a finding: while DuckDuckGo's challenge pause lasts, every book looked up settles publisher and Litres as "nothing found" for good, without a request being made (`LOOKUP_POLICY` makes `'none'` final). That is R32 as ruled.

### 7. Maintainability (no Critical findings on its own)

- Status: Pass
- Findings: none new. m7 and m8 are still open. `choice_after_write` copies part of `sorting_follow_up`'s refusal handling, but not its classification (see m9).

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **[Minor] m12** `CHANGELOG.md:28-29`: "no longer leaves two copies… Whichever began first finishes; the other stops". When the move wins, the stopped write leaves its rewritten copy behind (M5). The R30 line (`:31`) says his choice "now wins", which holds only after the catalog step (M4).
  - m5 is partly fixed. The `name_write.py` comment and the `sorting_moves.certain` docstring are corrected. Still open:
    - A held write of names still reports series wording. P2 shows "The catalog could not record the series" for a write of names.
    - `BooksArranger_0.31.0_Scope.md:90` still reads "0.31.0 = steps 1 and 4".

### 9. Build & Release Hygiene

- Status: Pass
- Findings: none.
  - No change to `package.json`, the lockfile, `scripts/` or `desktop/`, and no new test module, so the gate inventory is unchanged.
  - The entry check on `8cc8c5a` passed.
  - No commit carries Claude attribution (`git log --format=%B` grep: 0 hits).

---

## Patterns

R30 was fixed at the boundary where the earlier finding sat (the catalog step) and nowhere else. A write has three phases: retag and proof, then rename and proof, then catalog. The Mover is coordinated with the last one only. In the first phase a share-read handle quietly turns his move into an "in use" failure. In the second, the guard keeps the catalog right but strands a copy.

A ruling about something the user does during a long operation should be probed in every phase of that operation, with the competing worker actually running.

---

## Verdict

- Total Critical: 0
- Total Major: 2 (M4, M5)
- Total Minor: 4 new (m9, m10, m11, m12); m1–m8 from the full review carried (m5 partly fixed)

M1, M2 and M3 from the full review are fixed. No open finding is Critical, and the safety floor is intact: every write stays inside the library, no secrets are involved, and no history is rewritten. M4 and M5 are gaps in R30 with no loss of audio, and they need one shared fix. They are logged for Ender; whether they go into this release or the next is Sergei's call, through Jane.

**Verdict:** RELEASE CLEAR
