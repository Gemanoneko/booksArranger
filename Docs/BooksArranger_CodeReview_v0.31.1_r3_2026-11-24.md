# Code Review — Books Arranger v0.31.1, round 3

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-24
Tool: Books Arranger
Release: v0.31.1
Commit range: b497778..534d0c9fe2e5d1891210344a1c9d4c02405f564c (2 commits); earlier rounds covered v0.31.0..b497778
Files changed: 3 files, +69 / -8 (merge_service.py, tests/test_relink_found.py, Docs/BooksArranger_Brief.md)
Stand-down dimensions: none
```

---

## Summary

This round is a delta review of the fixes for round 2's two Minors (`BooksArranger_CodeReview_v0.31.1_r2_2026-11-24.md`):

- r2-m1: a book whose recorded path runs through a folder the search skips is never removed.
- r2-m2: the 20 s sweep rhythm applies only while the queue is idle.

The Brief changes are documentation only. They add the r2 rows and Sergei's "Direction — the lean end state" section, which changes no code.

**Method.**

- Read the code diff.
- Ran `tests/test_relink_found.py` (27 tests, including Ender's two new ones and four probes of mine). All pass.
- The probes cover:
  - a dot-folder deeper in the path (`Author\.extras\Bonus.m4b` renamed in place);
  - a file name, not a folder, starting with `#` that was moved;
  - two cases at the edge of the design, below.
- Fixture libraries only, nothing run against Sergei's install, catalog or `Z:\`. The scratch folder `senua-0311c` is deleted.

---

## Round-2 findings: status

| # | Round-2 finding | Status at 534d0c9 | Evidence |
|---|---|---|---|
| r2-m1 | A book renamed or moved inside a folder the search skips was removed | **Fixed** | `merge_service.py` `_absence_proof`. Any folder part of the recorded path whose name starts with `#`, `@`, `.` or `$` answers False before anything is listed (`parts[:-1]`, so a file name like `#1 Bestseller.m4b` is still searched; my probe confirms it). A folder on the way that has the hidden or system attribute answers False during the walk. `_missing` logs it and returns False, so the book stays. `_remove_missing` calls `_absence_proof` again just before removal (`if not again: continue`), so the second check is real. The constants are shared with `_output_files` (`SKIPPED_FOLDER`, `HIDDEN_OR_SYSTEM`), so the search and the proof can't drift apart. Probe: `Author\.extras\Bonus.m4b` renamed in place stays `completed`. Ender's test covers the dot-named and attribute-hidden cases, with a book genuinely gone as the positive control. |
| r2-m2 | 20 s sweep for the whole conversion run after a Start | **Fixed** | `_recheck_waits` now returns False while the converter thread is alive, so the sweep keeps its 60 s rhythm. The 20 s rhythm resumes once the queue is idle and the waiting check can start. `_recheck_waits` has one caller (`merge_service.py:1674`) and catches its own exceptions. |

---

## Red-team of the delta

- **Nothing new deletes anything.** The fix only adds ways for `_absence_proof` to answer False ("never removed"). No path that used to refuse now removes. The empty-part case cannot fire, because `relative_to().parts` has no empty parts.
- **Edge-of-design observations (not graded, not new):**
  1. A book moved into a skipped folder from a normal one (probe: `Author\Archived.m4b` moved to `#Archive\`) is still removed. The same happens to a normal folder renamed to a dot-name. That is the existing rule that a book in a folder the search does not enter counts as deleted, the same rule that covers `#recycle`. The Brief states the folders stay unsearched (Sergei 2026-11-24).
  2. A folder with a normal name, hidden only by its attribute, that is itself renamed, makes its books removed (probe: `Hidden Shelf` set hidden, then renamed to `Hidden Shelf 2`, removed). Its old name is gone, so the proof can no longer read the attribute. The Brief's line "a book whose recorded path runs through such a folder is never removed" is true for dot-named folders. For attribute-hidden ones it is true only while the folder keeps its name. This rests on the same rule as observation 1, needs a manually hidden folder that is then renamed, and is too narrow to grade.
  3. The r2-m2 condition tests only the converter thread. A queue that is idle but blocked keeps the 20 s rhythm while a Start's check waits: Sergei's Pause after a Start, or a scan. Nothing converts in those states, so the contention behind r2-m2 does not apply. If it matters, use the same conditions as `start_published_check` (`background_stop`, `_resuming`).

---

## Rubric

### 1. Security
- Status: Pass. No shell-outs, no new IPC, no secrets.

### 2. Correctness & Logic
- Status: Pass. r2-m1 is fixed in both the search and the re-check before removal. The edge-of-design cases are recorded as observations, not findings.

### 3. Crash / Stability Safety
- Status: Pass. The new `entry.stat()` call sits inside the existing `except OSError: return None`.

### 4. Performance
- Status: Pass. r2-m2 is fixed. The extra cost is one attribute read per folder on the recorded path, served from the directory listing.

### 5. State & Data Safety
- Status: Pass. Removal is only made stricter. Every deletion path cleared in rounds 1 and 2 is unchanged.

### 6. Input Handling
- Status: Pass. No new inputs.

### 7. Maintainability
- Status: Pass. The skip rule is now one pair of constants shared by the search and the proof.

### 8. Doc/Code Drift
- Status: Pass. The Brief rows match the code, with the precision note in observation 2. The new "Direction" section is direction only and matches no code change.

### 9. Build & Release Hygiene
- Status: Pass. `package.json` is still 0.31.0; Sully bumps it. No stray files are in the range. Untracked in `Docs/`: the round 1 and round 2 reviews, Futaba's two QA reports and Judy's UX spec.

---

## Verdict

- Total Critical: 0
- Total Major: 0
- Total Minor: 0

**Verdict:** RELEASE CLEAR

Both round-2 Minors are fixed correctly, and the delta adds no new risk. All round-1 and round-2 findings are now closed. The three observations sit at the edge of the agreed "skipped folders stay unsearched" rule and are not graded.
