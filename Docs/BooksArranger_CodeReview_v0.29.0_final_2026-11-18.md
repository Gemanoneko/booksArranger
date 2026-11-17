# Code Review — Books Arranger v0.29.0 (final)

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-18
Tool: Books Arranger
Release: v0.29.0
Commit range: 92e8fb3..edf974f on ender/0.29.0, 12 commits. This follows my delta review
  (BooksArranger_CodeReview_v0.29.0_delta_2026-11-17.md, 50ce63c..6e3de5f). 6e3de5f..92e8fb3 is one
  docs-only commit (QA r2, the delta review, Sergei's M-5 answer), read and checked.
  The verdict below covers the full 0.29.0 range, d29f8ed..edf974f.
Files changed: 20 files, +609 / -53 (8 code files: +198 / -44; 11 test files: +408 / -6; the Brief)
Full 0.29.0 range: 69 files, +4460 / -228
Stand-down dimensions: none. Electron security is a light pass only: desktop/* is untouched in this range.
```

---

## Summary

What changed:
- Fixes for my D-M1 and D-m1..D-m4, and for Futaba's N-1, M-5 (Sergei: yes), O-r2-1, O-r2-3 and O-r2-4.
- `edf974f`: the pending-cleanup overlap check now reads registry subkeys until two reads agree, and skips a key removed between listing and opening. Root cause: the gate's entry check at b527230 failed with WinError 259.
- New tests: two real-server tests (D-M1 round trip, M-5), five unit tests, a D-m3 retry test, and tests that pin D-m2's two halves.

How it was checked:
- Every hunk was read, with the surrounding code at edf974f.
- Targeted tests ran on private `git archive` exports of edf974f and 92e8fb3 in the brief's scratch folder:
  - the gate's pinned `build-cache/qa-runtime` Python and FFmpeg (hashes match `scripts/qa-runtime.json`);
  - `support_dispositions` over the export's `scratch/`, the gate's fixture-root map, and a private TEMP.
- 31 mutations. Each was applied by a script that requires exactly one match. Each was reverted from the commit, then checked against `git archive` output by SHA-256.
- Two new probes (L and S).
- No full suite. Nothing was run on Z:, on live data or in Sergei's app. The checked-out branch was not switched, and the repo's tree is clean.

What I found:
- **No Critical. The safety floor is intact.**
  - No new delete path or trigger.
  - Every delete guard in range is stricter than before: a check before each file goes (D-m1), and fewer watches dropped (D-m4).
- **D-M1 is closed.** Ender's real-scanner test reproduces it on 92e8fb3 and passes on edf974f.
- **D-m1, D-m2 and D-m4 are closed. D-m3 is narrowed but stays an open Minor:** a long scan uses up the retries.
- **Two new Minors:**
  - F-m1: two fixes are held by no test.
  - F-m2: the gate race edf974f fixes is narrowed, not closed.
- Nothing new above Minor.

---

## Rulings on the brief's questions

1. **D-M1: a book hidden by the pass is listed again when its files come back. Closed.**
   - **The fix:**
     - Each pass tests the paths of hidden books again, if their root answers (`source_presence.py:368-382`).
     - `_forget` drops both records the pass wrote: `source_gone`, and the `attention_dismissals` row with the recorded fingerprint (`:133-146`).
     - The stale branch in `_books` uses `_forget` too (`:171-174`).
     - Only an existing path counts. A read error keeps the book hidden, which is the safe direction.
   - **Real scanner:**
     - `test_http_0290 ..._d_m1` covers both P5 variants: away with no scan, and away across a scan.
     - It asserts the scan sees the very fingerprint the pass recorded.
     - On 92e8fb3 it fails at line 271: `{} != {'title_author': 1}`.
   - **Caught by tests:** `noback`, `forgetkeepsdismissal` and `removednotfiltered` (the Details count).
   - **Not caught:** the stale-branch `_forget` (F-m1). Probe S shows that code is right, and that 92e8fb3 hides the book there.
   - The doc drift from the delta review is fixed: the Brief row and the module docstring now say what the code does.
2. **D-m1: the guards run again before each file goes. Closed.**
   - `_held(..., [item])` runs inside the loop (`:335-338`). It fails closed: the folder stays, and files already removed are reported (S-m7).
   - `noperitem` is caught by `..._d_m1`. That test adds a job naming the second leftover while the first is being removed.
3. **D-m2: both halves are now pinned. Closed.**
   - `msnoown` is caught by `test_startup_loading ..._s_m8` (both origins).
   - `resumeNoClear` is caught by `test_stop_now_frontend`.
4. **D-m3: the retry loop (15 s × 8, never during a scan).**
   - **Can it delete anything outside the approved triggers? No.**
     - Each try is the same drive-return pass as before the fix: `_check_sources(merge, roots=back, wait=True)`, `back` only, folders included.
     - `run()` probes again itself, and the 10-min folder grace still applies.
     - Within its own two minutes, a retry cannot both start and finish a folder's grace.
     - It never runs during a scan:
       - the loop skips while the scan worker is alive (`web_server.py:388-390`);
       - `check_sources` refuses again under its lock (`merge_service.py:1061`).
     - Never on focus. Never after Quit: `_check_sources` refuses while closing.
     - The pass has the same callers as before: launch, a finished scan, the drive-return retry, and focus with `books=False, folders=False`.
   - **Caught:** `retryonce`, `retryduringscan`, `nochecked` and `routeoldpath` (`test_merge_http`). `nostamp` is caught by `test_http_0290`.
   - **Residual, so it stays open as a Minor:** a try made while a scan runs still counts as one of the eight (see Findings).
5. **D-m4: a folder whose drive left mid-phase stays watched. Closed.**
   - A folder that looks absent is dropped only after its root, probed again, still answers (`:452-459`).
   - `vanishdrop` and `vanishnoprobe` are caught by `..._d_m4`, which has a positive control.
6. **M-5: gone books leave All candidates and the count; a book with any job is never hidden. Accepted.**
   - `hidden()` (`:149-157`) is `still_gone` minus every candidate with any `audio_jobs` row. Job rows are deleted only by Delete book (`book_delete.py:857`), and that removes the book's own record in the same transaction. So a converted book stays in the converted list and in All.
   - It is applied in three places:
     - All candidates (`review_backend.py:419`), in both page paths (`groups.py:940`, `:979`);
     - search;
     - the "N book candidates found" count (`merge_service.py:530`).
   - **Caught:** `hiddennojobs` (unit test), and `nohiddenall`, `nohiddencount`, `pagenohiddensearch` and `pagenohiddenfast` (the real-server test).
   - On 92e8fb3 the new real-server test fails at line 312.
   - **Not caught:** the multi-root `page_sources` clause (F-m1).
   - **Scope note, not a finding:**
     - The "Candidate changed" and "Source read errors" filters still list hidden books.
     - The Brief says so ("the other candidate filters are unchanged"), and Sergei's answer named All candidates.
     - Futaba first saw these books labelled "Candidate changed". If Sergei expects them gone from that filter too, the change is small: `status in ('all','changed')` at `review_backend.py:419`. Sergei's call, through Jane.
7. **N-1: an untouched Author unclear row leaves the list. Fixed.**
   - Rendering records the preselected author in `d.preselected` (`app.js:3394`).
   - A choice counts as his work only when it differs from that one (`:3004`).
   - This is the only code that sets a choice without his click. Same author? preselects nothing (ruling 12).
   - `nopreselected` is caught by `test_source_check_frontend`. That test builds a real row through `renderRows`, as Futaba's PA-2 asked.
8. **`edf974f`: can "refuse if it keeps changing" block a real uninstall or update? No, not in practice. The change refuses less often than before, never more.**
   - **When it refuses:**
     - The subkey list must differ on five back-to-back reads (four changes within the few milliseconds the reads take).
     - The only writer in normal use is the app's own terminal cleanup journal: one key created and one deleted per transaction.
     - Normally the namespace does not exist at all (`FileNotFoundError` → return).
     - Probe L: a list that changes once, then settles, passes. A stale count passes; on 92e8fb3 it raised WinError 259. 512 entries pass; 513 are refused, as before.
   - **What a refusal does:**
     - It is `ControlRecordsHeld` with no recovery record. The lifecycle command maps that to `control_records_held`: "This location could not be checked…" (`storage_lifecycle.py:2212`).
     - Nothing on disk changes, and a retry can succeed.
     - The old WinError 259 reached the same message through `could_not_check`.
   - **The FileNotFoundError skips are sound:** the journal deletes a transaction key only at terminal, so a key that is gone has finished.
   - **Caught by probe L:** `subkeyonce` (the "kept changing" case then passes) and `nofnfskip`.
   - **Residual (F-m2):** an entry that exists but whose Authority cannot be read still refuses, as the commit says.
9. **Futaba O-r2-1, O-r2-3, O-r2-4: read, accepted.**
   - `keepShownDestination` only changes what is shown. Approve sends the shown path, and the server refuses a destination that differs (0.22.0 m1), so a wrong kept path can only refuse.
   - Files mode reads the first chosen file's folders.
   - The Save As fallback is passed as `remembered`. The desktop module checks it exists before using it (`desktop-folder-picker` test, real `existingFolder`).

### My delta-review findings

| ID | Status at edf974f | Evidence |
|---|---|---|
| D-M1 | **Closed** | Real-server round trip fails on 92e8fb3 and passes here; `noback`, `forgetkeepsdismissal`, `removednotfiltered` caught |
| D-m1 | **Closed** | `noperitem` caught |
| D-m2 | **Closed** | `msnoown`, `resumeNoClear` caught |
| D-m3 | **Narrowed, open (Minor)** | Retry works for a stop within about 2 min and for a failed pass; a longer scan uses up the tries |
| D-m4 | **Closed** | `vanishdrop`, `vanishnoprobe` caught |
| S-m3, S-m4 (stall half), S-m9 (overlap half) | Open, accepted skips (delta review) | Unchanged in this range |

---

## Rubric

### 1. Security

- Status: Pass.
  - No new shell-outs or IPC, and no Electron change.
  - The registry change only reads.
  - New SQL passes ids through `json_each(?)` and is never interpolated.
  - No secrets.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - [Minor] D-m3 (narrowed) `web_server.py:383-390`: each try made while a scan is alive counts as one of the eight (`continue`).
    - So a scan that runs longer than about 2 minutes (8 × 15 s) and is then stopped still leaves the root that came back unchecked, until the next finished scan or launch.
    - This is the same case as in the original finding, now only for longer scans. A full scan of Z: may well run that long.
    - Safe direction: books stay and folders stay.
    - **Fix:** while the scan worker is alive, wait for it (join, as `_check_sources_after_scan` does) and do not count that try. Then check `checked()` again.

### 3. Crash / Stability Safety

- Status: Pass.
  - The retry thread is a daemon. It checks `closing` on every try and sleeps only between tries.
  - Every pass still runs inside `_check_sources`'s `try/except`.
  - `_subkey_names` is bounded: at most 513 `EnumKey` calls on each of five reads.

### 4. Performance

- Status: Pass for this range (S-m3 is still open from before).
  - `hidden()` adds a `sqlite_master` read and the `still_gone` join to each status computation. The `audio_jobs` scan runs only when a book is hidden.
  - The new loop for books coming back stats each hidden book's folders once per pass.
  - Both are small next to the pass itself.

### 5. State & Data Safety

- Status: Pass. The safety floor holds:
  - The delete path is unchanged except for the stricter per-file guard (D-m1) and fewer dropped watches (D-m4).
  - The D-M1 release deletes only the pass's own two records.
  - The test fixture removal in `test_storage_relocation_operator.py:102-108` deletes only the test's own uuid-tagged folders in the gate's fixture area.

### 6. Input Handling

- Status: Pass. The new page parameters (`hidden`) are internal sets, never request input. The registry names are still checked as canonical UUIDs before use.

### 7. Maintainability

- Status: Concerns
- Findings:
  - [Minor] F-m1: two fixes are held by no test.
    - **(a) The stale-branch `_forget` (`source_presence.py:171-174`), the D-M1 fix's second half.**
      - The `partial` sub-case of `test_files_back_after_a_scan_marked_them_missing_..._d_m1` rewrites the fingerprint to `fp-partial`. That is the fixture's own fingerprint (`book()` sets `'fp-' + identity`), so the release goes through the new loop for returned books and never through the stale branch.
      - The mutation `staleplain` (drop only `source_gone`, as 92e8fb3 did) passes every test.
      - Probe S plays the real sequence:
        - files gone, the pass hides the book;
        - a scan finds one file (the fingerprint changes), the pass runs;
        - the other file comes back unchanged and the fingerprint returns to the recorded one.
      - Results: edf974f leaves no dismissal; the mutant and 92e8fb3 keep `('partial', fp-partial)`, so the book is hidden for good. That is D-M1's shape.
    - **(b) The multi-root clause in `groups.page_sources` (`groups.py:979-981`).**
      - `pagesourcesnohidden` passes `test_http_0290` and `test_groups_filters`, because the M-5 test has one root.
      - The code reads right.
    - **Fix:** in (a), give the scan-found case a fingerprint different from the recorded one. Add a two-root case for (b).
  - Not counted (display-only or redundant), listed for Ender. These mutations also pass every test:
    - `nokeepshowndone` (the `namesDone` call);
    - `keepshownnokey` (the preview-key guard);
    - `stampend` (stamping the pass's end instead of its start: the 30 s re-check corrects a stale state anyway);
    - `noclosing` (`_check_sources` refuses while closing anyway).

### 8. Doc/Code Drift

- Status: Pass.
  - The Brief rows for items 1, 4 and 5 and the module docstring match the code, including the D-M1 wording the delta review flagged.
  - The Brief's D-m3 sentence ("tried again 15 s apart, at most 8 more times") is accurate. It does not say that tries during a scan count (D-m3 above).

### 9. Build & Release Hygiene

- Status: Concerns
- Findings:
  - [Minor] F-m2 `storage_lifecycle_controls.py:105-112`: the gate race edf974f fixes is narrowed, not closed.
    - A key deleted after it was opened gives WinError 1018 (ERROR_KEY_DELETED) from `EnumKey`/`QueryValueEx`, not `FileNotFoundError`. Probe L shows it propagates.
    - `test_terminal_cleanup_journal`'s teardown deletes its installation key on the real HKCU namespace (`tests/test_terminal_cleanup_journal.py:74-78`).
    - So another gate worker inside `assert_no_pending_overlap` can still fail the same way, in a narrower window.
    - A transaction key created, but with its Authority not yet written, still raises `FileNotFoundError` (probe L). That window is microseconds.
    - In the app both refuse (`could_not_check`), which is fail-closed.
    - Context (outside this range):
      - the gate's journal tests write the same `HKCU\Software\Books Arranger\UninstallTransactions` namespace that Sergei's installed app reads at install, update and uninstall;
      - a key left without Authority (a worker killed in that microsecond window) would refuse his update until it is removed.
    - **Fix:** treat WinError 1018 like the `FileNotFoundError` skips; a deleted key is finished. Separately, give the journal tests a private `BASE` (Ender's call).
- Not findings:
  - `test_http_0290` stays in the gate (`check-desktop.mjs:98`), now with 8 cases.
  - The version is still 0.28.13 and there is no CHANGELOG entry. Both are Sully's at release.

---

## Targeted test spot-check (edf974f export)

| Module | Result |
|---|---|
| test_source_presence | 25 OK |
| test_http_0290 | 8 OK (none skipped; pinned FFmpeg on PATH) |
| test_merge_http | 26 OK |
| test_startup_loading | 22 OK |
| test_groups_filters, test_quiet_status, test_catalog_paging, test_review_backend | 11, 10, 3, 19 OK |
| test_storage_relocation_operator (the changed case) | 1 OK; its fixture folders are gone afterwards |
| node: test_source_check_frontend, test_light_novel_frontend, test_picker_memory_frontend, test_stop_now_frontend | PASS |
| node --test desktop-folder-picker.test.mjs | 22 pass |
| test_http_0290 (edf974f's file) on the 92e8fb3 export: the two new cases | 2 of 2 fail (expected: D-M1 at line 271, M-5 at line 312) |
| test_storage_lifecycle_controls | **Not run here.** Its `setUp` refuses any folder below a git repository (`application_target_source_repository`), and the brief's scratch is inside one. The new case is replayed by probe L with the same doubles |

**Mutations.** Each was reverted, and the export was verified against `git archive` output.

| Mutation | Change | Caught by |
|---|---|---|
| noback | no re-test of hidden books | test_source_presence (2 D-M1 cases); test_http_0290 D-M1 |
| forgetkeepsdismissal | `_forget` keeps the Remove-from-list row | the same three |
| **staleplain** | the stale branch drops only `source_gone` (92e8fb3 behaviour) | **nothing** (F-m1a; probe S) |
| removednotfiltered | a returned book stays counted as removed | test_http_0290 D-M1 |
| noperitem | no guard before each file | test_source_presence `..._d_m1` (leftover) |
| vanishdrop / vanishnoprobe | a vanished folder loses its watch at once / with no second probe | test_source_presence `..._d_m4` |
| nostamp | no "checked at" stamp | test_http_0290 scan test |
| retryonce / retryduringscan / nochecked | no retry / retry during a scan / no check for a pass that already ran | test_merge_http `..._d_m3` |
| routeoldpath | the route goes back to the one-shot pass | test_merge_http routes test |
| stampend / noclosing | stamp at the pass's end / no closing check in the loop | nothing (redundant; see Maintainability) |
| hiddennojobs | a job book can be hidden | test_source_presence `..._m_5` |
| nohiddenall / nohiddencount / pagenohiddensearch / pagenohiddenfast | M-5 dropped from the list / the count / search / the single-root page | test_http_0290 M-5 |
| **pagesourcesnohidden** | M-5 dropped from the multi-root page | **nothing** (F-m1b) |
| msnoown | the jobs-pause writer guard is removed | test_startup_loading `..._s_m8` |
| nopreselected | N-1 reverted | test_source_check_frontend |
| resumeNoClear | Resume no longer clears the re-pause | test_stop_now_frontend |
| nokeepshown / nokeepshownsave | O-r2-1 removed / its Save call removed | test_light_novel_frontend |
| nokeepshowndone / keepshownnokey | the `namesDone` call / the preview-key guard removed | nothing (display only) |
| filesnolight | O-r2-3 reverted | test_picker_memory_frontend |
| nooutputfallback | O-r2-4 reverted | test_picker_memory_frontend |
| subkeyonce | the first registry read is trusted | probe L ("differs on every read" passes) |
| nofnfskip | a key removed before it is opened raises | probe L |

## Probes (reviewer-only; private fixtures and registry doubles, nothing written to the real registry)

| Probe | What | Result |
|---|---|---|
| L | `assert_no_pending_overlap` with `winreg` doubles. Cases: a stale count; a key removed before it is opened; a list that changes once; a list that changes on every read; 512 and 513 entries; a key deleted after it is opened (1018); a key whose Authority is not written yet | edf974f: passes, passes, passes, refused, passes, refused, 1018 raises, FileNotFoundError raises. 92e8fb3: the stale count raises WinError 259. The other base cases do not apply: base reads the count before the double fills the list |
| S | The stale branch, using `test_source_presence`'s harness: a scan finds one file, then the other returns and the fingerprint is the recorded one | edf974f: no dismissal left (pass). `staleplain` mutant and 92e8fb3: `('partial', fp-partial)` left, so the book is hidden (fail) |

---

## Patterns

This round mostly closes the "test the guard against the real producer" lesson: D-M1 now has a real-scanner round trip, and N-1 has a test that renders a real row. But the same slip shows up again in a smaller place. The `partial` sub-case was written to cover the stale branch, and its comment says so. Yet its fixture fingerprint equals the recorded one, so a different branch does the work. A test that names the branch it covers should fail when that branch is removed. Mutating the line it means to cover is the cheap check.

---

## Verdict

Counts cover the full 0.29.0 range, d29f8ed..edf974f, open findings only:

- Total Critical: 0
- Total Major: 0
- Total Minor: 6
  - New in this range: F-m1, F-m2.
  - Narrowed, still open: D-m3.
  - Open from the first review (accepted skips): S-m3, S-m4 (stall half), S-m9 (overlap half).

Closed in this range: D-M1, D-m1, D-m2, D-m4. Earlier in 0.29.0: S-M1, S-M2, S-M3, S-m1, S-m2, S-m5, S-m6, S-m7, S-m8, S-m10.

**Verdict:** RELEASE CLEAR

Advisory for Jane, not a gate:
- **Nothing here needs a fix before release.**
- F-m1 is two small tests.
- D-m3's remaining case (a scan longer than about 2 min that is then stopped) and F-m2 can go in the next cycle.
- One question for Sergei (M-5 scope): should gone books also leave the "Candidate changed" filter, where Futaba first saw them? Today only All candidates and the count leave them out, as the Brief says.
