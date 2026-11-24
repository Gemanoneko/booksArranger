# Code Review — Books Arranger v0.31.0 (delta 4)

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-24
Tool: Books Arranger
Release: v0.31.0
Commit range: 399caea9da73ce0c6ee516105f80bc64ae2f9a56..d96979d8acae368e6fc76245cb502dfa76a7772a (branch ender/0.31.0)
Files changed: 5 files, +3 / -51 in 1 commit (no merges); product code outside tests and *.md: 2 files, +2 / -15
Stand-down dimensions: none
```

Counts come from `git diff --numstat 399caea d96979d`. Earlier reports certified these ranges:
- The full review: `50c4d4b..a8b6804`.
- Delta 1: `a8b6804..8cc8c5a`.
- Delta 2: `8cc8c5a..7023cc9`.
- Delta 3: `7023cc9..399caea`.

This report starts at `399caea`, so the five reports together cover `50c4d4b..d96979d` with no gap. This report certifies the range through `d96979d`.

---

## Summary

The range has one commit, `d96979d`. It reverts M1 from `61c61b6` and keeps B1. Jane withdrew the Goodreads extension of R32, and the Scope doc's R32 row now says Goodreads is not included (`Docs/BooksArranger_0.31.0_Scope.md:64`).

I read every line of the diff and compared blob hashes across `91ee90f`, `61c61b6`, `399caea` and `d96979d`. I rebuilt my delta-3 probes for M7, M8 and B1, and added probes for R32 through the real client.

**Answers to the brief's attacks:**

1. **The revert is complete. No Goodreads-specific 1-hour pause and no Goodreads "nothing found" on a challenge are left.**
   - Byte-identical to `91ee90f` (same blob hash): `public_research.py` (`11e9686`), `tests/test_automatic_processing.py` (`ac8ce15`) and `tests/test_series_lookup_ends_031.py` (`a30a1c9`).
   - `series_backfill.py` differs from `91ee90f` only by B1's `_verified` hunk. `CHANGELOG.md` differs from `91ee90f` only by B1's line.
   - `git grep` over every `.py`, `.js`, `.mjs`, `.ts`, `.html`, `.json` and `.css` file at `d96979d` for `waf_challenge`, `HUMAN_CHECK_HOSTS`, `amzn` and `waf-action`: 0 hits.
   - `CHALLENGE_REASON` is checked in one product place only: `series_backfill.py:831`, which needs `wait.source == 'html.duckduckgo.com'`.
   - Probe R1a: `public_research.waf_challenge present: False | series_backfill.HUMAN_CHECK_HOSTS present: False | HUMAN_CHECK_HOST = html.duckduckgo.com | HOST_SOURCES[HUMAN_CHECK_HOST] = ('publisher', 'litres')`.
   - Probe R1b, with the real `PublicClient`:
     - These all give `Public source unavailable…`, `source_unavailable`, 300 s: Goodreads 202 with `challenge`, 202 with `" CHALLENGE "`, 202 with no header, 405 with the header, and FantLab or Wikidata 202 with the header.
   - Goodreads can still get a 1-hour pause in three ways: a 403 or 429 (`source_pause`, 3600 s; R1b), a `Retry-After` header, or a body that contains a challenge marker. None of these is in this range, all of them were already in `7023cc9`, and none of them gives "nothing found".
   - No tag contains `61c61b6` (`git tag --contains`: none), so M1 never shipped. No data from a released version holds an M1 "nothing found" that would need undoing.
2. **B1 is untouched.**
   - These files are byte-identical between `399caea` and `d96979d`: `conversion_progress.py` (`placed_by_write`, `completed_book`), `merge_service.py` (the `rewrites` read in `progress_books`), `name_write.py` (`self._verified`) and `tests/test_automatic_media.py`.
   - In `series_backfill.py` the commit changes only the M1 lines, at `:117-122` and `:831-838`. `_verified` and its call in the catalog step (`:1289`, `:1293-1300`) are unchanged.
   - `RewrittenBookTests`: 7 of 7 pass.
   - Probes B1a to B1d, rerun unchanged from delta 3, still read `True -> False` in every case:
     - B1a: the file renamed away.
     - B1b: one byte changed in place.
     - B1c: lane H, then the file moved by hand elsewhere.
     - B1d: the in-memory verification dropped.
3. **M7 and M8 probes come back clean.**
   - M7: the real client's wait for a Goodreads challenge goes through `gap_fill.remember` with the look-up before review's own arguments.
     - Output: `kind source_unavailable | tries 1 | next try in 600 s`. Delta 3 read 3600 s at `399caea`, and `7023cc9` read 600 s.
     - So three tries take about 20 minutes again, not about 2 hours.
   - M8: the real client under the real `SeriesBackfill.lookup`, with two books in one pass. Goodreads challenges the first request.
     - Output: `goodreads requests sent 1 | [('0', 'deferred', None, 1, 21600, 'Public source unavailable…'), ('1', 'deferred', None, 1, 21600, 'Public source unavailable…')]`. The finished state is `background_only`.
     - 30 minutes later, another book's read sends a request: `requests sent 2`, and the wait is `source_unavailable` for 300 s.
     - Neither book records Goodreads as `none`, so each keeps its remaining tries.
     - Note, not a finding: book 1 still spends a try without a request while the 300-second host back-off lasts. That has been the case since before 0.31.0 (Futaba's r2 Minor 3). The window is 5 minutes, as on `7023cc9`.
4. **R32 still works for DuckDuckGo.**
   - The R32 check is now `wait.source == HUMAN_CHECK_HOST and name in HOST_SOURCES[HUMAN_CHECK_HOST]`. For DuckDuckGo it gives the same result as delta 3's `in HUMAN_CHECK_HOSTS` form, and its text matches `91ee90f`.
   - Probe R32, the real client under the real look-up: the publisher source asks, DuckDuckGo answers 202, and Litres then meets the stored 1-hour challenge pause.
     - Output: `duckduckgo requests 1 | state none | publisher none | litres none no next_attempt | finished all_done`.
     - Three later passes, 6 hours apart: `publisher asked 1 | litres asked 1 | requests 1`.
   - Control: DuckDuckGo answers 503. Output: `state deferred | publisher tries 1 | finished background_only`.
   - At the client, DuckDuckGo's 202 and a 200 with `anomaly.js` in the body both still give `Public source presented a human check…`, `source_pause`, 3600 s (R1b).
   - `HumanCheckTests` (3 of 3) pass. So do `test_local_identity…test_duckduckgo_human_check_is_a_long_pause_not_a_retry` and the DuckDuckGo 202 case in `test_gap_fill…test_reserved_dispatch_waits_for_a_pause_commit_and_rechecks_the_host_family`.

**Construction verdict.** The commit is a clean, scoped revert. M7 and M8 are closed, and B1 and R32 are intact. It adds no new finding.

### Tests run (targeted, lean verification)

Runtime: the gate's pinned QA runtime, `WIP/Books Arranger/build-cache/qa-runtime`. Hashes, all matching `scripts/qa-runtime.json`:
- `python.exe`: `434b361f…`
- `ffmpeg.exe`: `a3bf949b…`
- `ffprobe.exe`: `fe818a56…`

How every run was set up:
- It used a `git archive d96979d` copy under `I:/AI Projects/Worktrees/Books Arranger/senua-031e-scratch/copy`.
- `TEMP`, `TMP` and `TMPDIR` all pointed into the copy's `scratch/tmp`.
- It went through the gate's `support_dispositions(runroot/'scratch', [runroot/'scratch'])` wrapper, with the gate's fixture-root map. `scripts/`, `desktop/`, `package.json` and the lockfile are unchanged in the range (`git diff --quiet`).
- Counts are the runner's `testsRun`. The per-class counts come from the run log.

| Run | Modules | Result |
| --- | --- | --- |
| 1 | `test_series_lookup_ends_031` (18: delta 3's 20, less the two M1 tests), `test_series_backfill` (33), `test_automatic_media:RewrittenBookTests` (7), `test_local_identity.SchedulingTests.test_duckduckgo_human_check_is_a_long_pause_not_a_retry`, `test_gap_fill.ClientLockTests.test_reserved_dispatch_waits_for_a_pause_commit_and_rechecks_the_host_family`, `test_automatic_processing.AutoTests.test_source_http_pause_honors_retry_after_without_exposing_error`, `…test_later_inflight_failure_cannot_shorten_a_shared_source_pause` | 62 tests, OK (167 s) |
| Probes | Senua's `senua_probe_031e.py`: R1a, R1b, M7, M8, R32 and its control, B1a to B1d | 10 cases, OK (63 s); outputs quoted in this report |

Entry check, `q031i` (`d96979d`):
- Receipt: `books-arranger v0.31.0 @ d96979d8… (dirty: N)`, `check pass`.
- Python: 3,199 tests, the sum of the 13 shards' `Ran N tests` lines.
- Node: 279 (`# tests 279`, `# pass 279`).

The full suite was not run here.

---

## Rubric

Severity tags `[Critical]` / `[Major]` / `[Minor]` are defined in `Team/Docs/ProcessRules.md` § Severity definitions.

### 1. Security

- Status: Pass. The commit only removes code: the header reading and one host tuple. Nothing new is shelled out, routed or rendered.

### 2. Correctness & Logic

- Status: Pass.
  - M7 and M8 from delta 3 are closed (attack 3).
  - R32 for DuckDuckGo is unchanged (attack 4).
  - The restored control test, `test_control_a_human_check_from_another_host_is_still_a_try`, uses Goodreads again, as on `91ee90f`. That is the case Jane's withdrawal names.
  - Still open from earlier reports: m3 and m4 (full review), m10 (delta 1) and m17 (delta 3; deferred to the next version, not re-litigated).

### 3. Crash / Stability Safety

- Status: Pass. The commit removes the client's one new `try`/`except` and adds no new path. m1 and m2 are still open.

### 4. Performance

- Status: Pass. Goodreads' challenge is back to the 300-second host back-off. That ends the hour-long stall of the look-up before review (M7).

### 5. State & Data Safety

- Status: Pass. B1's relaxed converted check and `_verified` are untouched (attack 2). No file operation changed. M1 never shipped, so no stored record needs migrating. m16 (delta 3) is still open and deferred to the next version.

### 6. Input Handling

- Status: Pass. The only input M1 read, the `x-amzn-waf-action` response header, is no longer read.

### 7. Maintainability (no Critical findings on its own)

- Status: Pass. The revert restores the three files byte for byte and removes the M1 comments with the code. m7 and m8 are still open.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Pass.
  - The M1 line is gone from `CHANGELOG.md`, which closes delta 3's note on the old line 39.
  - `CHANGELOG.md:33` ("through DuckDuckGo") matches the code.
  - The Scope doc's R32 row matches the code.
  - The commit message's "the old 300 s host back-off" matches `public_research.py:555`.
  - m5 is still partly open, as in delta 2.

### 9. Build & Release Hygiene

- Status: Pass.
  - No change to `package.json`, the lockfile, `scripts/` or `desktop/`.
  - The entry check on `d96979d` passed (`q031i`).
  - The worktree is clean (`git status --short`: 0 lines).
  - The commit carries no Claude attribution (`git log --format=%B 399caea..d96979d` grep: 0 hits).

---

## Verdict

- Total Critical: 0
- Total Major: 0 new; M7 and M8 (delta 3) closed
- Total Minor: 0 new. Carried: m1–m8 from the full review (m5 partly fixed), m10 from delta 1, and m16 and m17 from delta 3, which are deferred to the next version.

The safety floor is intact. The range removes code only, deletes no files, involves no secrets and rewrites no history.

Note for Jane, not a finding: with M1 withdrawn, a Goodreads challenge again holds a finished book between tries. That is Futaba's r2 M1 symptom, now accepted under the ruling. Her report should mark it as accepted, so her GO does not carry it as open.

**Verdict:** RELEASE CLEAR

---

## Disposal

**Not done: all four of my scratch folders are still on disk, locked.** None of them holds evidence anyone needs, because this report carries the outputs.

- Processes: none of mine is running.
  - Both runs ended with exit 0.
  - A process query (`Get-CimInstance Win32_Process`, read-only) found no process whose command line or executable names `senua-031`, apart from the query's own shells. I sent it through `powershell.exe -Command` from Bash, because `wmic` is not installed.
  - No process runs from the QA runtime's `python.exe`.
  - The Python processes still running belong to the installed app, to a packaged build under `ender-031/dist/builds/` (another agent's current QA run) and to unrelated tools. I left them alone.
- Sweep: I ran it from the studio root: `node scripts/studio-sweep.mjs --project "Books Arranger" --path "<folder>" --apply`, naming all four folders.
  - The dry run planned exactly these four, and nothing else.
  - The apply kept all four: `in use or locked (rename refused: EBUSY)`.

| Folder | Size | State |
| --- | --- | --- |
| `I:/AI Projects/Worktrees/Books Arranger/senua-031e-scratch/` (this review: the `git archive d96979d` copy, probes, runner, logs) | 122.57 MB | locked |
| `I:/AI Projects/Worktrees/Books Arranger/senua-031d-scratch/` (delta 3) | 127.72 MB | still locked |
| `I:/AI Projects/Worktrees/Books Arranger/senua-031c-scratch/` (delta 2) | 124.17 MB | still locked |
| `I:/AI Projects/Worktrees/Books Arranger/senua-031b-scratch/` (delta 1) | 253.85 MB | still locked |

- The lock has the same shape as in delta 3. `copy` and `probes` inside `senua-031e-scratch` rename freely and back, but the top folder does not (`Device or resource busy`). So something holds a handle on each top folder itself, not on a file inside it.
- That holds even for a folder this session created minutes earlier, which no shell of mine ever had as its working directory. The likely holder is the long-running session process that created the folders. If so, the handles go when that session ends.
- No handle-listing tool is installed (`handle.exe` / `handle64.exe`), so I could not name the holder.
- I did not delete anything by hand.
- Next step: once the session ends, run the same sweep line again, naming the four folders.
