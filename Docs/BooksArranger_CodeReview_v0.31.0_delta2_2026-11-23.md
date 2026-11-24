# Code Review — Books Arranger v0.31.0 (delta 2)

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-23
Tool: Books Arranger
Release: v0.31.0
Commit range: 8cc8c5a59dd40c30df708762a1d4fe3093586935..7023cc9e77fb8cb528991e3ec287891787c2a7df (branch ender/0.31.0)
Files changed: 10 files, +479 / -73 in 2 commits (no merges); product code outside tests and *.md: 6 files, +185 / -67
Stand-down dimensions: none
```

Counts: `git diff --numstat` on the two endpoints. The full review (`BooksArranger_CodeReview_v0.31.0_2026-11-23.md`) certified `50c4d4b..a8b6804`. The first delta (`BooksArranger_CodeReview_v0.31.0_delta_2026-11-23.md`) certified `a8b6804..8cc8c5a`. This report starts at `8cc8c5a`, so the three reports together cover `50c4d4b..7023cc9` with no gap. This report certifies the range through `7023cc9`.

---

## Summary

The range has two commits:
- `e7f889b` (R33, for M4 and M5):
  - A move of a book waits while the app writes that book. The action queue's blocker says `'book'`, and `run_move` asks again after it registers the move.
  - The write marks itself `'writing'` before it opens the file, and steps aside if a move is already registered.
  - The R30 follow-up re-points the waiting move.
  - Backstop: if a move still started before the catalog step, the write deletes its own rewritten copy through its checked handle (`_withdraw`).
- `7023cc9` (R34, for m9 and m11, plus m12):
  - A lasting refusal of his move fails it once, with the "path too long" sentence.
  - A 0.30-era hold counts as "to look up" only if the look-up would take that job.
  - CHANGELOG corrections.

I read every product line in the range. I re-ran P1, P2 and P3, and added P4 to P8 for the six attacks in the brief.

**Answers to the brief's six attacks:**
1. **P1, P2 and P3 now resolve. M4, M5, m9, m11 and m12 are fixed.**
   - P1: a press during the retag now waits (`WaitsForWrite`, blocker `'book'`). After the write, the move takes the rewritten bytes to Mine. One copy, his one move, no rules move. Both kinds of write.
   - P2: the engine's move now waits through the catalog window. A Mover registered by hand inside that window still ends with one copy: the backstop removed the rewritten file.
   - P3: the superseded hold is no longer "to look up", and "All done" shows. The control (current job) still counts.
2. **No deadlock. But the wait can last until he presses Start, and it holds every action queued behind it (M6).**
   - `run_move` drops its registration in `finally`, and nothing takes a Python lock.
   - The wait does not end when the write's file work ends. It ends when the write's follow-up is recorded. After a Quit at the end of a write, or a crash, that follow-up only runs once the pass finds the app idle and not paused.
3. **The backstop cannot remove the only good copy.**
   - It deletes only the write's own proven file, re-hashed through the delete handle with one link, and only while the catalog still names the old file.
   - The receipt change and the `'cataloged'` state commit in one transaction, and a committed receipt is recognised (`series_backfill.py:1212-1214`) before the move check (`:1241`). A rename the catalog already recorded can never be withdrawn.
   - It can fire on a move that has not begun, during startup move recovery. The rewrite is then thrown away and his move takes the original file (m13, P6). No audio is lost.
4. **The step-aside is race-free: the write and the move can never both go ahead.** Each side marks itself before it looks at the other: the ledger `'writing'` (`series_backfill.py:1295`), then the registration (`merge_service.py:6650`).
   - In one interleaving both step aside (P5). The write is held "moved to a folder you chose". The move runs one poll later and moves the original file. The rules' entry ends (left 0, could not 0).
   - The outcome is safe. Only R33's "rewritten file" promise is missed, in a window of microseconds.
5. **A share that is briefly offline cannot trigger the "permanent" path.** `choice_after_write` reads only the catalog and does no file I/O. The only refusal it treats as lasting is the 240-character path check (`book_move.py:350`), which does not change from one try to the next.
   - **The catch-all around it does misfire (m14, P7).** Two errors that clear on their own are read as lasting: "Move state changed" and "Publication generation changed during protection". The rules' follow-up then cancels his queued move.
6. **No.** `_look_up_jobs` applies the same fixed checks as `candidates()`: newest completed, published job of the book; not a reuse task; not retained; no series; has a title and an author. Any hold it drops is one the look-up never takes.
   - Note, not a finding: `summary()`'s cache can show the old count until the next ledger write or pass, at most 10 minutes (P3: `1` right after the newer job appears).

**Construction verdict.** No audio can be lost. The backstop deletes only a proven copy that the catalog never named. Every refusal leaves the original file in place. M6 is a liveness defect: the wait is tied to the follow-up's idle gate rather than to the write itself.

### Tests run (targeted, lean verification)

Runtime: the gate's pinned QA runtime, `WIP/Books Arranger/build-cache/qa-runtime`. `python.exe` SHA-256 is `434b361f…`, `ffmpeg.exe` is `a3bf949b…` and `ffprobe.exe` is `fe818a56…`, all matching `scripts/qa-runtime.json`.

Every run used a `git archive 7023cc9` copy under `I:/AI Projects/Worktrees/Books Arranger/senua-031c-scratch/`. TEMP, TMP and TMPDIR all pointed into the copy's `scratch/tmp`. Each run went through the gate's `support_dispositions(runroot/'scratch', [runroot/'scratch'])` wrapper, with the gate's fixture-root map. Counts are the runner's `testsRun`.

| Run | Modules | Result |
| --- | --- | --- |
| 1 | `test_name_write_031.py`, `test_series_moves_031.py`, `test_destination_override.py`, `test_action_queue.py`, `test_rule_filing_031.py`, `test_series_backfill.py`, `test_finished_state_031.py`, `test_book_move.py` | 275 tests, OK (190 s) |
| Probes | Senua's `senua_probe_031c.py`: P1 to P8 (14 cases). The loader also picked up `PressDuringWriteTests` (9) through the import | 23 cases, OK (53 s). Outputs are quoted below |

The entry check on `7023cc9` (`q031e`) reads `check pass`, exit 0. The full suite was not run here.

The probe file and the runner sat in the scratch folder's `probes/`, beside the copy, not in it. Each finding below gives the probe's method, so Ender can rebuild it from the `MoveWindow`, `PressDuringWriteTests` and `PreRuleSeriesTests` fixtures and `test_action_queue.Server`.

**Disposal: not done yet.** Two scratch folders are still on disk:
- `I:/AI Projects/Worktrees/Books Arranger/senua-031c-scratch/` (124.17 MB): this review's `git archive` copy, probes, runner and logs.
- `I:/AI Projects/Worktrees/Books Arranger/senua-031b-scratch/` (253.85 MB): left over from the first delta.

I ran the studio sweep twice, 90 s apart, naming both folders: `node scripts/studio-sweep.mjs --project "Books Arranger" --path "<folder>" --apply`. Both times it kept both: `in use or locked (rename refused: EBUSY)`. No running Python process names either folder in its command line. Neither folder holds anything to keep. Both need the same sweep line again once the lock clears.

---

## Rubric

Severity tags `[Critical]` / `[Major]` / `[Minor]` are defined in `Team/Docs/ProcessRules.md` § Severity definitions. New findings continue the earlier numbering (M6 onward, m13 onward).

### 1. Security

- Status: Pass. No new shell-out, route or `innerHTML`, and nothing in `desktop/` changed. The table name in `rewriting()`'s SQL comes from a fixed tuple.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **[Major] M6: his Choose folder… waits for the write's follow-up, not for the write. The follow-up waits for an idle, unpaused app. Every action queued behind his move waits with it.**
    - Where: `merge_service.py:6638`. `rewriting()` is true while the ledger is `'done'` with `move_approved` and no `follow_up`, and while it is in `ACTIVE`.
    - The pass retries an unrecorded follow-up, or an interrupted write, only after `_idle()` (`series_backfill.py:568`, `:576-578`, `name_write.py:407-411`). `_idle()` raises Later under a Pause, whether his own or one saved before this launch (`:856`). It also raises Later while any book converts or cleans up, or a scan runs. The pass comes back every 10 minutes.
    - Two shapes leave the ledger like that:
      - A Quit in the last seconds of a write: the follow-up answers "closing" and records only `follow_up_wait`.
      - A crash mid-write: an `ACTIVE` row.
    - Probe P4a (method): a write of names with a folder change (`ORDERED` author). The pass ran with `merge.draining = True`. The next launch then has a saved Pause (`merge.filing_paused = lambda: True`). His press then came through `choose_folder`, the queue's blocker and `merge.run_move`. Output:
      - After Quit: `write done | follow_up None | follow_up_wait Books Arranger is closing. Nothing was moved.`
      - Under the saved Pause, 3 passes: `(rewriting, blocker, run_move) = [(True, 'book', 'WaitsForWrite')] x3`.
      - No Pause, another book converting: `(True, 'book')`.
      - Idle: `follow_up none | rewriting False | run_move ('moved', None)`.
    - Probe P4b: a series write left `'renamed'` (as after a crash), saved Pause. Output: `[('renamed', True, 'book')] x3`.
    - Probe P8 (method): the real `ActionQueue` with `test_action_queue.Server`. His move (`rewriting` true) is pressed first, then a Retry of another book. Output: `while his move waits (1 s): ran [] | waiting [('move', {'kind': 'book'}), ('retry', {'kind': 'book'})]`. Both ran once the write ended.
      - The queue looks only at its head (`action_queue.py:665-681`) and gives every waiting item the head's blocker.
      - The page shows both as "It runs when this book's processing finishes." For the Retry, that names the wrong book. Under a saved Pause, nothing finishes until Start, and nothing on the page says so.
    - Fix direction (Ender's call):
      - Once a write is `'done'`, stop holding the move on the idle gate. For example, `run_move` could do the R30 re-point itself, under the write lock, when the follow-up is still unrecorded.
      - Or resume a begun write without the Pause or conversion gate (ruling 27: a begun file change finishes).
      - Separately: a move that waits for its own book should not hold other books' actions.
  - **[Minor] m14: R34's catch-all treats errors that clear on their own as lasting. His queued move is then cancelled by the rules' follow-up, which is R30's original defect.**
    - Where: `merge_service.py:6572-6573`. Every ValueError that `_passing()` does not name becomes `None`. `_passing()` was written for `sorting_follow_up`'s own refusal texts.
    - With `None`, the follow-up queues the rules' move, and `book_move.plan` cancels any queued move of the book (`book_move.py:378-385`). That includes his. Before R34, the same errors were "later", and the pass asked again.
    - Probe P7 (method): a write of names with a folder change, left `'renamed'`, and his move queued from the old file. `merge._publication_location` was wrapped so that its first call does one of the following:
      - Raises `ValueError('Publication generation changed during protection')`, the error `publication_binding.py:48` raises when a relocation commits during the read. Output: `follow_up move_queued | moves [(his, 'cancelled', 'user', 'his'), ('queued', 'rules', None)]`.
      - Plans his second press to `Mine2` (he presses again between the follow-up's read and its write lock). `rebase` then raises "Move state changed". Output: `moves [(his, 'cancelled'), (his2, 'cancelled', 'user', 'his2'), ('queued', 'rules', None)]`. His newer choice is cancelled too.
    - Both windows are a few milliseconds wide, so this is Minor.
    - Fix direction: name the refusals that last (`Refused` cause `not_writable`, "newer version", "no completed publication") and let every other ValueError stay "later". Or never let the rules' follow-up cancel a queued move that carries his override.
  - Verified sound:
    - R33's step-aside cannot let both sides go ahead (attack 4).
    - R30 re-points the waiting move on both writes (P1).
    - The R34 lasting path fails his move with `cause='not_writable'` and the `plan` sentence, under `BEGIN IMMEDIATE`, after the `_move_running` check. When the queue later reaches the move, `Mover.run` returns the failed row unchanged (`book_move.py:522-523`).
    - `_passing()` was extracted unchanged for `sorting_follow_up`.
  - Still open: m3 and m4 from the full review. m10 (a Quit between a write and its follow-up drops his choice) is unchanged: a queued move is still cancelled at start (`book_move.py:891-892`). Its second case now has a different outcome, see m13.

### 3. Crash / Stability Safety

- Status: Pass. No lock-order deadlock: `rewriting()` and `_give_way` take no Python lock, and `run_move` clears its registration in `finally` (`merge_service.py:6664`). An unreadable catalog makes the move wait (`:6655`, `action_queue.py:285`), never run. `WaitsForWrite` reaches the queue as `None`, and the action goes back to the front (`web_server.py:682-683`, `action_queue.py:696-702`). m1 and m2 are still open.

### 4. Performance

- Status: Pass. While his move waits, the blocker opens one catalog connection per 0.5 s poll. `summary()` runs `_look_up_jobs()` once per recount, and only while a hold is due. The result is cached.

### 5. State & Data Safety

- Status: Concerns
- Findings:
  - **[Minor] m13: during startup move recovery, a resumed write reads his waiting move as begun. It deletes its own rewritten copy, and his move then takes the original, un-rewritten file.**
    - Where: `merge_service.py:6671`. `_move_running()` is true for every move while `_move_recovery` is alive. The catalog step's `begun()` therefore reads a queued move that waits (`rewriting()`) as begun, and `_withdraw` runs (`series_backfill.py:1159`, `:1176`).
    - Probe P6 (method): a series write left `'renamed'`, as after a crash. His press after the restart waits (`(True, 'WaitsForWrite')`). A live thread stands in as `merge._move_recovery` while the pass resumes the write. Output:
      - Recovery alive: `write: held 'The audiobook was moved meanwhile; the catalog is unchanged; the rewritten copy was removed' | run_move -> ('moved', None) | Mine holds the original bytes: True`.
      - Control (no recovery): `write: done | Mine holds the rewritten bytes: True`.
    - No audio is lost: the original is the catalog's own receipt and is never disposed in `'renamed'`. The reason text says "moved meanwhile", but nothing had moved. The write is listed again as could not (`approved_failed`).
    - This is m10's second case. R33 changed its outcome from a stray copy kept to the rewrite thrown away.
    - Fix direction: the writer's `begun()` should not take recovery's "everything runs" shortcut for a move created after recovery took its list. Or the catalog step should treat a queued move that `rewriting()` holds as not begun.
  - Verified sound (attack 3, the backstop):
    - `_withdraw` deletes only through `_protected(new, …, delete=True)`, which checks identity, size, full SHA-256 and one link (`series_backfill.py:1185`, `:1106`).
    - It runs only when the catalog step refused with `MOVED_MEANWHILE`. The receipt still names the old file there, because the checks at `:1212-1216` run before the move check (`:1241`) and the state change shares that transaction.
    - The old file is never disposed in `'renamed'`, and a move only deletes its source after a verified target. In every shape probed, the original bytes stayed (P2b, P5, P6).
    - If the deletion cannot be confirmed, the write is held with "copies kept" and both stay (`:1191-1193`).
    - P2b, the backstop itself: `move: complete | write: held '…the rewritten copy was removed' | files under Sorted: ['Mine\<old name>.m4b'] | rewritten copy exists: False | catalog: Mine\<old name>.m4b`.
  - Still open: m10 (see section 2).

### 6. Input Handling

- Status: Pass. There is no new user input. `move_id` reaches `rewriting()` only as a bound SQL parameter.

### 7. Maintainability (no Critical findings on its own)

- Status: Pass. m7 and m8 are still open. Observation: `_resume_protected` picks the backstop path by comparing exception text (`str(error) != MOVED_MEANWHILE`, `series_backfill.py:1154`). A dedicated `Held` subclass would survive a rewording.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **[Minor] m15** `CHANGELOG.md:34` overstates three things:
    - "waits until the rewrite ends": it waits until the follow-up is recorded, which under a saved Pause means until Start (M6).
    - "then moves the rewritten file": not across a Quit (m10), not in the recovery window (m13), and not in P5's interleaving.
    - "never leaves a second copy": when the rewritten copy cannot be removed, both are kept by design (`series_backfill.py:1191-1193`).
  - m12 is fixed: `:28` and `:31` now match the code.
  - m5 is still partly open. A held write of names still uses series wording. `_withdraw`'s fallback reason also starts "The catalog could not record the series" for a write of names (`:1192`). The old "0.31.0 = steps 1 and 4" line in the Scope doc is now marked superseded by R20's row.

### 9. Build & Release Hygiene

- Status: Pass. No change to `package.json`, the lockfile, `scripts/` or `desktop/`. No new test module, so the gate inventory is unchanged. The entry check on `7023cc9` passed. No commit carries Claude attribution (`git log --format=%B` grep: 0 hits).

---

## Patterns

The last review asked for every phase of a write to be probed with the competing worker actually running. R33 did that, and M4 and M5 close in every phase. The new defects come from the same habit one level up. R33 ties his move to a ledger state that is ended by a different worker, the follow-up, on that worker's own gate (idle, unpaused, every 10 minutes). The queue then makes that wait everyone's. When one worker waits for another, check what lets the second one run, not only what it does.

---

## Verdict

- Total Critical: 0
- Total Major: 1 new (M6)
- Total Minor: 3 new (m13, m14, m15); m1–m8 from the full review and m10 from the first delta carried (m5 partly fixed)

M4, M5, m9, m11 and m12 from the first delta are fixed. No open finding is Critical, and the safety floor is intact:
- Every delete is of the write's own proven file, inside its held folder.
- No secrets are involved, and no history is rewritten.

M6 can hold his queued actions until Start, but nothing is lost. It is logged for Ender. Whether it goes into this release or the next is Sergei's call, through Jane.

**Verdict:** RELEASE CLEAR
