# Code Review — Books Arranger v0.31.0

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-23
Tool: Books Arranger
Release: v0.31.0
Commit range: v0.30.1 (50c4d4bbfd65733c215089c130d1c6ba0b8699a4)..a8b6804a013b643412c72aedf34f1e7e00de1455 (branch ender/0.31.0)
Files changed: 97 files, +27,965 / -1,122 in 76 commits (67 without merges); product code outside tests, Docs, *.md and *.json: 29 files, +5,267 / -551
Stand-down dimensions: none
```

Counts: `git diff --shortstat` and `git rev-list --count [--no-merges]` on the two endpoints. The previous review (v0.30.1) certified `2c7129f..f658d2e`; `f658d2e` is an ancestor of `v0.30.1`, and the only commit between them is `50c4d4b`, a docs record. Coverage is contiguous.

---

## Summary

0.31.0 makes the app rename and move finished audiobooks by its rules with no approval step (`rule_filing.py`). It writes English titles and ordered author credits into the files' tags (`name_write.py`, plus hooks in `series_backfill.py`). It adds Wikidata as a book source (`wikidata_books.py`) and one certain-or-doubtful rule (`series_certainty.py`). The look-ups are bounded, and the release brings an "all done" state.

I read the riskiest areas line by line:
- the pass, its guards and pacing;
- the write of names, its five steps and recovery;
- the publication-intent swap;
- the move-guard commit `436911b` and the series write's catalog step;
- `withdrawn_to_pending` and action-queue parking;
- the Wikidata and FantLab adapters;
- the schema additions.

I ran two probes against copies of the committed tree. They measured the two move windows directly.

**Construction verdict.** Nothing here can destroy audio. Every rewrite is proven before the old file goes, and every rename is no-replace. Both copies survive each race I could construct. The defects are in which books the rules act on, and in two windows where a Choose folder… press during an automatic write leaves a book the app can no longer locate.

### Tests run (targeted, lean verification)

All runs used the gate's pinned QA runtime. Its `python.exe` SHA-256 is `434b361f…` and its `ffprobe.exe` SHA-256 is `fe818a56…`, both matching `scripts/qa-runtime.json`. They ran in a `git archive a8b6804` copy under `I:/AI Projects/Worktrees/Books Arranger/senua-031-scratch/`, with TEMP in the copy's own scratch. Each run used the gate's own `support_dispositions(runroot/'scratch', [runroot/'scratch'])` wrapper, as `scripts/check-desktop.mjs` does. Counts are the runner's `testsRun`.

| Run | Modules | Result |
| --- | --- | --- |
| 1 | `test_name_write_031.py`, `test_rule_filing_names_031.py` | 37 tests, OK (66 s) |
| 2 | `test_rule_filing_031.py`, `test_series_write_guard_031.py`, `test_series_moves_031.py`, `test_series_lookup_ends_031.py`, `test_series_031.py`, `test_lookup_before_review_031.py`, `test_destination_clash.py` | 181 tests, OK (59 s) |
| 3 | `test_action_queue.py`, `test_finished_state_031.py` | 63 tests, OK (7 s) |
| Probe A | Senua's `test_senua_probe_031.py`: the name-write window (M1) with its control, and the series-write window (M2) | 3 cases ran; outputs quoted under M1 and M2 |
| Probe B | Senua's `probe_certain.py`: what the plan's re-judgment can see (M3), with a control | output quoted under M3 |

The full suite was not run here. It runs once, in Ender's entry check. The probe files were in the scratch folder and were deleted with it. Each finding below gives the method, so Ender can rebuild a probe from the fixtures in `test_name_write_031.py` and `test_rule_filing_names_031.py`.

---

## Rubric

Severity tags `[Critical]` / `[Major]` / `[Minor]` are defined in `Team/Docs/ProcessRules.md` § Severity definitions.

### 1. Security

- Status: Pass
- Findings: none.
  - Online answers are parsed defensively, with type checks and bounds: 10 search hits, 50 related ids, 60 statements and 30 aliases; names are capped at 500 characters and series names at 300.
  - Every external name reaches the disk through `metadata.safe_name`, which handles reserved names, `..` and separators.
  - The new routes `/api/filing/record` and `/api/filing/could-not` validate their input shape, the search length and the limit.
  - The page adds no `innerHTML`.
  - Nothing in `desktop/` changed: no Electron, preload or IPC surface was touched.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **[Major] M3 — series found before 0.31.0 are filed automatically on a re-judgment that cannot see the doubtful shapes.** `sorting_moves.py:250-262` (`certain`), applied at `sorting_moves.py:393`.
    - Books that 0.30.x held under `MOVE_WAITS` are never looked up again. Only `OLD_FOLDER_REASON` and `REVIEW_REASON` holds are reopened (`series_backfill.py:417`, `:680`). Ender's diagnosis counts 55 such books on the live copy.
    - Instead, the plan re-judges the stored record with `{'name','number','provider','source_url'}` and the title's volume only. It cannot see `several_series`, `universe` or a local contradiction.
    - Those are exactly the shapes the 0.30.1 adapters let through. Goodreads kept `series[0]` of a page that lists several series (`v0.30.1:public_research.py:1912`). FantLab had no universe/conditional-cycle check.
    - Probe B: `certain()` returns `true` for a 0.30.1-shaped Goodreads record. The 0.31.0 adapter's answer for the same page is `doubtful` (control). A stored `doubt` key is dropped by `certain()` as well (`true`).
    - Result: the rules rewrite these books' series tags and move them into the series folder, which is contrary to R18 ("if a result could be wrong, treat it as if nothing was found").
    - Fix direction: send pre-`series_certainty` `MOVE_WAITS` records back through the bounded look-up, as the two other legacy holds are, before the rules may approve them.
  - **[Minor] m3 — a doubtful source does not make the book doubtful; the next source still files it.** `series_backfill.py:757-766`.
    - In the finished-book look-up, a doubtful answer (for example Goodreads listing the book in two series) counts as that source answering "none". The look-up then goes on, and the next source's single series files the book.
    - That look-up also never cross-checks sources. `sources_disagree` is applied only before review, against Wikidata (`public_research.py`, `_gap_fill_once`).
    - This is a reading of R21 that Sergei should confirm (via Jane). It is not a code defect.
  - **[Minor] m4 — the 0.30.0 approval route bypasses the write of names.** `merge_service.py:6439-6443`.
    - `/api/sorting-moves/apply` is still served and used by `scripts/sorting_moves.py`. It approves series writes without names and moves a names item with a plain rename.
    - Such a book then counts as moved, and `sorting_moves.target` never plans names for a moved book. Its file name ends up English while its tags stay Russian, permanently.

### 3. Crash / Stability Safety

- Status: Concerns
- Findings:
  - **[Minor] m1 — stalled moves don't count against the two-book limit.** `rule_filing.py:567-568`.
    - A move left journaled for a restart (its retries ran out because the share dropped) is excluded from FEED, with no cap or back-off. On a network share that drops repeatedly, each drop can add up to two more unfinished moves.
    - Those moves stay in `left`, so the status reads `continues` while nothing runs until a restart. Both copies are kept, and recovery at the next start handles them.
  - **[Minor] m2 — a write that becomes blocked after dispatch holds its slot indefinitely.** `rule_filing.py:399-404`.
    - If a book's cleanup goes on hold after dispatch, its write becomes `blocked` (`name_write.py:443-444`; the series write is the same). The entry stays open and keeps its FEED slot.
    - Two such books stall the whole pass until Sergei clears those cleanups.
  - The pass, the name writer and the series writer otherwise contain their errors, and they are stopped in close order (`merge_service.py:5988`). Nothing found here can crash the app.

### 4. Performance

- Status: Pass
- Findings: none blocking. While books are left, the pass rebuilds the whole plan every 60 s: one manifest parse, two `propose()` calls and one move query per finished book, with `exists()` only on listed paths. The module's own run moved 300 fixture books in 41 s.

### 5. State & Data Safety

- Status: Concerns
- Findings:
  - **[Major] M1 — the `436911b` guard does not close the move window it was written for.** `name_write.py:575` and `book_move.py:538-589`.
    - The guard treats a move whose journal reads `queued` as "not begun". That is not true. `Mover._run` resolves the start (`book_move.py:538-541`) and hashes the whole held file (`:589`) while the journal still reads `queued`. Its first state write is at `:619` for a rename and `:668` for a copy.
    - On a network share, that hash takes seconds to minutes. Choose folder… stays enabled during an automatic write, because `web/app.js:4657-4663` disables it only for a queued or running move.
    - Probe A forced this sequence: the move's state was `queued` when the names catalog ran, so the guard let the English receipt commit. The old-file removal then hit `WinError 32` and the write was held. The move then completed from the old receipt.
    - The book now resolves to `ValueError: Moved audiobook history does not link to its publication`. Two copies sit on disk (`Mine\<old name>.m4b` and `<author>\White Nights Ghosts - ….m4b`), and the app cannot locate the book.
    - The control is the same sequence with the move past `queued`; the guard refused it, as `436911b`'s test asserts. No bytes are lost, but the catalog needs a hand repair.
    - Fix direction: also refuse when the move is running (`merge._move_running`), or have the Mover re-read the receipt inside the transaction that writes `rename_intent`/`copy_intent`, or refuse Choose folder… while a write of the book is in hand.
  - **[Major] M2 — the series write's catalog step has no move check at all.** This is the window Ender left open on purpose (`series_backfill.py:1145`).
    - Probe A forced this sequence: the series was written and renamed, and a Choose folder… move completed before the catalog step. The catalog then replaced the receipt.
    - Recovery held the book with "The former file is missing without a removal receipt". The book resolves to the same `ValueError` as in M1, and both copies are on disk.
    - The window predates this release (0.16.12). 0.31.0 changes its exposure: the rules now start series writes by themselves for every eligible finished book, and the window lasts the whole retag and proof time, minutes per book on the share.
    - It needs the same fix as M1, in the same place.
  - **[Minor] m6 — a write of names in flight at a rollback to 0.30.1 is never finished there.**
    - 0.30.1 has no reader for `name_writes`. A book caught in `written`, `renamed` or `cataloged` keeps a stray `.books-arranger-names-*.m4b` temp, or a second copy, in its author folder until 0.31.0 runs again and resumes it.
    - A completed write needs nothing: 0.30.1 reads it as an ordinary publication, because `publication_locations.py`, `publication_binding.py`, `audio_jobs.py` and `native_io.py` are byte-identical between the endpoints, so the rollback test runs 0.30.1's own readers.
  - **Verified sound:**
    - A write is proven before the old file goes: media and sample tables byte-identical, packet hash, decoder configuration, chapters, streams, and every other tag read back unchanged (inherited `_write`, plus `check`).
    - A kill between any two steps resumes (five child-process kill tests).
    - The publication-intent swap keeps the first intent once, as `publication_intent_before_names`.
    - The old file is disposed through a held, hash-checked handle only after the catalog commit.
    - Every rename and publish is no-replace.
    - Choose folder… remains his (R26), keyed on `override_id`, which has existed since 0.24.0.
    - Schema: `rule_filings.written`, `name_writes` and `book_moves.origin` are all `IF NOT EXISTS` or additive `ALTER`. 0.30.1 reads by column name (`sqlite3.Row`, named INSERT columns), so an older build's catalog survives in both directions.
    - `withdrawn_to_pending` keeps what the next reading needs, acts only on records without `LOCAL_RECHECK`, and is idempotent.
    - Parking holds the rules' moves under a Pause and lets his presses run.

### 6. Input Handling

- Status: Pass
- Findings: none.
  - A Wikidata match needs the title, every credited author and a written-work type, and excludes editions (P629). Two fitting works are a conflict, never a guess.
  - The FantLab cycle, search and work ids are bounded.
  - Retry limits hold: three tries per source, at least 10 minutes and at most 6 hours apart before review, with a 12-hour cap per book. The app's own hourly limits are not counted as tries.

### 7. Maintainability (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **[Minor] m7** `NameWrite` inherits `SeriesBackfill` wholesale (`name_write.py:262`). It overrides each method that names the `series_backfill` table today, but a future SQL line added to an inherited method would silently hit the wrong ledger.
  - **[Minor] m8** The two writers exclude each other by check-then-act reads (`_series_in_hand`, `_names_in_hand`), with no lock and no tie-break. Today only the pass's one-route-per-book keeps them apart.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings: **[Minor] m5**:
  - `436911b`'s message and the comment at `name_write.py:576` say "A move only queued has not begun"; see M1.
  - The `sorting_moves.certain` docstring says records kept before the rule are judged by it; see M3.
  - A held write of names reports series wording: "Series recovery could not verify the files…" and "The catalog could not record the series…" (`series_backfill.py:1011`, `:1084`).
  - `BooksArranger_0.31.0_Scope.md`, § Steps, still ends "0.31.0 = steps 1 and 4… Steps 2 and 3 follow as the next version", which R20 superseded.

### 9. Build & Release Hygiene

- Status: Pass
- Findings: none.
  - `package.json` and `package-lock.json` move to 0.31.0 in one commit (`8b4b540`), and the pinned lockfile hash in `scripts/build-inputs.json` matches the lockfile bytes (`95314a07…`).
  - The ten new 0.31.0 Python test modules are in the gate's inventory (`scripts/check-desktop.mjs:114-119`). The three heaviest have measured weights in `scripts/python-check-batches.mjs`.
  - No commit carries Claude attribution (`git log --format=%B` grep, 0 hits).

---

## Patterns

In this release, a guard is written against a journal state name rather than against what the other worker is doing at that moment: `queued` is treated as "not begun" while the Mover is already holding and hashing the file. Move-window fixes should be measured with the competing worker actually mid-run, not with its state set by hand.

---

## Verdict

- Total Critical: 0
- Total Major: 3 (M1, M2, M3)
- Total Minor: 8 (m1–m8)

No open Critical finding; the safety floor is intact (all writes stay inside the library boundary, no secrets, no history rewrite). M1–M3 are logged for Ender. Of these, M3 is the one that acts on Sergei's books without anyone pressing anything, and M1/M2 need a single shared fix.

**Verdict:** RELEASE CLEAR
