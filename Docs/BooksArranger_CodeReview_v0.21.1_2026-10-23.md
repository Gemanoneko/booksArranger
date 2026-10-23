# Code Review — Books Arranger v0.21.1

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-23
Tool: Books Arranger (Electron / Python)
Release: v0.21.1
Commit range: e78b74746d1c84e48ab3b11b6ddfad17f3997f38..f64d46b74fe92af164f9189b2cb8c93ee44ac590
Release source commit: f64d46b74fe92af164f9189b2cb8c93ee44ac590
Release artifact manifest SHA256: 9a5b6ed94d580164bc68b5521f2ef936bf155d6b6b39d9bfa3ecca1cfd4472cb
Reviewed source: C:/Antigravity Projects/Worktrees/Books Arranger/inplace-m4b (branch codex/books-inplace-m4b, clean tree at HEAD f64d46b, level with origin)
Files changed: 7 files, +447 / -61 (1 commit, f64d46b): inplace_m4b.py +124 / -33, zone_identifier.py +26, tests/test_inplace_m4b.py +269 / -20, design note +16 / -5, CHANGELOG +9, package.json and package-lock.json version only (git diff --numstat)
Stand-down dimensions: none
```

**What this report certifies.** The range starts at the `v0.21.0` tag (e78b747). That tag is f2de1ed plus one docs-only commit, and f2de1ed is where my last report (`Docs/BooksArranger_CodeReview_v0.21.0_2026-10-24.md`) ended. This pass reviews the one commit f64d46b. It re-tests every finding of that report that is still open. The open ones are carried forward by reference.

**The artifact.** I checked `dist/release-artifacts.json` read only:
- It hashes to the pinned value above.
- Its `source_head` is f64d46b, and its version is 0.21.1.
- Its `product_digest` `d9d11c58…` equals `productTree(ls-tree f64d46b)`, which I recomputed with the repo's own `release-contract.mjs`.

## Summary

f64d46b fixes my F15, F16, F17 and F20, and Futaba's m-3 (the download marker is put back on undo) and m-4 (write time and attributes are checked before any write). I re-ran my r2 and r3 probes against f64d46b. I mutated each fix one clause at a time, mutated the writer to test the matrix's claim, and probed what the fixes break.

**The fixes:**
- **Closed:** F15, F16, F20 and m-4. Each is shown closed by a probe that now gives the safe result, and by a mutation that the suite now catches.
- **Closed for the case it names:** F17. A renamed or deleted book folder is now reported as missing, and nothing is deleted. The offline-versus-missing test is still an inference (F23).
- **Closed for the paths it names:** m-3. The marker comes back on the in-process undo, after a crash, and for a row 0.21.0 wrote. The 8 KiB bound holds at both ends. The new restore step has its own gaps (F21, F22).

**What the fixes break or leave open** (all Minor):
- **F21:** if the marker cannot be put back, the undo stops half done: the bytes are restored, but the write time and attributes are not. A crash inside the restore leaves an empty marker that is kept for good and blocks the book.
- **F22:** a 0.21.1 row's marker bytes are written back on shape alone. There is no hash check, although the 0.21.0 path has one.
- **F23:** "missing" is still inferred from failed lookups. A lookup error on a live share, or an output root out of sight, gives a false "missing" until Retry.
- **F24:** the CHANGELOG says edits recorded by 0.21.0 get their marker back. Only the ones 0.21.0 left open do.
- **F25:** the matrix varies types, never values. Four of the new value checks can be removed with the whole suite green, and one of them is m-4's own promise for the marker.

**Carried forward, still open:** F6 (attribute half), F8, F9, F10, F11, F18 and F19, all Minor.

There is no Critical or Major finding, and the safety floor is intact.

## Focus questions (brief items 1–3)

| # | Question | Answer |
|---|---|---|
| 1 | Does each fix close its finding? | **F15:** yes. In my r3 probe, a row without `identity` whose destination holds the output used to stop the engine from starting. Now the engine starts, the book needs attention with the damaged-record reason, and `confirm_move` returns None. R1, which drops `identity` from `_SHAPE`, is caught at startup and before an attempt. **F16:** yes. A NULL-`job_id` row no longer touches other books. The intact book restarts, and its edit is undone to the original. I also tried other key shapes. An integer key is stored as text (the column has TEXT affinity) and settles normally. A BLOB `attempt_id` is damaged on its own book only. A BLOB `job_id` is an orphan, like NULL. R2–R6 (each `_keyed` clause) are all caught. **F17:** yes, for its case. A renamed folder now reads "The edited original is missing…" at starts 1, 2 and 3, and again after Start. R7 (the folder test back) is caught. **F20:** yes. Q9b, which survived on 2026-10-23, is now caught by `ServiceTests` and by 34 matrix subtests. **m-3:** yes, for the in-process undo, a crash after the removal, and a 0.21.0 row. An 8192-byte marker is edited and restored exactly, both in process and after a crash. Markers of 8193 and 0 bytes fall back before any journal row, with the file unchanged. R8–R12 are caught, but R13 is not (F25). **m-4:** yes. R14, R14b, R14c and R15 are all caught. **r3 probes re-run:** torn tails still roll back to the original. The four F3 re-check cases are unchanged: two undone to the original, two refused and left untouched. `_intent` refuses no real row at any of the six fault points, or when published. My r3 "offline" probes hid the book folder, not the root, so they now read as missing, as they should. I re-ran the share race with the root hidden: `before_append` is edited again and published, `type_patched` is refused and then undone, the same safe outcomes as r3. |
| 2a | `zone_marker`: damaged or oversized, the mtime order, the 8 KiB limit, 0.21.0 rows | **Damaged or oversized:** an oversized value, text that is not base64, an empty string, and base64 with whitespace are each damaged, and nothing is written. Three other values pass the shape check and are written back as a marker that is not the original: 8192 bytes that are not an INI marker, a valid `ZoneId=0` marker, and a bit-flipped copy of the real one (F22). `CREATE_NEW` never writes over an existing stream. **The mtime order:** the marker is put back before the write time is restored. The baseline's `ZONE_FIXTURE_FACTS` shows that writing a stream moves the base file's write time, and R9, which swaps the order, is caught by 33 failures. A *failed* restore does leave the write time unrestored (F21). **The 8 KiB limit:** it holds at both ends, see item 1. **0.21.0 rows:** the marker is taken from the removal receipt (the matrix's "zone_marker missing" case and the legacy test). With a wrong receipt hash, no marker is put back, as designed. Closed 0.21.0 rows are never revisited (F24). |
| 2b | F17: can a live NAS read as missing? Can a missing folder lead to a deletion? | **A slow NAS:** a slow lookup blocks; it does not fail. **A failing lookup does:** `os.path.lexists` answers False for any `OSError`. With the root visible and both lookups failing (error 64), the book needs attention with "missing", and its edit is not undone. A separate output root that is out of sight after the rename gives the same result. Retry, or the next `clear()`, settles both: one rolled back, one `published` (F23). **Deletion:** none. I renamed a book folder next to a sibling folder, then ran startup, Retry and source cleanup. A file-and-stream tree compare shows no path removed or changed. Cleanup refuses with "receipt is missing", and Retry is refused until the folder is back. |
| 2c | Do legitimate 0.21.0 receipts pass the new `identity` check? | **Yes.** Only two writers put a `rename` into the journal: `merge_service.py:2695` (the native receipt) and `_prove_move` (the recovered one). Both take `identity` from `VerifiedFile.facts()`, which is `[volume, index_high, index_low]` as DWORDs and refuses zero. A real native receipt (`[2803554832, 2555904, 7344210]`) and a recovered one both pass `_identity`. `published_move` accepts the native receipt on its own, with `confirm_move` patched to fail. I did not read the live DB (excluded); this answer rests on the code and on real receipts from the scratch copy. |
| 2d | Does the matrix derive its keys from the writer? | **Yes.** `key_paths` walks a row the edit really wrote, and I counted 153 + 304 = 457 subtests. Three writer mutants test the claim. W1 adds `'senua_field': 1` to the intent without listing it: it fails at startup, at the attempt and at cleanup, for both the missing and the wrong-type case. W2 lists the field with an accept-anything validator: it fails on the wrong-type cases. W3 lists it as `_count` and passes, the positive control. One limit: the matrix only deletes keys or changes their type, never their value (F25). |
| 3 | Are the tests real? | **Mostly.** Of 59 mutants, 50 are caught, and the positive control W3 passes. Every r3 mutant that was caught then is still caught, and Q9b is now caught too. The 9 survivors are: N2, N11 and R21 (identity and sign clauses the content proof already covers, so not gaps); P2 and P3 (F18, carried); and R13, R16, R17 and R18 (F25). See the table under Evidence. |

## Rubric

### 1. Security

- Status: Pass. The one new write is the literal `:Zone.Identifier` stream of the held original. It is created new and never written over an existing stream, and its bytes come from the user's own journal. A restored marker can only add the download mark back, never remove one. There is no new shell-out, IPC, Electron change or secret.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **F23 [Minor]** `inplace_m4b.py:513`, `:517`, `:519`. F17's offline test still infers "missing" from failed lookups.
    - **Any error reads as absent:** `os.path.lexists` returns False for any `OSError`, not only "not found". Take a live share that fails both lookups (a dropped SMB session, a timeout) and then answers `isdir(root)`. The probe gives needs attention with "The edited original is missing and its destination does not hold it", and the edit is not undone.
    - **Only the source root is tested:** after the rename the book lives under `output_root`, which can be another folder. Probe: the output root is out of sight after a kill between the rename and its receipt. The result is the same false "missing". Once the output root is back, `clear()` records `published`.
    - **Cost:** nothing is written or deleted, and one Retry settles both cases. 0.21.0's folder test had the same class of error, so this is a residual, not a regression.
    - **Fix:** decide absence with `os.lstat`, and treat only `FileNotFoundError` as absent. Any other `OSError` means offline. Also test the destination's root, from a journaled `output_root` or the destination's nearest existing ancestor.
  - **F8 [Minor], carried, still open.** `merge_service.py:2685-2686` is unchanged.

### 3. Crash / Stability Safety

- Status: Concerns
- Findings:
  - **F21 [Minor]** `inplace_m4b.py:309`, `:315-319`, `zone_identifier.py:113-136`, `Design:117`. The marker step can leave an undo half done, or leave a torn marker for good.
    - **The restore fails:** `restore_marker` runs after the truncate and the type revert, and before `restore_metadata`. If it raises, the write time and attributes are not restored.
      - Probe, with `restore_marker` refusing: recovery records `unresolved` ("Cannot restore the download marker"). The bytes are the original, the write time is not, and there is no marker. The in-process undo leaves the same state.
      - The next start that can create the stream finishes the undo, and the file is exactly the original.
      - Where the stream can never be created, the book stays in needs attention with the wrong write time. 0.21.0 finished the same undo, just without the marker. CHANGELOG:15 promises a record "is left as it is … instead of being half undone".
    - **A torn restore:** a crash inside `restore_marker` leaves an empty stream, if it lands after `CREATE_NEW` created the stream and before `WriteFile` filled it.
      - Recovery reads that as "a marker still present" and leaves it: `rolled_back`, marker `b''`. The post-check never looks at the marker, so the row closes as an exact undo.
      - After that, the in-place path falls back with "Unknown download marker size preserved", and the copy flow's read admission refuses the book with the same text. The book cannot be processed until someone removes the empty stream by hand.
    - **Not measured on the share:** `restore_marker`, and the new read of the marker through Python `open()` while the writer is held (`:267-268`), have only run on local NTFS. A refused read falls back safely before any write. A refused restore is the first case above.
    - **Severity:** Minor. No audio byte is at risk. The first case heals itself where the stream can be created. The second needs a crash in a window of microseconds inside an undo that only runs after a failure.
    - **Fix:**
      - Restore the write time and attributes even when the marker step fails (`try`/`finally` around `restore_marker`, then raise).
      - When the detail holds the removal receipt and the marker on the file differs from the journaled bytes, treat it as an unfinished restore: replace it, or leave the row `unresolved` with a marker reason, never `rolled_back`.
      - Have Futaba measure one marked undo on the library share.

### 4. Performance

- Status: Pass. A marked edit reads one marker of at most 8 KiB. An undo with a marker lists the streams once. The offline test costs the same as before.

### 5. State & Data Safety

- Status: Concerns
- Findings:
  - **F22 [Minor]** `inplace_m4b.py:99-107`, `:117`, `:308`, compared with `:144`. A 0.21.1 row's marker bytes are written back on shape alone: valid base64 of 1 to 8192 bytes.
    - **The gap:** the 0.21.0 path checks the bytes against the receipt's `marker_sha256`. The new path does not, although the same receipt is in the detail whenever the edit removed a marker.
    - **Probe:** I gave three intents a different marker: a bit-flipped copy of the real one, a valid `ZoneId=0` marker, and 8192 bytes of `x`. Each was `rolled_back` with exact bytes and write time, and with a marker that is not the original. A marker that is not INI then refuses the book at the copy flow's read admission, as in F21.
    - **Why it matters:** this is the one intent value the undo writes to disk without a proof. `Design:121` ("every value the undo uses is checked before its first write") holds for its shape only.
    - **Reach:** only a damaged or hand-edited journal.
    - **Fix:** when the detail holds the removal receipt, require the intent's marker to hash to its `marker_sha256`, else treat the row as damaged. Alternatively, journal the hash in the intent and check it in `_SHAPE`.
  - **F6 [Minor], carried, attribute half still open.** The undo's post-check (`inplace_m4b.py:319`) compares size, write time and hash, but not attributes. The marker half is closed by m-3.
  - **F10 [Minor], carried, still open.** `inplace_m4b.py:62-63`: the journal still does not assert synchronous FULL.
  - **File deletes:** this range adds none. The F17 probe confirms that a missing book folder leads to no removal (Focus 2b).

### 6. Input Handling

- Status: Pass. `_SHAPE` now checks every field the writer writes, by value as well as by type, and `_keyed` checks the key columns. The remaining gaps are F22 (marker content, under 5) and F25 (untested value checks, under 9).

### 7. Maintainability (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **F9 [Minor], carried, still open.** `inplace_m4b.py:208` still turns `KeyError`/`TypeError` before the first write into a silent fallback. `merge_service.py:2677` still has its `hasattr` for test fakes.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **F24 [Minor]** `CHANGELOG.md:14`: "Edits recorded by 0.21.0 get their marker back too."
    - **What is true:** only the edits 0.21.0 left open get it back, because recovery reads open rows only.
    - **What is not:** an in-process 0.21.0 undo after the marker removal (Futaba's repro B) closed its row `rolled_back` without the marker. Its bytes are still in that row's detail, and 0.21.1 never revisits it. v0.21.0 is tagged and was accepted against an installer, so such rows can exist.
    - **Also overstated:** `Design:121` (see F21 and F22).
    - **Fix:** reword it to "interrupted edits 0.21.0 left open". Whether to restore markers for closed rows is a product call.
  - **F11 [Minor], carried, still open.** `inplace_m4b.py:213` still says "None for the unchanged copy flow".

### 9. Build & Release Hygiene

- Status: Concerns
- Findings:
  - **F25 [Minor]** `tests/test_inplace_m4b.py:630-640` (`damaged`) and `:390`. The matrix deletes keys and changes their type; it never changes a value. Four value checks the commit adds can be removed with the whole suite green:
    - **R17:** `_marker_bytes` without its size bound. I ran my marker probe on this mutant. An oversized or an empty marker then passes `_SHAPE`, and the undo cuts the file before `restore_marker` refuses the size. The result is `unresolved`, with the bytes restored and the write time not. That is exactly m-4's failure, for the field this commit adds.
    - **R16:** `_marker` without its size bound at the edit. An empty or oversized marker then gets journaled. My probe shows the real code falls back before any journal row; no test needs it to.
    - **R13:** `_legacy_marker` without its hash check. This is the marker's only content proof (see F22).
    - **R18:** `_path` without `ordinary()`. A relative `root` would then be tested against the current directory.
    - **Fix:** add value cases next to the m-4 test: a marker that is oversized, empty, or does not match its receipt hash, and a relative or stream-shaped path, root and destination. Add one edit of a marked source with a 0-byte and an 8193-byte marker that expects a fallback with no journal row.
  - **F18 [Minor], carried, still open.** `tests/test_inplace_m4b.py:812`, `:858-887`, `:904` are unchanged. P2 (a `try`/`except` gate) and P3 (a gate inside `verify_candidate`) still pass the parity test.
  - **F19 [Minor], carried, outside the range.** `scripts/release-contract.mjs:73` is unchanged. This file's name was free, so nothing is overwritten.
- Verified, no finding:
  - **Gate:** gate run 2 (`ba-0.21.1-check-run2-f64d46b.log`) starts with `HEAD f64d46b… dirty-files 0`. It ends with `BOOKS_INTEGRATED_CHECKS_PASS`: 1278 Python cases (1274 + the 4 new in-place tests) and 57 Node, with 0 skipped. `test_inplace_m4b.py` is still in `scripts/check-desktop.mjs:40`.
  - **My baseline:** 98/98 on the scratch copy (`r4-baseline.log`): `test_inplace_m4b` 40, `test_zone_identifier` 13, `test_cleanup_resume` 23, `test_attention_audio_admission` 10, `test_source_proofs` 6, `test_standing_admission` 6.
  - **Version:** `package.json`, `package-lock.json` and the CHANGELOG heading all read 0.21.1. `scripts/` is untouched.
  - **Manifest:** see the header.
  - **Attribution:** f64d46b has no Claude attribution.

## Patterns

The r3 pattern is fixed at the level it named: the key list now comes from the writer, and W1–W3 prove it. It returns one level down. The matrix generates its damage from the row's *shape* (delete a key, change its type), so the checks that judge *values* (sizes, bounds, hashes, path form) are covered only where someone wrote a case by hand. For the new marker field, nobody did (F25). A generated test reaches only as far as its generator.

## Evidence

**Setup:**
- All runs used `git archive f64d46b` copies under the short path `C:/Users/AnGeLZzZ/AppData/Local/Temp/sn21/r4/`: `base` for the baseline, `p4` for the probes, and one folder per mutant.
- The runtime was the worktree's build-cache runtime `c3d7d82c…` (Python 3.14.8, SQLite 3.50.4, its FFmpeg), with the same fixture-root mapping as `check-desktop.mjs`.
- Nothing ran in the worktree, the live DB, Z:, the installed app or `dist/`, except a read-only hash and parse of `release-artifacts.json`. This report is the only file written in the worktree, and it is uncommitted.

**Logs and sources** are in `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/64106cea-b39e-4987-9571-6ad97339dc8a/scratchpad/shared/senua-0210/`:
- **Baseline:** `r4-baseline.log`, 98/98.
- **r2 and r3 probes re-run:** `r4-probe-r2.log` and `r4-probe-r3.log`. The r3 run has two errors in the share-race probe: it hides the book folder, which now reads as missing, as it should. `RootRace` repeats that probe with the root hidden.
- **New probes:** `test_senua_r4_probes.py`, logged in four files:
  - `r4-probe.log`: marker variants, the torn restore, a failed restore, a 0.21.0 receipt with a wrong hash, F16 key shapes, F17 transient errors and the deletion tree compare, receipt identities;
  - `r4-probe-bounds.log`: markers of 8192, 8193 and 0 bytes;
  - `r4-probe-race.log`: the share race, with the root hidden;
  - `r4-probe-outroot.log`: the output root out of sight.
- **R17 impact:** `r4-probe-R17.log`, the marker probe run on the R17 mutant.
- **Matrix count:** `r4-runner-count.py`, logged in `r4-subtests.log` (153 + 304 = 457).
- **Mutations:** `r4-mutate.py` (it reuses r3's table for the carried mutants), `r4-run-mutations.sh`, one `r4-mut-<name>.log` per mutant, and `r4-summarize.sh`. Each mutant changes one clause, or one field for W1–W3, and was run on `test_inplace_m4b`, `test_source_proofs` and `test_standing_admission`.

| Mutation | What it breaks | Result |
|---|---|---|
| r3's carried set: M1, M2, M4, M5, M6, M7, M9, N0, N1r, N3–N10, Q1–Q8, Q9, Q10–Q13 (Q1–Q3, Q5, Q8, Q11, Q12 re-targeted at the new text) | As in the 2026-10-24 report | All 30 caught, as on 2026-10-23 |
| N2, N11 | Identity clauses of the in-process undo | Survive, as before. The content proof refuses every rewrite; not a gap |
| P2, P3 | Parity-test blind spots | **Survive** (F18, carried) |
| Q9b | `published_move` rejects only the native receipt | **Caught now** (survived on 2026-10-23): `ServiceTests` and 34 matrix subtests (F20 closed) |
| R1 | Drops `identity` from `_SHAPE` (F15) | Caught: 5 matrix subtests, at startup and at the attempt |
| R2 | `reconcile` without the `_keyed` pre-check (F16) | Caught: 6 matrix subtests |
| R3 | `reconcile` records an unkeyed row (F16's original bug) | Caught: 106 matrix subtests |
| R4 | `unresolved()` stops reporting unkeyed rows | Caught: 2 matrix subtests |
| R5 | `published_move` without `_keyed` | Caught: 1 matrix subtest |
| R6 | `confirm_move` without `_keyed` | Caught: 2 matrix subtests |
| R7 | F17 revert: the folder test instead of the root test | Caught: `test_startup_leaves_an_edit_open_only_while_its_library_root_cannot_be_seen` |
| R8 | Drops the marker restore (m-3) | Caught: the marker test and 32 matrix subtests |
| R9 | Restores the marker after the write time | Caught: the marker test and 32 matrix subtests |
| R10 | Restores the marker even when one is present | Caught: the marker test |
| R11 | Drops the "marker changed" check in `persist` | Caught: the marker test |
| R12 | No legacy marker from the 0.21.0 receipt | Caught: the marker test and 2 matrix subtests |
| R13 | `_legacy_marker` without its hash check | **Survives** (F25) |
| R14, R14b, R14c | `_write_time` by type only, without whole ticks, without its range (m-4) | Each caught by the m-4 test |
| R15 | `_attributes` by type only (m-4) | Caught: the m-4 test |
| R16 | `_marker` without its size bound at the edit | **Survives** (F25) |
| R17 | `_marker_bytes` without its size bound | **Survives** (F25); m-4's failure comes back (`r4-probe-R17.log`) |
| R18 | `_path` without `ordinary()` | **Survives** (F25) |
| R19 | `published_move` checks only that `identity` is present | Caught: 1 matrix subtest (retired identity `'x'`) |
| R21 | `_count` accepts negative values | Survives. A negative size or offset fails the content proof before any write; not a gap |
| W1 | Writer adds an unlisted intent field | Caught: 10 subtests, missing and wrong type, at startup, attempt and cleanup |
| W2 | W1, with the field listed but accepting any value | Caught: 5 subtests (wrong type) |
| W3 | W1, with the field listed as `_count` (positive control) | Passes, as it must |

**Totals:** 59 mutants plus the positive control W3. 50 are caught and 9 survive. N2, N11 and R21 are not gaps. P2 and P3 are F18. R13, R16, R17 and R18 are F25.

## Verdict

- Total Critical: 0
- Total Major: 0
- Total Minor: 12 (F21, F22, F23, F24 and F25 new; F6 attribute half, F8, F9, F10, F11, F18 and F19 carried)

No safety-floor item: no unsafe Electron config, no secret leakage and no source-of-truth destruction. The new marker write touches only the held original's own `Zone.Identifier` stream, as the undo the design approves.

**Verdict:** RELEASE CLEAR

| # | Sev | Dim | file:line | Finding | Next cycle |
|---|-----|-----|-----------|---------|------------|
| F21 | Minor | 3 Stability | `inplace_m4b.py:315-319`, `zone_identifier.py:113` | A failed marker restore leaves the write time and attributes unrestored; a torn restore (empty stream) is kept as "present" and blocks the book; never run on the share | Restore metadata in a `finally`; treat a marker that differs from the receipt as an unfinished restore; measure on the share |
| F22 | Minor | 5 Data safety | `inplace_m4b.py:99-107`, `:117`, `:308` | 0.21.1 marker bytes are written back on shape alone; a damaged intent writes a marker that is not the original | Check the bytes against the receipt's `marker_sha256` |
| F23 | Minor | 2 Correctness | `inplace_m4b.py:513`, `:517`, `:519` | `lexists` turns any lookup error into "absent", and only the source root is tested; a false "missing" lasts until Retry | `os.lstat` with `FileNotFoundError` only; test the destination's root too |
| F24 | Minor | 8 Drift | `CHANGELOG.md:14`, `Design:121` | "Edits recorded by 0.21.0 get their marker back" holds only for open rows | Reword it; restoring closed rows is a product call |
| F25 | Minor | 9 Hygiene | `tests/test_inplace_m4b.py:630`, `:390` | The matrix varies type, never value; R13, R16, R17 and R18 survive, and R17 brings back m-4's failure for the marker | Add value cases for the marker bounds and hash, and for path form |
| F6 | Minor | 5 Data safety | `inplace_m4b.py:319` | Post-undo check does not compare attributes (the marker half is closed) | Carried |
| F8 | Minor | 2 Correctness | `merge_service.py:2685` | Publication intent committed before the locked guard | Carried |
| F9 | Minor | 7 Maintainability | `inplace_m4b.py:208` | `KeyError`/`TypeError` before the first write become silent fallbacks | Carried |
| F10 | Minor | 5 Data safety | `inplace_m4b.py:62` | The journal does not assert synchronous FULL | Carried |
| F11 | Minor | 8 Drift | `inplace_m4b.py:213` | One docstring still says "unchanged copy flow" | Carried |
| F18 | Minor | 9 Hygiene | `tests/test_inplace_m4b.py:858` | Parity test blind spots (P2 and P3 survive) | Carried |
| F19 | Minor | 9 Hygiene | `scripts/release-contract.mjs:73` | One acceptance report per version per date | Carried |

Closed in this range: F15, F16, F17 (its stated case), F20, and Futaba's m-3 and m-4.
