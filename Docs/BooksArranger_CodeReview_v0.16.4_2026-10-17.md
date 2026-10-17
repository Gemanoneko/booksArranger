# Code Review — Books Arranger v0.16.4

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-17
Tool: Books Arranger
Release: v0.16.4
Status: FINAL; accumulated range, the routine-check fix delta, the unreleased v0.16.2 and v0.16.3 deltas and the actual installer artifact reviewed
Commit range: 95febcdd4f4de4ffb59a3507053c4eb86f53936a..b6cae4c21dc667eaafa27bd74a50504d7de54d13
Accumulated committed diff: 128 files, +16043 / -269
Last published release: v0.16.1, tagged at 5420254e79f239f7df0f737966c8652e4db30f4a (its report cleared 95febcdd..78b442135b70eb2d061a8f5d3571f706a1b256ae)
Since the last published release: 5420254..b6cae4c, 19 files, +1760 / -60 (13 non-Docs files, +880 / -55)
  v0.16.2 (never tagged): 5420254..d8349715dd03afe2cc12ea9db59cffd4c4c38fd0, reviewed in full in Docs/BooksArranger_CodeReview_v0.16.2_2026-10-17.md
  v0.16.3 (never tagged; QA NO-GO): be3062e..950857617e96a0ab2ef780c3cb7b15846a5b3d67, reviewed in full in Docs/BooksArranger_CodeReview_v0.16.3_2026-10-17.md
Delta reviewed in full here: 950857617e96a0ab2ef780c3cb7b15846a5b3d67..b6cae4c21dc667eaafa27bd74a50504d7de54d13 (14 files, +950 / -51)
  dddedb4 Docs only (v0.16.3 review and QA reports)
  f34e82de9994e14379ddeab94491de6da588ea8a routine-check fix (audio_jobs.py, merge_service.py, current_audiobook.py, replacement_retirement.py, desktop_backend.py, two test files, scripts/check-desktop.mjs, QA recipe)
  b6cae4c21dc667eaafa27bd74a50504d7de54d13 version bump to 0.16.4 + CHANGELOG (3 files)
Stand-down dimensions: none
Release source commit: b6cae4c21dc667eaafa27bd74a50504d7de54d13
Release product tree SHA256: 1b642bd1dd1884732bab0bf641702c5c4583c533e6595ab46a5672f63a63b682
Release artifact manifest SHA256: 69d1272b3b181b91a03181828a496cb77328a81307114380b2f30d6b3fa6973c
Release installer: dist/builds/fda054e7-1abd-4a1a-8102-40c512e18f9c/Books-Arranger-Setup-0.16.4.exe
Release installer SHA256: 758a0d08faf0e4483dc27f1035404bbbf6bd1b8b47852b13859bf27639cd16a4 (172,948,408 bytes)
```

What carries forward unchanged:
- `95febcd..78b4421`: cleared in `Docs/BooksArranger_CodeReview_v0.16.1_2026-10-17.md`.
- v0.16.2 (`5420254..d834971`): cleared this morning. Nothing in this delta touches its status logic (`_worker_active`, `_state`).
- v0.16.3 (`be3062e..9508576`): cleared at `9508576`. f34e82d rewrites part of it (the background check now uses the identity check and the pacer, and Start's re-check moved out of the lock). Its conclusions still hold where not superseded below; in particular the background check can still only demote a `completed` row, never promote one.
- v0.16.2 and v0.16.3 were never published, so their changes ship for the first time in v0.16.4.

## Delta 9508576..b6cae4c

### The fix (f34e82d), confirmed against the code

- **verified_outputs.** A new table, created with `CREATE TABLE IF NOT EXISTS` (`merge_service.py:136`), keyed by (normalised path, SHA-256). A row is written only after a successful full hash:
  - by `_output_valid` (`merge_service.py:1011-1015`), which holds the output open with read-only sharing (`ProtectedFiles([final])`, `:1007`) across both the hash and the identity capture;
  - by the book-list verifier (`current_audiobook.py:158`), inside `protected()`, which also holds the file read-only.
  So a remembered identity always belongs to the bytes that were hashed. I tried to write the file in place between the last block and the stat: the write was refused with a sharing violation, every time, for 5 s.
- **Routine check.** `_output_current` (`merge_service.py:1020-1027`) passes a book whose (volume, file id, size, mtime) equals its remembered identity, after the same root, profile and parent-folder identity checks as the full check (`:1029-1040`). Otherwise it runs the full, interruptible `_output_valid`.
- **Who uses it.** Only `AudioJobs` routine checks (`merge_service.py:143` → `audio_jobs.py:103-104`): the launch background check (`:197`) and Start's re-check (`:348`). Non-routine checks (construction's crashed-publication settle, a new book's completion) still call the full validator.
- **Start.** `AudioJobs.resume` (`audio_jobs.py:326-362`) now runs the check outside `_lock`, guarded by `_resuming`, with `stop = _Any(_stop, _drain)` (`:341`). It applies its changes and starts the worker in one locked step, and only if nothing stopped it and every changed row is still exactly what it read (`:353-357`).
- **Pacer.** One shared 32 MiB/s budget (`merge_service.py:41-56`), used by the background check and by the book-list verifier.
- **Status and Quit.** Desktop status runs `state()` in a helper thread and gives up after 4 s (`desktop_backend.py:36-59`). `MergeService.drain()` no longer computes state, and `pause()` returns `None` while draining (`merge_service.py:313-321`).
- **Ready count (v0.16.3 s1).** `_validated_outputs` is seeded from the remembered identities at construction (`merge_service.py:167-173`). The Ready count is right from the first status on every launch except the first one after the update, when the table is still empty.

### Release questions

1. **Is the guarantee change acceptable? Yes.**
   - **Every delete path still hashes in full, by its own code, which this delta does not touch:**

     | Delete path | Full check |
     |---|---|
     | Originals removal | `source_cleanup.py:194`, `output.sha256()` under `VerifiedFile`, then the `BEGIN IMMEDIATE` row guard |
     | Recovery purge | `recovery_retention.py:102` → `storage_cleanup.protected_output` (`storage_cleanup.py:128-142`) |
     | Working and temporary files, folder cleanup | `storage_cleanup.py:466`, `:525`, `:726`; `working_lifecycle.py:526`; all through `protected_output` |
     | Replacement publication | `merge_service.py:564`, `_output_valid` under `VerifiedFile` |
     | Former-output retirement | `replacement_retirement.py:47`, `:61`: the non-historical branch still hashes with `self.stop`, unchanged; only the read-only historical proof takes the new `stop` |

     `source_cleanup.py`, `storage_cleanup.py`, `recovery_retention.py` and `working_lifecycle.py` are unchanged in `9508576..b6cae4c`. The duplicate-recording decision also still hashes in full (`merge_service.py:918`).
   - **Nothing destructive trusts the new record.** I grepped every reader:
     - `verified_outputs` is read only by `_identity_current` (routine checks), `_known_identities` (Ready seeding) and `_publication_current` (the book view);
     - `_validated_outputs` is read only by `progress_books` (Ready list and converted count);
     - the book view's `describe()` feeds only the inspector and Open folder, which opens Explorer.
   - **What the gap can cost.** A book changed in place with its size, mtime and file id kept (for example, a tag editor set to preserve the modification time, writing inside the existing padding) stays `completed` and Ready. If originals removal later runs for it, `CleanupJobs.run` refuses on its own hash and keeps every original. No data is at risk.
   - **One correction to the brief.** "Routine checks no longer re-hash" has one exception, which predates this release: the one historically retired book (t6).
2. **verified_outputs integrity: sound.**
   - **Stale rows after a replacement, re-publish or move.** A row vouches only for a record naming exactly that path and SHA-256, and only while the live identity equals the stored one.
     - A replacement publishes to a new path and refuses an existing destination (`merge_service.py:600`).
     - A re-publish to the same path is a new file, with a new file id and mtime, so it gets a full hash.
     - A book moved away fails as before.
     - A book moved away and back on the same volume keeps its file id, mtime and bytes, so "current" is correct.
     - Rows are never deleted. That is harmless: tens of bytes per book.
   - **File id reuse.** A false pass needs the reused id at the same path with the same size and the same mtime to the nanosecond. In practice that only happens when the same bytes are restored with their timestamps preserved, and then the verdict is right.
   - **Z: (SMB).** Python 3.14's `os.stat` reports the volume serial and file id that the server returns. A Samba-based NAS derives these from the share and the inode, so they should survive reconnects. This was not measured across a NAS sleep, a reconnect or a reboot.
     - The failure direction is safe: an identity that changes only costs a full hash, never a false pass.
     - The unsafe direction (an identity stable while the bytes change) is exactly the accepted gap.
     - But an unstable identity on Z: would make t1 happen at every Start. Futaba should check that.
   - **Schema migration on the live catalog.** It is additive only: no `ALTER`, and no existing table changes. The read-only catalog recogniser checks only `jobs`, `queue` and `files` (`desktop_catalog.py:36-37`). If the table cannot be read or written, every helper falls back to a full hash (`merge_service.py:1046-1065`).
   - **Rollback.** v0.16.1 and v0.16.3 ignore the table and hash in full as before. On re-upgrade, a book changed meanwhile has a new identity, unless it falls into the accepted gap.
3. **Lock-free Start re-check: no unsafe race. Two old lost-command windows remain.**
   - **Worker.** `_thread` is assigned only under `_lock`, and `_resuming` excludes a second concurrent check. The final step re-checks `_closed`, the stop and a live worker under the lock, so there is never a double worker.
   - **Pause.** It sets `_stop` under the lock, and the check stops at the next row or 1 MiB block. Measured: under 0.5 s (test).
   - **Quit.** `drain()` sets `_drain`, which is part of Start's stop. Each Start path is waited for before close:
     - an HTTP Start is a merge admission, and `finish_shutdown` waits for admissions (`web_server.py:87`);
     - an automatic Start: `_parked` waits for the automatic thread;
     - the cleanup thread's `after_drain` Start (`merge_service.py:150`): `drained()` waits for the cleanup thread.
     So `close()` does not race a running check in practice, and `_closed` is in the final locked step anyway.
   - **Background verifier.** Start sets `_verify_stop` under the lock first, and the verifier writes only under the lock after re-checking the stop. Nothing is written after a Start.
   - **Cleanup and recovery admission.**
     - HTTP cleanup, enrolment, recovery delete and the retention thread all wait on the operation lock, which an HTTP or automatic Start holds for the whole check.
     - In the `after_drain` path the cleanup thread is alive, so `source_cleanup.resume` refuses a second worker (`source_cleanup.py:157`) and `_recovery_idle` refuses (`merge_service.py:424`).
     - Every destructive path re-hashes anyway.
   - **Residual: r1, extended.** If a Start arrives while another Start's check is still running, `AudioJobs.resume` now returns at once on `_resuming` (`audio_jobs.py:337-338`, new in f34e82d).
     - Probe at queue level: Start, then Pause and a second Start while the first check is still running. The second Start is dropped, and the queue reads Paused with work queued.
     - Over HTTP the operation lock serialises two Starts, so the second one runs normally.
     - Only the cleanup thread's `after_drain` Start is exposed. There, `MergeService.resume` already returned early before this release, because the cleanup thread is alive.
     - It is the same family as r1, and clicking Start again works.
   - **Residual: a lost Pause, predating this release, now narrowed.** `AudioJobs.resume` clears `_stop` (`audio_jobs.py:340`) after `MergeService.resume` last polled it (`merge_service.py:338`). At `9508576` a Pause anywhere in the prune loop was lost. Now the window is one DB read (`:341`).
4. **Rate limiter and interruption: correct.**
   - **Pacer.**
     - It reserves time first-come, first-served and builds up no burst credit while idle (`start = max(now, next)`).
     - Measured on the real class: two readers moving 16 MiB at 8 MiB/s took 1.88 s, against 1.875 s expected (the first block is free).
     - A stop wakes a waiting reader within one 0.1 s slice. Measured: 0.30 s for a stop set at 0.30 s.
     - A stopped reader's unused reservation delays the next reader by at most one block (about 31 ms).
   - **Interruption.**
     - `InterruptedError` is a subclass of `OSError`, so I checked every `except OSError` on the path. Each re-raises the interruption first (`merge_service.py:1017`, `replacement_retirement.py:198`, `audio_jobs.py:161-162`).
     - `_output_current`'s `OSError` catch covers only the identity check.
     - Both callers stop without writing (`audio_jobs.py:204-205`, `:351-352`).
     - Even if `_settle` did misreport a stop as invalid, both callers re-check the stop under the lock before any write (from reading the code). The unit test catches the misreport itself (M8).
   - **What the pacer does not cover:** Start's re-check (t1), the historical proof (t6), and new-book completion checks (unchanged).
5. **Bounded status and Quit: Quit cannot skip the drain.**
   - **Engine side, unchanged.** `quit()` → `drain()` → `_park` waits for `drained()`, which needs the converter and cleanup threads to finish (`desktop_backend.py:107-145`, `merge_service.py:323-326`).
   - **What the Quit request still does:** `inventory.stop()` and `automatic.stop()`. The latter is a few database reads plus `merge.pause()`, which returns at once while draining. So nothing slow remains.
   - **Status threads stay bounded.** One owner computes, and the other helpers wait at most 4 s in the shared snapshot.
   - **What changed is the shell's view (t2).** When state takes more than 4 s, the desktop status now answers `busy: null`. The shell then skips "Quit after the current book?" and quits after the book without asking. Before, the same slow state made Quit fail outright (the v0.16.3 Blocker).
6. **Tests and version bump.**
   - **The new tests.** `tests/test_startup_published_check.py` has 18 cases, 12 of them new, and `test_replacement_jobs.py` has one new assertion. `test_replacement_jobs.py` is newly enrolled in `scripts/check-desktop.mjs`, and the script has no hard-coded case count.
   - **Determinism: confirmed.** The new cases use Events with 5 s bounds and wall-clock limits of 0.5 s (Pause), 2 s (Quit) and 5 s (status). All are generous.
     - Runs on a private `git archive` export of `b6cae4c`, with the pinned QA runtime and `-I -B`: 1 run, then 10 in a row, then 2 rounds of 8 concurrent processes, plus 1 inside the regression run.
     - 28 runs of 18 cases in all. No failures, errors or skips in any of them.
   - **Positive controls.** I ran 16 mutants of the five changed modules against `test_startup_published_check.py` and `test_replacement_jobs.py` (57 cases). 9 were caught:

     | Mutant | Caught by |
     |---|---|
     | M1, the routine check ignores a changed identity | `test_changed_file_is_hashed_in_full_and_fails` |
     | M2, the removal check trusts the identity | `test_removal_paths_keep_the_full_hash` |
     | M3, Start's check runs under the queue lock | the Pause case blocks forever; the suite hung and was killed at 180 s |
     | M8, `_output_valid` reports a stop as invalid | `test_a_stop_is_raised_never_reported_invalid` |
     | M9, the pacer never waits | `test_shared_pacer_holds_the_rate_and_stops` |
     | M11, desktop status unbounded | `test_status_answers_within_bound_while_state_is_slow` |
     | M13, the retirement proof swallows a stop | `test_paused_history_proof_preserves_partial_base_retirement` |
     | M14, Start passes changed books | `test_start_still_rechecks_a_changed_book_before_any_new_work` (v0.16.3 gap M10, now closed) |
     | M15, the routine check ignores historical retirement | `test_actual_audio_pause_resume_preserves_retired_completed_history` (v0.16.3 gap M8, now closed) |

     7 survived; they are listed under t5.
   - **Regression comparison.**
     - I ran 34 queue, cleanup, storage, status, automatic and replacement test files that bind no listener, each in its own process, on private exports of `9508576` and `b6cae4c`, with the pinned runtime (SHA-256 `434b361f…`) and `-I -B`.
     - That is 478 cases at `9508576` and 490 at `b6cae4c`. All 478 shared cases have identical outcomes, and the 12 new cases pass.
     - The same 17 cases fail on both commits, for environmental reasons:
       - 9 are the app's own path-length guard, tripped by my longer scratch path;
       - 4 are missing fixture paths;
       - the other 4 are one-offs that also fail at `9508576`.
     - So those 17 were not independently re-verified here.
     - `test_source_cleanup.py` was run separately, because my result collector failed on it: 13 of 13 pass on both commits.
   - **Not run.** `test_web`, `test_desktop_quit`, `test_desktop_host`, `test_status_read_contention` and `test_merge_http` bind listeners or launch hosts. `test_app_launcher` and `test_tk_review` need `tkinter`.
   - **Version bump: complete.**
     - `package.json` and both root version fields in `package-lock.json` read 0.16.4, in one commit (`b6cae4c`). No other lockfile line changed.
     - The packaged `VERSION`, the ASAR `package.json` and both manifest versions read 0.16.4.
     - The only `v0.16*` tag, locally and on `origin`, is v0.16.1 (→ `5420254`); v0.16.2, v0.16.3 and v0.16.4 are not tagged.
     - The tool repo was clean at `b6cae4c` before this report was written.

## Artifact binding (independent, 2026-10-17)

Everything was read-only on the artifact, using private scratch copies. Nothing was installed, launched, packed or rebuilt.

- **Manifest.** `sha256(dist/release-artifacts.json)` = `69d1272b…` (full value in header).
  - It equals `manifest_receipt.sha256` in `build-cache/builds/f5a53549-2e4e-4037-87ca-57556b719a05/metadata-rotation-complete.json`.
  - That rotation archived the previous manifest as `release-artifacts.json.previous-c877d2f4-…`, whose SHA-256 is `299f15d6…6ce89`. That is exactly the v0.16.3 manifest the v0.16.3 report bound.
- **Manifest contents.**
  - Schema `books-desktop-artifacts-v1`, version `0.16.4`, `source_head` `b6cae4c21dc667eaafa27bd74a50504d7de54d13`, `build_id` `fda054e7-1abd-4a1a-8102-40c512e18f9c`.
  - `payload.verified` and `installer_equivalent` are true; the shell and backend versions are `0.16.4`.
  - 219 payload files, 581,980,105 bytes. `payload.manifest_sha256` is `aa0b76b8…c819`; I recomputed it and it is equal.
- **Product digest.** I recomputed `1b642bd1…b682` with the tool's own `productTree`, through both its `-z` release-flow parser and its build-manifest parser. Both give the manifest value.
  - Controls:
    - `f34e82d` gives `14b7ba23…`, which differs because the version files changed;
    - `dddedb4` and `9508576` both give `9b791328…c7a1`, the v0.16.3 digest, because `dddedb4` is Docs-only;
    - `5420254` gives `b9c6db72…`.
- **Release files.**
  - The installer, blockmap and `latest.yml` SHA-256 values and sizes equal the manifest's three artifact entries.
  - Both `sha512` lines in `latest.yml` equal the installer's actual SHA-512, and its size line matches.
- **Installer bytes.**
  - Exactly one 7z signature, at offset 171,345, with valid start-header and next-header CRCs.
  - Physical size 172,385,248; tail 391,815. The length field just before the signature equals that size.
  - The carved SHA-256 is `02541ce98566424281b26d85011b1cb5f2baa48c49ca8d0114017b67aee81082`. It matches the producer receipt entry, with the same size.
- **Extracted payload.**
  - I extracted the carve privately with the repo's own `7za`: 219 files, byte-identical to `payload.files`, with nothing missing, extra or different. `win-unpacked` is likewise identical.
  - Against the 0.16.3 payload, 53 of 219 files differ and none was added or removed:
    - `Books Arranger.exe`, `resources/app.asar` and `VERSION`;
    - the five changed modules: `audio_jobs.py`, `current_audiobook.py`, `desktop_backend.py`, `merge_service.py` and `replacement_retirement.py`;
    - 45 `.pyc` files.

    The runtime map is identical. This is exactly what the source delta predicts.
- **Source binding.**
  - All 51 tracked backend files equal the `b6cae4c` git blobs under git's own clean filter (`git hash-object --path`). `VERSION` is generated by the build.
  - The protected data files keep their hashes (`replacement_eye_plan.json` `db493dbb…`, `public_source_leads.json` `cfa08525…`).
  - All 11 ASAR application files equal the git blobs. The ASAR `package.json` reads 0.16.4 with `electron-updater` 6.8.9.
  - The shipped `desktop/main.js` keeps `contextIsolation: true`, `nodeIntegration: false` and `sandbox: true`.
  - The packaged `app-update.yml` feed is `Gemanoneko/booksArranger`, `releaseType: release`.
- **Native receipt** (`native-operation-result.json`, same build folder): mode `build`, `root_exit_code 0`, `native_job_closed true`, `active_processes_after 0`.

How the packaged app behaves on the real-catalog copy is Futaba's QA and is not part of this verdict.

## Summary

I read every file in the delta: the five modules, both test files, the check script, the QA recipe, the CHANGELOG and the version files. I read them against every destructive and lifecycle caller: `source_cleanup.py`, `storage_cleanup.py`, `recovery_retention.py`, `working_lifecycle.py`, `replacement_retirement.py`, `automatic_processing.py`, `web_server.py`, `desktop_backend.py` and `desktop/main.js`.

Each release question was answered from the code and backed by measurements:
- probes for the pace each caller passes, the pacer, the post-hash write window and a lost Start;
- mutants the tests must catch;
- a regression comparison against `9508576`.

The installer is bound to `b6cae4c` independently of the build's own receipts.

The fix is correct and safe. It resolves the v0.16.3 Blocker by construction, plus three of the v0.16.3 findings: s1 the Ready lag, s2 Start's full re-hash under the locks, and s4 the 10 s Quit wait. Ender's one guarantee change is acceptable, because every delete path still hashes in full.

The new Major is t1. On the first launch after the update, a Start before the background check finishes re-hashes the rest of the library unpaced, which is the v0.16.3 Finding 2 load again. Pause and Quit still work during it.

## Rubric

Severity tags and the always-blocking floor are those in `Team/Docs/ProcessRules.md`, Severity definitions.

### 1. Security

Pass.
- The delta adds no route, IPC channel, shell-out, credential handling or file write outside the catalog. The new writes are `verified_outputs` rows and the existing guarded `audio_jobs` row update.
- The Electron flags and the update feed are confirmed in the actual artifact.

### 2. Correctness & Logic

Concerns. No finding touches data; the details are in questions 1 to 3.

- [Minor t2, new] With a slow status, Quit skips the "Quit after the current book?" confirmation.
  - **Where.** `desktop/main.js:358` reads `status.busy || {}`. `desktop_backend.py:38-59` now turns any state computation over 4 s into `busy: null`.
  - **Effect.** During a conversion, a Quit sent while status is slow is accepted with no prompt. The tray reads "quitting" instead of "quitting after the current book", and the user cannot cancel a long finish.
  - **Data.** None at risk: the engine still drains the book (question 5). It is the deliberate trade against the v0.16.3 Blocker.
  - **Fix.** The shell treats `status: 'unavailable'` as "possibly converting" and asks.
- [Major r1, carried from v0.16.2, extended] Lost Start: `audio_jobs.py:336-338`. Now also on `_resuming` (question 3).
- [Minor r2, carried from v0.16.2] `merge_service.py:249-255`: the capture order in `_worker_active` does not match its docstring.
- [Minor n1, carried from v0.16.1] `desktop/main.js:353,358-370`: the Quit confirmation decides from a cached answer. t2 widens the same spot.

### 3. Crash / Stability Safety

Concerns: Minor only. The delta adds no crash path. The helper threads are daemons and bounded; interruptions are raised and caught at both callers; the identity helpers fall back to a full hash on any database or decode error.

- [Minor t4, new] The book-list verifier's 600 s per-book limit now runs under the shared 32 MiB/s pacer (`current_audiobook.py:153-154`).
  - **Effect.** A book larger than about 18.7 GiB alone, or about 9.4 GiB while the background check shares the budget, always exceeds the limit. Its book view then reads "Current audiobook unavailable" for the session, and Open folder is unavailable.
  - **Severity.** Display only, and latent: the library averages about 450 MB a book.
  - **Fix.** Scale the limit with size at the paced rate, or exempt paced waiting time.
- [Minor n2, carried from v0.16.1, narrowed] `merge_service.py:95-110`: the status owner thread is unbounded. The desktop route is now bounded; `/api/state` is not.
- [Minor n3, carried from v0.16.1] `web/app.js:58-68`: a 503 goes through the generic disconnect path.

### 4. Performance

Concerns: one new Major.

- [Major t1, new] Start's re-check is not paced.
  - **Where.** `audio_jobs.py:348` calls `self._settle(row, True, stop)` with no pace. The launch check passes `self.verify_pace` (`:197`). Probe: the background check receives the shared pacer, Start receives `None`.
  - **When it bites.** On the first launch after the update, `verified_outputs` is empty, so the background check needs about 14 minutes at 32 MiB/s for the 26.3 GiB library. A Start in that window, manual or through automatic processing, stops the paced check. It then hashes every book not yet reached at full share speed: about 100 MiB/s, up to the ~258 s Ender measured before the fix.
  - **While it runs:**
    - the NAS is saturated again, which is the cause of the v0.16.3 Finding 2 503s;
    - the check runs inside `MergeService.resume`'s `@operation` (`merge_service.py:328`), so queue, create, approval, cleanup enrolment, recovery delete and the retention thread wait for it.
  - **What still works.** Pause and Quit, measured. No data is at risk.
  - **Exposure.** Once per catalog. But every Start if the identity proves unstable on Z: (question 2). It contradicts the stated "capped at 32 MiB/s shared".
  - **Fix.** Ender's or Judy's call:
    - pass `self.verify_pace` (a slower first Start, with visible progress);
    - or let Start begin work only after the paced background check finishes, instead of taking it over.
- [Minor t6, predates this release] The one historically retired book (the "Eye of God" parent) is still hashed in full on every routine check, unpaced.
  - **Where.** `audio_jobs.py:165` → `replacement_retirement.py:183-197`. `historical_retired` hashes the current replacement and its recovery copy. It runs once in every launch check and twice at every Start (`AudioJobs.resume` and `_prune_completed`, `merge_service.py:504`).
  - **Severity.** It is the only full read left in routine checks. Interruptible.
- [Major, advisory, carried from v0.16.0] `working_lifecycle.py:228` (and `:411`): reference rescans scale with catalog size times disposable-file count.

### 5. State & Data Safety

Concerns: one Major predating this release, carried. The guarantee change is acceptable, and every delete path re-hashes (question 1). The integrity of `verified_outputs` holds (question 2). Start's changes apply only when nothing stopped them and every changed row is still exactly what it read (question 3).

- [Major s3, carried from v0.16.3; predates it] A transient share failure permanently marks finished books "Output needs attention".
  - **Where.** `merge_service.py:1018` with `audio_jobs.py:161-166`.
  - **Unchanged by this delta.** When Z: is unreachable, the identity check raises `OSError` and falls through to the full check. That check fails at once with `False`, and the book is demoted. The exposure is the same as at `9508576`: a launch or Start before Z: reconnects demotes every finished book.
  - **Fix as before.** "Unavailable" should mean not checked; only a mismatch, or a file missing under a reachable parent, should mean changed.

### 6. Input Handling

Pass. The delta adds no input surface.

### 7. Maintainability (no Critical findings on its own)

Concerns: Minor only.

- [Minor t5, new; replaces s5] Test gaps: 7 of 16 mutants survive (question 6).
  - **The one that matters most.** M7: the book view's identity comparison (`merge_service.py:1067-1070`) has no test, because the view tests inject a lambda. A regression there would show a changed book as verified in the inspector.
  - **The others:**
    - M6: the Ready seeding at construction (the s1 fix) is not tested;
    - M4: Quit's `_drain` stopping Start's check, because the Quit case also calls `close()`;
    - M5: the background check's pacer wiring;
    - M10: Start's compare-before-write;
    - M12: Quit not computing status (`test_desktop_quit` may cover it; not run here);
    - M16: per-row exception containment in the background check (the v0.16.3 gap M12, still open).
  - **Brittle failure mode.** M3 is caught only by a hang. The Pause case would block `scripts/check-desktop.mjs` until its own timeout, instead of failing. Give `queue.pause()` a bounded thread join.
- [Minor t3, new] `MergeService.pause()` now returns either a state dict or `None` (`merge_service.py:316`).
  - **Effect.** A Pause admitted just before Quit sets `closing` answers HTTP 200 with `null` (`web_server.py:356`).
  - **Severity.** The page ignores the body (`web/app.js:107`), so it is harmless today, but the contract is split.
- [Minor r3, carried from v0.16.2] `tests/test_automatic_processing.py:675-731`: the `elif` branch with Stop set is not covered.
- [Minor n4, carried from v0.16.1] `tests/test_status_snapshot.py`: these cases rely on real time.
- [Minor m2, carried from v0.16.0] `scripts/check-desktop.mjs`: `tests/test_build_external_tools.py` is still not enrolled.
- [Minor s7, carried from v0.16.3] `tests/test_desktop_host.py:39`: the real-host case flakes. Not run here (it binds a listener).

### 8. Doc/Code Drift (no Critical findings on its own)

Concerns: Minor only. The new docstrings and comments are accurate.

- [Minor t7, new; replaces s6] Gaps in the v0.16.4 CHANGELOG entry:
  - **The guarantee change is not disclosed.** Routine checks no longer notice an in-place change that keeps size, modification time and file id. Sergei should read that in the notes, and `Docs/BooksArranger_Brief.md` should record it.
  - **"The Audiobook Ready count no longer reads 0 after launch"** is not true on the first launch after updating. The table is empty, so the count rises as the background check proceeds. The QA recipe says so; the CHANGELOG does not.
  - **"Start no longer holds the queue"** is true of the queue lock, but Start still holds the operation lock for the whole check (t1).
  - **No mention of the unreleased versions.** The entry does not say "v0.16.2 and v0.16.3 were never released; their changes ship in this version", although the v0.16.1 entry set that precedent.
  - **Fix.** These are CHANGELOG and Docs-only edits. They keep the product digest (see release path).
- [Minor n5, carried from v0.16.1] Three small inaccuracies remain: `merge_service.py` "indexed existence check"; `Docs/BooksArranger_Brief.md:303`; the v0.16.1 CHANGELOG entry "the whole job table".

### 9. Build & Release Hygiene

Pass, with Minor concerns carried forward.
- The version bump, the lockfile in the same commit, and the CHANGELOG are present.
- No dependency changed.
- The installer is bound to the source, and the payload was reproduced from the installer bytes.
- This review does not claim the publication run.

- [Minor m1, carried from v0.16.0] `scripts/build_phase.py:103-121`: the carve checks are partly self-consistency. I re-checked them independently for this artifact.
- [Minor m3, carried from v0.16.0] `scripts/build_phase.py:99-107`: an implicit coupling to the reduced `7zip-bin` 5.2.0 `7za`, which fails closed.

Release-path requirements in the tool's own contract (`scripts/release-contract.mjs:18-36`, `:68-76`; `scripts/release-flow.mjs:38-46`), for Sully and Futaba. These are not findings, and each fails closed:
- **Installer reuse.** Only Docs-only or CHANGELOG-only descendants of `b6cae4c` may be released with this installer. A CHANGELOG fix for t7 keeps the product digest.
- **`Docs/BooksArranger_ReleaseAcceptance_v0.16.4.json`** needs:
  - exactly the keys `schema` (`books-desktop-acceptance-v1`), `version`, `qa` and `review`;
  - version `0.16.4`;
  - `review` set to `Docs/BooksArranger_CodeReview_v0.16.4_2026-10-17.md`;
  - `qa` matching `^Docs/BooksArranger_QA_v0\.16\.4_\d{4}-\d{2}-\d{2}\.md$`.
- **Futaba's report** needs, like this one:
  - exactly one `**Verdict:**` line;
  - exactly one source-commit pin line naming `b6cae4c21dc667eaafa27bd74a50504d7de54d13`;
  - exactly one artifact-manifest line naming `69d1272b3b181b91a03181828a496cb77328a81307114380b2f30d6b3fa6973c`.
- **The v0.16.2 and v0.16.3 reports** pin other sources and manifests. They cannot clear v0.16.4, and v0.16.2 and v0.16.3 must not be tagged.

**Suggested checks for Futaba's live pass** (behaviour, not this verdict):
- On a fresh copy (empty `verified_outputs`), click Start a minute after the first launch. This is t1: expect a long check, NAS saturation and slow controls; Pause and Quit must still answer.
- Relaunch after the NAS has slept, or after the share reconnects, and confirm Start's re-check stays at about 1 s (identity stable on Z:).
- Quit during a conversion while status is slow (t2).

## Finding rollup

- Open Critical: 0.
- Open Major: 4, all advisory.
  - New: t1, Start's re-check is unpaced on the first launch after the update.
  - Carried: s3 (v0.16.3; transient share failure demotes books), r1 (v0.16.2; lost Start, now extended), and `working_lifecycle.py:228` (v0.16.0).
- Closed since v0.16.3: s1 (Ready lag, except the first post-update launch, now t7), s2 (Start's full re-hash under the locks; its residual is t1), s4 (10 s Quit wait: the hash now stops within one block or 0.1 s), and s6 (folded into t7).
- Open Minor: 17.
  - New: t2, t3, t4, t5, t6, t7.
  - Carried from v0.16.3: s7.
  - Carried from v0.16.2: r2, r3.
  - Carried from v0.16.1: n1, n2, n3, n4, n5.
  - Carried from v0.16.0: m1, m2, m3.
- Always-blocking floor: intact.
  - No machine harm: the Electron flags are unchanged in the actual artifact, there is no new delete, and the new writes are catalog rows.
  - No secret exposure.
  - No risk to repo history.

Major and Minor findings are logged for Ender's next cycle and do not gate this release.

## Verdict

- Total Critical: 0
- Total Major: 4
- Total Minor: 17

**Verdict:** RELEASE CLEAR

This clearance covers the accumulated range `95febcdd4f4de4ffb59a3507053c4eb86f53936a..b6cae4c21dc667eaafa27bd74a50504d7de54d13`, including the unpublished v0.16.2 and v0.16.3 deltas. It also covers the installer `Books-Arranger-Setup-0.16.4.exe` (SHA-256 `758a0d08faf0e4483dc27f1035404bbbf6bd1b8b47852b13859bf27639cd16a4`), bound by the manifest hash in the header.

It covers construction only. Futaba's packaged real-catalog-copy QA GO is the independent behaviour gate.

A rebuild, or any product-file change after `b6cae4c`, voids this artifact binding and needs a fresh binding check.
