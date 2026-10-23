# Code Review — Books Arranger v0.21.0 (delta re-review)

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-23
Tool: Books Arranger (Electron / Python)
Release: v0.21.0
Commit range: 004ab2a2b7732892c1be40ed3c0a535d151447be..c08c3bc9c391aa29f9351b235e1140cd6132793b
Delta reviewed in this pass: 73215173a8b5c2f8324b89c34a06e470cee4b3a3..c08c3bc9c391aa29f9351b235e1140cd6132793b
Release source commit: c08c3bc9c391aa29f9351b235e1140cd6132793b
Release artifact manifest SHA256: 5526d9e9582a75a32a83814c429a526451bbebbdf69d839eacdf837fec9fcf38
Reviewed source: C:/Antigravity Projects/Worktrees/Books Arranger/inplace-m4b (branch codex/books-inplace-m4b, clean tree at HEAD c08c3bc, level with origin)
Files changed in the delta: 9 files, +696 / -52 (2 commits: c296a1e, c08c3bc); product 4 files +100 / -28, tests +188 / -10, docs 3 files
Stand-down dimensions: none
```

**What this report certifies.** It certifies the full range from `v0.20.3` (`004ab2a`) to c08c3bc:
- `004ab2a..7321517` was reviewed in `Docs/BooksArranger_CodeReview_v0.21.0_2026-10-22.md` (RELEASE CLEAR, 4 Major, 7 Minor). That report is now committed as history.
- This pass reviews `7321517..c08c3bc` and re-tests every finding of that report. Findings that are still open are carried forward by reference.

**The artifact.** I checked `dist/release-artifacts.json` read only:
- It hashes to the pinned value above.
- Its `source_head` is c08c3bc.
- Its `product_digest` `4c5b50db…` equals `productTree(ls-tree c08c3bc)`, recomputed with the repo's own `release-contract.mjs`. c08c3bc changes only `Docs/`, so this digest equals c296a1e's tree.

## Summary

c296a1e fixes F1–F5, F7 and F11. c08c3bc only commits the two superseded reports. I re-ran my 2026-10-22 probes and mutations against c08c3bc, then mutated each new fix and probed what the fixes could break.

**The fixes:**
- **Closed:** F1, F2, F3, F4, F5 and F7. Each closing is shown by a probe that now gives the safe result and by a mutation the gate now catches.
- **Mostly closed:** F11. Two module docstrings still say the copy flow "runs unchanged".

**The fixes break one thing:**
- **F12 [Major]:** the undo's new tail check refuses a book whose append was torn at full length, although the head proof already shows the undo is safe. The book then stays blocked for good, with a reason that tells Sergei the file is not his original when it is. This check came from my own F3 recommendation, which was over-strict.

**Two new Minor findings:**
- **F13:** a library share that is unreachable at startup now puts the interrupted book in needs attention, with a reason that reads like data loss.
- **F14:** four edges of the fixes have no test.

**Carried forward, still open:** F6, F8, F9 and F10, all Minor.

There is no Critical finding, and the safety floor is intact.

## Focus questions (brief items 1–3)

| # | Question | Answer |
|---|---|---|
| 1 | Does each fix close its finding? | **F1:** yes. My cover probe now gets "Selected cover dimensions are invalid or too large" from the copy flow after the in-place fallback (`audio_pipeline.py:526-533`), and mutation N0 is caught. **F2:** yes. My post-death catalog probe and my in-process postcondition probe both now give `published`, with a receipt `published_move` accepts. M7 and Ender's revert of the cleanup proof are caught. **F3:** yes. A foreign file at either length is left untouched, and N3 is caught. The side effect is F12. **F4:** yes. M4 and M5 are now caught, and startup errors are narrowed and surfaced. **F5:** yes, M6 and M7 are caught. **F7:** yes. My zero-filled destination of the right size now gives `unresolved`, and N4 is caught. **F11:** mostly; see the residual under 8. |
| 2a | Could cleanup retire an original on a wrong or stale output hash? Is there a TOCTOU between the proof and the retirement? | **No.** `_prove_move` (`inplace_m4b.py:365-381`) hashes the current file in full and compares it with the journal's planned `output_sha256`. That value was fixed at intent time, and the byte proof bound the same plan. In cleanup, `run()` already holds `VerifiedFile(final)`, shared for READ only, for the whole run (`source_cleanup.py:334`), and has hashed it against the job's record. So the output cannot be written, replaced or renamed between the proof and the commit. **Probe:** a write-open of the output during `confirm_move` was refused with `PermissionError`, both before and after the proof. The old path is checked twice in `_prove_move` and again at `source_cleanup.py:420` before the commit. Retirement deletes nothing. The destination's file ID is recorded but not compared; that is deliberate for the share, and it is safe because the content proven contains the whole original extent. |
| 2b | Undo tail check: does power loss mid-append now leave the book in attention? Is that safe? | **Real**, reproduced at both pre-type-patch crash points with a zero-filled tail of full length. **Safe in the narrow sense:** nothing is written, and the file is the reviewed original plus a dead tail. **But unnecessary, and a dead end with no in-app recourse.** See F12. |
| 2c | Startup now raises on errors other than OSError, ValueError and sqlite3 errors. Can a benign condition stop the engine? | **None found.** Every native wrapper raises `BoundaryError` (a `ValueError`, `native_io.py:11`; `FileInUse` is a `BoundaryError`, `:13`) or `OSError`. `sqlite_retry` re-raises `sqlite3.OperationalError`, and JSON errors are `ValueError`s. `ordinary()` and the intent parse moved inside `reconcile`'s per-row `try`, and an unreachable share becomes a per-row `unresolved` (probe). What still escapes is `KeyError`/`TypeError`/`AttributeError` from a journal row of the wrong shape, ctypes errors and `MemoryError`. Those are programming or corruption faults, which is what F4 asked to surface. Only this module writes the rows, and the intent schema did not change in the delta. One benign condition does change behaviour without stopping the engine: F13. |
| 2d | Recovery skips the file-ID check. Does that reopen F3? | **No.** The skip applies in recovery on every volume, not only on shares (`inplace_m4b.py:390`). But `_edited_original` now runs before any write, through a handle that shares READ only (`native_io.py:282`), so no other writer can change the file between the proof and the undo. Ender's tests show a same-ID foreign rewrite at the original length and at the edited length left untouched. N1 shows the head proof alone refuses both. The skip still allows an undo of a different file whose first `size` bytes equal the original with the type reverted, such as a copy restored over the path. The undo turns that file into the reviewed original, which is harmless. |
| 3 | Do the tests still prove themselves? | **Mostly.** All seven of my 2026-10-22 mutations are now caught, including the four that survived then (M4–M7). Of twelve new mutations, one clause at a time, 5 are caught and 7 survive. Three survivors are not gaps: N1 is F12's clause, which should go, and N2/N11 are identity clauses that the content proof subsumes. The other four are real gaps (F14). See the table under Evidence. |

## Rubric

### 1. Security

- Status: Pass. There is no new shell-out. The only new process is a test child (`sys.executable -I -B`, `CREATE_NO_WINDOW`, killed by handle). New paths go through `ordinary()`, and there is no Electron, IPC or renderer change and no secret.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **F13 [Minor]** `inplace_m4b.py:392-395` with `audio_jobs.py:375-391`. A library share that is unreachable when the engine starts (for example, the Windows logon reconnect race) puts an interrupted in-place book into needs attention. The reason reads "The edited original is missing and its destination does not hold it".
    - **Mechanism:** `os.path.lexists` returns False for an unreachable path, so `reconcile` cannot tell "offline" from "missing".
    - **Probe** (scratch copy, faithful: the real `_work_attempt`, a crash mid-edit, then a restart with both paths unreachable):
      - The book shows needs attention with that text.
      - Once the share is back, `attention_summary` offers Retry (group `retry`, allowed), and `retry_failed` refuses ("unclassified").
      - The next attempt's `clear()` then undoes the edit.
    - **Before c296a1e:** the book went to pending, and the next Start healed it with no action.
    - **Now:** Sergei must press Retry, after a reason that reads like data loss. The design note accepts needs attention for an offline library, so only the wording and the extra press are at issue.
    - **Fix:** in `reconcile`, test whether the journaled root or source folder is reachable, and give an offline reason when it is not. Optionally, leave an offline interrupted book pending.
  - **F8 [Minor], carried, still open.** See the 2026-10-22 report. The design note now documents the order difference (`Design:93`), but the behaviour at `merge_service.py:2685-2688` is unchanged.

### 3. Crash / Stability Safety

- Status: Pass. F4 is closed. Both recovery calls are reached through the queue in gated tests (M4/M5 caught). Startup catches only `(ValueError, OSError, sqlite3.Error)` and surfaces each failure on the interrupted book. Focus 2c found no benign condition that stops the engine.

### 4. Performance

- Status: Pass, with one note.
  - **The note:** each undo now reads the file in full twice (the proof, then the post-undo hash) instead of once, and a recovered move adds one full read.
  - **Where that matters:** at startup these reads run inside `AudioJobs` construction. The `_recover` docstring says that code must let the engine answer health within 3 minutes. One row for a large book over the share fits that window, and a Pause that lands in an undo waits for both reads.
  - **The risk:** rows stuck in `unresolved` (F12) are read in full again at every start.

### 5. State & Data Safety

- Status: Concerns
- Findings:
  - **F12 [Major]** `inplace_m4b.py:188-189`, the tail clause of `_edited_original`, enforced by `_undo` at `:201`. A torn append of full length can never be undone, and the book is blocked forever.
    - **What the undo writes:** it truncates everything past `size`, writes `moov` into 4 bytes inside `[0, size)`, and restores the write time and attributes.
    - **Why the clause adds nothing:** the head proof shows that `[0, size)` with the type reverted is the reviewed original. That already proves the result will be exactly the reviewed original. The tail clause puts a condition on the very bytes the undo is about to discard. It refuses whenever the length is exactly `output_size` and the tail is not the planned `moov`.
    - **When it happens:** the length reached `output_size` but the appended bytes did not become durable.
      - Power loss or an OS crash between `write_at` and `flush` (`:300`). NTFS can persist a new length ahead of its data, and the gap then reads as zeros.
      - A drop of the library share mid-append, if a later SMB write landed and an earlier one did not. That is the design's own "NAS drop after the write starts" case (§6).
    - **Probe** (scratch copy): I crashed at `appended` and at `before_type_patch`, then zeroed the tail at full length.
      - The head is the reviewed original, and the type bytes are still `moov`.
      - `recover_all` gives `unresolved`, "The file at the original path is not the edited original; it was not changed". Three more `clear()` calls refuse the same way.
      - At the queue, a restart gives needs attention with that reason.
      - The same tear at half length is undone (`rolled_back`, with bytes equal to the original).
    - **Effect:**
      - No audio byte is at risk, and nothing is written.
      - Every Retry or Start over on that path reaches `clear()` (`audio_jobs.py:1087`) and is refused again, and nothing in the app can settle the row.
      - The stated reason is false.
      - The whole file is read again at every start.
      - `CHANGELOG.md:8` ("A file that can no longer be proven to be the edited original…") does not describe this case, because this file *is* proven.
    - **Untested:** removing the clause (N1) leaves the gate green. No test needs it; the head proof alone refuses every foreign file the F3 tests write.
    - **Origin:** my F3 recommendation asked for this tail check, and Ender implemented it as written. The recommendation was over-strict.
    - **Fix next cycle:**
      - Drop the tail clause from the write gate. Keep the length window, the link count, the identity check outside recovery, and the head proof. If wanted, record the tail hash in the row detail as evidence.
      - Add a test showing that a zero tail of full length is rolled back.
  - **F6 [Minor], carried, still open.** The probe re-run shows the same result: the marker stream is gone after a rollback, and the attributes are restored but not compared. `CHANGELOG.md:8` now states the marker exception, which covers half of the 2026-10-22 fix. The design note does not state it (`Design:36` only describes the removal).
  - **F10 [Minor], carried, still open.** `inplace_m4b.py:64-77`: the journal still does not assert synchronous FULL.
  - F2, F3 and F7 are closed, with the evidence under Focus 1 and Evidence.

### 6. Input Handling

- Status: Pass. The new paths, the journaled `destination` and the job's `final_path` all go through `ordinary()`. `_prove_move` only reads through a held handle.

### 7. Maintainability (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **F9 [Minor], carried, still open.** `inplace_m4b.py:110` still converts `KeyError`/`TypeError` into a silent fallback. `merge_service.py:2677` still has its `hasattr` for test fakes, and the new kill-test child (`tests/test_inplace_m4b.py:34`) uses the same kind of fake.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **F11 [Minor], carried, mostly fixed.** The design note's six statements and `CHANGELOG.md:8` now match the code. The test count is 27, which I counted. Two residuals remain:
    - `inplace_m4b.py:10-11` and `:45` still say the copy flow "runs unchanged", although since F1 it repeats the cover gate.
    - `Design:114`'s "a full-length tail hashes to the planned `moov`" describes the F12 clause. Update it together with that fix.

### 9. Build & Release Hygiene

- Status: Concerns
- Findings:
  - **F14 [Minor]** Four edges of the fixes have no test. A mutation of each leaves the gate green:
    - **N5** `inplace_m4b.py:369`, `:375`: `_prove_move` without its old-path checks. Cleanup still refuses at `source_cleanup.py:420`, but by then the journal row is already `published` with `old_absent: True`, so `clear()` stops reconciling it.
    - **N6** `audio_jobs.py:376`: the startup `except` widened back to `Exception`. No test shows that a programming error is no longer swallowed.
    - **N9** `inplace_m4b.py:449`: `confirm_move` accepting only `publishing` rows. A row that startup recovery left `unresolved` (output relocated, or the share offline at that start) would block cleanup forever again. That is F2 by another route.
    - **N10** `inplace_m4b.py:454`: `confirm_move` proving the journaled destination instead of the job's current output. A book relocated before its cleanup would be refused again.
    - **Fix:** one test for each of these four. The identity-clause survivors (N2, N11) need none, because the content proof already refuses every file they would.
- Verified, no finding:
  - **Gate:** gate run 6 at c296a1e, the tree c08c3bc packages: `BOOKS_INTEGRATED_CHECKS_PASS`, 1265 Python and 57 Node, 0 skipped (`ba-0.21.0-run6-gate.log`). `test_inplace_m4b.py` is still in `scripts/check-desktop.mjs:40`.
  - **My baseline:** 39/39 on the scratch copy (`r2-baseline.log`).
  - **Ender's mutations:** his nine reverts of the fixes all fail the module (`ba-0.21.0-ender-fixes/mut-*.log`).
  - **Version and lock:** `package.json` and `package-lock.json` still read 0.21.0. The delta does not touch them or `scripts/`.
  - **Manifest:** see the header.
  - **Attribution:** no Claude attribution in c296a1e or c08c3bc.

## Patterns

The 2026-10-22 pattern is fixed where it was named: the queue now reaches recovery under test, and the masking test is replaced by a real kill. It recurs one level down. Each fix is proven by reverting the whole fix, but a fix made of several clauses can hide a clause no test needs. In this delta that hidden clause is the one that does harm (F12). A mutation pass for a data-path fix should therefore remove one clause at a time, not revert the fix as a block.

## Evidence

**Setup:**
- All runs used `git archive c08c3bc` copies under the short path `C:/Users/AnGeLZzZ/AppData/Local/Temp/sn21/` (`b` = baseline, `p2` = probes, `r2/<mutant>`).
- The runtime was the worktree's build-cache runtime `c3d7d82c…` (Python 3.14.8, SQLite 3.50.4, its FFmpeg), with the same fixture-root mapping as `check-desktop.mjs`.
- Nothing ran in the worktree, the live DB, Z:, the installed app or `dist/`, except a read-only hash and parse of `release-artifacts.json`.

**Logs and sources** are in `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/64106cea-b39e-4987-9571-6ad97339dc8a/scratchpad/shared/senua-0210/`:
- **Baseline:** `r2-baseline.log`, 39/39 (`test_inplace_m4b` 27, `test_source_proofs` 6, `test_standing_admission` 6).
- **2026-10-22 probes re-run:** `r2-probe-r1.log`.
  - Cover: now refused.
  - Death and postcondition: `published` with a receipt.
  - Size only: `unresolved`.
  - Marker: still dropped.
- **New probes:**
  - `test_senua_r2_probes.py`, logged in `r2-probe-new.log`: the torn tail at full and half length and at the queue, an offline library at startup, and the output lock during `confirm_move`.
  - `test_senua_r2_offline.py`, logged in `r2-probe-offline.log`: the faithful offline restart and the Retry offer.
- **Mutations:** `r2-mutate.py`, `r2-run-mutations.sh`, `r2-mut-<name>.log`.

| Mutation | What it breaks | Result |
|---|---|---|
| M1 | Drops the keep-sources policy condition (7321517) | Caught: `test_sources_kept_by_policy_are_never_moved`, plus the startup journal-failure test |
| M2 | Skips `_byte_proof` | Caught: `test_unprovable_original_stays_journaled_and_blocks_new_attempts` |
| M4 | Skips the pre-attempt `clear` | Caught (survived on 2026-10-22): `test_an_attempt_first_undoes_or_refuses_an_interrupted_edit_of_its_source`, both subtests |
| M5 | Skips the startup `recover_all` | Caught (survived): `test_startup_undoes_an_interrupted_edit`, `test_startup_shows_an_edit_it_cannot_undo_on_its_book` |
| M6 | Skips the in-place cleanup contract | Caught (survived): four subtests of `test_edit_moves_original_and_equals_copy_flow_output_bytes` |
| M7 | Retires without a receipt | Caught (survived): `test_cleanup_refuses_to_retire_without_a_provable_move` |
| M9 | Journals after the append | Caught: `test_crash_at_each_step_after_intent_is_undone_by_recovery` (`before_append`, `appended`) |
| N0 | F1 revert: reuses the stage cover without its gate | Caught: `test_cover_gate_still_refuses_after_an_in_place_fallback` |
| N1 | Drops the tail clause of `_edited_original` | **Survives.** No test needs it (F12) |
| N2 | Drops the native-identity clause of `_undo` | Survives. The content proof refuses every rewrite the tests make; not a gap |
| N3 | Drops the head proof of `_edited_original` | Caught: `test_recovery_writes_nothing_into_a_file_it_cannot_prove` (`size`). The `output_size` subtest is still refused, by the tail clause |
| N4 | `_prove_move` checks the size only | Caught: `test_recovery_never_trusts_a_destination_of_the_right_size`, `test_cleanup_refuses_to_retire_without_a_provable_move` |
| N5 | `_prove_move` skips both old-path checks | **Survives** (F14) |
| N6 | The startup `except` widened back to `Exception` | **Survives** (F14) |
| N7 | Startup ignores `unresolved()` | Caught: `test_startup_shows_an_edit_it_cannot_undo_on_its_book` |
| N8 | Startup ignores a journal read failure | Caught: `test_startup_shows_a_journal_it_cannot_read_on_interrupted_in_place_books` |
| N9 | `confirm_move` accepts only `publishing` rows | **Survives** (F14) |
| N10 | `confirm_move` proves the journaled destination, not the current output | **Survives** (F14) |
| N11 | The in-process reopen skips the identity check | Survives. Same as N2; not a gap |

Ender's own nine reverts of the fixes (`ba-0.21.0-ender-fixes/`) all fail the module. They revert each fix as a block, which is why N1 and the four F14 gaps did not show up there.

## Verdict

- Total Critical: 0
- Total Major: 1 (F12)
- Total Minor: 7 (F6, F8, F9, F10 and F11 carried; F13 and F14 new)

No safety-floor item: no unsafe Electron config, no secret leakage and no source-of-truth destruction. F12 writes nothing; its harm is a stuck book, not lost bytes.

**Verdict:** RELEASE CLEAR

| # | Sev | Dim | file:line | Finding | Next cycle |
|---|-----|-----|-----------|---------|------------|
| F12 | Major | 5 Data safety | `inplace_m4b.py:188` | The undo's tail clause refuses a full-length torn append that the head proof already makes safe to undo; the book is blocked forever with a false reason | Drop the tail clause from the write gate; test a full-length zero tail |
| F13 | Minor | 2 Correctness | `inplace_m4b.py:392`, `audio_jobs.py:375` | An unreachable share at startup parks the interrupted book in needs attention as "missing" | Give an offline reason; optionally keep it pending |
| F14 | Minor | 9 Hygiene | `inplace_m4b.py:369`, `:449`, `:454`; `audio_jobs.py:376` | Four edges of the fixes are untested (N5, N6, N9, N10 survive) | One test each |
| F6 | Minor | 5 Data safety | `inplace_m4b.py:320`, `:207` | Rollback drops the download marker (now in CHANGELOG, not in the design note); attributes are not compared | Carried from 2026-10-22 |
| F8 | Minor | 2 Correctness | `merge_service.py:2685` | Publication intent committed before the locked guard | Carried from 2026-10-22 |
| F9 | Minor | 7 Maintainability | `inplace_m4b.py:110` | KeyError/TypeError become silent fallbacks; product code bends to fakes | Carried from 2026-10-22 |
| F10 | Minor | 5 Data safety | `inplace_m4b.py:64` | Journal does not assert synchronous FULL | Carried from 2026-10-22 |
| F11 | Minor | 8 Drift | `inplace_m4b.py:10`, `:45` | Two docstrings still say the copy flow runs unchanged | Align with F1; revise `Design:114` with F12 |

Closed in this delta (from the 2026-10-22 report): F1, F2, F3, F4, F5, F7.
