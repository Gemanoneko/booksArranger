# Code Review — Books Arranger v0.16.1

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-17
Tool: Books Arranger
Release: v0.16.1
Status: FINAL; accumulated range, the status-fix delta and the actual installer artifact reviewed
Commit range: 95febcdd4f4de4ffb59a3507053c4eb86f53936a..78b442135b70eb2d061a8f5d3571f706a1b256ae
Accumulated committed diff: 116 files, +13953 / -223
Previously cleared (v0.16.0 report): 95febcdd..8d6272593645226af711e2eb21a2c0d731d6d3d3; 8d62725..e5ca65d is Docs-only (the v0.16.0 review, QA report and acceptance index)
Delta reviewed in full here: e5ca65d16097bc6cd96265308afc440449ba5ffc..78b442135b70eb2d061a8f5d3571f706a1b256ae (17 files, +876 / -37)
  7efdde2af1e97aa85a2935af1a6f01dfab5d2d58 status pile-up fix (14 files)
  78b442135b70eb2d061a8f5d3571f706a1b256ae version bump to 0.16.1 + CHANGELOG (3 files)
Stand-down dimensions: none
Release source commit: 78b442135b70eb2d061a8f5d3571f706a1b256ae
Release product tree SHA256: b9c6db7276787c2d5ff6c484975c991fc511cb6e4a869c88a664ae79f5f4de11
Release artifact manifest SHA256: 21c07853ab5c33e4d388bac0cd53a156f0a990faa86c3c83527ca7aec00d759a
Release installer: dist/builds/7b6d2a35-8394-44d2-85b0-13dfdf589235/Books-Arranger-Setup-0.16.1.exe
Release installer SHA256: 24e67a05aba2322b1fa2db61eaf6ae34b102c9c522d5c92494836127890370cb (172,936,681 bytes)
```

v0.16.0 was never tagged or published. Its source (`95febcd..8d62725`) was cleared in `Docs/BooksArranger_CodeReview_v0.16.0_2026-10-15.md`, and those findings still stand; they are not re-derived here. The delta `e5ca65d..78b4421` is reviewed in full below. The status-fix delta review (no Critical; M1 and m1–m4, not filed as a separate report) is closed out item by item.

## Delta e5ca65d..78b4421

### Status-fix findings and the release questions

1. **M1: snapshot timed from computation start, invalidated by every POST and desktop control, including a computation in flight. Closed.**
   - Engine. `SharedSnapshot` (`merge_service.py:39-68`) records `started` before computing and caches with `_at=flight['started']` (`:63`). `invalidate()` (`:50`) bumps the generation, drops the value and detaches `_flight`. A computation finishing later is cached only if its generation still matches (`:63`), and no reader arriving after the invalidation can join it.
   - Engine invalidation point. `Handler.response()` (`web_server.py:143-148`) consumes `status_control`. That flag is set for every POST that passes `trusted(token=True)` (`web_server.py:421`) and for every desktop control that passes `desktop_trusted()` (`desktop_backend.py:184`). So every exit (200/202/400/409/500) invalidates before the reply bytes leave. The control's own work runs before `response()`, so any computation that started before the reply is either dropped or detached.
   - Shell. `desktop/status-flight.js` stamps `sentAt` before the fetch and remembers an answer only when `born === generation` (`:18`). `invalidate()` clears both `last` and `flight` (`:37`). `engineRequest` (`desktop/main.js:241-246`) invalidates before and after the Quit and update POSTs. The update park loop's status GETs also go through it, with `maxAge: 0`.
   - Positive controls. I ran five mutants on a private `git archive` export, and the shipped tests caught every one:
     - engine caches a detached computation: 1 failure;
     - engine ages the answer from finish instead of start: 1 failure;
     - `response()`/`invalidate_status` disabled: 2 failures;
     - shell remembers a stale generation: 2 failures;
     - shell `invalidate()` leaves the request joinable: 1 failure.
   - Limits (not findings):
     - A reader that joined before the invalidation still gets the pre-control answer. This is by design: it asked before the click.
     - Page controls invalidate the engine, not the shell's desktop-status cache (at most 1 s). That cache feeds the tray, the desktop panel and the Restart-to-update enablement. `prepare_update` (`desktop_backend.py:132-144`) re-checks idle freshly, so this is safe.
     - Stop-now bypasses `engineRequest`; see n5.
2. **m1: shell generation counter. Closed.** The counter works as described above. The request's `.finally` clears `flight` only when it is still that same request, so a detached request cannot clear a newer one. Tests: `tests/status-flight.test.mjs:68-86`.
3. **m2: monotonic clock. Closed.** The shell uses `performance.now()` (`desktop/status-flight.js:12`, age check `:26`) and the engine uses `time.monotonic` (the `SharedSnapshot` default). Both treat a negative age as expired. Tests: `status-flight.test.mjs:88-104` and `tests/test_status_snapshot.py:73-81`.
4. **m3: bounded 4 s wait, "unavailable", 503, `busy:null`. Closed as specified; Quit stays safe.**
   - Waiters use `flight['done'].wait(4.0)` and then raise `StatusUnavailable` (`merge_service.py:66`). `STATUS_WAIT` is 4.0 s, below the shell's 5 s timeout, and a test asserts that.
   - `/api/state` answers 503 "Status is still updating; retrying" (`web_server.py:258-259`). `StatusUnavailable` is a `RuntimeError`, so the earlier ValueError/TypeError 400 branch cannot swallow it.
   - Desktop status answers `status:'unavailable'`, `busy:null`, `idle:false`. Phase and error are still read under the lock (`desktop_backend.py:53-79`).
   - **Quit safety, confirmed.**
     - `busy` decides only two things: whether the shell asks "Quit after the current book?" and which tray text it shows (`desktop/main.js:358-370`).
     - The shell always sends `POST /api/desktop/quit`. The engine's `quit()` always calls `merge.drain()`, which sets `AudioJobs`' drain event: the current book finishes and nothing new starts (`desktop_backend.py:81-99`, `audio_jobs.py:261-265`). `_park` then waits for `drained()`.
     - Stop-now is reachable only from Windows session-end (`desktop/main.js:303`).
     - No path leads from `busy:null` to skipping or shortening the drain.
     - `watchQuit` still sees phase `blocked` while status is unavailable.
     - `idle:false` keeps Restart to update unavailable, and the update fence re-verifies idle freshly.
   - Limits: n1 and n2.
5. **m4: recipe wording. Closed.**
   - `Docs/BooksArranger_RealCatalogCopy_QA_Recipe.md:12` now carries the correction.
   - `:19-21` name the read-only `is_dir` checks on `Z:`. They match `source_cleanup.py:146`, where `restore_available` checks each original's `parent.is_dir()`.
   - C2 (`:29`) says that private roots do not prevent those checks.
   - The recipe still rests its safety on the C4 before/after fingerprint, not on the argument.
6. **Test races: test-only and deterministic. Confirmed.**
   - Only `tests/test_automatic_processing.py` and `tests/test_web.py` changed for these. No product file is involved.
   - Before the fix, the two automatic tests had two stoppers racing between a status snapshot and its assertions: the `wait_auto` loop and the fake `stop_event.wait`. Now `wait_auto(stop_when_held=False)` leaves the fake as the only stopper. Each stop decision and each recorded wake comes from one snapshot.
   - `test_web` now joins the server's own shutdown thread (5 s, asserted) before tearDown's second close.
   - What timing remains is bounded waits that fail loudly: the existing 5 s `wait_auto` deadline and the 5 s join.
   - Focused run on a private export, 5 consecutive runs, 31/31 cases each, no failures, errors or skips. The 31 cases were the three changed automatic tests, 8 neighbouring wait/retry/cleanup tests and all 20 `test_status_snapshot` cases. `status-flight.test.mjs` passed 11/11.
   - I did not run `test_web` here because it binds a local listener while Futaba's QA is live. The new tests' own timing assumptions are n4.
7. **Version bump and changelog. Complete and accurate, with one wording slip.**
   - `package.json` and both `package-lock.json` root version fields read 0.16.1, in one commit (`78b4421`). No other lockfile line changed.
   - The backend `VERSION` is generated from `package.json` at build time; the packaged value is 0.16.1.
   - 0.16.1 is newer than the latest tag, v0.15.0; v0.16.0 was never tagged.
   - The CHANGELOG entry is accurate in substance. The wording slip is n5.

### Other delta checks

- **Replacement snapshot** (`replacement_jobs.py:28-44`, `merge_service.py:192-195`).
  - The snapshot is thread-local, scoped to one `state()` computation, nesting-safe and reset in `finally`. Other threads read fresh; a test covers this.
  - `_state()` writes no replacement relations.
  - `structural_guard` re-reads the relation row and requires equality (`replacement_jobs.py:155-160`). A stale snapshot can therefore only make it return False.
- **`has_unfinished()`** (`audio_jobs.py:290-293`) guards recovery deletion (`_recovery_idle`).
  - Its predicate is the same as the old scan: raw `state IN ('pending','running')` over the same table and rows.
  - The connection is closed by `_Connection.__exit__`.
  - One difference: a row with an unparseable manifest no longer makes the gate throw. That was incidental, not a designed guard.
- **`web_server` now imports `merge_service` at module level** (it was lazy).
  - No entry module fails with a circular import: I checked `web_server`, `app_launcher`, `desktop_catalog`, `desktop_backend`, `desktop_host` and `merge_service`.
  - Importing it creates no files.
  - It adds about 0.1–0.2 s to the first-run read-only folder check, which has a 15 s budget.
- **Invalidation fires on every trusted POST, including read-only ones** (`/api/inspect`, `/api/open-folder`, the 45 s draft lease).
  - Detached computations keep running, so a burst of POSTs can overlap computations.
  - New computations start only when a reader arrives: the page about every 0.8 s after its last answer, the shell at most once per second. Concurrency is therefore bounded by readers, not by POSTs.
  - This is not the old unbounded pile-up.

## Artifact binding (independent, 2026-10-17)

All checks were read-only on the artifact, with private scratch copies only. Nothing was installed, launched, packed or rebuilt.

- `sha256(dist/release-artifacts.json)` = `21c07853…d759a` (full value in header). It equals the `manifest_receipt` in the build's own `build-cache/builds/abec96d0-001d-4887-91f7-d174da532be4/metadata-rotation-complete.json`. The 0.16.0 manifest is retained beside it as `release-artifacts.json.previous-61d2b050-…`.
- Manifest contents:
  - schema `books-desktop-artifacts-v1`, version `0.16.1`, `source_head` `78b442135b70eb2d061a8f5d3571f706a1b256ae`, `build_id` `7b6d2a35-8394-44d2-85b0-13dfdf589235`;
  - `payload.verified true`, `installer_equivalent true`, shell and backend version `0.16.1`;
  - 219 payload files, 581,940,644 bytes;
  - `payload.manifest_sha256` `f1920fd8…d9cc`, recomputed and equal.
- I recomputed `product_digest` `b9c6db72…de11` with the tool's own `productTree` over `git ls-tree` at `78b4421`. Both the `-z` release-flow parser and the build-manifest parser give the same value. As a positive control, the digest at `e5ca65d` differs. The worktree is clean at `78b4421`.
- The installer, blockmap and `latest.yml` SHA256 and sizes equal the manifest's three artifact entries and `producer-receipt.json`. Both `sha512` values in `latest.yml` equal the installer's actual SHA512.
- I checked the installer bytes structurally, without 7za:
  - exactly one 7z signature, at offset 171,357, with valid start-header and next-header CRCs;
  - physical size 172,373,511; tail 391,813;
  - the NSIS data-block length just before the signature is 172,373,511, with the compressed bit clear;
  - the carved SHA256 is `7098989c33817523abed39fb013a6ff8674d4de77b3b69761fbfd5ca9f1a7ca0`, equal to the build's `producer-receipt.json` entry for `nsis-archive/bf119499-…/app-64.7z`. The retained copy itself was cleaned after the build; its receipt remains.
- I extracted the carve privately. The 219 extracted files are **byte-identical** to `payload.files`, with nothing missing, extra or different. `win-unpacked` is likewise identical.
- Against the 0.16.0 payload, 53 of 219 files differ, and no file was added or removed:
  - `Books Arranger.exe` (version resource) and `resources/app.asar`;
  - the five changed backend sources (`audio_jobs`, `desktop_backend`, `merge_service`, `replacement_jobs`, `web_server`) and `VERSION`;
  - 45 `.pyc` files.
  - The python/ffmpeg runtime map is identical. This is exactly what the source delta predicts.
- Source binding of the packaged payload:
  - All 51 non-cache backend files equal the `78b4421` git blobs under git's own clean filter (`git hash-object --path`). 30 of them are checked out with CRLF line endings by `core.autocrlf=true`. Their shipped bytes are identical to 0.16.0's, including the protected `public_source_leads.json` (`cfa08525…`).
  - All 11 ASAR application files equal the git blobs, including the new `desktop/status-flight.js`. The ASAR `package.json` is the builder-stripped subset; every shared field is equal (version 0.16.1, `electron-updater` 6.8.9).
  - The shipped `desktop/main.js` keeps `contextIsolation:true`, `nodeIntegration:false` and `sandbox:true`.
  - The packaged `app-update.yml` feed is `Gemanoneko/booksArranger`, `releaseType: release`.
- Native receipt `build-cache/builds/abec96d0-…/native-operation-result.json`: mode `build`, `root_exit_code 0`, `native_job_closed true`, `active_processes_after 0`.

Behaviour of the packaged app on the real-catalog copy is Futaba's QA and not part of this verdict.

## Summary

I reviewed every file in the delta:
- product code: `audio_jobs.py`, `desktop/main.js`, `desktop/status-flight.js`, `desktop_backend.py`, `merge_service.py`, `replacement_jobs.py`, `web_server.py` and `scripts/check-desktop.mjs`;
- the four test files;
- the Brief, the QA recipe, the CHANGELOG and the version files.

Each status-fix finding and release question was checked against the code and, where possible, against a mutant that the tests must catch. The new installer is bound to `78b4421` independently of the build's own receipts.

The v0.16.0 clearance of `95febcd..8d62725` carries forward. The only reviewed files that changed afterward are the five backend sources and `desktop/main.js` in this delta, and they are reviewed here.

I did not run the integrated `npm run check`, because it writes inside the worktree. I found no integrated-check receipt at `78b4421` in the worktree. The focused runs above were made on a private export.

## Rubric

Severity tags and the always-blocking floor are those in `Team/Docs/ProcessRules.md`, Severity definitions.

### 1. Security

Pass. The delta adds no IPC channel, route, shell-out, delete path or credential handling. `status_control` is set only after the existing trust checks, and invalidation is harmless even if triggered. The packaged Electron flags and update feed are confirmed in the actual artifact.

### 2. Correctness & Logic

Concerns (Minor only). M1 and m1–m4 are verified closed (see the delta section).

- [Minor n1] `desktop/main.js:353,358-370`: The Quit confirmation decides from a cached answer, up to about 2 s old (the shell's 1 s since the request was sent, plus the engine's 1 s since its computation started). It also treats `busy:null` as "not converting". So when status is unavailable, or a book started in the last couple of seconds, "Quit after the current book?" is skipped, and the tray says "quitting" instead of "quitting after the current book". The engine still drains, so this is safe, but the user loses the chance to cancel. Read with `maxAge: 0` for this decision, and treat `busy === null` / `status === 'unavailable'` as unknown, which should ask.

### 3. Crash / Stability Safety

Concerns (Minor only). Pile-up is bounded: one shell request at a time, one engine computation per generation, and waiters bounded at 4 s. Every failure path below fails closed.

- [Minor n2] `merge_service.py:57-66` with `desktop/main.js:511` and `web/desktop-ui.js:13-14`: the 4 s bound covers waiters only. The thread that owns a computation answers only when it finishes. Because the page and the shell alternate, the desktop status thread is the owner roughly half the time. If one computation exceeds the shell's 5 s timeout (the recipe's own NAS spin-up case), the shell's request fails. Then:
  - `books:status` reports phase `unavailable`, which `desktop-ui.js` treats as quitting. The window shows "Waiting for the engine checkpoint…" and disables the mutating controls. This mapping existed before this release.
  - A Quit at that moment is refused with "did not confirm a safe Quit".

  It clears on the next answer. It is the original symptom, now limited to computations longer than 5 s. Consider computing in a dedicated worker, so that every HTTP reader is bounded, and stop mapping a failed status read to the quitting panel.
- [Minor n3] `web/app.js:58-68` with `web_server.py:258-259`: a 503 goes through the page's generic disconnect path. It:
  - closes an open recovery-delete confirmation dialog;
  - disables controls for one poll and shows "Connection interrupted…";
  - appends "Status is still updating; retrying" to the message line, where it stays after recovery, because `clearConnectionNotice` does not clear `#message`.

  The path fails closed and existed before; it is newly reachable. The wording and the sticky message mislead.

### 4. Performance

Concerns: one Major carried forward from v0.16.0, advisory. The delta itself passes. It computes state once per poll, uses an existence query per cleanup row, reads replacement relations once per computation, and serves cached copies cheaply (recipe measurement: 0.02 s).

- [Major, advisory, carried] `working_lifecycle.py:228` (and `:411`): reference rescans scale with catalog size times disposable-file count. The file is unchanged since v0.16.0.

### 5. State & Data Safety

Pass. The recovery-delete gate predicate is unchanged (`has_unfinished` is equivalent; see above). The replacement snapshot can only make lineage checks fail closed. Cached status never feeds a fence: `prepare_update`, control replies and `drain()` all compute fresh `state()`. The Quit drain does not depend on shell-side status. Nothing new is written or deleted.

### 6. Input Handling

Pass. The delta adds no new input surface. `/api/state` keeps its library and query validation, and the desktop routes keep the empty-body and token checks.

### 7. Maintainability (no Critical findings on its own)

Concerns (Minor only). The single-flight designs are small, commented and enrolled in the ordinary checker (`test_status_snapshot.py`, `status-flight.test.mjs`, and the syntax list, now 7 files).

- [Minor n4] `tests/test_status_snapshot.py:39,67,128-131`: these cases rely on real time. Threads must arrive within 0.2–0.3 s, and a real 1.0 s `max_age` applies. On a loaded machine a late thread starts a second computation, and `len(calls)==1` or `call_count==1` fails. `:67` is the tightest: a caller arriving after the failure recomputes. Use a barrier or arrival counter and an injected clock, as the other cases do.
- [Minor, carried 0.16.0-m2] `scripts/check-desktop.mjs:19-23`: `tests/test_build_external_tools.py` is still not enrolled. The build-fix negatives (carve refusals, the `allow_child_rename` share, the Job settle loop) still have no tests.

### 8. Doc/Code Drift (no Critical findings on its own)

Concerns (Minor only).

- [Minor n5] Three small inaccuracies:
  - `merge_service.py:355` says "an indexed existence check", but `audio_jobs` has no index on `state`. The query is a narrow scan, cheap at this size.
  - `Docs/BooksArranger_Brief.md:303` says the shell drops its answer before and after "a desktop control", but stop-now (`desktop/main.js:402`) uses raw `request()`. This is harmless, because the shell exits within 8 s.
  - `CHANGELOG.md:9` says replacement lookups no longer reload "the whole job table". In fact they re-read the replacement-relations table.

  Elsewhere, the Brief's freshness, bound and measurement text matches the code. The recipe's m4 correction matches `source_cleanup.py:146`.

### 9. Build & Release Hygiene

Pass, with Minor concerns carried forward. The version bump, the lockfile in the same commit, and the CHANGELOG are complete. No dependency changed. The worktree is clean at `78b4421`. The installer is bound to the source and the payload was reproduced from the installer bytes (see Artifact binding). This review does not claim the publication run.

- [Minor, carried 0.16.0-m1] `scripts/build_phase.py:103-121`: the carve's size-sum and listing checks are partly self-consistency, and NSIS framing is not checked in code. I re-checked both independently for this artifact: one signature, and the framing length equals the physical size.
- [Minor, carried 0.16.0-m3] `scripts/build_phase.py:99-107`: an implicit coupling to the reduced `7zip-bin` 5.2.0 `7za`, which fails closed.

Release-path requirements in the tool's own contract (`scripts/release-contract.mjs:24-36,68-76`, `scripts/release-flow.mjs:38-46`), for Sully and Futaba. These are not findings, and each fails closed:
- Only Docs-only or CHANGELOG-only descendants of `78b4421` may be released with this installer. Any version, lock or product-file change alters the product digest.
- `Docs/BooksArranger_ReleaseAcceptance_v0.16.1.json` needs:
  - exactly the keys `schema`, `version`, `qa` and `review`;
  - version `0.16.1`;
  - `review` set to `Docs/BooksArranger_CodeReview_v0.16.1_2026-10-17.md`;
  - `qa` matching `^Docs/BooksArranger_QA_v0\.16\.1_\d{4}-\d{2}-\d{2}\.md$`. A `_QAReport_` name is refused by the tool's contract, although the studio precondition script accepts both.
- Futaba's report needs, like this one:
  - exactly one line starting with `**Verdict:**`;
  - exactly one source-commit pin line naming `78b442135b70eb2d061a8f5d3571f706a1b256ae`;
  - exactly one artifact-manifest line naming `21c07853ab5c33e4d388bac0cd53a156f0a990faa86c3c83527ca7aec00d759a`.

## Finding rollup

- Open Critical: 0.
- Open Major: 1 (advisory, carried from v0.16.0): `working_lifecycle.py:228`.
- Open Minor: 8.
  - New: n1, n2, n3, n4, n5.
  - Carried from v0.16.0: m1, m2, m3.
- Status-fix review findings: M1, m1, m2, m3 and m4 are all closed.
- Always-blocking floor: intact.
  - No machine harm: the Electron flags are unchanged in the actual artifact, and there are no new writes or deletes.
  - No secret exposure.
  - No risk to repo history.

Major and Minor findings are logged for Ender's next cycle and do not gate this release.

## Verdict

- Total Critical: 0
- Total Major: 1
- Total Minor: 8

**Verdict:** RELEASE CLEAR

This clearance covers the accumulated range `95febcdd4f4de4ffb59a3507053c4eb86f53936a..78b442135b70eb2d061a8f5d3571f706a1b256ae`, and the installer `Books-Arranger-Setup-0.16.1.exe` (SHA256 `24e67a05aba2322b1fa2db61eaf6ae34b102c9c522d5c92494836127890370cb`) bound by manifest SHA256 `21c07853ab5c33e4d388bac0cd53a156f0a990faa86c3c83527ca7aec00d759a`.

It covers construction only. Futaba's packaged real-catalog-copy QA GO is the independent behaviour gate.

A rebuild, or any product-file change after `78b4421`, voids this artifact binding and needs a fresh binding check.
