# Code Review — Books Arranger v0.29.0 (delta)

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-17
Tool: Books Arranger
Release: v0.29.0
Commit range: 50ce63c..6e3de5f on ender/0.29.0, 8 commits. This delta follows my first review
  (BooksArranger_CodeReview_v0.29.0_2026-11-17.md, d29f8ed..50ce63c). The verdict below covers
  the full 0.29.0 range, d29f8ed..6e3de5f.
Files changed: 22 files, +1318 / -106 (11 code files: +333 / -97; 8 test files: +493 / -6; 3 docs)
Full 0.29.0 range: 61 files, +3468 / -209
Stand-down dimensions: none. Electron security is a light pass only: desktop/* is untouched in this range.
```

---

## Summary

What changed:
- Fixes for my S-M1..S-M3 and S-m1, S-m2, S-m4, S-m6..S-m10, and for Futaba's B-1, M-1..M-6, m-1, m-3..m-6.
- The check pass now runs after a scan (the pass thread waits for the scan's thread to end) and on drive return, for that root only.
- New `source_gone` record: a gone book leaves Needs attention in every group at once.
- New real-server tests (`tests/test_http_0290.py`), added to the gate.

How it was checked:
- Every hunk was read.
- Targeted tests ran on private `git archive` exports of 6e3de5f and 50ce63c, in the brief's scratch folder. Removing that folder is still pending: the studio sweep's rename probe was refused with EBUSY four times.
- The runner matched the gate's Python worker: the pinned `build-cache/qa-runtime` Python and FFmpeg, `support_dispositions` over the export's `scratch/`, the gate's fixture-root map, and a private TEMP.
- 22 mutations, each applied by a script that requires exactly one match and reverted from the commit's blob.
- One new probe.
- No full suite. Nothing was run on Z:, on live data or in Sergei's app. The checked-out branch was not switched.

What I found:
- **No Critical. The safety floor is intact.**
  - The delete path is still allowlist-only, works on exact handles, records each file first and never removes the root.
  - The new triggers do not widen it (focus question 1).
- **S-M1, S-M2 and S-M3 are fixed.**
- **One new Major (D-M1), a regression from the S-M2/M-3 fix:**
  - A book the pass judged gone stays hidden from Needs attention after its files come back unchanged, across every later scan and pass.
  - Probe P5 shows it on 6e3de5f. 50ce63c lists the book again.
  - Nothing on disk is affected.
- **Four new Minors (D-m1..D-m4).**
- **Ender's three skips are accepted as deferrals.** S-m3, S-m4's stall half and S-m9's overlap half stay open as Minors.

---

## Focus questions — answers

1. **Does deletion ever run from an unavailable or empty root, on window focus, or from the 30 s re-check? No, with one approved exception: a root that came back.**
   - **Unavailable or empty root:**
     - Each watched folder is skipped unless its root answered, with content, in this pass's own probe (`source_presence.py:382`).
     - The drive-return pass probes again inside `run()`. The route's probe only chooses which root to check; it never authorizes a delete.
     - Books are dropped only after a second probe (`:356-365`).
     - Mutations `noreprobe` and (from the first review) `emptyok` are caught.
   - **Window focus:**
     - The route sends `books=False, folders=False` (`web_server.py:1077`).
     - `run()` returns at `:326` before any probe, book decision or folder.
     - The mutations `focusroute` (route) and `focusfull` (the pass ignores `books=False`) are each caught.
     - The S-m6 test is now past the grace and has a positive control.
   - **30 s re-check:**
     - A pass starts only for a root that did not answer at the last check and answers now (`back`, `web_server.py:1069`).
     - A root that answered all along is never passed again from here. The `allroots` mutation is caught.
     - The pass for a root that came back does run the folder phase. That is the approved drive-return trigger: that root only, its own probe, the 10-min grace.
   - **The new S-m1 guards fail closed:**
     - an unreadable folder identity keeps the folder;
     - an exception in `_held` keeps it ("Ownership … could not be read; retained");
     - a changed identity before `rmdir` keeps it.
     - The mutations `noheld` and `noident` are caught.
2. **Can the new real-server tests in `tests/test_http_0290.py` fail? Yes.**
   - **On 50ce63c**, 5 of 6 fail with the errors Ender quotes:
     - names-save 409;
     - approve-preview 400;
     - candidate review 500 "Local control failed";
     - the M-6 proposal is False;
     - "scan 1: the check pass ran after the scan" is None.
   - The Manual Conversion save passes on both commits. It is a route guard, as Ender says.
   - **On 6e3de5f**, the scan-hook test is broken by:
     - `nowait`: the pass does not wait for the scan thread;
     - `nogoneskip`: `_todo` ignores `source_gone`;
     - `noscanbranch`: `still_gone` loses its after-scan branch.
   - **They are real:**
     - a loopback `BrowserServer` on port 0 that asserts it is not 5210, with the page's token;
     - a real `MergeService` and scanner over a private catalog;
     - FFmpeg audio.
   - **In the gate:** Ender's entry log for 6e3de5f shows all 6 as `ok`, not skipped.
   - **`settle()` is sound.** The pass thread starts inside the scan worker before the worker ends, so there is no moment when neither is alive.
   - **Limits:**
     - The M-6 no-review case patches `approval_preview`, which the docstring says.
     - A stray `books-source-check` thread from another module in the same batch would make `settle()` wait 90 s and fail. That fails safe.

### My first-review findings

| ID | Status at 6e3de5f | Evidence |
|---|---|---|
| S-M1 | **Closed.** The line is gone. `save_review`'s ebook refusal includes `light_novel` | Three of the new real-server tests fail on 50ce63c and pass here |
| S-M2 | **Closed, with a regression: D-M1.** `_todo` skips `source_gone` books in every group (`merge_service.py:2762`) | `nogoneskip` caught twice (unit and real-server); probe P5 |
| S-M3 | **Closed.** Only a root that came back is checked | `allroots` and `nowaitflag` caught by `test_merge_http` |
| S-m1 | **Closed, with residue: D-m1.** Ownership, `protected_dependency`, `LEFTOVER_LIMIT` and folder identity are all present | `noheld` and `noident` caught |
| S-m2 | **Closed.** (a) queued presses wait for the re-pause; (b) a Resume in flight counts; (c) a later Start or Resume clears it | (a), (b) and (c)-Start caught; (c)-Resume not caught (D-m2) |
| S-m4 | **Half closed.** The re-probe is closed. **The stall half is skipped** (see the rulings) | `noreprobe` caught |
| S-m5 | **Closed** (Futaba m-1): focus runs rows only | `focusroute` and `focusfull` caught |
| S-m6 | **Closed.** The test is past the grace, with a positive control | `focusfull` caught. The old `focusdel` is now unreachable: no caller passes `folders=False` with `books=True` |
| S-m7 | **Closed.** `report['files']`, `files_removed`, and the page line | `noident` and `sm7line` caught |
| S-m8 | **Closed in `automatic_processing`. The `merge_service` half is not pinned (D-m2)** | `noown`, `no028clear` and `nowriter` caught; `msnoown` not caught |
| S-m9 | **Half closed.** The pass after a scan runs. **The overlap half is skipped** | `nowait` caught |
| S-m10 | **Closed.** The `managed_read_path` and `book_delete._remove_folder` docstrings now say what the code does. The Brief's item 1 row now overclaims (D-M1) | Read |

### Rulings on Ender's skips

- **S-m3 (Check again and the 30 s re-check probe all roots while holding a merge admission): skip accepted. It stays an open Minor.**
  - S-M3 no longer starts passes on healthy roots.
  - The probe still holds the admission for up to 11 s every 30 s, but only while a root hangs. A cleanly unplugged drive errors at once.
- **S-m4, stall half (the startup pass has no stop wired to a loading abort): skip accepted. It stays an open Minor.**
  - The disk is safe.
  - The cost is startup and Quit latency on a stalled share.
  - The new re-probe adds at most one more 10 s probe, and only when books were found gone.
- **S-m9, overlap half (a scan started while a background pass runs is not refused): skip accepted. It stays an open Minor.**
  - Overlaps are now more likely, because passes after scans really run.
  - The pass still decides from paths it tests now, never from scan rows.
  - Each delete is per file and fails closed.

---

## Rubric

### 1. Security

- Status: Pass. No new shell-outs, IPC or Electron changes. The new request fields are strict booleans (`NAME_BOOLS`, `light_novels.check`). The new tests bind to loopback port 0 and refuse 5210. No secrets.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **[Major] D-M1 `source_presence.py:104-122` (`still_gone`) with `:333` and `merge_service.py:2762`: a book the pass judged gone stays off Needs attention after its files come back unchanged. Nothing brings it back.**
    - **Why it sticks:**
      - `still_gone` keeps a record while the group's fingerprint equals the recorded one (`:115`).
      - The fingerprint is a hash of the scan evidence (`groups.py:891`): paths, sizes, mtimes and missing flags.
      - So files that return unchanged hash to the same value.
      - The pass never tests a recorded book's paths again: it filters them out at `:333`.
      - Records are dropped only when the fingerprint differs and the files are not all missing (`_books`).
      - Neither `attention_dismissals` nor `source_gone` has an undo.
    - **Probe P5** (real scanner, `ApproveFixture`; a Held book in `title_author`):
      - the folder is moved out, then the pass runs;
      - the folder is moved back (mtimes kept), then a scan, then the pass;
      - 6e3de5f: listed `[]`, removed 1;
      - 50ce63c: listed `['title_author']`.
      - The variant with a scan while the folder was away gives the same result.
    - **Realistic triggers:**
      - a Recycle Bin or NAS #recycle restore, which keeps mtimes;
      - a folder moved out and back;
      - a transient SMB error on one path. `os.path.isdir` and `lexists` return False on any `OSError`, and the S-m4 re-probe runs after the loop. A blip that ends before the re-probe drops every book checked during it, and with no mass-drop guard (Sergei's Q5) these now leave every group, with no way back.
    - A Held book that is hidden this way never shows its question.
    - **Not Critical:**
      - list-only;
      - files and catalog untouched;
      - audio in the folder drops its watch, so nothing is deleted;
      - `source_gone` is its own table, so a fix can release every affected book.
    - **Fix:** in the pass, test again the paths of recorded books whose root answers (the same `_gone` call), and delete the record when any file exists. Then the Brief's promise holds.
    - The test's positive control uses a synthetic `fp-back` fingerprint, so it cannot see this.
  - [Minor] D-m3 `web_server.py:1067-1070`: the route records the root as answering before its drive-return pass runs.
    - If that pass is skipped, the root is not checked again until the next finished scan or launch. A skip happens when a scan is alive and that scan is then stopped (a stopped scan runs no hook).
    - The same applies if the pass raises.
    - Safe direction: books stay and folders stay.
    - **Fix:** update the root's state from the pass's own report only.

### 3. Crash / Stability Safety

- Status: Pass. The pass runs inside `_check_sources`'s `try/except`. The after-scan thread joins only the scan worker, never a lock. `wait=True` blocks only its own daemon thread. `NO_COVERAGE` has the `removed` key that `_todo` now increments.

### 4. Performance

- Status: Concerns. S-M3 is closed. Open:
  - S-m3: skip accepted (see the rulings).
  - Note, not a finding: a drive that flaps makes the 30 s re-check run one pass for that root about every 60 s while the line shows. Each pass is guarded, as above.

### 5. State & Data Safety

- Status: Concerns. The safety floor holds (focus question 1). Findings:
  - [Minor] D-m1 `source_presence.py:300`: `_held` runs once, before the loop.
    - The reviewed 74e path checks it again for each file, just before that file goes (`storage_cleanup.py:957`).
    - So an Approve whose job names a leftover in a gone book's folder, between the check and the removal, is missed. That window is very narrow.
    - **Fix:** call `_held` with `[item]` inside the loop. The ownership index is cached by token, so it is cheap.
  - [Minor] D-m4 `source_presence.py:384-386` (unchanged since 50ce63c; I missed it in the first review): the folder phase drops a watch whenever `isdir` is False. That includes a drive that left after the probe.
    - The book is already recorded, so that folder is never watched again, and its leftovers stay.
    - Safe direction, but item 5 silently gives up on those folders.
    - **Fix:** drop a watch only after the root still answers (one more probe, as `:356` now does for books).
  - Open from the first review: S-m4's stall half and S-m9's overlap half (see the rulings).

### 6. Input Handling

- Status: Pass. `light_novel` is an explicit boolean in `NAME_FIELDS` and in the partial list. The error text names the field. The panel's ebook refusal sits in `save_review`, where the catalog row is. `ROW_NAME_FIELDS` keeps the saved value under ruling 40, and the review save drops a False key (`review_backend.py:633`).

### 7. Maintainability

- Status: Concerns
- Findings:
  - [Minor] D-m2: two fixes read right, but no test holds them.
    - `msnoown`: removing `or not pause_state.own(saved)` at `merge_service.py:1024` passes `test_startup_loading`, `test_automatic_processing` and `test_desktop_update` (125 tests). This is the jobs-queue half of S-m8.
    - `resumeNoClear`: removing `app.js:703` passes `test_stop_now_frontend`. This is S-m2(c) for Resume.

### 8. Doc/Code Drift

- Status: Concerns
- Findings:
  - [Minor] (part of D-M1) Two places promise more than the code does:
    - the Brief's item 1 row (`Docs/BooksArranger_Brief.md:13`): "a scan that finds a file again lists it again";
    - `source_presence.py:9-10`: "A scan that finds any of its files again lists it again".
    - Both hold only when the returning files differ from when the pass saw them gone.

### 9. Build & Release Hygiene

- Status: Pass.
  - `test_http_0290.py` is in the gate (`check-desktop.mjs`), and Ender's 6e3de5f entry log shows its 6 cases `ok`.
  - The version is still 0.28.13 and there is no CHANGELOG entry. Both are Sully's at release.

---

## Targeted test spot-check (6e3de5f export)

| Module | Result |
|---|---|
| test_source_presence | 20 OK |
| test_http_0290 | 6 OK (not skipped; pinned FFmpeg on PATH) |
| test_merge_http | 25 OK |
| test_automatic_processing | 77 OK |
| test_startup_loading | 21 OK |
| test_desktop_update | 27 OK |
| test_light_novels | 7 OK |
| test_folder_unit_grouping | 51 OK (includes the m-5 TagRepair) |
| node: test_stop_now_frontend, test_source_check_frontend, test_ruling35_frontend, test_light_novel_frontend | PASS |
| test_http_0290 on the 50ce63c export | 5 of 6 fail (expected; see focus question 2) |

**Mutations.** Each one is reverted, and the export's files are verified against the commit's blobs.

| Mutation | Change | Caught by |
|---|---|---|
| noheld | `_held` skipped | test_source_presence `..._s_m1` |
| noident | no identity check before `rmdir` | test_source_presence `..._s_m7`, `..._s_m1` |
| noreprobe | no second probe before books are dropped | test_source_presence `..._s_m4` |
| focusfull | `run()` ignores `books=False` | test_source_presence `..._s_m6_m_1` |
| focusroute | the focus route drops `books=False` | test_merge_http |
| allroots | the re-check passes every answering root | test_merge_http |
| nowaitflag | the drive-return pass is skipped while another pass runs | test_merge_http |
| nowait | the pass after a scan does not wait for the scan thread | test_http_0290 scan test |
| nogoneskip | `_todo` ignores `source_gone` | test_source_presence `..._s_m2`; test_http_0290 scan test |
| nolistfilter / noscanbranch / nostale | `still_gone` and the record lifecycle | test_source_presence `..._m_3` (noscanbranch also caught by test_http_0290) |
| noown / no028clear / nowriter | the S-m8 writer stamp and the 0.28.x flag clear | test_automatic_processing `..._s_m8` (nowriter also caught by the r_m1 and r_m2 tests) |
| **msnoown** | the jobs-pause writer guard is removed | **nothing** (D-m2) |
| repauseSameTick / resumeNotCounted / startNoClear | the S-m2 (a), (b) and (c)-Start fixes | test_stop_now_frontend |
| **resumeNoClear** | Resume no longer clears the re-pause | **nothing** (D-m2) |
| sm7line | "No files were touched" is back | test_source_check_frontend |
| namesSentAll | an untouched Light novel box is sent | test_ruling35_frontend |

## Probes (reviewer-only; private fixtures in the reviewer scratch)

| Probe | What | Result |
|---|---|---|
| P5 | Real scanner: a Held book's folder is moved out, the pass runs; the folder is moved back, then a scan, then the pass. Run on both commits | 6e3de5f: hidden for good (listed `[]`, removed 1). 50ce63c: listed again (D-M1) |
| P6 | The 6e3de5f `test_http_0290.py` run against the 50ce63c export | 5 of 6 fail: the new tests can fail |

---

## Patterns

The guard-copy pattern from my first review is mostly closed: the S-m1 guards are now the reviewed ones, but checked once instead of per file (D-m1). A new pattern appears in the S-M2 fix. The fix proves the hide with a synthetic fingerprint (`fp-back`). It never runs the real round trip, where a file comes back unchanged. That is the one case where a fingerprint-keyed record cannot tell "still gone" from "back" (D-M1). This is the same lesson as before: test the guard against the real producer of its input, not a stand-in.

---

## Verdict

Counts cover the full 0.29.0 range, d29f8ed..6e3de5f, open findings only:

- Total Critical: 0
- Total Major: 1 (D-M1)
- Total Minor: 7
  - New: D-m1, D-m2, D-m3, D-m4.
  - Open from the first review: S-m3, S-m4 (stall half), S-m9 (overlap half).

Closed in this range: S-M1, S-M2, S-M3, and S-m1, S-m2, S-m5, S-m6, S-m7, S-m8, S-m10.

**Verdict:** RELEASE CLEAR

Advisory for Jane, not a gate:
- **D-M1 is the one to fix before the next release.** A book restored after the pass saw it gone (Recycle Bin, moved back, or a short Z: blip at startup) never returns to Needs attention by itself. The fix is small: the pass tests the paths of recorded books again and drops the record when a file exists.
- D-m1 to D-m4 are small and can go in the same cycle.
