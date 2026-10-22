# Code Review — Books Arranger v0.20.3

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-22
Tool: Books Arranger (Electron / Python)
Release: v0.20.3
Commit range: 9717bf63bdf0ab4b258ed31d1e2801f32219f9f8..a159b16bcb75d78bddeaa7b6a1f44cc2ec5bcc88
Release source commit: a159b16bcb75d78bddeaa7b6a1f44cc2ec5bcc88
Release artifact manifest SHA256: 9cdf0ee36472d5dd73a4a7cd658aa0d0e4915dcf7c036e913fda51906d6dfc6f
Reviewed source: C:/Antigravity Projects/Worktrees/Books Arranger/qa-0.20.0 (branch codex/books-processing-0.20.3, clean tree at HEAD a159b16)
Files changed: 20 files, +313 / -48 (5 commits: 589269f, 48ef9a4, feecbd7, 94f110a, a159b16)
Stand-down dimensions: none
```

Range start `9717bf6` is the `v0.20.2` tag. This review covers the full range, not only 48ef9a4. The earlier 2026-10-21 report in `electron-m1` covered only 48ef9a4 and was used as background only. I formed this verdict separately.

## Summary

The range adds the stopped-flow UX spec, the v0.20.3 fix (mixed scan resume, bulk Retry selected by capability instead of group label, settling of the automatic-processing request flight, new refusal copy), test updates (including a fixed hollow Pause-fence test), skipping `dist/` and `build-cache/` in check-desktop worker copies, and a re-pin of the bootstrap Python hash to the installed 3.14.9. I read the review red-team style, so the focus was what breaks.

The scan-resume change is sound. Two problems are worth fixing next cycle:
- **Retry all now submits a different set of books than the one the page confirms.**
- **The backend tests for the headline fix sit outside the release gate.**

Neither is a data-loss path. Every target still passes the per-book capability recheck and the unchanged worker admission.

## Rubric

### 1. Security

- Status: Pass. No new shell-out, IPC, renderer privilege or HTML sink; new strings go through `textContent`/`setText`. `guarded-io.mjs` still spawns with an argument array, `-I -B` and a scrubbed environment. No Electron config change and no secrets.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **F1 [Major]** `merge_service.py:1712-1713` vs `merge_service.py:143-149`, `web/app.js:1177-1181`, `web/app.js:1249-1256`, `web/app.js:1212`. Retry all (no `items`) now targets every attention row whose `retry.allowed` is true, whatever its group. The page shows, labels and confirms Retry all with `attention_counts()['retry']`, which is the **Can retry group** count. These are two different projections.
    - **Probe** (scratch copy only, not committed): 2 Can retry books plus 3 Other books with user-fixable refusals. The page would confirm "Request 2 retries". The server submitted and accepted 5 (`total 5 / accepted 5 / refused 0`).
    - **What gets swept in:** Other rows with a current `file_problem` refusal (fix `user`), rows whose pre-check could not run (`precheck: unavailable`), and producer-recovery rows (`merge_service.py:1146`).
    - **Undisclosed clearing:** each target's cleanable working files are cleared first (`merge_service.py:1830/1832`). The dialog's "cleared first" clause only counts Can retry rows.
    - **Silent drops:** Can retry rows whose E8 check now says no are dropped from the submission even though the confirmation counted them.
    - **Spec conflict:** this contradicts the committed UX spec (`Docs/BooksArranger_StoppedFlow_UX_2026-10-21.md:40`: "confirmation target IDs, group membership and server admission must use one coherent projection"). It also contradicts the release's own help text: "Previous attempts were refused. Check each book's reason before retrying."
    - **Why not Critical:**
      - Every target still passes `_retry_one`'s capability recheck and the worker's unchanged admission.
      - Checked by reading the code: producer-recovery rows (the Сказка case) are refused by `_m4b_refusal_gate` (`working.stops`) or by `retry_admission_hold` (no retry shape).
      - Working-file blocks are re-refused in the worker by `_m4b_working_refusal` (`merge_service.py:2393`).
      - "Source audio needs replacement" MP3 rows (the Iron Inferno case) never carry `retry.allowed`. Even if forced, `retry_admission_hold` refuses them because they have no retry shape.
      - Retry all is hidden when Can retry is below 2, so the observed 0 / 46 case cannot reach this path.
      - The only caller is the user's press. Nothing automatic calls `retry_all()`.
    - **Fix next cycle:** make the no-arg path submit exactly the confirmed projection. Either send the confirmed target IDs, as Retry selected does, or restrict the path to group `retry` with `retry.allowed`, and compute the button count from the same function.
  - **F5 [Minor]** `web/app.js:1189`. The new zero-accepted receipt returns early, before the total and the `receipt_error` reason. Example: a run paused after 3 refusals out of 44 reads "No retry requests accepted. 3 refused. No conversion started from this request." It does not say that 41 books were never submitted. A receipt that could not be saved no longer says so.

### 3. Crash / Stability Safety

- Status: Concerns
- Findings:
  - **F3 [Minor]** `scanner.py:198-231` with `web_server.py:681-697` and `sqlite_retry.py:6-7`.
    - **Longer lock hold:** scan launch now retries its prepare transaction for up to 30 s (60 attempts). The web scan start/resume call runs inside the global `control_lock`. Under catalog contention, every control POST waits behind it, Pause and Quit admission included: up to about 30 s, where it was about 10 s before.
    - **Generic error on exhaustion:** running out of retries raises `CatalogHold`. That becomes the generic 500 "Local control failed; inspect saved job and source cleanup status" (`web_server.py:727`).
    - **Stop can be cleared:** `stop_event.clear()` (`scanner.py:231`) runs after the retry loop, so a scanner Stop that arrives during the wait is cleared. The automatic path re-stops through its own event. The ordering was already there; the window is wider now.
  - **F4 [Minor]** `web/app.js:1389`. The new 60 s bound on `/api/automatic/*` turns a slow but live server into "connection interrupted". `refreshFailed` sets `recoveryDisconnected` and closes the recovery dialog. A 200 with an incomplete acknowledgement takes the same path. Recovery waits for the next good poll.

### 4. Performance

- Status: Pass. Capability selection now runs `attention_summary()` with `retry=True`: one catalog pass per bulk press and one single-job read per target under `operation_lock`. These are the same read-only E8 checks the individual Retry button runs. The check-desktop exclusion removes about 4.6 GB of hashing per worker.

### 5. State & Data Safety

- Status: Pass. Scan resume checked against the four requested risks:
  - **Catalog corruption:** `prepare` runs only SQL inside `BEGIN IMMEDIATE` and re-reads `jobs` on every replay. A `ValueError` or `CatalogHold` rolls the whole plan back before any worker exists (tests: invalid other source; exhausted busy).
  - **Wrong generation for the failed source:** a saved resumable source keeps its generation and queue.
  - **Missing-files false positive:** a source with no saved job starts at generation 1 with a fresh root task. Job rows are never deleted, and source roots cannot overlap (`source_config.py:46-49`), so no stale `files.seen` collision exists. Completed sources are skipped untouched. `missing` is still set only at completion, with an empty queue and zero errors.
  - **Lost pending tasks:** no pending queue row of a saved source is deleted on resume.
  - **Bulk Retry:** opens no admission bypass (see F1).

### 6. Input Handling

- Status: Pass. `_retry_one` now rejects an unknown `kind` explicitly and requires the exact mode's capability. Selected-item shape, revision, identity and newest-parent checks are unchanged (`BulkCapabilityTests`).

### 7. Maintainability

- Status: Concerns
- Findings:
  - **F8 [Minor]** `scanner.py:201-222`. The nested `prepare` uses 2-space indentation inside a 4-space module. It also has a redundant `if job and` inside `if resume and job`. The resume-or-fresh decision is now split between a pre-loop `any()` and the in-loop branch, so the next edit has two places to keep in step.

### 8. Doc/Code Drift

- Status: Concerns
- Findings:
  - **F7 [Minor]**
    - `CHANGELOG.md:12` says Bulk Retry accepts eligible Other books. It does not say that Retry all now reaches beyond the Can retry group (F1).
    - The spec's readable launch cause, "The app could not start discovery for all source folders." (`Docs/BooksArranger_StoppedFlow_UX_2026-10-21.md:20`), exists only as a test fixture string (`tests/test_automatic_frontend.js:189`). A real launch failure still records "Automatic pass could not continue; saved source and job evidence preserved" (`automatic_processing.py:487`).
    - `desktop/runtime-pins.json:8` still says the bundle "matches the CPython used by the source checkout". The checkout's bootstrap Python is now 3.14.9 and the bundle is 3.14.8.

### 9. Build & Release Hygiene

- Status: Concerns
- Findings:
  - **F2 [Major]** `scripts/check-desktop.mjs:21-39`. `tests/test_refused_retry.py` is not in the gate's pattern list. It holds `BulkCapabilityTests`, the only backend tests that prove this release's headline fix:
    - 44 Other books reach worker admission without parent mutation;
    - identity, revision and newest-parent guards on selected items;
    - repair and retry modes are not interchangeable.

    It passes when run directly (23/23, isolated copy), but `npm run check` would pass a regression of the fix. Gated `test_blocked_retry` and `test_retry_start_fence` only touch the selection through stand-ins or mocks. The gap is wider than this one file. By `comm` of `tests/test_*.py` against the pattern list, 31 of 110 Python test files are ungated. These include `test_merge_service.py`, `test_start_over.py`, `test_working_clear.py`, `test_source_cleanup.py` and `test_safety_boundaries.py`. Those others are outside this range; they are listed for Ender to triage, not counted here.
  - **F6 [Minor]** `scripts/build_native.py:16`, `scripts/guarded-io.mjs:6`. The re-pin is trust-on-first-use. The commit records only that the installed binary changed. It does not record provenance, such as a PSF Authenticode signature or the python.org 3.14.9 artifact hash. The pin also covers only the 106 KB `python.exe` launcher, not `python314.dll` or the stdlib under `C:/Python314` that the release path loads; that scope was already there before this range.
- Verified, no finding:
  - **Pin values:** both values agree and match `C:/Python314/python.exe` (3.14.9). The fail-closed check is intact in both places.
  - **Bundled 3.14.8 pins untouched:** `scripts/qa-runtime.json` (434b361…) and `desktop/runtime-pins.json` (embed zip a93abe…) are unchanged in the range. The packaged payload still ships `resources/python/python.exe` 434b361…, matching the QA runtime.
  - **Worker-copy exclusion:** it applies only at the top level, and `dist/` and `build-cache/` hold no tracked files at a159b16. No gated test reads the repo root's `dist/` or `build-cache/`:
    - `test_build_guard.py` builds its own fixture roots;
    - `test_series_backfill.py` falls back to `build-cache` ffmpeg only when ffmpeg is not on PATH, and check-desktop prepends it;
    - a missing input would fail loudly, because skips fail the gate.
  - **Version and lock:** `package.json` and the lock move together in 48ef9a4. The CHANGELOG is present.
  - **Manifest:** `dist/release-artifacts.json` hashes to the pinned value (read only). Its `source_head` is a159b16, and its `product_digest` 4c4e5466… equals `productTree(ls-tree a159b16)`, recomputed with the repo's own `release-contract.mjs`.
  - **Attribution:** no Claude attribution in any range commit.

## Patterns

This is the second review in a row where a focused-receipt clearance missed a red gate. The 48ef9a4 version commit, and the earlier zero-finding review of it, landed while the gated `test_blocked_retry` and `test_retry_start_fence` failed against it (feecbd7's own message says so). The 94f110a fix shows the fence test had been passing with the fence removed. The gate list is hand-maintained and is now 31 files behind the suite. A test that should gate a fix but is never added to `patterns` is the recurring way coverage silently drops. A mechanical "every `tests/test_*.py` is gated or explicitly exempted" check would close it.

## Evidence

All runs were in an isolated `git archive a159b16` copy under `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/64106cea-b39e-4987-9571-6ad97339dc8a/scratchpad/shared/senua-0203-review/src`, using the gate's QA Python (3.14.8, sha 434b361…) and the QA ffmpeg. Nothing was run in the QA checkout, the live DB or `dist/` (except reading `dist/release-artifacts.json`).

- Gated suites touched by the range (`test_multisource`, `test_catalog_contention`, `test_retry_start_fence`, `test_blocked_retry`, `test_bulk_retry_receipts`): 99 passed, 0 failed or skipped (`focused_gated.log`).
- Ungated `test_refused_retry.py`: 23 passed.
- Related ungated suites: 128 run. The only 4 errors are in `test_merge_service.py` ("Verified metadata exceeds the supported Windows output path length"), caused by the long scratch path. They are environment noise and not concluded.
- Gate node suites: 57/57 passed. All 16 `tests/test_*.js` frontend scripts passed. Syntax checks passed.
- F1 probe: `tests/test_senua_probe_0203.py`, in the scratch copy only.
- The full `npm run check` was not run. It would create worker folders inside the shared QA checkout. Futaba's canonical gate run on the committed build remains the authority for that.

## Verdict

- Total Critical: 0
- Total Major: 2
- Total Minor: 6

No safety-floor item: no unsafe Electron config, no out-of-scope writes, no secret leakage, no source-of-truth destruction.

**Verdict:** RELEASE CLEAR

| # | Sev | Dim | file:line | Finding | Next cycle |
|---|-----|-----|-----------|---------|------------|
| F1 | Major | 2 Correctness | `merge_service.py:1712` | Retry all submits every `retry.allowed` row; the page confirms only the Can retry count | Submit the confirmed projection (IDs, or group retry plus allowed) and count with the same function |
| F2 | Major | 9 Hygiene | `scripts/check-desktop.mjs:39` | `test_refused_retry.py` (headline-fix backend tests) is not gated; 31/110 Python test files are ungated | Add it; add a gated-or-exempt completeness check |
| F3 | Minor | 3 Stability | `scanner.py:229` | Launch retries up to 30 s inside `control_lock`; exhaustion is a generic 500; Stop can be cleared | Retry outside the global lock, or bound it shorter; map `CatalogHold` to a busy message |
| F4 | Minor | 3 Stability | `web/app.js:1389` | 60 s abort and malformed acknowledgements are reported as a disconnect | Report "status unconfirmed" without marking a disconnect |
| F5 | Minor | 2 Correctness | `web/app.js:1189` | Zero-accepted receipt hides the total, unsubmitted books and `receipt_error` | Keep total/unsubmitted and the receipt reason |
| F6 | Minor | 9 Hygiene | `scripts/build_native.py:16` | Re-pin is trust-on-first-use, with no recorded provenance; only the launcher is hashed | Record the provenance check; consider pinning `python314.dll` too |
| F7 | Minor | 8 Drift | `CHANGELOG.md:12` | CHANGELOG, spec launch-cause copy and runtime-pins note no longer match the code | Align the text |
| F8 | Minor | 7 Maintainability | `scanner.py:201` | 2-space nested `prepare`, redundant guard, resume decision split in two places | Tidy when next touched |
