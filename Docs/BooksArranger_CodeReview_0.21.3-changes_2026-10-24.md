# Code Review findings — Books Arranger, the 0.21.3 changes (input to the 0.22.0 review)

**Not a release clearance.** Sergei cancelled the 0.21.3 release on 2026-10-24, and its changes fold into 0.22.0. This file records my code findings on that range so Ender can fix them on `ender/0220`. The 0.22.0 review carries the verdict. This file has no verdict line, and the release gate must not read it as one.

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-24
Tool: Books Arranger
Release: none (0.21.3 cancelled; folds into 0.22.0)
Commit range: v0.21.2 (b467308)..d0e6962 (origin/main)
Files changed: 53 files, +2568 / -104 (git diff --shortstat). Product code: 13 files, +195 / -52
  (source_cleanup.py +50/-2, merge_service.py +30/-8, series_backfill.py +23/-3, source_config.py +21,
  m4b_preservation.py +18/-5, review_backend.py +17/-21, automatic_processing.py +13/-1, web/app.js +8/-5,
  scanner.py +7/-3, storage_cleanup.py +3/-1, groups.py +2/-2, two gate scripts +3/-1).
  Tests: 31 files, +600 / -49. Docs and CHANGELOG: 7 files, +1770. package.json and package-lock.json: version only.
Stand-down dimensions: none
```

Commits: 5f22c96 (zero udta box), 3432897 (F31), a32c81f (gone files), 0f1a0db (C2), ac7ebca (m1), 58e0383 (m2), 36b3613 (m3), fedd08c (m4), 6756158 (m5), d7237f3 (M1), 033cb23 and a82a6e6 (docs), d0e6962 (version bump).

Rulings checked against: `Team/Docs/BooksArranger_Rulings_2026-10-24.md`, items 2 (delete only when the verified result is in Sorted), 1a (a book that isn't done stays unchanged), 2b (the in-place M4B exemption) and 3 (the zero box, audio proven identical).

---

## Summary

This range closes my delete-path audit (`Docs/BooksArranger_DeletePaths_Audit_2026-10-24.md`), admits the Макс Фрай zero udta box, removes the converted-set reads from the converter and the approval (F31), and stops counting gone files as read errors. I read every product hunk, traced each new check to its callers, ran the suites on a detached worktree, ran 20 mutants against the new safety code, and probed the production wiring against the live configuration (read-only).

**Answers to the four questions.**

1. **The audit fixes close what I found, and none deletes too early.** One new path parks a cleanup for good (F1, Major): a cleanup refused because the process has no output folder stays in Needs attention after the setting is back, and nothing ever runs it again. Sources are kept, so rulings 2 and 1a hold. It cannot happen in the installed setup with a valid `audiobook-sources.json`. m3 and m4 are each closed only in part (F4, F5). The guard that keeps the in-place edit out of non-Sorted destinations works, but no test covers it (F8).
2. **The zero-box admission is narrow enough.** It takes exactly one box, directly in `moov/udta`, with an 8-byte header, and every byte after the size field must be zero, the type included. Such a box carries no information. It is never copied into the new `moov`, while `mdat` and every chunk offset stay where they were. Near-misses are refused and the mutants are caught.
3. **The F31 removal is safe.** Server-side, only the inspector reads `audiobook_ready` (`merge_service.py:3008`), and it still computes it. Nothing that builds or guards a job reads it. The one side effect the old read had, `synchronize_groups`, still runs in every `build_manifest` through `_row` → `Inventory.candidate` → `groups.sync`.
4. **"Gone" marking does not hide a real read error.** A file is marked gone only in `complete()`, when the scan generation finished with `errors == 0` (`scanner.py:285-290`). An offline root ends as `offline`, a failed listing or read adds to `errors` (`scanner.py:306-313`), and a stopped scan never reaches `complete()`. A gone member still blocks creation (`groups.py:192`). Only the display and the count changed.

---

## Rubric

### 1. Security

- Status: Pass
- Findings: none. Nothing new shells out. The only new delete is the series-backfill temp file, which now goes through a held single-link handle and a fixed name check (`series_backfill.py:677-688`). Nothing under `desktop/` changed, and no secrets are in the diff (grep for key, token and password patterns).

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **F1 [Major]** `source_cleanup.py:312-313`, `merge_service.py:363-372`, `merge_service.py:945,954`. **A cleanup refused by the new rule is parked for good.**
    - What happens: when `require_sorted` refuses a cleanup, `hold()` sets the cleanup to `needs_attention` with the refusal text. `_work` re-runs only three fixed reasons, `_finish_held_cleanups` only the two `HELD_FOR_METADATA` reasons, and no code path or UI action ever sets such a cleanup back to `waiting` or `paused`. A grep of `UPDATE source_cleanup SET` finds four writers: the startup pause, `LEGACY_BUSY`, `hold` and `_set`.
    - **Trigger 1.** Starting with no output folder (a repo launcher, a missing `audiobook-sources.json`, or any `--roots-json` launch), then Resume. Retry, Repair and Confirm-and-convert also count, because they call `merge.resume()` directly (`web_server.py:602`, `merge_service.py:1612-1687`) and skip the automatic-processing Start block. Any waiting or paused cleanup is then refused and parked.
    - **Trigger 2.** The same kind of launch while a book has completed but is not yet enrolled. `_enroll_completed_without_start` runs at construction and writes a `needs_attention` row with an empty binding (`_enrollment_attention`).
    - **Proof.** I ran a probe in a copy of the review tree (`CleanupTest` fixture):
      - Run with no output folder: `needs_attention | No sorted output folder is set; the source files are kept`.
      - Setting restored, then a `_work` pass: still `needs_attention`, 0 removed.
      - Control: the same row reset to `waiting` by hand completes, 2 removed.
    - **Impact.** No loss: the sources stay, as rulings 2 and 1a require. The book's cleanup never runs again, though, and Needs attention keeps showing a reason that is no longer true.
    - **Fix (Ender's choice).** Either make the three `require_sorted` reasons retryable in `_work`, or refuse `merge.resume()` and skip startup enrolment while `sorted_problem()` is non-empty, so nothing gets parked.
  - **F2 [Minor]** `source_cleanup.py:441-449`, `source_cleanup.py:494-503`. The new per-disposal checks (`_sorted` and the m1 re-read) run after `removal_intended` is committed. If either refuses, the original is still present while its member reads `removal_intended`. `restore()` treats that member as a collision (`Restore collision; existing file preserved`) and stops, even though nothing needed restoring. This widens an edge that already existed (an `output_location_guard` refusal at the same point does the same). Both checks are pure reads, so they can also run before the intent commit.

### 3. Crash / Stability Safety

- Status: Concerns
- Findings:
  - **F3 [Minor]** `source_config.py:15-19`, `automatic_processing.py:199-219`. `contains()` catches only `ValueError`. `os.path.realpath` raises `OSError` for network errors outside ntpath's allowed list (bundled Python 3.14 `ntpath.py:626`; for example 59, 64, 121 and 1201). Since 0.21.3, `_start_block` calls `sorted_problem` on every uncached `/api/state`: about 16 `realpath` calls on Z:, 12.5 to 13.3 ms in total on a healthy NAS (measured, read-only). During an outage of that kind, the state poll can raise instead of answering. Not reproduced, because only Z: is mapped here. Fix: in this status path, treat an `OSError` as "output folder unavailable", which fails safe.

### 4. Performance

- Status: Pass
- Findings: none.
  - F31: Ender's Brief measures converter reads per book going from 4 to 0, and approval reads from 1 to 0, with 194 instead of 138 books in a 3000 s run.
  - The new policy reads add about 13 ms to an uncached state poll (see F3).
  - m5 adds one full hash of a recovery child's output, a rare path.

### 5. State & Data Safety

- Status: Concerns
- Findings:
  - **The C2 closure holds.**
    - Enrolment, run start and each disposal all check the effective output, after any relocation binding, against the configured folder, and read that folder live each time.
    - The run-start check comes before any recovery copy or marker change.
    - The in-place session is created, and its rename made, only for a destination in Sorted (`merge_service.py:2742-2743, 2785-2786`), so ruling 2b's exemption cannot reach outside Sorted.
    - Production wiring probe, with a real `Inventory` holding the live path strings, the real `MergeService.output_policy`, and a scratch catalog:
      - Policy: `Z:\Audiobooks Sorted` plus four roots; `sorted_problem` returns `''`.
      - Admitted: `Z:\Audiobooks Sorted\Author\Book.m4b`.
      - Refused: `Z:\Audiobooks\Unsorted\…`, `Z:\OLD_Audiobooks\…` and the prefix trap `Z:\Audiobooks Sorted Old\…`.
      - No output folder: refused with "No sorted output folder is set".
  - **m1, m2 and m5 are closed.**
    - m1: the output is re-read through the held handle (size, links, identity) and its path must still exist, before every disposal.
    - m2: a direct child of a source root is never a candidate. This also means a book folder directly under a root, such as `Z:\OLD_Audiobooks\<Book>`, is never removed. That is conservative, and on Z: folder removal refuses anyway (named streams).
    - m5: `protected_output` hashes the child's output in full and holds it.
  - **F4 [Minor]** `source_cleanup.py:333-357, 416`. m3 is closed for a pause or a hold. A marker removed by a run that is then killed (crash or power loss) is never put back: the next run lists only markers it removed itself, and the old receipt stays in `source_zone_marker_intents` unused. This affects a done book, and only a metadata stream.
  - **F5 [Minor]** `series_backfill.py:376-393`. m4 is closed only in part. The pathname delete and the source-folder writes are gone. Naming is still relative to `manifest['root']`, the source root, so every book in Sorted fails "name does not follow" and the feature stays silently off. The Brief records this as deferred to Sergei; see F7 for the changelog wording.
  - The safety floor is intact: no new path writes outside its boundary, and nothing deletes a source before its verified result is in Sorted.

### 6. Input Handling

- Status: Pass
- Findings: none. `udta_padding` takes one box (`blank()`: header 8, every byte after the size field zero) and drops it from the new `moov`. A box with a 64-bit header, a second zero box, a non-zero byte, an unknown type, or a zero box anywhere else is refused. The boxes tile their parent exactly (`boxes()`), so a blank box cannot overlap real data. `test_inplace_m4b` decodes the source and both paths' outputs to f32 PCM and compares their SHA-256 (ruling 3).

### 7. Maintainability (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **F6 [Minor]** `tests/sorted_fixture.py:20-28`. 22 test modules replace `MergeService.output_policy` with "this library is the output folder, no sources", so no gate test runs the production `output_policy` or a full convert-then-cleanup with a separate Sorted folder. My probe above confirms the wiring today. One integration test with `Inventory(output_root=<separate folder>)` through conversion and cleanup would keep it confirmed.
  - **F8 [Minor]** `merge_service.py:2742-2744`. The guard that keeps the in-place edit away from destinations outside Sorted has no test. The mutant that admits the session anyway survives both suites, because the module-wide fixture (F6) always counts the library as Sorted. Without the guard, a not-done original would be edited and then undone by the publish-time check (`merge_service.py:2785`). That is a ruling 1a regression no test would see, and if the undo cannot run it becomes C1's residual. Add a test with a destination outside the output folder that asserts the copy flow ran and the original's bytes and `inplace_edits` were never touched.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **F7 [Minor]** `CHANGELOG.md:14`. "series backfill works only in the Sorted folder" reads as if it works there. It renames nothing anywhere (F5); the Brief says so correctly.

### 9. Build & Release Hygiene

- Status: Pass
- Findings: none.
  - The version is bumped in `package.json` and `package-lock.json` (both fields).
  - `M1`: the four source-removal suites are in the gate, and the stale `test_cleanup_scope` assertion is fixed.
  - No commit in the range carries a Claude attribution trailer.
  - **Cancelled build (not certified).** Before the cancellation I read `cand-0213/dist/release-artifacts.json`, read-only:
    - Version 0.21.3 and source d0e6962 match.
    - The installer's recomputed SHA-256 equals the manifest's.
    - All 75 shipped backend files are byte-identical to d0e6962.

    That build will not ship, so this file deliberately carries no manifest line. 0.22.0 needs its own check.

---

## Tests run

All on a detached worktree of d0e6962 at `C:/Antigravity Projects/Worktrees/Books Arranger/review-0213`, never in `WIP/`. Runtime: system Python 3.14.9 and WinGet FFmpeg 8.1.1, not the gate's pinned runtime (none on this machine).

| Run | Result |
| --- | --- |
| Every Python module in `scripts/check-desktop.mjs` (88 patterns), with the gate's own discovery and fixture-root map, one process | 1373 run, 0 failures, 0 errors, 1 skipped, 1094 s. The skip is most likely `ActualPrivateStagingTests`, which needs the `BOOKS_MP3_REAL_FIXTURE` opt-in; every other skip condition holds here |
| `node --test`, the 10 gate node suites | 63 pass, 0 skipped |
| `tests/test_*.js`, 18 frontend scripts | 18 pass |
| Probe for F1 (a copy of the tree, `CleanupTest` fixture) | Parked after the setting returned; the hand-reset control completed |
| Production wiring probe (real `Inventory` and `MergeService.output_policy`, live path strings, scratch catalog) | See dimension 5 |

## Mutants

20 mutants, applied one at a time to a copy of the tree. The named tests ran, then the file was restored. **19 caught, 1 survived.**

| Mutant | Caught by |
| --- | --- |
| C2 run-start check removed; per-disposal check removed; enrolment check removed | `test_source_cleanup` (2, 1 and 3 failures) |
| `require_sorted` overlap rule removed; containment rule removed; a missing policy admits | `test_source_cleanup` |
| m1 re-read removed; m3 put-back disabled | `test_source_cleanup` |
| m2 reverted | `test_source_folders` (4 failures) |
| m4 Sorted gate removed | `test_series_backfill` |
| m5 `protected_output` removed | `test_iron_skazka::…changed_child_output…` |
| In-place rename check removed | `test_inplace_m4b::…rename_outside_the_sorted…` |
| Start block `output` removed | `test_automatic_processing` |
| Zero box: two admitted; zero box kept in the new `moov` | `test_m4b_preservation -k zero_padding` |
| F31: `build_manifest` reads the set again | `test_automatic_media -k converted_set` |
| Gone: status count, candidates filter, Files filter each count gone files again | `test_groups_filters` |
| **`_run_media` offers the in-place session outside Sorted** (`merge_service.py:2743`) | **Survived** the whole of `test_inplace_m4b` (43) and `test_automatic_media` (10). See F8 |

---

## Patterns

Each refusal added to the delete paths ends in `needs_attention`, and `needs_attention` is terminal for source cleanup. That was acceptable while refusals meant "the files changed". It is not acceptable once a refusal can mean "this process was started without its configuration" (F1). The second recurring pattern is safety fixtures that bypass the rule they protect (F6, F8). Last cycle the same kind of gap showed up as suites missing from the gate (M1).

---

## Totals (no verdict: input to the 0.22.0 review)

- Critical: 0
- Major: 1 (F1)
- Minor: 7 (F2 to F8)

For Ender on `ender/0220`, F1 first. The 0.22.0 review re-checks F1 to F8 against the new range and gives the verdict there.

Not done: the quick check of Ender's adapted `qa-run-0213/assemble-entry-0213.mjs` (its fixture folder now points at a hash-checked copy). The cancellation arrived before I started it, and it belonged to the 0.21.3 release flow. If that change carries into 0.22.0, the 0.22.0 review should cover it.
