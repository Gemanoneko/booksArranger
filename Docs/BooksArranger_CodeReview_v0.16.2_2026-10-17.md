# Code Review — Books Arranger v0.16.2

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-17
Tool: Books Arranger
Release: v0.16.2
Status: FINAL; accumulated range, the between-books fix delta and the actual installer artifact reviewed
Commit range: 95febcdd4f4de4ffb59a3507053c4eb86f53936a..d8349715dd03afe2cc12ea9db59cffd4c4c38fd0
Accumulated committed diff: 119 files, +14483 / -225
Previously cleared (v0.16.1 report): 95febcdd..78b442135b70eb2d061a8f5d3571f706a1b256ae; 78b4421..5420254 is Docs-only (the v0.16.1 review, QA report and acceptance index); v0.16.1 is tagged at 5420254e79f239f7df0f737966c8652e4db30f4a
Delta reviewed in full here: 5420254e79f239f7df0f737966c8652e4db30f4a..d8349715dd03afe2cc12ea9db59cffd4c4c38fd0 (5 files, +189 / -5)
  3360cf0e68dbf036d60535af3548ee3054fd330c between-books status fix (merge_service.py, tests/test_automatic_processing.py)
  d8349715dd03afe2cc12ea9db59cffd4c4c38fd0 version bump to 0.16.2 + CHANGELOG (3 files)
Stand-down dimensions: none
Release source commit: d8349715dd03afe2cc12ea9db59cffd4c4c38fd0
Release product tree SHA256: 02b319443f2e8f57756eafe67c46e1615b351311723ac7a836c1778fa3bff0fa
Release artifact manifest SHA256: 03c2c9dce5e834df2ec18890a9411e34e84eaeb87e1dd1e0f62e93f811d347cb
Release installer: dist/builds/ace099b6-d69d-42be-8da3-47ffa8a29751/Books-Arranger-Setup-0.16.2.exe
Release installer SHA256: a485118afcbc4cacdf76504d90910922b85388fc0cc63605866b2a90be5a8356 (172,937,209 bytes)
```

The source `95febcd..78b4421` was cleared in `Docs/BooksArranger_CodeReview_v0.16.1_2026-10-17.md`. Its findings still stand and are not re-derived here. `78b4421..5420254` touches only `Docs/` (3 files). The delta `5420254..d834971` is reviewed in full below.

## Delta 5420254..d834971

### The fix (3360cf0)

- **Root cause, confirmed against the code.**
  - `_after_completed` (`merge_service.py:458-473`) runs on the converter thread.
  - It inserts the cleanup row as `waiting` before it sets `cleanup.current` (`:466`).
  - It clears the marker in `finally` (`:471`). Only after that does it prune and loop to the next book's `running` update (`audio_jobs.py:320`).
  - The old override (`merge_service.py:211-213` at `5420254`) looked only at the marker and the cleanup thread. So a read in the gap before the marker was set, or a read that straddled the clear, said "Paused" while the converter was alive.
  - The automatic waiting loops (`automatic_processing.py:349`, `:441`) treat "Paused" as a stop. They call `merge.pause()` (`:449`), which interrupts the book that has just started.
- **Change.**
  - `_worker_active()` (`merge_service.py:197-203`) is true when any of these holds: the marker is set, the cleanup thread is alive, or the converter thread is alive.
  - It is sampled before the durable read (new, `:210`) and after it (kept from v0.16.1, `:224`).
  - The pending-cleanup override now uses it (`:225-227`).
  - A new `elif` (`:228`) handles `AudioJobs.status()`'s own "Paused" (converter dead at its read, books queued). It becomes Running, or Pausing when Stop is set, if a worker was seen at either sample.

### Release questions

1. **Can the fix hide a genuine stop? No.**
   - **Safety stops do not depend on the status label.**
     - A full disk (`audio_jobs.py:373-376`) and a working-file hold (`:312-316`, `:380-385`) set the stop event, then call `on_space_hold` / `on_working_hold`, which call `automatic.stop(force=True)` (`merge_service.py:118-119`).
     - Both waiting loops exit on `stop_event.wait` (`automatic_processing.py:348`, `:440`) before they read the state.
     - A user Stop takes the same path.
     - A user Pause (`web_server.py:354` → `merge.pause()`) sets the shared stop event (`merge_service.py:101`). Workers exit at their next checkpoint. The state reads Pausing while they are alive and Paused once they are gone.
     - Quit drains, and while draining `pause()` is a no-op. Quit also stops the automatic run directly (`desktop_backend.py:92-96`).
   - **A truly stalled queue still reads Paused.** With books queued and no worker at either sample, the read says Paused (`test_stalled_queue_with_no_worker_still_pauses_the_run`). Positive control: forcing `_worker_active()` to always return true makes 5 of the 9 new cases fail and 1 error. The process then hung on exit, because the automatic thread spun forever in its Pausing wait. That is the outcome the safety tests exist to catch.
   - **A dead thread reading as alive: not possible.**
     - `Thread.is_alive()` is false once the thread has returned, and nothing caches it.
     - A thread that exits during the read makes that one read say Running (through the before-read sample). The next read is fresh.
     - Both code paths that set `cleanup.current` clear it in `finally` (`merge_service.py:471`, `source_cleanup.py:174`), so the marker cannot stick.
   - **A hung worker reads Running or Pausing for as long as it is alive. This is not new.**
     - `AudioJobs.status()` (`audio_jobs.py:286-287`) already reports Running whenever the converter thread is alive.
     - `drained()` (`merge_service.py:270-273`) already waits on the same three facts.
     - The delta brings the one branch that ignored the converter into line. It adds no new way to wait forever.
   - **Restart guard and update fence** (`app_launcher.py:159-171`, used by `/api/shutdown` at `web_server.py:453`, `prepare_update` at `desktop_backend.py:138` and desktop `idle`).
     - In the original bug state a cleanup row is pending, so `cleanup_active` (`merge_service.py:259`) already refused a restart at `:164`. That outcome is unchanged.
     - The only newly refused case is the `elif` branch: books queued, the converter dead at the read, a worker seen at a sample. Each such worker ends on its own (the converter at queue end, the cleanup thread after its rows) or at the Pause the guard's own message asks for.
     - Both fences read a fresh `state()`, never the cached snapshot. So the refusal is correct and bounded by worker lifetime. It is never permanent unless a thread is hung, which already blocked a restart before this release.
     - **No restart or update is blocked incorrectly.**
   - **Other readers of Running/Pausing**: the scan-start gate (`web_server.py:99`), the automatic start gate (`automatic_processing.py:165-166`) and the desktop busy/Quit question (`desktop_backend.py:46`). All of them move toward refusing or asking, which is the safe direction.
2. **Thread-liveness races.** I found one race and it is masked: r2. Every other ordering I checked is covered:
   - **Inline cleanup.** Every step runs on the converter thread: enroll, marker, run, `finally`, prune, next book. The converter check therefore covers both the pre-marker gap and the post-clear gap.
   - **Cleanup thread hands back to the converter.** `after_drain` → `jobs.resume()` assigns and starts the new converter before the cleanup thread exits (`source_cleanup.py:175`, `audio_jobs.py:251-253`). `Thread.start()` returns only once the new thread is running.
   - **A worker started mid-read.** The after-read sample catches it.
   - **GIL.** The bundled runtime is a standard GIL build of CPython 3.14.8, so the attribute reads are atomic.
3. **Ender's residual is confirmed. It predates this release, and the delta neither causes nor widens it.** See r1 (Major, advisory). It is now the one remaining path to the reported symptom ("Paused — pending work saved" with no one asking), but no book is interrupted on this path.
4. **Test determinism: confirmed.**
   - **The new cases.** There are 9: 7 in `BetweenBooksStateTests`, plus `test_between_books_cleanup_gap_does_not_pause_the_run_or_stop_the_next_book` and `test_stalled_queue_with_no_worker_still_pauses_the_run`.
     - The fixture drives the real `_after_completed`, `_state` and `pause` over a real `AudioJobs` ledger. Every step waits on an Event, and no case relies on sleeps or real time.
     - Each case asserts its own precondition (the next book started, or the converter exited), so a wait that times out fails loudly instead of passing.
   - **Runs**, on a private `git archive` export of `d834971`, with the pinned QA runtime (`scripts/qa-runtime.json`, SHA256 `434b361f…` re-verified), `-I -B`. No failures, errors or skips in any of them:
     - the 9 cases, 20 times in a row;
     - the 9 cases, 3 rounds of 8 concurrent processes (24 runs under load);
     - the full `test_automatic_processing` and `test_status_snapshot`, 81 cases, 3 times.
   - **Positive controls.** I ran 9 mutants of `merge_service.py` against the 9 new cases:
     - full revert to the `5420254` file: 6 failures;
     - no before-read sample: 1 (the last-book straddle);
     - no after-read sample: 1 (cleanup resumed mid-read);
     - converter not counted: 2;
     - cleanup thread not counted: 2;
     - no `elif`: 1;
     - pending branch ignores Stop: 1;
     - always active: 5 failures and 1 error, then hung (see question 1);
     - the `elif` ignoring Stop: **survives all 81 cases** (r3).
   - **Not run.** `test_web`, `test_desktop_quit` and `test_status_read_contention` were skipped because they bind local listeners while Futaba's QA may be live. None of them changed, and the product delta does not touch what they cover.
5. **Version bump and changelog: complete and accurate.**
   - `package.json` and both `package-lock.json` root version fields read 0.16.2, all in one commit (`d834971`). No other lockfile line changed.
   - The packaged `VERSION` and the ASAR `package.json` read 0.16.2.
   - 0.16.2 is newer than the latest tag, v0.16.1. The tag v0.16.2 does not exist yet.
   - The CHANGELOG entry matches the code: the trigger, the effect, and that Stop, Pause, Quit, a full disk and a working-file problem still pause the run (verified in question 1).
   - The new comments at `merge_service.py:206-209` and `:224` are accurate. The docstring's ordering claim is not (r2).

## Artifact binding (independent, 2026-10-17)

All checks were read-only on the artifact, with private scratch copies only. Nothing was installed, launched, packed or rebuilt.

- **Manifest.** `sha256(dist/release-artifacts.json)` = `03c2c9dc…` (full value in header).
  - It equals `manifest_receipt` in the build's own `build-cache/builds/dd672b05-4dff-439f-997a-a3cb4f2d651f/metadata-rotation-complete.json`.
  - The 0.16.1 manifest is retained beside it as `release-artifacts.json.previous-19db6bc7-…`, SHA256 `21c07853…d759a`. That is exactly the value the v0.16.1 report bound.
- **Manifest contents.**
  - Schema `books-desktop-artifacts-v1`, version `0.16.2`, `source_head` `d8349715dd03afe2cc12ea9db59cffd4c4c38fd0`, `build_id` `ace099b6-d69d-42be-8da3-47ffa8a29751`.
  - `payload.verified true`, `installer_equivalent true`, shell and backend version `0.16.2`.
  - 219 payload files, 581,942,340 bytes.
  - `payload.manifest_sha256` `604c8708…9823`: recomputed, equal.
- **Product digest.** I recomputed `product_digest` `02b31944…f0fa` with the tool's own `productTree`, using both its `-z` release-flow parser and its build-manifest parser. Both give the manifest value.
  - Controls: `3360cf0` gives `3d4b7f3c…`, which differs because the version files changed.
  - `5420254` gives `b9c6db72…`. That differs too, and equals the v0.16.1 product digest, as it should, because `78b4421..5420254` is Docs-only.
  - The worktree is clean at `d834971`.
- **Release files.** The installer, blockmap and `latest.yml` SHA256 and sizes equal both the manifest's three artifact entries and `producer-receipt.json`. Both `sha512` lines in `latest.yml` equal the installer's actual SHA512, and its size line matches.
- **Installer bytes, checked structurally:**
  - exactly one 7z signature, at offset 171,358, with valid start-header and next-header CRCs;
  - physical size 172,374,045; tail 391,806;
  - the NSIS data-block length just before the signature is 172,374,045, with the compressed bit clear;
  - the carved SHA256 is `10f21f87d9e58b5ce0f7e3a2c3b2ad83530988b579f7fa9749b98b8a306ec9a4`, size equal. It matches the receipt entry `nsis-archive/5d6a5be8-…/app-64.7z`. The retained copy was cleaned after the build; its receipt remains.
- **Extracted payload.** I extracted the carve privately with the repo's own `7za`. The 219 extracted files are **byte-identical** to `payload.files`, with nothing missing, extra or different. `win-unpacked` is likewise identical.
- **Against the 0.16.1 payload**, 49 of 219 files differ, and none was added or removed:
  - `Books Arranger.exe` (version resource) and `resources/app.asar`;
  - `resources/backend/merge_service.py` and `VERSION`;
  - 45 `.pyc` files.
  - The python/ffmpeg runtime map is identical.
  - Inside the ASAR, only `package.json` changed (266 entries in each).

  This is exactly what the source delta predicts: `merge_service.py` is the only shipped source that changed, and tests are not shipped.
- **Source binding.**
  - All 51 non-cache backend files equal the `d834971` git blobs under git's own clean filter (`git hash-object --path`). 30 of them are checked out with CRLF line endings.
  - The protected data files keep their hashes (`replacement_eye_plan.json` `db493dbb…`, `public_source_leads.json` `cfa08525…`).
  - All 11 ASAR application files equal the git blobs. The ASAR `package.json` is the builder-stripped subset; every shared field is equal (version 0.16.2, `electron-updater` 6.8.9). The other 254 entries are bundled runtime dependencies, unchanged from 0.16.1.
  - The shipped `desktop/main.js` keeps `contextIsolation:true`, `nodeIntegration:false` and `sandbox:true`.
  - The packaged `app-update.yml` feed is `Gemanoneko/booksArranger`, `releaseType: release`.
- **Native receipt** (`build-cache/builds/dd672b05-…/native-operation-result.json`): mode `build`, `root_exit_code 0`, `native_job_closed true`, `active_processes_after 0`.

Behaviour of the packaged app on the real-catalog copy is Futaba's QA and not part of this verdict.

## Summary

I reviewed every file in the delta:
- `merge_service.py`, read against its callers and readers: `audio_jobs.py`, `source_cleanup.py`, `automatic_processing.py`, `app_launcher.py`, `desktop_backend.py` and `web_server.py`;
- the new tests;
- `CHANGELOG.md`, `package.json` and `package-lock.json`.

Each release question was answered from the code and backed by measurements: a mutant the tests must catch, or a probe. The new installer is bound to `d834971` independently of the build's own receipts. The v0.16.1 clearance of `95febcd..78b4421` carries forward. Since then, the only reviewed product file that changed is `merge_service.py`, and it is reviewed here.

I did not run the integrated `npm run check`, because it writes inside the worktree. The focused runs above were made on a private export.

## Rubric

Severity tags and the always-blocking floor are those in `Team/Docs/ProcessRules.md`, Severity definitions.

### 1. Security

Pass. The delta adds no route, IPC channel, shell-out, write, delete or credential handling. It changes only how one status label is derived. The packaged Electron flags and the update feed are confirmed in the actual artifact.

### 2. Correctness & Logic

Concerns: one Major (advisory) and Minor findings. The fix is correct for the reported failure and keeps every stop (question 1).

- [Major r1, advisory; predates this release; flagged by Ender] Lost wake-up, at `audio_jobs.py:243-244,303-305` with `merge_service.py:279-280`.
  - **Mechanism.** `resume()` returns early while the converter thread is alive. But the converter decides to exit (its empty pending query at `:304-305`) without the queue lock and without re-checking. A book that is queued and then "resumed" between that query and the thread's exit is left queued with no worker.
  - **Probe**, on a real `AudioJobs`, with the converter held between its empty query and its return: `resume()` answered Running; after the converter exited, the queue read Paused, `queued=1`, no worker alive.
  - **A second window has the same shape.** The cleanup thread stays alive while its `after_drain` → `jobs.resume()` returns, and that call ends with a full `status()` read (`source_cleanup.py:175`, `audio_jobs.py:254`). `merge.resume()` also returns early while the cleanup thread is alive (`merge_service.py:280`).
  - **Effect.**
    - If a later admission resumes the queue, the book is picked up and nothing visible happens.
    - Otherwise the automatic run's next wait reads a genuine "Paused", and the run pauses itself with "Paused — pending work saved".
    - No book is interrupted, the queued book and saved work are kept, and Start continues the run.
  - **Fix.** Make the exit decision under the same lock that `resume()` takes: re-check for pending work and detach `_thread` before returning. Alternatively, have the waiting loop resume once when it reads Paused with books queued and no stop requested, before it pauses the run.
- [Minor r2] Capture order, at `merge_service.py:197-203`.
  - **Mechanism.** `_worker_active()` reads both thread references before it checks either one. The docstring says that checking the cleanup thread first covers the handoff, because the cleanup thread starts the converter before it exits. But the converter reference has already been captured, and it may be the old, dead thread.
  - **Probe.** A cleanup thread that hands back between the capture and its own `is_alive()` check makes one sample return false while the new converter is alive. The next sample returns true.
  - **Masked in `_state()` by the two samples.** The after-read sample can hit this only in two cases:
    - the cleanup thread was already alive at the before-read sample, and that sample then answers true;
    - or the cleanup thread ran its entire cleanup between two bytecodes of the reader.

    I could not construct a wrong "Paused" from it.
  - **Fix.** Read `self.jobs._thread` after the cleanup liveness check, so the code does what the docstring says.
- [Minor n1, carried from v0.16.1] `desktop/main.js:353,358-370`: the Quit confirmation decides from a cached answer and treats `busy:null` as not converting. This file is unchanged.

### 3. Crash / Stability Safety

Concerns (Minor only, carried). The delta adds no exception path: `_worker_active()` uses `getattr` defaults, and a hung worker reads Busy, exactly as `AudioJobs.status()` already did.

- [Minor n2, carried from v0.16.1] `merge_service.py:57-66` with `desktop/main.js:511` and `web/desktop-ui.js:13-14`: the thread that owns a status computation is not bounded at 4 s. This code is unchanged.
- [Minor n3, carried from v0.16.1] `web/app.js:58-68` with `web_server.py:258-259`: a 503 goes through the page's generic disconnect path. This code is unchanged.

### 4. Performance

Concerns: one Major carried forward from v0.16.0, advisory. The delta itself passes: it adds at most two attribute reads and six `is_alive()` calls per state computation.

- [Major, advisory, carried from v0.16.0] `working_lifecycle.py:228` (and `:411`): reference rescans scale with catalog size times disposable-file count. The file is unchanged.

### 5. State & Data Safety

Pass. The change affects status only and writes nothing.
- The recovery-delete gate (`_recovery_idle`), restore, historical cleanup and `drained()` keep their own liveness checks, and these are unchanged.
- The restart and update fences read a fresh state, so an extra "Running" can only refuse.

### 6. Input Handling

Pass. The delta adds no input surface.

### 7. Maintainability (no Critical findings on its own)

Concerns (Minor only). The fix is small and commented. Its tests use the real methods under Event control and are enrolled in the ordinary checker through the existing `test_automatic_processing.py` pattern.

- [Minor r3] `tests/test_automatic_processing.py:675-731`: no case covers the new `elif` branch with Stop set, that is, books queued, the converter gone, and only the cleanup thread or marker alive.
  - Replacing that branch's `'Pausing' if … else 'Running'` with `'Running'` passes all 81 cases.
  - If that regressed, the automatic thread's Pausing wait (`automatic_processing.py:451`) would end early, and the run would record its paused checkpoint while the cleanup thread is still finishing.
  - Add one case: start a cleanup thread with no pending rows, set Stop, and expect Pausing.
- [Minor n4, carried from v0.16.1] `tests/test_status_snapshot.py:39,67,128-131`: these cases rely on real time. The file is unchanged.
- [Minor m2, carried from v0.16.0] `scripts/check-desktop.mjs:19-23`: `tests/test_build_external_tools.py` is still not enrolled.

### 8. Doc/Code Drift (no Critical findings on its own)

Concerns (Minor only). The CHANGELOG entry and the new comments match the code, except the docstring ordering claim, which is r2.

- [Minor n5, carried from v0.16.1; line references updated] Three small inaccuracies remain:
  - `merge_service.py:369` says "an indexed existence check", but `audio_jobs` has no index on `state`.
  - `Docs/BooksArranger_Brief.md:303` omits that stop-now bypasses `engineRequest`.
  - `CHANGELOG.md:15` (the v0.16.1 entry) says "the whole job table".

### 9. Build & Release Hygiene

Pass, with Minor concerns carried forward.
- The version bump, the lockfile in the same commit, and the CHANGELOG are complete.
- No dependency changed.
- The worktree is clean at `d834971`.
- The installer is bound to the source, and the payload was reproduced from the installer bytes (see Artifact binding). The build scripts are unchanged since v0.16.1.
- This review does not claim the publication run.

- [Minor m1, carried from v0.16.0] `scripts/build_phase.py:103-121`: the carve checks are partly self-consistency, and NSIS framing is not checked in code. I re-checked both independently for this artifact.
- [Minor m3, carried from v0.16.0] `scripts/build_phase.py:99-107`: an implicit coupling to the reduced `7zip-bin` 5.2.0 `7za`, which fails closed.

Release-path requirements in the tool's own contract (`scripts/release-contract.mjs:24-36,68-76`, `scripts/release-flow.mjs:38-46`), for Sully and Futaba. These are not findings, and each fails closed:
- **Installer reuse.** Only Docs-only or CHANGELOG-only descendants of `d834971` may be released with this installer. Any version, lock or product-file change alters the product digest.
- **`Docs/BooksArranger_ReleaseAcceptance_v0.16.2.json`** needs:
  - exactly the keys `schema` (`books-desktop-acceptance-v1`), `version`, `qa` and `review`;
  - version `0.16.2`;
  - `review` set to `Docs/BooksArranger_CodeReview_v0.16.2_2026-10-17.md`;
  - `qa` matching `^Docs/BooksArranger_QA_v0\.16\.2_\d{4}-\d{2}-\d{2}\.md$`. A `_QAReport_` name is refused by the tool's contract.
- **Futaba's report** needs, like this one:
  - exactly one line starting with `**Verdict:**`;
  - exactly one source-commit pin line naming `d8349715dd03afe2cc12ea9db59cffd4c4c38fd0`;
  - exactly one artifact-manifest line naming `03c2c9dce5e834df2ec18890a9411e34e84eaeb87e1dd1e0f62e93f811d347cb`.

## Finding rollup

- Open Critical: 0.
- Open Major: 2, both advisory.
  - New: r1, the lost wake-up in `AudioJobs.resume`. It predates this release.
  - Carried from v0.16.0: `working_lifecycle.py:228`.
- Open Minor: 10.
  - New: r2, r3.
  - Carried from v0.16.1: n1, n2, n3, n4, n5.
  - Carried from v0.16.0: m1, m2, m3.
- Always-blocking floor: intact.
  - No machine harm: the Electron flags are unchanged in the actual artifact, and there are no new writes or deletes.
  - No secret exposure.
  - No risk to repo history.

Major and Minor findings are logged for Ender's next cycle and do not gate this release.

## Verdict

- Total Critical: 0
- Total Major: 2
- Total Minor: 10

**Verdict:** RELEASE CLEAR

This clearance covers the accumulated range `95febcdd4f4de4ffb59a3507053c4eb86f53936a..d8349715dd03afe2cc12ea9db59cffd4c4c38fd0`, and the installer `Books-Arranger-Setup-0.16.2.exe` (SHA256 `a485118afcbc4cacdf76504d90910922b85388fc0cc63605866b2a90be5a8356`) bound by manifest SHA256 `03c2c9dce5e834df2ec18890a9411e34e84eaeb87e1dd1e0f62e93f811d347cb`.

It covers construction only. Futaba's packaged real-catalog-copy QA GO is the independent behaviour gate.

A rebuild, or any product-file change after `d834971`, voids this artifact binding and needs a fresh binding check.
