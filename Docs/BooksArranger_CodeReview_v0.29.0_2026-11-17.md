# Code Review — Books Arranger v0.29.0

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-17
Tool: Books Arranger
Release: v0.29.0
Commit range: main (d29f8ed, v0.28.13 + docs) .. ender/0.29.0 (50ce63c), 15 commits
Files changed: 55 files, +2230 / -183 (21 non-test, non-doc files: +1230 / -142)
Stand-down dimensions: none. Electron security is a light pass only: desktop/* is untouched in this range.
```

---

## Summary

What changed:
- A check pass at startup, after each scan, and when a drive comes back (`source_presence.py`, new):
  - item 1: drops gone books from the list;
  - item 3: checks Name taken rows again;
  - item 5: deletes source folders that hold only known leftovers.
- Light Novels routing (item 4).
- The jobs panel says what is running, and Stop acts at once (items 7, 8).
- The restart-intent work comes back from `feature/restart-intent`, with my 0.28.13 findings addressed (item 6).
- Cleanup reads the moved cover (item 2), and cp1251 chapter names and comments are repaired.

How it was checked:
- Every hunk was read.
- Five reviewer probes were run.
- Targeted tests ran on private `git archive` exports (`ender/0.29.0` and `main`) in a private scratch folder (removed after the run), through a runner that matches the gate's Python worker (`support_dispositions` over the export's `scratch/`).
- 10 mutations.
- No full suite. Nothing was run on Z:, live data or the running app. The working tree and its branch were not touched.

What I found:
- **No Critical.** The safety floor is intact, and the delete path does what the brief asks:
  - only `SAFE_LEFTOVERS` go;
  - audio, archives, partial downloads, unknown types, subfolders and links keep the folder;
  - an unavailable or empty root decides nothing;
  - a folder whose listing fails is never deleted;
  - the library root is never removed.
- Item 1 is list-only on disk. Item 2's cover read is safe.
- **Three Majors.**
  - **S-M1 is a one-line bug Ender should fix before Sergei uses Light novel:** every details-panel save that carries Light novel fails with a 500, and the message points at cleanup.
  - S-M2: item 1 says it removed books that stay on the list.
  - S-M3: the deletion pass runs every 30 s on healthy roots while any other root is away.

---

## Focus questions — answers

1. **Item 5, deleting source folders on Z:. Can audio, an archive or a partial download ever be deleted? No.**
   - **What may go:** `folder_verdict` (`source_presence.py:159`) lets a folder go only when every entry passes `storage_cleanup.leftover_verdict`.
   - **What keeps the folder:**
     - The check is an allowlist on the last extension. Any `SOUND` suffix anywhere in a file name keeps the folder, so `book.mp3.part` and `x.mp3.txt` keep it.
     - So do a subfolder, a symlink, a junction, a file with no extension, `.zip`, `.rar`, `.7z`, `.part`, `.crdownload`, `.!qB` and `.pdf`.
   - **How each file goes:** `remove_leftover` (`source_presence.py:177`) works on the exact handle, inside a `DirectoryBoundary` from the library root.
     - It checks one link and the listed size, then calls `dispose(remote_legacy=again)`. This is the method Sergei approved for source cleanup on Z: on 2026-11-16.
     - The NAS fallback runs only when the hardened guard refuses this file's own volume as remote and `remote_handle` confirms a network handle.
   - **Records and folders:** each file is recorded in `source_folder_removed_files` before it goes (ruling 77c). Folders then go only with `book_delete._remove_folder`, a non-recursive rmdir after an empty listing, with no reparse point. The parent walk stops at `_inside(parent, root)`.
   - **Unreachable or empty drive:** `answers()` requires the root to be available and non-empty. Every watched folder is skipped unless its root answered in this pass's own probe.
   - **Tests and mutations:**
     - The mutations `emptyok` (empty root counts as answering) and `jobsok` (books with a job become candidates) are each caught by `test_source_presence`.
     - `nograce` (no 10-min grace) is caught 4 times.
     - The window-focus guard is not caught (S-m6).
   - **Race with a scan or a conversion:**
     - A pass refuses while a scan runs (`merge_service.py:1055`).
     - Books with any `audio_jobs` row are never candidates.
     - A folder that holds audio again stops being watched.
     - A conversion cannot use a folder with no audio.
     - What remains: the pass skips three guards that the reviewed 74e path applies (S-m1), and it can run far more often than specified (S-M3).
2. **Item 1. Is it list-only, are converted books kept, and do unavailable or empty drives keep books? Yes to all three.**
   - `_dismiss` writes one `attention_dismissals` row and nothing else.
   - Books with a job are excluded, and the `jobsok` mutation is caught.
   - An unavailable or empty root leaves its books alone, and the `emptyok` mutation is caught.
   - **But the removal often does not happen on screen (S-M2).**
3. **Item 2. Is `source_cleanup._run` reading the cover through `reviewed_cover_path`/`managed_read_path` safe? Yes.**
   - The cover is opened read-only (`VerifiedFile(cover)`, no delete) and hashed against the manifest. A mismatch raises "Reviewed cover bytes changed", and the originals are kept.
   - It is never a disposal target.
   - `managed_read_path` gives no cleanup authority (its own docstring: "the consumer still checks its own manifest hash"). It refuses with no fallback to the stale path.
   - The three new `RelocatedCoverTests` cover all of this: the moved cover is read, changed bytes keep every original, and a refused lookup keeps every original.
   - The docstring "Never used for source retirement" is now wrong in its wording. It should say "never the disposal target" (S-m10).
4. **Item 7. Is any Stop press lost or duplicated, and does a press in flight after Stop stay paused? No Stop is lost or duplicated; the "stays paused" promise holds only partly.**
   - **No lost or duplicated Stop:**
     - A second Stop while one is in flight is refused.
     - A Stop that takes over an in-flight Start or Cancel start releases the `busy` that press set (`tookOver`). The press's own late answer is ignored (`automaticFlight!==flight`).
     - Queued Resume and Start presses are cancelled, and their lines are replaced.
   - **What "stays paused" covers:** the presses counted by `pressBusy()`. `test_stop_now_frontend.js` pins this for a scan press.
   - **Two gaps (S-m2):**
     - The deferred pause is sent in the same drain as a Start Sergei pressed after Stop. Probe P4 shows `/api/audiobook/pause` then `/api/automatic/start` back to back. If the server handles the Start first, that pause stops the run he just started.
     - A "Resume audiobook jobs" press in flight is not in `pressBusy()`, so it is not covered.
5. **R-M1..R-M4 and R-m1..R-m6: all closed.** The table follows.

### Restart intent: my 0.28.13 findings

| ID | Fix in this range | Evidence |
|---|---|---|
| R-M1 | One-time `automatic_restart_intent` marker. The first launch clears every legacy `restart_paused` (`automatic_processing.py:133-137`) | Mutation rM1 caught 4 times by `test_first_launch_starts_nothing_..._r_m1`. Rollback round trip: S-m8 |
| R-M2 | `pressed=False` on every restore path (`merge_service.py:1096`, `:1112`; `automatic_processing.py` `restored_without_press`; approvals at `merge_service.py:~4600`). Waiting cleanups need Sergei's own Start or Resume | Mutation rM2 caught by `test_restore_starts_the_queue_and_leaves_waiting_cleanups_for_a_press_r_m2` |
| R-M3 | A saved "user" or "interrupted" jobs pause wins and ends the intent (`merge_service.py:1019-1023`) | Mutation guardM3: caught (see the table below) |
| R-M4 | Stale fixtures updated | `test_backend_242` 29 OK, `test_merge_http` 25 OK |
| R-m1 | `_save_run_intent` and `_hold_queue` are best-effort, with `sqlite_retry.transaction`. The safety stop and callback come first. `start()` runs in one retried transaction | Read; `test_a_busy_catalog_never_skips_a_safety_hold_or_fails_a_start_r_m1` |
| R-m2 | Tests added for `nocancel` and `nojobattr` | Both mutations are now caught (see the table below) |
| R-m3 | The intent is cleared when there is nothing to resume | Mutation rm3: caught (see the table below) |
| R-m4 | Brief `:503` carries a dated "Superseded in 0.29.0" note. The row reason is reworded. The CHANGELOG entry is Sully's at release | Read |
| R-m5 | `report_restore_failure` puts the reason on the jobs line | `test_a_failed_restore_says_so_on_the_jobs_line_r_m5`. The non-deferred `BrowserServer` path still never restores (unchanged; no app uses it) |
| R-m6 | The `jobs._stop` guard on the attribution clear is gone | `test_resume_clears_paused_by_you_while_cleanup_owns_the_start_r_m6` |

---

## Rubric

### 1. Security

- Status: Pass. No new shell-outs, IPC or Electron changes. The three new POST routes take only `{}`. Paths come from the configured roots and the catalog, never from the page. New page text goes through `textContent` (`node()`), with no `innerHTML`. No secrets are added.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **[Major] S-M1 `web_server.py:1663`: `review_data` reads `source['kind']`, but `source` exists only in `save_review`. Every review that carries `light_novel` raises `NameError`.**
    - Two callers reach it:
      - `decision_contract.validate:44`: the details panel's Save preview metadata and Approve;
      - `/api/review`.
    - `NameError` is outside `do_POST`'s 400 tuple, so the answer is 500 with "Local control failed; inspect saved job and source cleanup status". That sends Sergei to cleanup for a metadata save.
    - Nothing is written.
    - **When it fires:**
      - Light novel is ticked in the panel.
      - Any panel save of a book whose saved review already has `light_novel` (`app.js:779` loads the box ticked; `:1141` sends it when locked). That includes every book automatic processing approved from a Light Novels or Ранобэ folder.
      - So a light-novel book's genre, topic or narrator cannot be saved from the panel.
    - **Probe P3:** `review_data(..., light_novel=True)` and `light_novel=False` both give `NameError: name 'source' is not defined`.
    - No test sends `light_novel` through `review_data`.
    - **Fix:** delete the line. Put the ebook refusal for `light_novel` beside the existing one in `save_review` (`:1644`).
    - **Why Major, not Critical:** the process keeps running, nothing is lost, and the row's Edit names and Approve paths work.
  - **[Major] S-M2 Item 1 reports books removed that stay on the list.**
    - `MergeService._todo` (`merge_service.py:2723-2800`) reads `attention_dismissals` in only three branches, and all of them are `files_missing` rows: catalog `files.missing=1`, `missing_parts`, or an established gap.
    - A book whose folder Sergei deleted since the last scan still has `missing=0`. The pass dismisses it (`source_presence.py:256-258`) and the page prints "Removed 1 book whose files are gone. No files were touched." But `_todo` keeps listing the book in its old group (Name taken, a question, and so on). The row leaves only after a scan marks the files missing.
    - **Probe P2** (real `_todo`, private catalog):
      - before the pass: `{'b1': 'name_taken'}`;
      - pass: `removed ['b1']`;
      - after the pass: `{'b1': 'name_taken'}`, removed 0;
      - after `files.missing=1`: `{}`, removed 1.
    - This is exactly Sergei's case: "I probably deleted it. Check on startup and delete from the list." The spec says "Gone books leave at startup; the list never shows ghosts."
    - The tests check that the dismissal row is written, not that the row leaves Needs attention.
    - **Fix (product call for Jane/Sergei):** treat a dismissed (id, fingerprint) as removed in every `_todo` branch. Or have the pass mark those catalog files missing, as a finished scan would. Until then the line overstates what happened.
  - [Minor] S-m4 `source_presence.py:238` with `:121-123`: each root is probed once, at the start of the pass, and only that probe has a time limit (10 s).
    - **Drive drops mid-pass:** `_gone` returns True for a book whose folder `isdir` reports missing. Every remaining candidate is then dismissed, and the page says "Removed N books".
    - **Startup can stall:** each book's `isdir` and `lexists` calls run on the loader thread (`web_server.py:403`), with nothing that stops them. `_retention_stop` exists but is not set when loading is aborted.
      - If Z: answers the probe and then stalls, loading waits on SMB timeouts at step 4.
      - A Quit during that wait reaches "Loading has not reached its safe checkpoint".
      - Not measured. Futaba can time step 4 against a stalled share.
    - The disk is safe: a folder is watched only when `isdir` is True, and deletion needs a successful listing.
    - **Fix:** probe the root again after the loop, and discard the pass's verdicts for a root that no longer answers. Give the startup pass the loader's abort as its stop.
  - [Minor] S-m5 `web_server.py:1055-1060`: window focus runs `run(folders=False)`, which still drops gone books (item 1) and adds watches.
    - The spec's section 0 table allows only item 3 on focus.
    - The disk is unaffected.
  - [Minor] S-m2 `web/app.js:4684` and `:4604`: Stop's deferred re-pause has two gaps.
    - `stopAfterFlights` is never cleared by a later Start or Resume.
    - It is sent in the same `drainLater` tick as a Start queued after Stop. Probe P4: posts `["/api/scan/start","/api/automatic/stop","/api/audiobook/pause","/api/automatic/start"]`.
    - `/api/audiobook/pause` now always calls `automatic.pause_jobs()`, which stops a Running run as Sergei's own. If the threaded server handles the Start first, his Start is undone.
    - Separately, `pressBusy()` does not count `jobControlFlights`, so a Resume audiobook jobs press in flight is outside the guarantee. Its admission generation usually loses to the pause, but this is not pinned.
    - **Fix:**
      - clear `stopAfterFlights` on any later start press;
      - count `jobControlFlights` in the check;
      - hold queued presses until the re-pause lands.
  - [Minor] S-m9 `scanner.py:278-282` with `merge_service.py:1055`: the after-scan hook runs on the scan worker thread itself.
    - The check thread it starts returns None if `inventory.worker.is_alive()`, and the worker is still finishing at that moment.
    - Whether the after-scan pass runs therefore depends on scheduling. A skipped pass is silent. It is likely rare.
    - Also, a scan started while a background pass runs is not refused: pass threads hold no admission.

### 3. Crash / Stability Safety

- Status: Concerns. No process-level crash: the pass runs inside `_check_sources`'s `try/except Exception` (`web_server.py:341`), and the restore inside `_restore_saved_work`. Two findings, both listed elsewhere:
  - S-M1: a request-level `NameError`.
  - S-m4: the startup pass has no time limit after the root probe.

### 4. Performance

- Status: Concerns
- Findings:
  - **[Major] S-M3 `web_server.py:1040-1053` with `web/app.js:1340`: while any root is away or empty, the page calls `/api/sources/check` every 30 s, and that route runs the full pass for every root that answers, folder deletion included.**
    - Each run:
      - parses every current book's evidence JSON (`_books`, which includes probe data);
      - stats every jobless book over SMB;
      - previews every Name taken row;
      - and, after the grace, deletes leftover-only folders.
    - With two or more sources and one unplugged, this repeats on the healthy roots indefinitely.
    - The spec (section 0, section 5 red-team) allows folder deletion only at start, after a scan, and for the root that came back.
    - The 10-min grace still holds, so this is not Critical.
    - Window focus (`/api/sources/rows`) repeats the same parse and stats at most once per 30 s.
    - **Fix:** pass only the roots that were away in the last report and answer now. Run the folder phase only for those.
    - Pass duration on the live catalog was not measured.
  - [Minor] S-m3 `web_server.py:1047`: Check again and the 30 s re-check probe every root synchronously (up to 11 s) while holding a merge admission (`:1614`).
    - For that time, Start scan is refused ("Pause audiobook work before starting a scan"), Restart Books Arranger is refused, and recovery deletion is refused (`recovery_admission`).
    - Each probe of a hung root leaves a daemon thread blocked in `scandir`.

### 5. State & Data Safety

- Status: Concerns. The safety floor holds: no delete outside a source root, no recursive delete, no audio or unknown type deleted, each file recorded before it goes, never the root, never on an unavailable or empty root. Findings:
  - [Minor] S-m1 `source_presence.py:211-226`: the new folder delete repeats the reviewed 74e path (`storage_cleanup.StorageCleanup._remove_folder` and `_leftovers`) but skips four of its guards.
    - **Ownership** (`cleanup_ownership.held`): a file named by another current book, by an unfinished job's sources or reviewed cover, or by a reacquire marker.
    - **`producer_recovery.protected_dependency`:** a folder that is the parent of an isolated-retained recovery's sources.
    - **`LEFTOVER_LIMIT`.**
    - **The folder identity captured before rmdir.**
    - The exposure is narrow. It needs a second book or job that names a leftover in a gone book's folder, for example a pending job's reviewed cover in that folder, or two book groups in one folder where one has a retained recovery.
    - **Fix:** call the same `_held` and `protected_dependency` checks before the first file goes.
  - [Minor] S-m7 `source_presence.py:215-221` with `web/app.js` `sourceRemovedText`: a folder whose leftovers were deleted but whose rmdir then failed is left out of `report['folders']`.
    - The files are recorded in the table but never shown.
    - The same pass can print "No files were touched."
  - [Minor] S-m8 `automatic_processing.py:125-137` and `:433-446`: R-M1 can come back after a rollback round trip.
    - The marker table survives a rollback to 0.28.13. That version writes `restart_paused=1` after a crash, and "closing" on Quit.
    - The next 0.29.0 launch restores that run without a press.
    - 0.28.13's reason text ("— start to continue saved work") tells its rows apart from 0.29.0's, so the fix can key on it.

### 6. Input Handling

- Status: Pass. Light novel is a strict bool everywhere: `light_novels.check`, `entered_names.check`, `organization._plan`, `review_backend` and `manual_conversion`. Light novel together with Short-story collection is refused with one sentence. The folder match is an exact segment, casefolded ("light novels", "ранобэ"). Output-path length still caps at 240 with the extra segment.

### 7. Maintainability

- Status: Concerns
- Findings:
  - [Minor] S-m6 `tests/test_source_presence.py:133`: the "never on window focus" assertion runs inside the 10-min grace, so it cannot fail. The mutation `focusdel` (folder phase runs whatever `folders` says) passes all 14 tests. The guard itself is right when read.
  - Note, not a finding: the three deletion tests in `test_source_presence` need the gate's `support_dispositions` owner. Run alone (`python -m unittest`), they fail with "Safe removal … could not be verified. The file was kept." (probe P1). That is the safe direction, but it misleads anyone running them alone. A module-level `support_dispositions`, or a skip with a reason, would fix it.

### 8. Doc/Code Drift

- Status: Concerns
- Findings:
  - [Minor] S-m10 Three places say more than the code does:
    - `storage_relocation_native.py:740`, "Never used for source retirement", is false in its wording since `source_cleanup.py:547`. It should say "never the disposal target; a read that retirement checks is allowed".
    - The Brief's item 1 row and `source_presence.py:5-8` ("leaves the list") hold only for rows a scan already marked missing (S-M2).
    - `book_delete.py:455-459`: `_remove_folder`'s docstring says "never directly inside a source folder". That is no longer true for this caller, by Sergei's Q6. Point the docstring at its callers.

### 9. Build & Release Hygiene

- Status: Pass.
  - The version is still 0.28.13 and there is no CHANGELOG entry for 0.29.0. Both are Sully's at release.
  - The gate now names the failing worker (`check-desktop.mjs`).
  - The new modules are in the batch.
  - `BOOKS_OPERATOR_C_ROOT` is opt-in, test-only and limited to the cross-drive case. Its comment records it as Sergei's exception.

---

## Targeted test spot-check

- **Setup:**
  - Private exports `cur` (ender/0.29.0) and `base` (main), made with `git archive`, Docs excluded, in a private scratch folder that was removed afterwards.
  - Private TEMP.
  - One process per module, 590 s limit.
  - The runner matches the gate's worker: discover under `tests/`, inside `support_dispositions(root/'scratch')`.

| Module | cur | Note |
|---|---|---|
| test_source_presence | 14 OK | |
| test_light_novels | 7 OK | |
| test_source_cleanup | 38 OK | includes RelocatedCoverTests |
| test_automatic_processing | 76 OK | |
| test_startup_loading | 21 OK | |
| test_backend_242 / test_merge_http | 29 OK / 25 OK | R-M4 closed |
| test_progress_rows, test_folder_unit_grouping, test_retry_start_fence, test_blocked_retry, test_inplace_m4b | 18, 50, 25, 21, 48 OK | |
| test_entered_names | 32, 1 F | same failure on `base` ("exceeds the supported Windows output path length": the export path is deeper). Environmental |
| node: test_stop_now_frontend, test_source_check_frontend, test_light_novel_frontend, test_progress_frontend | PASS | |

**Mutations.** Each was applied by a script that requires exactly one match.

| Mutation | Change | Caught by |
|---|---|---|
| nograce | no 10-min grace | test_source_presence (4 F, 1 E) |
| emptyok | an empty root counts as answering | test_source_presence |
| jobsok | books with a job become candidates | test_source_presence |
| focusdel | folder phase ignores `folders=False` | **nothing** (S-m6) |
| rM1 | no one-time restart-flag clear | test_automatic_processing (4) |
| rM2 | `backlog_waits=False` | test_startup_loading |
| guardM3 (R-M3) | a saved "user" or "interrupted" jobs pause no longer wins | test_startup_loading, `..._r_m3` (2 subtests) |
| nocancel (R-m2) | Stop/Pause no longer cancels a Paused restart run | test_automatic_processing, `test_stop_or_cancel_ends_a_restart_..._r_m2` |
| nojobattr (R-m2) | automatic restore ignores a user/interrupted jobs pause | test_automatic_processing, `test_restore_refuses_after_a_paused_or_held_queue_r_m2` (2) |
| rm3 (R-m3) | nothing-to-resume no longer ends the intent | test_startup_loading, `test_a_restore_with_nothing_to_do_ends_the_intent_r_m3` |

## Probes (reviewer-only; private fixtures; removed after the run)

| Probe | What | Result |
|---|---|---|
| P1 | `remove_leftover` on a fixture file with no catalog or support owner | Refused, file kept (safe direction; explains the standalone test failures) |
| P2 | Real `MergeService._todo` on a private catalog: Name taken book, files gone, then the pass | Pass reports it removed; `_todo` still lists it as `name_taken` until `files.missing=1` (S-M2) |
| P3 | `Handler.review_data` with `light_novel` true/false | `NameError: name 'source' is not defined` both times (S-M1) |
| P4 | Page only: scan press in flight → Stop → Start pressed → scan lands | `/api/audiobook/pause` and `/api/automatic/start` posted back to back (S-m2) |

---

## Patterns

The previous pattern comes back. A new delete path re-implements guards that the reviewed path already has, and loses some of them (S-m1; the NAS review's m-series before it). A guard's test sits where it cannot fail (S-m6 now; R-m2's `nocancel` last time). The fix pattern is the same both times: call the reviewed guard rather than copy it, and run each guard's test against a mutation once.

---

## Verdict

- Total Critical: 0
- Total Major: 3 (S-M1, S-M2, S-M3)
- Total Minor: 10 (S-m1 to S-m10)

**Verdict:** RELEASE CLEAR

Advisory for Jane, not a gate:
- **S-M1 is a one-line fix.** Without it, Light novel in the details panel fails on every save, and the error points Sergei at cleanup.
- **S-M3:** a narrower trigger keeps the folder delete to the triggers Sergei approved.
- **S-M2 needs a product call:** should gone books also leave rows that a scan has not yet marked missing?
