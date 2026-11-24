# Code Review — Books Arranger v0.31.0 (delta 3)

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-24
Tool: Books Arranger
Release: v0.31.0
Commit range: 7023cc9e77fb8cb528991e3ec287891787c2a7df..399caea9da73ce0c6ee516105f80bc64ae2f9a56 (branch ender/0.31.0)
Files changed: 13 files, +660 / -49 in 4 commits (no merges); product code outside tests and *.md: 6 files, +182 / -36
Stand-down dimensions: none
```

Counts come from `git diff --numstat` on the two endpoints. Earlier reports certified these ranges:
- The full review: `50c4d4b..a8b6804`.
- Delta 1: `a8b6804..8cc8c5a`.
- Delta 2: `8cc8c5a..7023cc9`.

This report starts at `7023cc9`, so the four reports together cover `50c4d4b..399caea` with no gap. This report certifies the range through `399caea`.

---

## Summary

The range has four commits:
- `0a03dd5` (R35: M6, m13, m14):
  - `rewriting()` now holds a move only while the write's file work is in progress (`ACTIVE`).
  - `run_move` records a write's pending follow-up itself (`_follow_up_now`) before it registers the move.
  - Both writers resume a begun write with only the scan gate (`_may_finish`), so Pause and conversions no longer hold it.
  - The action queue now runs the first action nothing holds. A move that waits for its own book keeps its place, and actions on that same book stay behind it.
  - m13: writers ask `_move_registered`, not `_move_running`.
  - m14: `_lasting()` lists the refusals that never clear.
- `91ee90f`: CHANGELOG (m15).
- `61c61b6` (B1 and M1):
  - B1: `placed_by_write` in `conversion_progress.completed_book`. The writers' catalog step now keeps the rewritten file as the book's last verification (`_verified`).
  - M1: `public_research.waf_challenge`, plus Goodreads added to `HUMAN_CHECK_HOSTS`.
- `399caea`: CHANGELOG.

I read every product line in the range and re-ran P4a, P4b and P8. I also added probes for the brief's five attacks: Q1 (the queue), A2 (Pause and the race), B1 (the converted check) and M1.

**Answers to the brief's attacks:**

1. **The queue cannot reorder actions on one book, starve an action, or run two actions on one book at once.**
   - The worker keeps one queue order. It skips a move that waits for its own book (`'book'`) and also skips every later action that touches that book through `parts_of` (`action_queue.py:679-689`). Then it runs the first action left.
   - Each poll starts again from the front, so a freed move runs before anything queued after it.
   - One action per book still holds: `enqueue`'s check counts both the waiting and the running actions.
   - Q1a: two moves wait and 20 other actions are queued. The 20 ran in their order, and each move ran as soon as it was freed (`ran 20 in order True`, then `['moveC', 'moveA']`).
   - Q1b: a join that takes book A in stayed behind A's move (`('joinXA', 'book')`). A second press for A was refused ("This book already has a queued action"). The rules' move of A was answered with his item, so no second item exists.
   - Note, not a finding: a historical Clean up or Restore is queued under the job id, not the candidate id. It is therefore not held behind the move of the same book (Q1b: `cleanupJobA` ran). It never was: the one-action-per-row check uses the same key, and a cleanup's blocker never looked at moves. Each side checks the other's file by hash, so there is no harm.
2. **The saved-Pause rulings are bent in two places, and neither loses audio (m16, m17).**
   - Every begun write now finishes under a saved Pause, even when no move of his waits for it (A2a). R35's text covers only the case where his move waits. The CHANGELOG states the wider rule.
   - The resumed write then runs its follow-up under the Pause as well. For a write he approved himself (the 0.30 `/api/sorting-moves/apply` route), that follow-up queues a `'user'` move. The queue does not park that move, so it runs under the saved Pause (A2b). The rules' own move is parked (the control).
   - A conversion of the same book: not probed end to end. Reading the code, each file step of the resume is guarded:
     - The rename uses `publish_no_replace`.
     - The catalog step compares the receipt and swaps it only if unchanged (`series_backfill.py:1263-1266`, `WHERE output=?`).
     - The delete goes through a hash-checked handle with one link.
     - So a conversion of the same book running beside it can make the write hold, but cannot remove the only copy.
     - For that to happen, the book must be approved again between the crash and the writer's first pass (2 minutes).
   - New and Minor (m17): the writer thread and the queue thread can now run the same follow-up at the same moment. Each reads the ledger, changes it and writes it back with no lock, so one can erase what the other wrote. A2c shows it.
3. **No. B1's relaxed check never counts a book as converted when its file is missing, changed, or somewhere else.**
   - `placed_by_write` only replaces the "receipt is the planned path" comparison. The book counts as converted only if all of these hold:
     - The live file at the effective place (receipt plus committed moves) has exactly the identity of its last verification (`merge_service.py:642-643`).
     - The validation passed.
     - The receipt is exactly one of the recorded writes (`new_path` and `new_sha256`).
     - That write planned the place the review plans now.
   - B1a, file renamed away: `True -> False`.
   - B1b, one byte changed in place: `True -> False`.
   - B1c, lane H (not moved), then the file moved by hand elsewhere: `True -> False`.
   - B1d, the in-memory verification dropped: `True -> False`.
   - A held or withdrawn write is not in the set (`state IN ('cataloged','done')`), so it errs on the safe side.
4. **The match is narrow: a 202 plus exactly that header. Its effect is not narrow (M7, M8).**
   - M1a, client level:
     - Only `202` with `x-amzn-waf-action: challenge` (case and spaces ignored) becomes a human check.
     - A 202 with no header, a 202 with `captcha` and a 405 with `captcha` all stay "unavailable" (300 s).
     - The match is not limited to Goodreads: a FantLab or Wikidata 202 with that header is also a human check, with a 1-hour pause and still a try. That is as the commit says.
   - The fix lives in the shared client. It therefore changes the look-up before review too, where the challenge is still a try, now spaced an hour apart (M7).
   - The 1-hour host pause it stores makes every Goodreads series look-up in that hour count as "nothing found" for good, without a request (M8).
5. **P4a, P4b and P8 now resolve. M6, m13, m14 and m15 are fixed.**
   - P4a, saved Pause, 3 passes: `(rewriting, blocker) = [(False, None)] x3`.
     - Then `run_move -> ('moved', None)`, follow-up `none`, and Mine holds the rewritten bytes.
     - With a conversion running instead: `(False, None, ('moved', None))`.
     - Delta 2 read `[(True, 'book', 'WaitsForWrite')] x3`.
   - P4b, saved Pause: `[('done', False, None)] x3`. Then `run_move -> ('moved', None)`, and Mine holds the rewritten bytes. Delta 2 read `[('renamed', True, 'book')] x3`.
   - P8: `while his move waits (1 s): ran ['retry'] | waiting [('move', {'kind': 'book'})]`. Then `ran ['retry', 'move']`, and the Retry's answer has no blocker. Delta 2 read `ran []` with both waiting.
   - m13 and m14: Ender's AfterTheWriteTests (P6 and P7 rebuilt) pass in my run.
   - m15: `CHANGELOG.md:34` no longer promises "never a second copy" and names the same-instant step-aside.

**Construction verdict.** No audio can be lost in this range:
- The relaxed converted check reads only. It is still tied to the live file's verified identity.
- The resume under Pause or beside a conversion keeps every hash and no-replace guard.
- The queue change cannot run two actions on one book.

The two Majors concern look-up outcomes, not files:
- One makes a new book wait up to about 2 hours before it converts.
- The other permanently records "nothing found" from Goodreads for books that were never asked.

Both are logged for Ender. Whether they go into this release is Sergei's call.

### Tests run (targeted, lean verification)

Runtime: the gate's pinned QA runtime, `WIP/Books Arranger/build-cache/qa-runtime`. Hashes, all matching `scripts/qa-runtime.json`:
- `python.exe`: `434b361f…`
- `ffmpeg.exe`: `a3bf949b…`
- `ffprobe.exe`: `fe818a56…`

How every run was set up:
- It used a `git archive 399caea` copy under `I:/AI Projects/Worktrees/Books Arranger/senua-031d-scratch/copy`.
- `TEMP`, `TMP` and `TMPDIR` all pointed into the copy's `scratch/tmp`.
- It went through the gate's `support_dispositions(runroot/'scratch', [runroot/'scratch'])` wrapper, with the gate's fixture-root map (unchanged at `399caea`).
- Counts are the runner's `testsRun`.

| Run | Modules | Result |
| --- | --- | --- |
| 1 | `test_name_write_031` (53), `test_action_queue` (41), `test_destination_override` (34), `test_automatic_media:RewrittenBookTests` (7), `test_series_lookup_ends_031` (20), `test_automatic_processing.AutoTests.test_m1_…` (1), `test_rule_filing_031` (51), `test_series_moves_031` (16), `test_series_backfill` (33) | 256 tests, OK (358 s) |
| Probes | Senua's `senua_probe_031d.py`: P4a (2), P4b, P8, Q1a, Q1b, A2a, A2b (2), A2c, B1a-d, M1a-c. The loader also picked up 11 cases through the imports. | 33 cases, OK (129 s); outputs quoted in this report |

Entry checks:
- `q031h` (`399caea`): receipt `@ 399caea… (dirty: N)`, `check pass`, exit 0.
- `q031f` (`91ee90f`): failed on one case outside this range. `test_storage_relocation_integration…test_real_approved_conversion_runs_after_copy_and_restart_keeps_verified_output` hit a 15-second engine-start timeout.

The full suite was not run here.

The probe file and the runner sat in the scratch folder's `probes/`, beside the copy. Each finding gives the probe's method, so Ender can rebuild it from the `MoveWindow`, `PressDuringWriteTests` and `RewrittenBookTests` fixtures, `test_action_queue.Server` and `PublicClient(fetch=…)`.

**Disposal.** See the end of this report.

---

## Rubric

Severity tags `[Critical]` / `[Major]` / `[Minor]` are defined in `Team/Docs/ProcessRules.md` § Severity definitions. New findings continue the earlier numbering (M7 onward, m16 onward).

### 1. Security

- Status: Pass. There is no new shell-out, route or `innerHTML`, and nothing in `desktop/` changed. `waf_challenge` reads one response header and never acts on its value beyond comparing it. The table names in the new SQL come from fixed tuples.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **[Major] M7: Goodreads' human check still holds a new book before review, now about 2 hours instead of about 20 minutes.**
    - Where:
      - `public_research.py:563-564`: the shared client's change, a 1-hour `CHALLENGE_PAUSE` with kind `source_pause`.
      - `gap_fill.py:42` and `:92`: `source_pause` is not in `NO_TRY_KINDS`, so it is a try, next due at `max(retry, now + 600)`.
      - `public_research.py:1025`: the look-up before review uses that rule.
    - M1 was meant for the look-up of finished books. The challenge is recognised in `PublicClient`, which every Goodreads consumer shares. That includes the look-up before review (`LOOKUP_SOURCES` has `goodreads`, `:149`, which serves the `series` gap).
    - That look-up does not apply R32's "nothing found at once". The challenge stays a try, and its next try is now an hour away instead of 10 minutes.
    - When no other source names a series (any standalone, or a series FantLab and Wikidata do not know), the gap waits for Goodreads. With Goodreads challenging, the three tries are about an hour apart: the book converts about 2 hours after its first try, against about 20 minutes on `7023cc9`.
    - Every other book that asks Goodreads inside that hour meets the stored host pause and spends a try with no request (Futaba's r2 Minor 3 shape).
    - Meanwhile the page is not All done. R32 as extended on 2026-11-24 says Goodreads' challenge "does not hold back All done". `CHANGELOG.md:39` ("no longer holds back All done for 6 hours") describes only the finished-book look-up.
    - Probe M1c: the same closure through `gap_fill.remember` with the look-up before review's own arguments:
      - `challenge (0.31.0 M1) -> tries 1 | next try in 3600 s`
      - `unavailable (7023cc9) -> tries 1 | next try in 600 s`
    - Fix direction (Ender's call; the rule is Sergei's): either count Goodreads' challenge as "nothing found" in the look-up before review too, as `series_backfill.py:834` does, or keep the client's pause for Goodreads' challenge at the old 300 s.
  - **[Major] M8: one Goodreads challenge records "nothing found" from Goodreads for every book whose series look-up asks within the next hour, permanently, without a request.**
    - Where:
      - `public_research.py:553`: a stored host pause is raised with its stored reason, here `CHALLENGE_REASON`.
      - `series_backfill.py:834-838`: any `CHALLENGE_REASON` from `www.goodreads.com` becomes `{'answer': 'none'}`.
      - `:848`: a source that answered `none` is never asked again for that book. Ender's own test asserts "never asked about this book again".
    - R32 answers DuckDuckGo with "nothing found" because it never answers. Goodreads answers most of the time: Futaba saw 3 of 3 challenged at 23:40 and a 200 for the same URL later.
    - After one challenge, the 1-hour host pause makes each later Goodreads look-up in that hour raise the same reason before any request. Each of those books then settles Goodreads as `none` for good.
    - For a book whose series only Goodreads knows, the result is a book filed with no series, and nothing looks it up again. Sergei ruled on 2026-10-18 that Goodreads is the series source.
    - Probe M1b: the real `PublicClient`, one challenge, then another book's Goodreads read 30 minutes later: `requests sent 1 | wait ('www.goodreads.com', 'Public source presented a human check…', 'source_pause') | the series look-up counts it as nothing found (series_backfill.py:834): True`.
    - DuckDuckGo has had the same amplification since R32, and nothing is lost there.
    - Fix direction: count a human check as "nothing found" only when this book's own request received it. Treat a stored host pause as a wait (no try) or a try, as before. Whether a Goodreads challenge should settle a book at all is Sergei's call, through Jane.
  - **[Minor] m17: the writer thread and the queue thread can run one write's follow-up at the same moment, and the later write-back erases the recorded follow-up.**
    - Where: `merge_service.py:6690` (`_follow_up_now` calls `writer._follow_up` on the queue thread) and `series_backfill.py:431-447` (`_follow_up` reads the entry, then writes `dict(record, follow_up_wait=…)` back from what it read).
    - Since R35 his move is free as soon as the ledger reads `'done'`. The queue's poll can then run `run_move` → `_follow_up_now` while the writer thread is between its `_set('done')` (`series_backfill.py:1195`) and its own `_follow_up` (`:1105`).
    - In this interleaving the follow-up is erased:
      - The writer reads the entry before the queue records `none`.
      - The writer checks his move after `run_move` has registered it.
      - The writer then answers `busy` and writes back its stale record, without `follow_up`.
    - The follow-up then stays unrecorded until the writer's next idle pass. That is up to 10 minutes, and under a Pause until Start. Meanwhile the rules' entry for the book stays in hand (`rule_filing.py:381-383`), taking one of R28's two slots.
    - No file is affected: his move runs re-pointed.
    - Probe A2c (method): the writer's `choice_after_write` was wrapped. On its first call, the queue side ran `_follow_up_now(his)` and then registered his move, before the writer went on. Output:
      - `writer read follow_up None | queue recorded none | ledger after the writer: done follow_up None follow_up_wait This audiobook is being moved now…`
      - His move: `complete`.
      - Under a Pause after a writer pass: `follow_up None`.
      - Control, no Pause, next writer pass: `follow_up none`.
    - Fix direction: run the follow-up under one lock per job, or re-read the entry inside `_follow_up` just before each `_set` and do nothing if `follow_up` is already recorded.
  - Verified sound:
    - The queue (attack 1, Q1a/Q1b, P8).
    - `rewriting()` now ignores a pending follow-up. `run_move` records it first, and waits one poll for a write that ended between its look and its registration (Ender's `test_r35_a_write_that_ends_as_his_move_starts_makes_it_wait_one_poll` passes).
    - `_lasting()` lists only fixed texts and causes, and every other ValueError is `'later'` (m14).
    - `_move_registered` replaces recovery's "every move runs" only for still-queued moves (m13). Recovery cancels the queued moves it found and never runs one (`book_move.py:864-884`).
  - Still open from earlier reports: m3 and m4 (full review) and m10 (delta 1: a Quit cancels his queued move, by design of `drop()`).

### 3. Crash / Stability Safety

- Status: Pass.
  - `_follow_up_now` resets its re-entry flag in `finally`. `run_move` catches `sqlite3.Error` around it, and `_follow_up` already turns every other error into `'later'`.
  - The queue loop holds `self.lock` only for list changes, never across `item_blocker` or a run.
  - `waf_challenge` swallows any header-reading error.
  - m1 and m2 are still open.

### 4. Performance

- Status: Pass.
  - The queue now asks `item_blocker` once for each waiting move ahead of the head, each poll. That is one catalog read per waiting move every 0.5 s, and only while moves wait.
  - `progress_books` adds one scan of the two write ledgers, inside its existing snapshot.

### 5. State & Data Safety

- Status: Concerns
- Findings:
  - **[Minor] m16: under a saved Pause, a begun write now finishes even when nothing of his waits for it. For a write he approved himself, its follow-up queues a move the queue does not park, so the move runs under the Pause.**
    - Where:
      - `series_backfill.py:571` and `name_write.py:401`: `_may_finish`, which applies only the scan gate.
      - `series_backfill.py:1105`: `resume()` then calls `_follow_up` with no gate.
      - `merge_service.py:6505`: the follow-up's move is `origin='rules'` only when the rules approved the write, else the default `'user'`.
      - `action_queue.py:61-64`: `held_by_pause` parks only `'rules'` moves and restored presses.
    - F13 (`merge_service.py:6620`) says a Pause holds the series writes and the app's own moves. R35 made one exception: a Choose folder… waiting on a rewrite must not wait for Start. The code goes further:
      - **A2a (rules approval, no press):** `state done | files before [<renamed>, <original>] | after [<renamed>] | follow_up move_queued | moves [(…, 'queued', 'rules', …)]`. The rename, catalog step and removal of the former file all ran under the saved Pause. The rules' move is queued and parked. The CHANGELOG says so ("even under Pause"), so this half is a ruling question for Sergei, not a defect.
      - **A2b (his own approval, the 0.30 apply route, `by=None`):** `write done | approved_by None | follow_up move_queued | moves [(…, 'queued', 'user', None, None)] | queue parks it (held_by_pause): False`. That move runs under his saved Pause.
      - **Control (rules approval):** `'rules'`, `held_by_pause: True`.
    - Before R35 the resume waited behind `_idle()`, so neither happened.
    - Narrow: it needs a write approved through `/api/sorting-moves/apply` (no page control in 0.31.0), cut short by a Quit or a crash, then a launch under a saved Pause. The move is the verified move he approved.
    - Fix direction: after a resumed write, leave the follow-up to the pass's own follow-up loop, which already waits behind `_idle()` (`series_backfill.py:577-582`, `name_write.py:406-411`). `run_move` still records it for his waiting move.
  - Verified sound:
    - B1 (attack 3; B1a to B1d above). `_verified` stores the `stat` taken while the write held the proven file, inside the committed catalog step (`series_backfill.py:1268`, `name_write.py:584`).
    - A resume beside a conversion or a cleanup keeps every guard (attack 2).

### 6. Input Handling

- Status: Pass. The only new input is a response header from an allowed host. It is compared, never stored or echoed.

### 7. Maintainability (no Critical findings on its own)

- Status: Pass. Observations:
  - `_follow_up_now`'s re-entry guard lives in the engine's shared `__dict__`, not per thread. It is correct with one queue worker, but a second caller of `run_move` (any path where `move_requester` is unset) would skip a follow-up.
  - The action queue's module docstring still lists `'book'` as "Delete only". m7 and m8 are still open.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings:
  - `CHANGELOG.md:39`: "no longer holds back All done for 6 hours" is true only of the finished-book look-up. The look-up before review now waits longer (M7). This is covered by M7, not counted again.
  - `CHANGELOG.md:35` is accurate, including "even under Pause", and so documents A2a.
  - The Scope doc's R32 line now includes Goodreads (Jane, 2026-11-24). Sergei's own words covered "any source that answers only with a human check", and Goodreads answers intermittently (M8).
  - m15 is fixed. m5 is still partly open, as in delta 2.

### 9. Build & Release Hygiene

- Status: Pass.
  - No change to `package.json`, the lockfile, `scripts/` or `desktop/`. No new test module, so the gate inventory is unchanged.
  - The entry check on `399caea` passed (`q031h`).
  - No commit carries Claude attribution (`git log --format=%B 7023cc9..399caea` grep: 0 hits).

---

## Patterns

R35's fixes are right where they act, but two land in shared places and act further than their commits say:
- M1's recognition sits in the client every look-up uses, so a rule meant for one lane changed another lane's timing (M7). Its stored pause turned a per-request rule into a per-host one (M8).
- R35 removed the Pause gate from the resume, and that also removed it from the follow-up the resume calls (m16).
- Freeing his move at `'done'` put a second thread into the follow-up (m17).

When a fix goes into a shared function, list its callers and check each one.

---

## Verdict

- Total Critical: 0
- Total Major: 2 new (M7, M8)
- Total Minor: 2 new (m16, m17). Carried: m1–m8 from the full review (m5 partly fixed) and m10 from delta 1.

M6, m13, m14 and m15 from delta 2 are fixed: P4a, P4b and P8 resolve, and Ender's m13 and m14 tests pass. B1's relaxed check is sound against a missing, changed or displaced file.

No open finding is Critical, and the safety floor is intact:
- Every delete in the range goes through the write's hash-checked, single-link handle.
- No secrets are involved, and no history is rewritten.

M7 and M8 change look-up outcomes, not files. Whether they are fixed before this release is Sergei's call, through Jane.

**Verdict:** RELEASE CLEAR

---

## Disposal

**Not done: all three of my scratch folders are still on disk, locked.** Nothing in them is evidence anyone needs, because this report carries the outputs.

- Processes: none of mine is running. The two test runs ended with exit 0, and no Python, ffmpeg or Edge process names `senua-031*`. The Python and Edge processes running at the end belong to Futaba's `futaba-031d` run, so I left them alone.
- Sweep: I ran it from the studio root: `node scripts/studio-sweep.mjs --project "Books Arranger" --path "<folder>" --apply`, naming all three folders.
  - The dry run planned exactly these three, and nothing else.
  - The apply kept all three: `in use or locked (rename refused: EBUSY)`.

| Folder | Size | State |
| --- | --- | --- |
| `I:/AI Projects/Worktrees/Books Arranger/senua-031d-scratch/` (this review: the `git archive 399caea` copy, probes, runner, logs) | 127.72 MB | locked |
| `I:/AI Projects/Worktrees/Books Arranger/senua-031c-scratch/` (delta 2) | 124.17 MB | still locked |
| `I:/AI Projects/Worktrees/Books Arranger/senua-031b-scratch/` (delta 1) | 253.85 MB | still locked |

- One alternative, tried and noted:
  - A plain rename shows the lock is on each top folder itself. Every child (`copy`, `probes`, `base`) renames freely, but the top folder does not. So the blocker is a handle held on the folder itself, not an open file inside it.
  - No process names the folders in its command line. Futaba found the same with `futaba-031c` (Restart Manager reported nothing).
  - The sweep refuses child paths under Worktrees (`--path must name one <Tool>\<purpose> entry`), so the contents could not go separately.
  - I did not delete anything by hand.
- Next step: run the same sweep line again, naming the three folders, once the handle is released. A likely holder is the long-running session process that wrote files into them; if so, the handle goes when that session ends.
