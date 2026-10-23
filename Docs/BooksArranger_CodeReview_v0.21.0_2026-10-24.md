# Code Review — Books Arranger v0.21.0 (final delta re-review)

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-23
Tool: Books Arranger (Electron / Python)
Release: v0.21.0
Commit range: 004ab2a2b7732892c1be40ed3c0a535d151447be..f2de1ed87e2af0842660f97c8c20a275a71ab502
Delta reviewed in this pass: c08c3bc9c391aa29f9351b235e1140cd6132793b..f2de1ed87e2af0842660f97c8c20a275a71ab502
Release source commit: f2de1ed87e2af0842660f97c8c20a275a71ab502
Release artifact manifest SHA256: 5940e820ffc6ea86024e8950a2012d550020487c959a2f355fa5fd682f59af99
Reviewed source: C:/Antigravity Projects/Worktrees/Books Arranger/inplace-m4b (branch codex/books-inplace-m4b, clean tree at HEAD f2de1ed, level with origin)
Files changed in the delta: 5 files (2 commits: caccf5f docs only, f2de1ed); inplace_m4b.py +83 / -26, tests +272 / -1, design note +4 / -3, two superseded reports +345 (git diff --numstat)
Stand-down dimensions: none
```

**Why the file name carries 2026-10-24.** I did this review on 2026-10-23. `scripts/release-contract.mjs:73` accepts a review report only as `Docs/BooksArranger_CodeReview_v0.21.0_<YYYY-MM-DD>.md`, so the requested `…_2026-10-23b.md` would be refused at the release gate. The one compliant name for today already holds my superseded c08c3bc report, committed as history in caccf5f, and I do not overwrite history. The next free compliant name is `…_2026-10-24.md`. See F19.

**What this report certifies.** It certifies the full range from `v0.20.3` (`004ab2a`) to f2de1ed:
- `004ab2a..7321517` was reviewed in `Docs/BooksArranger_CodeReview_v0.21.0_2026-10-22.md` (RELEASE CLEAR).
- `7321517..c08c3bc` was reviewed in `Docs/BooksArranger_CodeReview_v0.21.0_2026-10-23.md` (RELEASE CLEAR, with Major F12). Both reports are committed as history.
- This pass reviews `c08c3bc..f2de1ed` and re-tests every finding still open in those two reports. Open findings are carried forward by reference.

**The artifact.** I checked `dist/release-artifacts.json` read only:
- It hashes to the pinned value above.
- Its `source_head` is f2de1ed, and its version is 0.21.0.
- Its `product_digest` `a0640e1a…` equals `productTree(ls-tree f2de1ed)`, which I recomputed with the repo's own `release-contract.mjs`.

## Summary

f2de1ed fixes Futaba's M1 (damaged journal rows), my F12 (torn append), F13 (offline library) and F14 (untested edges), plus the cover re-read gap and the F11 docstrings. It also adds a parity test against the copy flow. I re-ran my r2 probes and mutations against f2de1ed, mutated each new fix one clause at a time, and probed what the fixes could break.

**The fixes:**
- **Closed:** F12, F13, F14, and the cover re-read gap. Each is shown closed by a probe that now gives the safe result and by a mutation that the gate now catches.
- **Mostly closed:** M1 is closed for ten intent fields but not for `identity`. A row missing only that field still keeps the engine from starting (F15).
- **Mostly closed:** F11. One docstring still says "unchanged copy flow".

**What the fixes break or leave open:**
- **F15 [Major]:** M1's failure mode is still reachable through the one intent field `_SHAPE` does not list.
- **F16 [Minor]:** a journal row with a NULL key column puts every interrupted in-place book into needs attention with a false reason.
- **F17 [Minor]:** F13's offline test cannot tell an offline share from a book folder that was renamed or deleted. Such a row never settles, and the book loses its in-place reason.
- **F18 [Minor]:** the parity test certifies less than its docstring says. A copy-flow gate written as `try/except`, or added to one of four whitelisted functions, passes it unseen.
- **F19 [Minor]:** the release contract accepts only one review report per version per day. This is outside the range, but it forced this file's name.
- **F20 [Minor]:** no test fails if `published_move` stops accepting the native rename receipt. `confirm_move` masks it at the cost of a second full read.

**Carried forward, still open:** F6, F8, F9 and F10, all Minor.

There is no Critical finding, and the safety floor is intact.

## Focus questions (brief items 1–3)

| # | Question | Answer |
|---|---|---|
| 1 | Does each fix close its finding? | **M1:** for ten of the eleven intent fields recovery reads. `_intent` refuses every damaged row the three new tests inject (40 refusals, no escape), each stays on its own book, and Q1–Q8 and Q10 are caught. The eleventh field, `identity`, is still read unchecked (F15). **F12:** yes. A zero tail at full length is now `rolled_back`, to bytes equal to the original, at both pre-type-patch crash points and through the queue restart (`pending`, no attention). N1r, which puts the tail clause back, is caught. **F13:** yes, for an offline share. With both `lexists` and `isdir` failing on the folder, the restart leaves the book `pending` and the row open. Start with the share back undoes the edit, and Q11 is caught. The side effect is F17. **F14:** yes. N5, N6, N9 and N10 all survived on 2026-10-23, and each is now caught by its own new test. **Cover re-read:** yes. Q13 is caught by the cover test and by the parity test on its own. **F11:** mostly; `inplace_m4b.py:147` still says "None for the unchanged copy flow". |
| 2a | Does "folder not visible ⇒ offline, leave open" let a real missing original sit unresolved forever? | **Yes, for a renamed or deleted book folder** (F17). Probe: crash mid-append, then a torn tail, then the folder renamed by hand. Three restarts each give `pending` and "Interrupted book restarts on explicit resume", with the row still `intended` and `unresolved()` empty. Start then gives needs attention, "An inspected destination ancestor is unavailable", and the row stays open. The moved file keeps its torn tail, and nothing will ever cut it. Before f2de1ed the same book showed at startup with the in-place reason "The edited original is missing…". A file renamed inside a visible folder is still reported missing (Ender's test, and Q12 is caught). |
| 2b | Can head-proof-only undo (F12) write into a file that isn't the original? | **No file comes out as anything but the reviewed original, and the head proof is now the only content gate (N3 is caught).** Probe at recovery, which skips the file-ID check: (1) another tagger's append-style edit, shorter than ours, is undone to the original; (2) a foreign tail at exactly our length with the head intact is undone to the original (the tail clause used to refuse it); (3) a file rewritten whole at our output length is refused and untouched; (4) a file one byte longer than our output is refused by the length window. The undo writes only through a handle that shares READ only (r2 probe). After the write, `[0, size)` hashes to the reviewed SHA-256, which `_undo` checks again. The most that can be lost is `appended_size` bytes past the original end of file, and only another append-style tool working between a crash and the next start can put foreign bytes there. My F3 concern does not return. No finding. |
| 2c | Is the parity test sound? | **It is real, but narrower than its docstring** (F18). It catches my positive control P1 (a new `if`/`raise` gate in `_preserve_single_m4b`) and, on its own, the F1 revert N0, the keep-sources revert M1 and the cover-check removal Q13. It passes when the same new gate is written as `try/except` (P2) or added inside `verify_candidate`, one of four functions COVERED whitelists by bare prefix (P3). A trace over every repo module shows the copy flow also runs gates in `native_io` and `metadata`, which the test never parses. Two of those gates (`native_io` snapshot protection) are not evaluated by the edit; both guard the copy flow's own stage and need no in-place counterpart. The five copy-flow modules have 12 `raise` statements inside `except` handlers, which the test cannot see. Each one either sits on a path an M4B edit never takes (MP3 tag copy, decode, repair), or runs in a function the edit calls too (`audio_info`, `source_chapters`, `copied_audio_evidence`), or has an in-place counterpart: `snapshot_manifest`'s library-root check matches `DirectoryBoundary(root, …)`, and `_preserve_single_m4b`'s `Refused` wrapper matches `_before_write`'s fallback. So **no copy-flow gate is skipped today**; the test just cannot promise that for the next one. It also compares `create_private` only. The publish and cleanup phases, where F8 lives, are not compared. |
| 2d | Does `_intent()` reject a real journal row? | **No.** I wrapped `_intent` across the whole in-place module. 29 reads in 15 tests accepted their row, and all 40 refusals came from the three tests that inject damaged rows. A probe crashed the edit at each of the six fault points and also checked a `published` row: `_intent` accepted every one. `published_move` accepted the native rename receipt on its own, with the `confirm_move` fallback patched to fail. Every field's real type matches `_SHAPE`: `native_io` facts return `int` size, write time (ns) and attributes, and `type_offset = movie_offset + 4` lies inside the original. |
| 2e | (mine) `clear()` now lets an attempt run past an offline row. What if the share returns between `clear()` and the read? | **Safe.** Probe: offline at `clear()`, share back before the attempt. A row left at `before_append` (file untouched) is edited again under a new attempt and published, and the old row then reconciles to `published` against the same output. A row at `type_patched` is refused by the attempt ("Source changed before working-space admission"), nothing is written, and the next recovery undoes the edit. The docstring's "it cannot read the source either" is not strictly true, but its second reason, that nothing writes to a source that differs from its review, holds. |
| 3 | Are the tests real? | **Yes, with two gaps.** Of 36 single-clause mutants, 31 are caught: every carried mutant, every F14 edge, and every clause of the new fixes but one. The survivors are N2 and N11 (identity clauses, not gaps), P2 and P3 (F18), and Q9b (F20). The damaged-row tests are thorough within the key list they enumerate, which is exactly why F15 slips past them. See the table under Evidence. |

## Rubric

### 1. Security

- Status: Pass. There is no new shell-out, path or IPC. The parity test's `sys.monitoring` tracer is test-only and frees its tool ID. There is no Electron change and no secret.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **F17 [Minor]** `inplace_m4b.py:431-432`, `Docs/BooksArranger_InPlaceM4B_Design_2026-10-22.md:128`, `inplace_m4b.py:465-467`. `not os.path.isdir(path.parent)` treats any invisible book folder as an offline share.
    - **The case:** a crash mid-edit, then the book folder is renamed or deleted (by hand, or by another tool) before the next start. The row stays open and is never recorded, so it can never settle, and nothing reports it.
    - **What Sergei sees:** startup gives `pending`. Start gives "An inspected destination ancestor is unavailable", which says nothing about an interrupted edit. Before f2de1ed he got the in-place reason "The edited original is missing and its destination does not hold it" at startup.
    - **The file:** it keeps its edit wherever it was moved. That is either a valid edited M4B or, as in my probe, the original plus a torn zero tail. Its audio bytes are intact.
    - **The test encodes the misreading:** Ender's F13 test (`test_startup_leaves_an_edit_in_an_unreachable_folder_open…`) simulates an offline share by renaming the book folder, which is exactly the case that is misread.
    - **Fix:** call it offline only when the journaled library root (`intent['root']`) cannot be seen. A visible root without the book folder is a missing original: `unresolved`, as before. Simulate offline in that test by making the root unreachable, and add a folder-renamed case that expects `unresolved`. Update `Design:128` and the `clear()` docstring to match.
  - **F8 [Minor], carried, still open.** `merge_service.py:2685-2688` is unchanged. See the 2026-10-22 report.

### 3. Crash / Stability Safety

- Status: Concerns
- Findings:
  - **F15 [Major]** `inplace_m4b.py:68-69` (`_SHAPE`) with `:412` and `:435`. M1 is not closed for `identity`.
    - **What happens:** `_SHAPE` claims to list "every intent field recovery reads" but omits `identity`. `_prove_move` reads `intent['identity']` into its receipt (`:412`).
    - **The row that reaches it:** the original is absent and the destination holds the planned output, which is the post-rename crash F2 is about, and the row lacks only `identity`. That is a hand-edited, corrupted or future-schema row, the reach Futaba gave M1.
    - **Probe at startup:** `KeyError: 'identity'` escapes `reconcile` (`:435` catches only `ValueError`/`OSError`) and `_recover`'s narrowed except, so `AudioJobs` is never constructed: "ENGINE DID NOT START". That is exactly M1's failure.
    - **Probe at cleanup:** the same `KeyError` comes out of `confirm_move`. By code reading, the cleanup worker's broad handler (`source_cleanup.py:307`) then holds that book with the reason `'identity'`.
    - **Why the tests miss it:** the new damaged-row test (`tests/test_inplace_m4b.py:480`) enumerates `_SHAPE`'s own ten keys, so it cannot find a key the list leaves out.
    - **Severity:** Major, not Critical. The consequence is M1's (the app cannot start, with no in-app way out), but the app's own writes never produce such a row, and no byte is at risk.
    - **Fix:** add `'identity': list` to `_SHAPE`, or catch `KeyError`/`TypeError` per row in `reconcile` and `confirm_move`. Build the test's key list from the fields recovery reads, not from `_SHAPE`.
  - **F16 [Minor]** `inplace_m4b.py:437` with `:97-98`. A journal row with a NULL `job_id` or `attempt_id` makes `_record` look for a row it cannot match. It then raises `BoundaryError('In-place journal intent is missing')` outside `reconcile`'s `try`.
    - **Probe:** at startup the error reaches `_recover`'s handler. Every interrupted in-place book, including one whose own row had just rolled back (bytes equal to the original), goes to needs attention with "…In-place journal intent is missing".
    - Rows after the NULL row are not reconciled at that start.
    - The NULL row can never be recorded, so this repeats at every start.
    - SQLite allows NULL in this non-integer primary key. The app never writes one; `_create_private` validates both IDs as UUIDs.
    - **Fix:** in `reconcile`, treat a row with a non-text key as damaged without calling `_record`, and report it once.

### 4. Performance

- Status: Pass.
  - Dropping the tail hash changes no read count.
  - The cover re-read adds one small file read per edit.
  - An `offline` row costs two path checks per start and per attempt. F17's rows pay that forever, which is negligible.

### 5. State & Data Safety

- Status: Concerns (carried only)
- Findings:
  - **F12, closed.** See Focus 1 and 2b.
  - **F6 [Minor], carried, still open.** The undo's post-check (`inplace_m4b.py:240`) still does not compare attributes, and the download marker is still not restored. `CHANGELOG.md:8` states the marker exception; the design note (`:36`) still does not.
  - **F10 [Minor], carried, still open.** `inplace_m4b.py:61-62`: the journal still does not assert synchronous FULL.

### 6. Input Handling

- Status: Pass. `_json_object` and `_intent` now check the journal columns' shape before use, including the bound that stops a damaged `type_offset` from writing past the end of the original (Q2 is caught). The remaining gaps are F15 and F16, recorded under 3.

### 7. Maintainability (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **F9 [Minor], carried, still open.** `inplace_m4b.py:142` still turns `KeyError`/`TypeError` before the first write into a silent fallback. `merge_service.py:2677` still has its `hasattr` for test fakes.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **F11 [Minor], carried, mostly fixed.** The module docstring, `Ineligible` and `Design:114` now match the code. One residual remains: `inplace_m4b.py:147`, "or None for the unchanged copy flow".
  - The `_SHAPE` comment (`:66`) and `Design:128` overstate the code. Those are recorded under F15 and F17.

### 9. Build & Release Hygiene

- Status: Concerns
- Findings:
  - **F18 [Minor]** `tests/test_inplace_m4b.py:571-592`, `:634-646`, `:662-663`. The parity test promises that "a gate added to the copy flow fails this test until the in-place path evaluates it too". It keeps that promise only for an `if` whose own body raises, or a two-argument `need(...)`, in the six parsed modules, outside four whitelisted functions, within `create_private`.
    - **Shown:** P2 (a `try/except` gate) and P3 (a gate inside `verify_candidate`) both pass it. The copy flow also runs gates in `native_io` and `metadata`, which the test never parses.
    - **Not a gap today:** see Focus 2c.
    - **Fix:**
      - Also parse `except` handlers that raise.
      - Replace the four bare `'function: '` COVERED keys with the exact gates they cover today.
      - Add `native_io` and `metadata` to the parsed modules.
      - Narrow the docstring to what is compared (`create_private` only, not the publish or cleanup phases).
  - **F19 [Minor], outside the range (pre-existing)** `scripts/release-contract.mjs:73`. The acceptance regex allows exactly one review report, and one QA report, per version per date. This release had three review cycles in two days. A same-day re-review must therefore overwrite committed history or take another date, as this file does. **Fix:** accept an optional suffix (for example `_\d{4}-\d{2}-\d{2}(?:[a-z]|_r\d+)?\.md`), and keep the acceptance index as the one pointer to the binding report.
  - **F20 [Minor]** `inplace_m4b.py:493-496`. No test needs `published_move` to accept the native rename receipt.
    - **Mutant Q9b:** `published_move` rejects only the native receipt (`books-native-no-copy-rename-v1`). The whole suite stays green, because `confirm_move` then proves the move again and cleanup completes.
    - **The silent regression it would hide:** every in-place cleanup would hash the output in full again over the share, and would replace the native receipt in the journal with a recovered one.
    - Q9, which makes `published_move` return nothing, is caught, but only through the recovered-receipt kill test.
    - **Fix:** in the end-to-end test, assert that cleanup retired the book through the native receipt: the row's `rename.schema` is unchanged after cleanup, and `confirm_move` was not called.
- Verified, no finding:
  - **Gate:** gate run 8 (`ba-0.21.0-check-run8.log`, 12:44, after the f2de1ed commit at 10:48): `BOOKS_INTEGRATED_CHECKS_PASS`, 1274 Python (1265 + the 9 new in-place tests) and 57 Node, 0 skipped. The log carries no HEAD line; the case count and time match f2de1ed. `test_inplace_m4b.py` is still in `scripts/check-desktop.mjs:40`.
  - **My baseline:** 48/48 on the scratch copy (`r3-baseline.log`: `test_inplace_m4b` 36, `test_source_proofs` 6, `test_standing_admission` 6).
  - **Version and lock:** `package.json` and `package-lock.json` read 0.21.0. The delta does not touch them or `scripts/`.
  - **Manifest:** see the header.
  - **Attribution:** no Claude attribution in f2de1ed or caccf5f.

## Patterns

The r2 pattern held one more time, in a new shape. The fix was proven by a test generated from the fix's own list (`_SHAPE`'s keys), so the one key the list missed was missed by the test too (F15). The parity test has the same property at a larger scale: it reads gates out of the code in the shapes it knows, so a gate in another shape is invisible to it (F18). A check derived from the implementation needs at least one input that is not, such as the fields recovery actually reads, or every `raise`.

## Evidence

**Setup:**
- All runs used `git archive f2de1ed` copies under the short path `C:/Users/AnGeLZzZ/AppData/Local/Temp/sn21/r3/`: `base` for the baseline, `p3` for the probes, and one folder per mutant.
- The runtime was the worktree's build-cache runtime `c3d7d82c…` (Python 3.14.8, SQLite 3.50.4, its FFmpeg), with the same fixture-root mapping as `check-desktop.mjs`.
- Nothing ran in the worktree, the live DB, Z:, the installed app or `dist/`, except a read-only hash and parse of `release-artifacts.json`. This report is the only file written in the worktree, and it is uncommitted.

**Logs and sources** are in `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/64106cea-b39e-4987-9571-6ad97339dc8a/scratchpad/shared/senua-0210/`:
- **Baseline:** `r3-baseline.log`, 48/48.
- **r2 probes re-run:** `r3-probe-r2.log` and `r3-probe-r2-offline.log`.
  - Torn full tail at both points: now `rolled_back`, and three `clear()` calls pass.
  - Torn tail through the queue: `pending`.
  - Output lock during `confirm_move`: still refused before and after the proof.
  - The r2 offline probe hides only the file and destination, so the folder stays visible. That now reads as missing, as it should. The faithful offline probe is below.
- **New probes:** `test_senua_r3_probes.py` and `test_senua_r3_parity.py`, logged in `r3-probe.log`:
  - F12 torn tails and the F3 re-check (four foreign-file cases);
  - F13 faithful offline then back, the renamed folder over three starts and a Start, and the share returning between `clear()` and the attempt;
  - M1 real rows at every fault point, `identity` missing (F15), and a NULL `job_id` (F16);
  - the copy-flow gates outside the six parsed modules.
- **`_intent` across the suite:** `r3-runner-intentlog.py`, logged in `r3-intentlog.log`.
- **Unseen raise shapes:** `r3-scan_raises.py`, logged in `r3-scan-raises.log`.
- **Parity test stability:** `r3-parity-repeat-{1,2,3}.log`, 3/3 green, about 19 s each.
- **Mutations:** `r3-mutate.py` and `r3-run-mutations.sh`. Each mutant changes one clause and was run on the three in-place modules (`r3-mut-<name>.log`). Six were also run on `ParityTests` alone (`r3-parity-<name>.log`).

| Mutation | What it breaks | Result |
|---|---|---|
| M1 | Drops the keep-sources policy condition | Caught: `test_sources_kept_by_policy_are_never_moved` (5 subtests), `ParityTests` (6), the startup journal-failure test |
| M2 | Skips `_byte_proof` | Caught: `test_unprovable_original_stays_journaled_and_blocks_new_attempts`, `ParityTests` |
| M4 | Skips the pre-attempt `clear` | Caught: `test_an_attempt_first_undoes_or_refuses…` (both subtests), `test_a_damaged_row_refuses_only_its_own_books_attempt` |
| M5 | Skips the startup `recover_all` | Caught by 4 tests, among them `test_startup_undoes_an_interrupted_edit` |
| M6 | Skips the in-place cleanup contract | Caught: four subtests of `test_edit_moves_original_and_equals_copy_flow_output_bytes` |
| M7 | Retires without a receipt | Caught: `test_cleanup_refuses_to_retire_without_a_provable_move`, and 8 subtests of `test_cleanup_refuses_a_damaged_row…` |
| M9 | Journals after the append | Caught: `test_crash_at_each_step…` (`before_append`, `appended`), `test_a_torn_append_of_full_length_is_undone`, the startup damaged-row test |
| N0 | F1 revert: reuses the stage cover without its gate | Caught: `test_cover_gate_still_refuses_after_an_in_place_fallback`, `ParityTests` (both fallback subtests) |
| N1r | F12 revert: the tail clause of `_edited_original` comes back | Caught: `test_a_torn_append_of_full_length_is_undone` |
| N2 | Drops the native-identity clause of the in-process `_undo` | Survives, as on 2026-10-23. The content proof refuses every rewrite; not a gap |
| N3 | Drops the head proof of `_edited_original` | Caught by 5 tests, now including both `test_recovery_writes_nothing_into_a_file_it_cannot_prove` subtests (on 2026-10-23 the tail clause still refused `output_size`) |
| N4 | `_prove_move` checks the size only | Caught: `test_recovery_never_trusts_a_destination_of_the_right_size`, `test_cleanup_refuses_to_retire_without_a_provable_move` |
| N5 | `_prove_move` skips both old-path checks | Caught (survived on 2026-10-23): `test_cleanup_proves_a_move_only…` [N5] |
| N6 | The startup `except` widened back to `Exception` | Caught (survived): `test_startup_does_not_swallow_a_programming_error` |
| N7 | Startup ignores `unresolved()` | Caught by 3 tests, among them `test_startup_shows_an_edit_it_cannot_undo_on_its_book` |
| N8 | Startup ignores a journal read failure | Caught: `test_startup_shows_a_journal_it_cannot_read_on_interrupted_in_place_books` |
| N9 | `confirm_move` accepts only `publishing` rows | Caught (survived): `test_cleanup_proves_a_move_only…` [N9] |
| N10 | `confirm_move` proves the journaled destination, not the current output | Caught (survived): `test_cleanup_proves_a_move_only…` [N10] |
| N11 | The in-process reopen skips the identity check | Survives, as on 2026-10-23. Same as N2; not a gap |
| Q1 | `_intent` without its shape and bounds check | Caught: 7 subtests of `test_cleanup_refuses_a_damaged_row…`, plus the startup damaged-row test |
| Q2 | `_intent` without the `type_offset` bound | Caught: `test_startup_shows_a_damaged_journal_row…` [type offset outside the original], and that test's restored-bytes check |
| Q3 | `_intent` without `size < output_size` | Caught: the same test [output not longer than the original] |
| Q4 | `_record` parses a damaged detail as before | Caught: `test_startup_shows_a_damaged_journal_row…` |
| Q5 | `unresolved()` parses a damaged detail as before | Caught: the same test |
| Q6 | `clear()` matches by path only | Caught: `test_a_damaged_row_refuses_only_its_own_books_attempt` |
| Q7 | `clear()` without the `isinstance(path, str)` guard | Caught: the same test |
| Q8 | `published_move` without its shape checks | Caught: 6 subtests of `test_cleanup_refuses_a_damaged_row…` |
| Q9 | `published_move` returns nothing | Caught: `test_kill_after_rename_is_recovered_with_a_receipt_cleanup_accepts` |
| Q9b | `published_move` rejects only the native rename receipt | **Survives** (F20) |
| Q10 | `confirm_move` parses the intent without `_intent` | Caught: 6 subtests of `test_cleanup_refuses_a_damaged_row…` |
| Q11 | Drops the F13 offline branch | Caught: `test_startup_leaves_an_edit_in_an_unreachable_folder…`, and the startup damaged-row test [folder unreachable] |
| Q12 | Every not-found original reads as offline | Caught: `test_startup_leaves_an_edit_in_an_unreachable_folder…` (its "moved by hand" half) |
| Q13 | Drops the in-place cover re-read | Caught: `test_a_selected_cover_changed…`, and `ParityTests` (also alone) |
| P1 | New copy-flow gate, `if`/`raise`, in `_preserve_single_m4b` (positive control) | Caught by `ParityTests`, alone and in the suite: "Copy-flow gates the edit skips: `_preserve_single_m4b: Senua probe gate`" |
| P2 | The same gate as `try`/`except` | **Survives**, alone and in the suite (F18) |
| P3 | A new `if`/`raise` gate inside `verify_candidate` | **Survives**, alone and in the suite: whitelisted by the bare `'verify_candidate: '` key (F18) |
| N0, M1 (parity alone) | — | Both caught by `ParityTests` on its own: N0 by "Copy-flow gates skipped after the fallback: `protected_cover: Selected cover dimensions…`", M1 by the kept-source subtests |

**Totals:** 36 single-clause mutants, run on the three in-place modules. 31 are caught. 5 survive: N2 and N11, identity clauses the content proof subsumes (not gaps, unchanged since 2026-10-23); P2 and P3, the parity-test blind spots (F18); and Q9b (F20). All 12 of my 2026-10-23 mutants that were caught then are still caught, and all four F14 survivors are now caught.

## Verdict

- Total Critical: 0
- Total Major: 1 (F15)
- Total Minor: 10 (F16, F17, F18, F19 and F20 new; F6, F8, F9, F10 and F11 carried)

No safety-floor item: no unsafe Electron config, no secret leakage and no source-of-truth destruction. F15 writes nothing. It keeps the engine from starting on a hand-damaged or future-schema journal row, which the app's own writes never produce.

**Verdict:** RELEASE CLEAR

F15 is Major, not a release gate under ProcessRules. Futaba graded M1, its parent, Major with a recommendation to fix it before release, and the same reasoning applies here. The fix is one line plus a test. Whether to fix it before shipping is Jane's and Sergei's call.

| # | Sev | Dim | file:line | Finding | Next cycle |
|---|-----|-----|-----------|---------|------------|
| F15 | Major | 3 Stability | `inplace_m4b.py:68`, `:412`, `:435` | `_SHAPE` omits `identity`, which `_prove_move` reads; a row missing it keeps the engine from starting (M1 not fully closed) | Add `'identity': list` or catch `KeyError`/`TypeError` per row; derive the test's keys from the fields recovery reads |
| F16 | Minor | 3 Stability | `inplace_m4b.py:437`, `:98` | A NULL `job_id`/`attempt_id` row makes `_record` raise outside `reconcile`'s `try`; every interrupted in-place book gets a false reason, at every start | Treat a non-text key as damaged without `_record` |
| F17 | Minor | 2 Correctness | `inplace_m4b.py:431`, `Design:128` | A renamed or deleted book folder reads as an offline share; its row never settles and the book loses its in-place reason | Offline only when `intent['root']` is unreachable; fix the test's offline simulation |
| F18 | Minor | 9 Hygiene | `tests/test_inplace_m4b.py:571`, `:634-646` | The parity test misses `try/except` gates, gates in four whitelisted functions, other modules, and the publish/cleanup phases | Parse `except` raises, name whitelisted gates exactly, add `native_io`/`metadata`, narrow the docstring |
| F19 | Minor | 9 Hygiene | `scripts/release-contract.mjs:73` | One acceptance report per version per date; forces misdated names or overwritten history (pre-existing, outside the range) | Allow a suffix |
| F20 | Minor | 9 Hygiene | `inplace_m4b.py:493` | No test needs `published_move` to accept the native receipt (Q9b survives) | Assert the native receipt is the one cleanup uses |
| F6 | Minor | 5 Data safety | `inplace_m4b.py:240`, `:351` | Rollback drops the download marker (now in CHANGELOG, not the design note); attributes are not compared | Carried from 2026-10-22 |
| F8 | Minor | 2 Correctness | `merge_service.py:2685` | Publication intent committed before the locked guard | Carried from 2026-10-22 |
| F9 | Minor | 7 Maintainability | `inplace_m4b.py:142` | `KeyError`/`TypeError` before the first write become silent fallbacks; product code bends to fakes | Carried from 2026-10-22 |
| F10 | Minor | 5 Data safety | `inplace_m4b.py:61` | Journal does not assert synchronous FULL | Carried from 2026-10-22 |
| F11 | Minor | 8 Drift | `inplace_m4b.py:147` | One docstring still says "unchanged copy flow" | Carried; one line left |

Closed in this delta: F12, F13, F14 (from the 2026-10-23 report) and the cover re-read gap. Futaba's M1 is closed except for F15 and F16.
