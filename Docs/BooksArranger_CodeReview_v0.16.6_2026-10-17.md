# Code Review — Books Arranger v0.16.6

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-17
Tool: Books Arranger
Release: v0.16.6
Status: FINAL; lean pass focused on "is the progress work reporting-only" (style and maintainability skipped by brief)
Commit range: 9e1664ff50522a1afc92790f69f2efcba3240675..c823724a2f6fa83cf3f8d874568019178462700b
Last published release: v0.16.5, tagged at 57250387ebe8f2c41771f6ddf19a7949ca119df1 (its report cleared b6cae4c..9e1664ff)
  57250387ebe8f2c41771f6ddf19a7949ca119df1 Docs only (v0.16.5 review, QA and acceptance records; 3 files, +202)
Delta reviewed here: 57250387ebe8f2c41771f6ddf19a7949ca119df1..c823724a2f6fa83cf3f8d874568019178462700b (21 files, +907 / -103; 19 non-Docs files, +688 / -103)
  b398cd103da10c5f436c978468bf3936cd5c0429 live progress rows per running activity; fix stale panel after Retry
  c823724a2f6fa83cf3f8d874568019178462700b version bump to 0.16.6 + CHANGELOG
Stand-down dimensions: 7 and 8 skipped by brief
Release source commit: c823724a2f6fa83cf3f8d874568019178462700b
Release artifact manifest SHA256: e45899b533b30a8b693a2d1116566de4ad3d1746fcd73a4384f272b69f3e6f1c
Release installer: dist/builds/7c105c0c-e0dc-4dbf-9530-3a9dccd90e9d/Books-Arranger-Setup-0.16.6.exe
Release installer SHA256: 073f15f4dc1f1613bd756370f2bea159b19177e0215185155f70baaabbe2f004 (172,977,164 bytes)
```

What carries forward unchanged: everything cleared in `Docs/BooksArranger_CodeReview_v0.16.5_2026-10-17.md` (`b6cae4c..9e1664ff`), with its open Major and Minor findings. This delta does not touch any of them.

## Release questions (reporting-only)

1. **No change to conversion, verification or deletion: yes.**
   - `audio_pipeline.py`: every hash, comparison, refusal and its order is unchanged. The new hooks run only after the real work: `on_bytes` after `value.update`/`write`, and `PcmSeconds.feed` passes the bytes to the proof (or `Fanout`) before counting.
   - The only changed media command is the normalize step (`:527`). It gains `-progress pipe:1 -stats_period 1 -nostats`, and its stdout moves from a file to the drain pipe. These are the same options the encode already uses (`:764`) with the same bundled ffmpeg, and the output, `-n` and filter are unchanged.
   - `cover.stat()` (`_create_private`) reads the protected copy that was just made. It is harmless.
   - `audio_jobs.py` checkpoint: a measurement still returns before anything is journaled. Validation is now stricter: only known phase and unit pairs, with keys whitelisted.
   - `source_cleanup.py`: three in-memory lines (`:86`, `:309`, `:351`). There is no change to verifying or removing originals.
   - `merge_service.py`: a status label (`checking` → `recovery copies`) and a `report=` keyword on `publish`. Nothing else in the code or the desktop reads the old `checking sources` label for a decision.
   - Retry: only the refusal text changed.
2. **No new catalog writes on hot paths: yes. New lock use: yes, and it is bounded, with no deadlock.**
   - Progress writes only in-memory dicts. The new readers (`_research_pass`, `activities`, `published_check`) only read.
   - The one new lock use is the existing `AudioJobs._lock` (an RLock). It is now also taken from the ffmpeg drain threads, at most twice a second per step plus once per track. It is held only for a dict assignment.
   - No holder of `_lock` waits on the worker or on ffmpeg: `close()` lets go before `join`. The worker never holds a SQLite write transaction while it reports. So there is no lock-order inversion.
   - The cost of a blocked report is a stall. See m1, which is where that stall can turn into a failed attempt.
3. **Progress code itself cannot raise into a job; delivery can (m1).**
   - Every value comes from `StepProgress.update`. It clamps `completed` to 0..total, drops a total that is not finite or not positive, clamps `item`/`items` to ints, and always sends a unit that matches `MEASURED`. So the checkpoint validators cannot reject anything the pipeline sends.
   - `EncodingProgress` sends no unit, which defaults to `seconds` for `encoding`, so it still passes.
   - The exposure is in delivery: `run_owned` fails the attempt if the drain thread is still busy 3 s after ffmpeg exits (m1).
4. **Status payload bounded: yes.**
   - `activities()` returns at most three rows: one conversion or cleanup row, one identity row and one scan or research row. Each has fixed keys. Its strings are a title, a library label, the current scan path and a research source and stage.
   - The `started_at` memo is pruned to the rows seen on each call.
   - Per-job `progress` is now limited to 8 whitelisted keys. Before, it passed through `**measured`.
   - `published_check` and `research_pass` are a few integers each.
   - The unbounded parts of the payload (the `jobs` list and `scan_issues`) were already there and are not touched here.
5. **Frontend:** the new rows are written with `textContent` (`writeText`). There is no `innerHTML` in the delta. Titles and research text that came from the network cannot inject markup.

**Measured:** `test_progress_rows`, `test_progress`, `test_cleanup_resume` and `test_blocked_retry` ran 60 tests, all OK with 0 skipped, at `c823724`. They ran through the same discover runner that `scripts/check-desktop.mjs` uses. `node` passed `test_progress_frontend.js`, `test_retry_frontend.js` and `test_automatic_frontend.js`. The worktree was clean before and after (bytecode writing disabled).

- Note: run as `python -m unittest tests.test_progress_rows`, it errors at `tests/test_progress_rows.py:160` (`import test_cleanup_resume`). That import only resolves under the discover runner. It is runner-dependent only, and the gate's runner passes.

## Artifact binding (lean, 2026-10-17)

This was read-only. Nothing was installed, launched or extracted.

- `sha256(dist/release-artifacts.json)` = `e45899b5…f1c`, equal to the brief.
  - Manifest: version `0.16.6`, `source_head` `c823724a2f6fa83cf3f8d874568019178462700b`, `build_id` `7c105c0c-e0dc-4dbf-9530-3a9dccd90e9d`.
- The installer's SHA-256 and size (172,977,164 bytes) equal its manifest entry and the brief.
- All ten changed product files in `win-unpacked/resources` equal the `c823724` git blobs (`git hash-object --path`):
  - `audio_jobs.py`, `audio_pipeline.py`, `automatic_processing.py`, `conversion_progress.py`, `merge_service.py`, `source_cleanup.py` and `web_server.py`;
  - `web/app.js`, `web/index.html` and `web/style.css`.
- `desktop/` is not in the delta.
- **Not redone in this lean pass:** the 7z carve, the product-digest recompute and the ASAR comparison.

## Rubric

Severity tags and the always-blocking floor are those in `Team/Docs/ProcessRules.md`, Severity definitions.

### 1. Security
Pass.
- There is no new shell-out argument built from input; the normalize options are constants.
- There is no new route and no Electron change.
- The new UI text is written with `textContent` only.

### 2. Correctness & Logic
Concerns.
- m4 (Minor): see Finding rollup.

### 3. Crash / Stability Safety
Concerns.
- m1 (Major): see Finding rollup.
- m2 and m5 (Minor): see Finding rollup.

### 4. Performance
Concerns.
- m3 (Minor): see Finding rollup.
- Reports are throttled to two a second. The callbacks for each block are a single clock read.

### 5. State & Data Safety
Pass.
- No catalog writes were added.
- Originals, recovery copies and the publish order are untouched; see release question 1.

### 6. Input Handling
Pass.
- `_measure` rejects values that are not numbers, NaN, or out of range, and turns them into an indeterminate row.
- The checkpoint validators are stricter than before.

### 7. Maintainability
Skipped by brief.

### 8. Doc/Code Drift
Skipped by brief.

### 9. Build & Release Hygiene
Pass.
- The version bump and lockfile are in one commit (`c823724`).
- `check-desktop.mjs` now runs the new test file.
- The artifact is bound to `c823724` as stated above.

## Finding rollup

- **m1 (Major), `audio_pipeline.py:187-189` with `audio_jobs.py:597`. Progress delivery can fail an attempt.**
  - Every PCM decode now reports through `checkpoint` → `with self._lock` on the ffmpeg drain thread:
    - the check and format-matching decodes (`:469`);
    - normalize (`:528`);
    - the proof decode (`:661`);
    - the joined-audio check (`:674`).
  - `_lock` is held across SQLite calls with a 5 s busy timeout (`audio_jobs.py:113`). Examples are `enqueue` (`:269`), the Retry compare-and-set (`:432`, `:456`) and the background check's `_apply_unchanged` (`:237`).
  - If one of those waits on a busy catalog for more than 3 s just as an ffmpeg run exits, `drain.join(3)` times out. The attempt then fails with `ValidationError('Owned encoding progress has not finished draining')`, which is classed as not retryable.
  - Normalize is the most exposed. Its stdout is only progress text, so ffmpeg can exit while the drain is blocked.
  - This was already possible for the single encode step. This delta extends it to several ffmpeg runs per track.
  - Data stays safe: it is pre-publication, originals are kept, and there is no deletion path.
  - Fix: deliver progress without blocking. Either use `_lock.acquire(blocking=False)` and drop the sample, or use a separate progress lock that is never held across I/O.
- **m2 (Minor), `web_server.py:102-103`. Shared memo without a lock.**
  - The `_activity_started` memo is shared by every handler thread, and `state()` is not serialised.
  - A concurrent `setdefault` can raise `RuntimeError` (dictionary changed size) in the list comprehension. Two stale lists can also `del` the same key and raise `KeyError`.
  - Either way one status or control reply fails. The restart fence (`:537`) catches `RuntimeError` and refuses (fails closed).
  - There is no job impact. Fix: iterate `list(memo)` and use `memo.pop(key, None)`.
- **m3 (Minor), `web_server.py:204`. Duplicate status read.**
  - While a scan runs, every poll and control reply now calls `inventory.status()` a second time: four counts plus the scan-issues query (`scanner.py:91-99`). This happens even when `library == active_library`.
  - These are reads only, but they double that catalog load during scans. Reuse the first result when the libraries match.
- **m4 (Minor), `source_cleanup.py:309` and `:351`. Stale checked count.**
  - `self.checked[id]` is cleared only on the success path. A pause or hold during recovery-copy checking leaves a stale count.
  - When that cleanup resumes, the stale count briefly shows until the loop resets it to 0. It is display only.
- **m5 (Minor), `automatic_processing.py:194-196`. Narrow guard in `_research_pass`.**
  - It catches only JSON parse errors. A checkpoint that is not a dict, or one whose lists hold unhashable members, would raise out of `status()`, which every poll and the restart fence call.
  - This cannot happen today, because every writer stores a dict of id strings.
  - Separately, the whole checkpoint is parsed again on every poll during research.
- Open Critical: 0.
- Open Major: 5. New m1, plus 4 carried from v0.16.5: t1, s3, r1 and `working_lifecycle.py:228`.
- Open Minor: 23. New m2 to m5, plus the 19 carried from v0.16.5.
- **Always-blocking floor: intact.**
  - No change to verifying or deleting originals.
  - No new writes outside the library, the recovery root and the catalog.
  - No Electron change and no secret exposure.
  - No risk to repo history.

Major and Minor findings are logged for Ender's next cycle and do not gate this release.

## Verdict

- Total Critical: 0
- Total Major: 5
- Total Minor: 23

**Verdict:** RELEASE CLEAR

This clearance covers `9e1664ff50522a1afc92790f69f2efcba3240675..c823724a2f6fa83cf3f8d874568019178462700b` and the installer `Books-Arranger-Setup-0.16.6.exe` (SHA-256 `073f15f4dc1f1613bd756370f2bea159b19177e0215185155f70baaabbe2f004`), bound by the manifest hash in the header.

It covers construction only. Futaba's QA GO is the independent behaviour gate.

A rebuild, or any product-file change after `c823724`, voids this artifact binding.
