# Code Review — Books Arranger v0.31.1

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-24
Tool: Books Arranger
Release: v0.31.1
Commit range: v0.31.0..7ed4d624c67e21d9d6090f35fa3c771fac52a967 (branch ender/0.31.1-stuck-load, 14 commits)
Files changed: 33 files, +2040 / -163
Stand-down dimensions: none
```

---

## Summary

This range adds the stuck-load fix: background work waits for the first status (`_first_status`), the shell records a `loaded` flag, Restart Books Arranger relaunches the app, and Restart engine refusals now give a reason. It also adds the relink of finished books moved by hand (`_relink_found`, `book_move.found`), the removal of finished books proven missing (`finished_removal` tombstone, `_absence_proof`, `_remove_missing` with its brake), and the rule that published books keep no recovery copies. That rule covers Keep-files books, removed books (`_owners`), removed books' leftovers (`discharge_removed`, `release_unfinished`) and "Original changed since checked" holds (`release_changed`).

The review was red-team and centred on the six deletion paths in the brief. Each path stays inside the app's own folders: the recovery set folder or the job's staging folder, with a pinned ancestry and an unknown-content refusal. Each copy is checked for one link, a single stream and its full hash (against the reviewed original, or the producer receipt) before it is removed. Nothing in the range can remove a library file, a source file or a file outside the app's folders. The removal guards do hold for an offline, empty or partly unreadable NAS. The relink match (name, file ID, size, full hash, exactly one candidate) cannot adopt a different file.

The gap is a step earlier. "No file of this name under the output folder" is treated as "the book is gone". Two probes reproduce removals of books that still exist:

- a book the app itself has renamed whose journal never committed;
- a book Sergei renamed in place.

Each removal then releases the book's copies and snapshots without verifying the audiobook first. The probe used the fixture from `tests/test_relink_found.py` on its own temporary libraries. Nothing was run against Sergei's install, profile, catalog or `Z:\`.

---

## Rubric

### 1. Security

- Status: Pass. Nothing in the range shells out. Paths are scanned with `os.scandir` and compared after NFC and case folding, with no glob, so `[` `]`, spaces, Cyrillic and UNC roots are safe. Only the `app` sender can call the new `books:relaunch` IPC, which takes no arguments. No secrets were added.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **M1 [Major]** `merge_service.py:5982-5989`, `merge_service.py:6143-6160`, `finished_removal.py:53-67`: the removal ignores the app's own record of why a book is not at its path. A move in a non-effective state is one example: `rename_intent` means the OS rename happened but the commit did not. That is the ruling 73k "unfinished, renamed" state, and the brief says move recovery stays off in retained mode. For such a book, `bindings.current()` still returns the old path. The new name matches no same-name entry, so the absence proof succeeds and the book is tombstoned.
    - Reproduced: a fixture book with a rules move set to `rename_intent` and the file renamed to `Series\New Name.m4b` ended the pass as `removed`. The engine log said "Finished book removed from the list (not found; no files touched)".
    - Inferred, not reproduced: a replacement parent whose `historical_retired()` returns False. That function swallows any `ValueError`/`OSError`/`KeyError`, for example when the replacement output was moved by hand and not yet relinked. The parent's retired output is then "proven missing". The tombstone hides the shared `candidate_id`, so the live replacement drops out of every list and total. `replacement_jobs._bound_manifest` requires the parent and the replacement to share that candidate. A replacement parent in 'needs attention' also skips `_historical` entirely (`audio_jobs.py:648`).
    - Fix: before treating a book as missing, skip any job that has a non-terminal `book_moves` row (`state NOT IN book_move.TERMINAL`) or a replacement relation. Check again inside the `finished_removal.remove` transaction.
  - **M2 [Major]** `merge_service.py:5982`, `merge_service.py:6074`: the relink searches by file name only, so a book Sergei renamed in place is declared gone. That holds even when the file sits in the same folder with the recorded file ID, size and hash.
    - Reproduced: `Typo Titel.m4b` renamed to `Fixed Title.m4b` in the same folder ended the pass as `removed`.
    - The same happens to a book moved within a folder the search skips. The skip covers names starting with `.`, `#`, `@` or `$`, plus hidden folders. Samba marks dot-folders hidden by default, so a real series folder such as `.hack` is never searched.
    - The audiobooks survive. The app forgets them for good: a file that reappears never brings the book back, and only manual SQL restores it.
    - Fix: before proving absence, look for the recorded file ID among same-size `.m4b` files. At least do this in the recorded folder and its siblings. `os.stat` is only needed for size-equal entries. Keep the full-hash and exactly-one rules.
    - Whether a renamed book should be relinked is Sergei's call. Today it is removed silently.
  - **m1 [Minor]** `merge_service.py:6119` with `audio_jobs.py:726`: after the first pass, a pass only re-checks the books that were not confirmed. Its `checked` count is then about the missing count, so 3 or more missing books always trip the "over half" brake. One refused pass therefore refuses every later pass of the session. The message then says "3 of 3 finished books checked are missing at once. Check that the library drive is connected", which is misleading.

### 3. Crash / Stability Safety

- Status: Pass. `_first_status` is bounded by 600 s and stops on close (`stop_loading` now joins a loader that is still alive). Errors in the new background passes are caught, logged and tried once per run. The Restart Books Arranger flow leaves `state.relaunch` armed only after its Quit has been accepted.

### 4. Performance

- Status: Concerns
- Findings:
  - **m2 [Minor]** `merge_service.py:6047-6081`, `merge_service.py:1661`: only a complete listing of the output folder is cached. If any folder under Sorted cannot be listed, every pass does a full recursive SMB listing once for each missing book. Passes come every 20 s while `removal_refused` is set, and that flag never clears while the folder stays unlistable. This keeps the NAS awake and adds a permanent false "check the drive" line.
  - The per-book reference check (`working_lifecycle.py:754`) is the intended fix and works. The search token is the attempt id, so the single call stays a targeted query.

### 5. State & Data Safety

- Status: Concerns
- Findings:
  - **M3 [Major]** `finished_removal.py:66`, `merge_service.py:6166`, `web/app.js:1461`: the job reason, the engine log and the status line all say "no files touched" / "No files were touched". In fact the same removal makes the next sweep, within about 20-60 s:
    - delete the book's recovery copies without any output verification (`_owners`);
    - delete its staging snapshots (`discharge_removed`);
    - delete an unfinished cleanup's copies (`release_unfinished`).
    For a gone book with a finished cleanup, those copies are the last copy of the book's audio. Sergei ruled the deletion, but the only disclosure of it tells him the opposite. Fold the M1 and M2 false removals into this and he is told nothing happened to books that were not gone.
  - Deletion paths 1-6 from the brief, each verified:
    1. The snapshot check runs once per book, after hashing and the source proofs. Writes are confined to `stage/<job>/<attempt>`.
    2. The verified purge, now covering Keep-files books, still requires `protected_cleanup` (full output hash).
    3. For a removed book, `_owners` uses the stored receipt, and `_source_safety` still needs the library online and the originals retired and absent.
    4. `discharge_removed` checks the ownership marker, refuses unknown members, requires each file's parent to be the stage folder, and checks one link, the facts, the size and the full hash.
    5 and 6. `_release_copies` checks the recovery set folder, refuses unknown content, refuses any half-done intent (`removal_intended`, `disposition_set`, `restore_intended`), and runs `_prepare` (inside the root, ancestry pinned, one link, full hash and timestamp against the reviewed original) before `_dispose`.

    None of these paths can reach a library or source file. A resumed held cleanup whose copies were released fails closed, because its `VerifiedFile(backup)` open fails before any original is removed (`source_cleanup.py:608-645`).
  - **m3 [Minor]** `working_lifecycle.py:754-756`: the reference check now runs once, before the removal loop rather than before each removal. A durable reference written during the loop is no longer seen. I found no concurrent writer of another table that names this attempt's staging paths, and the brief's revisit row records the trade. A re-check every N files or K seconds would bound the window cheaply.
  - **m4 [Minor]** `merge_service.py:1692-1745`, `working_lifecycle.py:780-797`: the new background passes (`_release_removed_leftovers`, `_release_changed_copies`, and the removal of a retained 'needs attention' row, which `audio_jobs.py:648` does not short-circuit) never call `retained_job`. The brief's 0.30.0 item A row requires a new pass to decide this. File deletion is still refused by the native guards (`storage._prepare`, and `VerifiedFile(delete=True)` via `retained_path`), so this is a gap in the rule, not a deletion.

### 6. Input Handling

- Status: Pass. No new HTTP inputs. The new `/api/state` fields (`relinked`, `removed`, `removal_refused`) are written with `textContent`.

### 7. Maintainability

- Status: Pass. `_relink_found` and `_remove_missing` carry dense comments, but each proof step is commented and has its own test.

### 8. Doc/Code Drift

- Status: Concerns
- Findings:
  - **m5 [Minor]** `recovery_retention.py:128-129` (`kept()`: "no automatic purge touches it") and `merge_service.py:2462-2463` (`keep_files()`: "no automatic purge touches them again") still describe the 2026-10-18 rule. The 0.31.1 override makes both wrong.

### 9. Build & Release Hygiene

- Status: Pass. `package.json` is still 0.31.0 at `7ed4d62`. The bump and the lockfile are Sully's release step. No binaries, secrets or scratch files are in the range. `Docs/BooksArranger_StuckLoad_UXSpec_2026-11-24.md` is untracked (Judy's file, outside this range).

---

## Open questions (could not be settled from the code)

1. How often `historical_retired()` returns False for a parent that was properly replaced, which is the M1 inferred trigger. It needs a replacement fixture with the replacement moved by hand.
2. Whether Sergei's install runs in retained-runtime mode with any retained job in 'needs attention' (m4). The same mode keeps move recovery off, which makes the M1 `rename_intent` state permanent.
3. Whether the packaged Python and the NAS share handle paths over 260 characters. If not, `lexists` fails on long Cyrillic paths. The final folder listing then answers "unprovable", so nothing is removed, but the "check the drive" line stays up permanently.
4. Whether the share uses access-based enumeration or Windows Offline Files. Either would present a partial view that still lists "completely", which none of the guards can detect.
5. Whether a regroup can give a removed book's remaining originals (from an unfinished cleanup) a new candidate id. That new candidate has no job, so automatic processing could convert it again and the book would come back.

---

## Patterns

Again, the gap is a proof that answers a different question from the one it stands in for (as in the 0.31.0 delta reviews). The relink and removal correctly prove "no file of this name is listed". They are used as proof that "the book is gone", and neither checks the app's own move journal or the file ID.

---

## Verdict

- Total Critical: 0
- Total Major: 3
- Total Minor: 5

**Verdict:** RELEASE CLEAR

No finding deletes a library or source file, touches files outside the app's folders, deletes while the drive is unreadable, or adopts the wrong file. The M1 and M2 false removals cost the catalog entry, which can be restored by hand, plus copies the no-copies rule would have deleted after verification. Neither is audio loss in practice. They follow from states Sergei can reach (an unfinished app rename, a hand rename), and the fix for each is a few lines. I recommend fixing M1, M2 and M3 before this ships, but that is Jane's and Sergei's call. They do not block.

| # | Sev | Dim | file:line | Finding | Fix before release? |
|---|-----|-----|-----------|---------|--------------------------|
| M1 | Major | 2 | `merge_service.py:5982`, `finished_removal.py:53` | A book with an unfinished app move (or a replaced parent) is removed as gone | Recommended, not required |
| M2 | Major | 2 | `merge_service.py:5982`, `:6074` | A book renamed in place, or moved inside a skipped dot-folder, is removed as gone | Recommended, not required |
| M3 | Major | 5 | `finished_removal.py:66`, `merge_service.py:6166`, `web/app.js:1461` | "No files touched" while the removal triggers deletion of the last copies | Recommended, not required |
