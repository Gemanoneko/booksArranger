# Code Review — Books Arranger v0.16.6

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-17
Tool: Books Arranger
Release: v0.16.6
Status: FINAL; lean pass focused on "is the progress work reporting-only" (style and maintainability skipped by brief), plus a focused delta review of the m1 fix
Commit range: 9e1664ff50522a1afc92790f69f2efcba3240675..7619d12f6ba9fdb99202f48786155fdab92ef031
Last published release: v0.16.5, tagged at 57250387ebe8f2c41771f6ddf19a7949ca119df1 (its report cleared b6cae4c..9e1664ff); v0.16.6 is not yet tagged
  57250387ebe8f2c41771f6ddf19a7949ca119df1 Docs only (v0.16.5 review, QA and acceptance records; 3 files, +202)
Delta reviewed here: 57250387ebe8f2c41771f6ddf19a7949ca119df1..c823724a2f6fa83cf3f8d874568019178462700b (21 files, +907 / -103; 19 non-Docs files, +688 / -103)
  b398cd103da10c5f436c978468bf3936cd5c0429 live progress rows per running activity; fix stale panel after Retry
  c823724a2f6fa83cf3f8d874568019178462700b version bump to 0.16.6 + CHANGELOG
Fix delta reviewed here: c823724a2f6fa83cf3f8d874568019178462700b..7619d12f6ba9fdb99202f48786155fdab92ef031 (9 non-Docs files, +76 / -13)
  0c981be docs: record v0.16.6 review and smoke of c823724 (pre-fix build)
  7619d12f6ba9fdb99202f48786155fdab92ef031 fix: progress updates never wait on the queue lock; single version badge writer
Stand-down dimensions: 7 and 8 skipped by brief
Release source commit: 7619d12f6ba9fdb99202f48786155fdab92ef031
Release artifact manifest SHA256: 08ddf425efa16cb7b7ac71285a1d64ce5fc992b4ff0889ff809be432f0bb24d4
Release installer: dist/builds/bcc7c6fd-56ad-4c26-bb5f-d04264ff79e0/Books-Arranger-Setup-0.16.6.exe
Release installer SHA256: d6727de6a42d34ad76c462b80f46ff3889ae3f398011d96dc38f167967df68fc (172,977,931 bytes)
Superseded binding (void): build 7c105c0c-e0dc-4dbf-9530-3a9dccd90e9d, installer 073f15f4…f004, manifest e45899b5…f1c, source c823724
```

What carries forward unchanged: everything cleared in `Docs/BooksArranger_CodeReview_v0.16.5_2026-10-17.md` (`b6cae4c..9e1664ff`), with its open Major and Minor findings. Neither delta touches any of them.

## Release questions (reporting-only)

Answered at `c823724`; still true at `7619d12` unless noted.

1. **No change to conversion, verification or deletion: yes.**
   - `audio_pipeline.py`: every hash, comparison, refusal and its order is unchanged. The new hooks run only after the real work: `on_bytes` after `value.update`/`write`, and `PcmSeconds.feed` passes the bytes to the proof (or `Fanout`) before counting.
   - The only changed media command is the normalize step (`:527`). It gains `-progress pipe:1 -stats_period 1 -nostats`, and its stdout moves from a file to the drain pipe. These are the same options the encode already uses (`:764`) with the same bundled ffmpeg, and the output, `-n` and filter are unchanged.
   - `cover.stat()` (`_create_private`) reads the protected copy that was just made. It is harmless.
   - `audio_jobs.py` checkpoint: a measurement still returns before anything is journaled. Validation is now stricter: only known phase and unit pairs, with keys whitelisted.
   - `source_cleanup.py`: three in-memory lines (`:86`, `:309`, `:351`). There is no change to verifying or removing originals.
   - `merge_service.py`: a status label (`checking` → `recovery copies`) and a `report=` keyword on `publish`. Nothing else in the code or the desktop reads the old `checking sources` label for a decision.
   - Retry: only the refusal text changed.
   - `7619d12`: the new `try/except` blocks wrap only the progress callback. `PcmSeconds.feed` still calls `inner.feed` (the proof) outside the `try`, so a proof failure still raises.
2. **No new catalog writes on hot paths: yes. New lock use: yes, and it is bounded, with no deadlock.**
   - Progress writes only in-memory dicts. The new readers (`_research_pass`, `activities`, `published_check`) only read.
   - The one new lock use is the existing `AudioJobs._lock` (an RLock). It is now also taken from the ffmpeg drain threads, at most twice a second per step plus once per track. It is held only for a dict assignment.
   - No holder of `_lock` waits on the worker or on ffmpeg: `close()` lets go before `join`. The worker never holds a SQLite write transaction while it reports. So there is no lock-order inversion.
   - `7619d12`: measured reports now only try the lock (`acquire(blocking=False)`) and drop the tick when it is held, so a drain thread never waits on it. See m1 (fixed).
3. **Progress code itself cannot raise into a job; delivery could (m1, fixed in `7619d12`).**
   - Every value comes from `StepProgress.update`. It clamps `completed` to 0..total, drops a total that is not finite or not positive, clamps `item`/`items` to ints, and always sends a unit that matches `MEASURED`. So the checkpoint validators cannot reject anything the pipeline sends.
   - `EncodingProgress` sends no unit, which defaults to `seconds` for `encoding`, so it still passes.
   - The delivery exposure (a drain thread blocked past `run_owned`'s 3 s join) is closed by the try-acquire. Report exceptions are now also contained at all three reporters.
4. **Status payload bounded: yes.**
   - `activities()` returns at most three rows: one conversion or cleanup row, one identity row and one scan or research row. Each has fixed keys. Its strings are a title, a library label, the current scan path and a research source and stage.
   - The `started_at` memo is pruned to the rows seen on each call.
   - Per-job `progress` is now limited to 8 whitelisted keys. Before, it passed through `**measured`.
   - `published_check` and `research_pass` are a few integers each.
   - The unbounded parts of the payload (the `jobs` list and `scan_issues`) were already there and are not touched here.
5. **Frontend:** the new rows are written with `textContent` (`writeText`). There is no `innerHTML` in either delta. Titles and research text that came from the network cannot inject markup. The `7619d12` version badge is also `textContent`.

**Measured at `c823724`:** `test_progress_rows`, `test_progress`, `test_cleanup_resume` and `test_blocked_retry` ran 60 tests, all OK with 0 skipped. They ran through the same discover runner that `scripts/check-desktop.mjs` uses. `node` passed `test_progress_frontend.js`, `test_retry_frontend.js` and `test_automatic_frontend.js`. The worktree was clean before and after (bytecode writing disabled).

- Note: run as `python -m unittest tests.test_progress_rows`, it errors at `tests/test_progress_rows.py:160` (`import test_cleanup_resume`). That import only resolves under the discover runner. It is runner-dependent only, and the gate's runner passes.

## Fix delta `c823724..7619d12`

**m1 is fixed.**

- `audio_jobs.py:599-601`: the measured branch of `checkpoint` now does `if not self._lock.acquire(blocking=False): return`, then writes the progress dict and releases the lock in `finally`.
  - The lock is an RLock, so the worker thread, which may already hold it, still succeeds.
  - Validation still runs before the lock. Nothing is journaled on this branch.
- Every drain-thread reporter reaches only this branch:
  - `StepProgress` reports and the encode's `EncodingProgress` (`audio_pipeline.py:771`) all send `{'progress': …}`.
  - The stage branch (`:603`, still blocking) is called only from the worker, which is not under a drain join.
- Exceptions are contained in `StepProgress.update`, `PcmSeconds.feed` (callback only; the proof still raises) and `EncodingProgress.feed` (callback only). A rejected report can no longer fail a step.

**Measured at `7619d12` (2026-10-17):**

- Python: 83 tests, all OK with 0 skipped, through the gate's discover code (`-I -B`). The patterns were `test_progress_rows`, `test_progress`, `test_cleanup_resume`, `test_blocked_retry` and `test_status_snapshot`. This includes the new `LockedQueueTests`.
  - The interpreter was Python 3.14.8 from PATH, not the pinned `scripts/qa-runtime.json` interpreter.
- Node: all eight `tests/test_*.js` frontend scripts passed.
- **Positive control:** `LockedQueueTests.test_normalize_completes_while_the_queue_lock_is_held` was run against the pre-fix `audio_jobs.py` from `c823724`, loaded in place of the current module.
  - It **fails** with `Owned encoding progress has not finished draining`, which is the exact m1 failure. It passes at `7619d12`.
  - The test asserts that the lock really was held during normalizing, and that no drain-thread report waited more than 0.5 s.
- The worktree was clean after all runs.

**m5 is fixed.** `automatic_processing.py:192-201`:

- The whole `_research_pass` body is inside `try/except Exception: return None`.
- A checkpoint that is not a dict gives `None`. List members that are not strings are ignored, and a non-list value counts as empty.
- The new test cases cover a list checkpoint, nested lists, a dict value, a string value, `None` and invalid JSON.
- The checkpoint is still parsed again on every research poll. That is a small cost and is not counted as a finding.

**Version badge:**

- `renderVersion()` in `web/app.js` is now the only writer of `#version`. It uses `textContent`, and the badge is hidden when there is no version string.
- `[hidden]{display:none!important}` in `style.css` beats `.badge`, so an empty badge cannot show as a blank pill.
- `desktop-ui.js` no longer writes the badge.
- `desktop/main.js` still sends `engineVersion` over `books:status` (`:440`, `:511`), but nothing reads it now. It is dead and harmless.

**Accepted behaviour:** under contention a progress tick is dropped. That can include a step's final forced tick, so a row can lag briefly until the next report or stage change. This is display only.

**No regression found:**

- No change to conversion, verification, publish or deletion.
- No new lock, no new I/O and no new route.
- No Electron or `desktop/` change.

## Artifact binding (lean, 2026-10-17)

This was read-only. Nothing was installed, launched or extracted.

- `sha256(dist/release-artifacts.json)` = `08ddf425…24d4`, equal to the brief.
  - Manifest: version `0.16.6`, `source_head` `7619d12f6ba9fdb99202f48786155fdab92ef031`, `build_id` `bcc7c6fd-56ad-4c26-bb5f-d04264ff79e0`.
  - It also records `payload.verified` true, shell and backend versions `0.16.6` and `installer_equivalent` true.
- The installer's SHA-256 (`d6727de6…68fc`) and size (172,977,931 bytes) equal its manifest entry and the brief.
- Eleven product files in `builds/bcc7c6fd…/win-unpacked/resources/backend` equal the `7619d12` git blobs (`git hash-object --path`):
  - `audio_jobs.py`, `audio_pipeline.py`, `automatic_processing.py`, `conversion_progress.py`, `merge_service.py`, `source_cleanup.py` and `web_server.py`;
  - `web/app.js`, `web/desktop-ui.js`, `web/index.html` and `web/style.css`.
- `desktop/` is not in either delta.
- **Not redone in this lean pass:** the 7z carve, the product-digest recompute and the ASAR comparison.

## Rubric

Severity tags and the always-blocking floor are those in `Team/Docs/ProcessRules.md`, Severity definitions.

### 1. Security
Pass.
- There is no new shell-out argument built from input; the normalize options are constants.
- There is no new route and no Electron change.
- The new UI text, including the version badge, is written with `textContent` only.

### 2. Correctness & Logic
Concerns.
- m4 (Minor): see Finding rollup.

### 3. Crash / Stability Safety
Concerns.
- m1 (Major): fixed in `7619d12`.
- m5 (Minor): fixed in `7619d12`.
- m2 and m6 (Minor): see Finding rollup.

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
- `_research_pass` now tolerates any checkpoint shape.

### 7. Maintainability
Skipped by brief.

### 8. Doc/Code Drift
Skipped by brief.

### 9. Build & Release Hygiene
Pass.
- The version bump and lockfile are in one commit (`c823724`).
- The fix stays at `0.16.6`. No `v0.16.6` tag exists, and the latest tag is `v0.16.5`.
- `check-desktop.mjs` runs `test_progress_rows.py`, which now includes the m1 regression test.
- The artifact is bound to `7619d12` as stated above.

## Finding rollup

- **m1 (Major) — FIXED in `7619d12`. `audio_pipeline.py:187-189` with `audio_jobs.py:597`. Progress delivery could fail an attempt.**
  - Every PCM decode reported through `checkpoint` → `with self._lock` on the ffmpeg drain thread.
  - `_lock` is held across SQLite calls with a 5 s busy timeout. If one waited more than 3 s just as an ffmpeg run exited, `drain.join(3)` timed out. The attempt then failed with `ValidationError('Owned encoding progress has not finished draining')`, which is not retryable.
  - Fixed by a non-blocking acquire that drops the tick. A regression test fails on the pre-fix code and passes on the fix; see Fix delta.
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
- **m5 (Minor) — FIXED in `7619d12`. `automatic_processing.py:194-196`. Narrow guard in `_research_pass`.**
  - Its guard caught only JSON parse errors. A checkpoint of an unexpected shape could have raised out of `status()`.
  - The body is now fully guarded, and the input shape is checked.
- **m6 (Minor, new in `7619d12`), `audio_pipeline.py:43-44`, `:54-55` and `:157-158`. Progress failures are silent.**
  - All three containment blocks are `except Exception: pass`, with no log.
  - Before, a progress-contract drift (for example a phase or unit mismatch with `MEASURED`) failed the attempt loudly. Now in production that row just stops moving, with no diagnostic.
  - `RealConversionTests` still catches that drift in the gate.
  - Fix: log the first swallowed exception once per step (the class and message only).
- Open Critical: 0.
- Open Major: 4. All are carried from v0.16.5: t1, s3, r1 and `working_lifecycle.py:228`.
- Open Minor: 23. m2, m3, m4 and m6, plus the 19 carried from v0.16.5.
- **Always-blocking floor: intact.**
  - No change to verifying or deleting originals.
  - No new writes outside the library, the recovery root and the catalog.
  - No Electron change and no secret exposure.
  - No risk to repo history.

Major and Minor findings are logged for Ender's next cycle and do not gate this release.

## Verdict

- Total Critical: 0
- Total Major: 4
- Total Minor: 23

**Verdict:** RELEASE CLEAR

This clearance covers `9e1664ff50522a1afc92790f69f2efcba3240675..7619d12f6ba9fdb99202f48786155fdab92ef031` and the installer `Books-Arranger-Setup-0.16.6.exe` (build `bcc7c6fd-56ad-4c26-bb5f-d04264ff79e0`, SHA-256 `d6727de6a42d34ad76c462b80f46ff3889ae3f398011d96dc38f167967df68fc`), bound by the manifest hash in the header.

It covers construction only. Futaba's QA GO is the independent behaviour gate.

The earlier `c823724` binding (installer `073f15f4…f004`) is void. A rebuild, or any product-file change after `7619d12`, voids this artifact binding.
