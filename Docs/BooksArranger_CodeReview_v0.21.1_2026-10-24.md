# Code Review — Books Arranger v0.21.1 (final)

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-23 (filed under 2026-10-24 because the 2026-10-23 name holds my f64d46b report; see F19)
Tool: Books Arranger (Electron / Python)
Release: v0.21.1
Commit range: e78b74746d1c84e48ab3b11b6ddfad17f3997f38..711074842ea0a70bd2afd05503527b10b6471f6a
Release source commit: 711074842ea0a70bd2afd05503527b10b6471f6a
Release artifact manifest SHA256: ea199365a02a55b68a58cee44b4fbca8cbcfd4bd69af4526b8c734353830e523
Reviewed source: C:/Antigravity Projects/Worktrees/Books Arranger/inplace-m4b (branch codex/books-inplace-m4b, clean tree at HEAD 7110748, level with origin)
Reviewed in this pass: f64d46b..7110748, 3 commits: 83c5652 (docs: the superseded 10-23 reports), ca61894 (Iron Inferno and Сказка), 7110748 (tag-repair working-file names)
Files changed in this pass: 24 files, +1279 / -63 (git diff --numstat). Product code: producer_recovery.py +139/-11, merge_service.py +85/-11, web/app.js +75/-12, scripts/python-check-batches.mjs +22/-7, audio_jobs.py +21, web_server.py +15/-3, and 9 smaller edits. Tests: +439/-4 in 4 files. Docs and CHANGELOG: +447.
Stand-down dimensions: none
```

**What this report certifies.** The range runs from the `v0.21.0` tag (e78b747) to 7110748.
- f64d46b was reviewed in `Docs/BooksArranger_CodeReview_v0.21.1_2026-10-23.md` (RELEASE CLEAR). That report pins f64d46b, so it cannot clear this build: the release flow compares each report's pinned product tree with the release's.
- This pass reviews the three commits after f64d46b and re-checks that report's open findings against them. They are carried forward by reference.

**The artifact.** I checked `dist/release-artifacts.json` read only (`r5-digest.log`):
- It hashes to the pinned value above.
- Its `source_head` is 7110748, and its version is 0.21.1. `package.json` and both lockfile version fields at 7110748 also read 0.21.1.
- Its `product_digest` `6ff3d3e5…` equals `productTree(ls-tree 7110748)`, which I recomputed with the repo's own `release-contract.mjs`.

## Summary

There is no Critical finding, and the safety floor is intact. There is one Major finding (F26), four new Minor findings (F27–F30), and twelve carried Minor findings.

**The boot proof: accepted, with F26 [Major].**
- The rule is sound under one assumption: the wall clock was not stepped forward within the current Windows session after the attempt's last recorded time. The design states that residual correctly. It is the only arithmetic residual, provided `GetTickCount64` counts sleep. Microsoft's documentation implies that it does, and I could not measure it here.
- What the design gets wrong:
  - The triggers are mostly automatic, not someone moving the clock: Windows correcting a clock that started wrong, or a VM resumed from saved state.
  - "The app cannot detect that clock change" is not true. Windows logs every clock step (System log, Kernel-General event 1), and the kernel keeps their sum since startup.
- A probe shows the proof accepting an attempt from the current session after a +3 h step.
- Why this is not Critical: a live writer still blocks status, isolation and removal, and removal re-hashes every file.
- For Сказка the residual did not happen. The only clock step since this startup is −2.1 s.

**Fenced deletion: sound** for what it deletes and when.
- It removes only files that are identical, by identity and by full hash, to the ones fenced at isolation. They are removed through a held handle, only after the child is verified.
- I found no TOCTOU.
- Library-root containment holds against five other spellings of the same folder.
- F27 is about what happens after a refusal, not what gets deleted:
  - a child whose frozen policy keeps its original gets a false "needs attention";
  - a refused removal is never retried;
  - an interrupted removal whose folder is gone can never finish.

**Confirm and convert: sound.**
- The exact statements are enforced on the server, and the recorded text comes from the server's constant.
- The route sits behind the same token, Host, Origin and Sec-Fetch-Site gate as every other POST.
- It can only queue the job whose candidate and revision the request names.

**Iron: sound for the class it names.**
- It cannot retry forever. The automatic pass asks exactly once per failed job.
- The three name rules match exactly the names the repair writes.
- F28: the failures that 7110748's own message describes are not offered. Since v0.20.1 they were recorded as "Unknown producer artifact is not admitted".

**The gate: sound.** The three-worker split still places every module exactly once, on an isolated copy.
- My third run on a `git archive` of 7110748 passed: 1298 Python cases, 59 Node cases, 17 front-end scripts, 0 skipped.
- Ender's last gate log (21:32:51) predates the 7110748 commit (21:37:04). This run closes that gap.
- My second run failed one case only because another process held the fixed test port 5212 (F30).

**Are the tests real? Mostly.** I ran 69 one-clause mutants: 49 are caught and 20 survive.
- Seven of the survivors are covered by another check by construction.
- The other 13 are real gaps (F29): two of the five time sources, `windows_boot()` itself, the hash-only, stream and marker checks of removal, the service's library roots, the startup removal path, the dialog's own labels, and the exactness of all three name rules.

## Focus questions

| # | Question | Answer |
|---|---|---|
| 1a | Is "startup = clock − `GetTickCount64`, at least 10 min after every recorded time" sound? | **Yes, with one assumption.** **The reading:** on this PC, wall − tick gives 2026-10-22T05:07:20Z. The kernel's own boot time (`NtQuerySystemInformation` class 3) agrees to 0.13 s, and the System log's boot event (Kernel-General 12) reads 05:07:22.5Z (`r5-clock-probe.log`). **The logic:** a process alive now started after this startup. The old producer, or the app that started it, wrote the recorded times. So if this startup follows all of them, the producer predates it and is gone; the largest time and the margin only add caution. **Exactly:** an attempt from an earlier session is always closed, whatever the clock says. An attempt from this session is accepted only when the clock gained at least (its last time − the real startup) + 10 min between its last time and now. Nothing else in the arithmetic can make it accept. |
| 1b | Is the stated residual the only one? | **It is the only one, but its triggers are wider than the design says.** **Sleep and hibernation:** `GetTickCount64` counts them; Microsoft points to `QueryUnbiasedInterruptTime` for time without sleep. The derived startup stays put, so they can only make the proof fail. Not measured: this PC has not slept since it started (tick − unbiased time = −7 ms, `SleepTimeBias` 0). **Fast Startup:** the kernel session and its counter continue, so the derived startup is the last full restart. The proof fails although user processes ended, and R1a's "Restart it" is the right advice. **NTP:** w32time's *steps* are exactly the residual. **Rollback:** a backward step only fails the proof, and a recorded time later than now gives `startup_unavailable`. **Missing from the design:** most triggers are automatic. Windows can start with a wrong hardware clock (flat CMOS battery, BIOS reset, or dual-boot with a system that keeps the RTC in UTC; this PC keeps it in local time, bias −180 min, so that skew is 3 h) and correct it later in the same session. A VM resumed from saved state steps forward too. The step needed is small when a conversion starts soon after startup. **And it is detectable** (F26). |
| 1c | Can the proof ever accept while the old producer is alive? | **Yes, in that residual only.** **Probe `BootResidual`:** the attempt is stamped 30 min after the real startup by a clock 3 h slow, then the clock is stepped +3 h. The status is `ready`, and `isolate` returns `isolated_retained`. **What still stops harm** (probe `LiveWriterFence`): an open write handle on an old file makes status, isolation and removal fail with WinError 32. The positive control removes both files once the handle is closed. On top of that, the child's lease denies writes and deletes, and removal re-hashes every file. **For Сказка:** the System log shows one clock step since this startup, −2135 ms at 2026-10-23T08:14:39Z, and the kernel's `BootTimeBias` reads −2.135 s. So no forward step has happened, as of my reading at 18:47Z. |
| 2 | Fenced deletion | **What it deletes:** only `native['files']` from the isolation record, under all of these conditions: each file is at `stage/<name>`; the names equal the ledger; the folder is exactly `stage_root/<job>/<attempt>` with no protected root inside or around it; each file is opened by path with writes and deletes denied; its native facts (volume, file ID, size, write time, attributes, one link) and full SHA-256 equal the isolation record; it has one data stream; it is deleted through that same handle. **Not before verification:** `dispose` requires a completed child, its own output record with `validation.passed`, the saved relation equal to its binding, and the parent, checkpoint and consent fields. Its two callers run only after completion. **TOCTOU:** none. Facts and hash are read through the held handle, and the share mode blocks writes and deletes until that handle deletes the file. A name swapped before the open fails the facts check, which is the shipped "replaced identity" test. **Interrupted `disposing`:** it resumes. A file missing after the durable intent counts as removed, and only in that state; the rest are re-checked. Probe `InterruptedThenFolderGone`: if the old folder itself is gone, the resume fails for good and stays `disposing` (F27). **Containment:** upper case, forward slashes, a trailing separator, the stage in lower case and a dot segment are all refused (probe `RootSpellings`). It compares paths, so another alias of the same folder (a `subst` drive, a junction) is not seen. Even then, removal is limited to the fenced ledger files. |
| 3a | Verbatim statements enforced on the server? | **Yes, twice.** `web_server.py:532` requires a list of exactly two strings. `merge_service.py:269` requires them equal, in order, to `ORIGIN_STATEMENTS`. The recorded evidence is built from the server's constant, not from the request (`:278`), and this is the only caller of `record_origin`. A crafted request cannot record a weaker statement. The three copies of the text (`index.html:134`, `app.js:701`, `merge_service.py:261`) are identical today and match ruling 6 word for word. Nothing ties the dialog's own labels to the other two (F29, S11). |
| 3b | Covered by the token, Host and Origin checks? | **Yes.** `do_POST` calls `trusted(token=True)` (Host, Origin, Sec-Fetch-Site, token) before any route (`web_server.py:683`), and the new HTTP test asserts 403 without the token. The route also gets the merge routes' scan, closing and admission-count handling. One limit: "Sergei's own press" is checked only on the page. `isTrusted` (`app.js:1126`) stops a click made by page script, but not CDP input or a direct POST that carries the page token. "An agent never makes it" remains a process rule, which is enough for a one-user local tool. |
| 3c | Can it convert a book other than the one confirmed? | **No.** `_m4b_parent` (`merge_service.py:1630`) requires the job's candidate id and revision to equal the request's, and the job to be that candidate's newest current job. The saved fact is bound to the job, its attempt, the scope digest, the machine identity and the native fence. The worker rebuilds the child from the same candidate, and `retry_intent.bind` refuses a changed review. |
| 4a | Can `tag_repair_checked` retry a damaged MP3 forever, or never? | **Not forever.** A Retry, Repair or replacement child never qualifies. A failure recorded since 0.21.1 carries the marker: `raise original from repair` re-raises the marked error. The automatic pass asks once (4b). **Never, for one class: yes (F28).** 7110748's message says that since v0.20.1 every repair was refused at "checking sources" with "Unknown producer artifact is not admitted". That failure is a `BoundaryError`, so `source_remedy` and `tag_repair_retry` never match it. Probe `StrandedIronClass`: group `other`, no remedy, no Retry. |
| 4b | Is the automatic retry limited to one attempt? | **Yes.** `retry_automatic_job` asks only when the parent has no `m4b_readmissions` row in any state (`merge_service.py:2145`), and rows are never deleted. Sergei's own Retry can still ask again after a refusal, as designed. |
| 4c | Do the three name rules admit only the exact pattern? | **Yes.** All three call `fullmatch` on `tag-repair-[0-9a-f]{32}\.(?:mp3\|json)` (`storage_cleanup.py:21` used at `:432` and `:482`; `working_lifecycle.py:24`). That is exactly what `uuid.uuid4().hex` writes (`audio_pipeline.py:371`). No test pins that exactness: N1–N3 survive (F29). |
| 5 | Does the third worker still run every module exactly once, with isolation intact? | **Yes.** `pythonBatches` gives each pattern one worker in a `Map`, and builds the batches from the declared list. `validatePythonReports` re-derives the split and compares each report's pattern list and counts. Each worker still gets its own copy, cwd and TEMP, and the serial-server modules stay together on worker 0. All 82 patterns name a real file. G1 (one module dropped), G2 (serial modules spread) and G3 (two workers) are each caught. My three gate runs are listed under Evidence; run 3 passed. Headroom is thin: the workers took 440, 388 and 435 s against the 540 s deadline (F30). |
| 6 | Are the tests real? | **Mostly.** 69 mutants, one clause each: 49 are caught and 20 survive (table under Evidence). **Caught:** every boot-proof bound and refusal (the margin, the file times, the attempt row's time, a clock behind the attempt, a negative uptime, a zone-less time, the stored proof's re-derivation, isolation's own proof, a status after a failed proof). Every child-verification clause of removal, containment in both directions, and the unknown-file, missing-file, identity and durable-intent checks. Every server-side statement, identity, sole-blocker, scan and ready check, the recorded evidence, the page's statement text and its trusted-press check. Every Iron marker, child exclusion and once-only rule. The name rules' admission (N4–N6) and the partition (G1–G3). **Survive, but covered by construction (7):** D7, D9, D10, D16, D19, D21, D26. **Survive, real gaps (13, F29):** B3, B4, B11, B12, D11, D15, D17, D20, D27, S11, N1, N2, N3. |

## Rubric

### 1. Security

- Status: Pass.
  - The new route is behind the same local gate and an exact body shape (Focus 3).
  - There is no new shell-out: the tag repair's FFmpeg calls are unchanged.
  - The new deletion is fenced (dimension 5). There is no Electron change and no secret.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **F26 [Major]** `producer_recovery.py:48-75`, `:234-238`, `:275-287`; design note `:78-90`. The boot proof trusts a wall clock that nothing checks. Windows keeps an independent record of every clock step, and the proof does not read it.
    - **The gap:** an attempt from the current session is accepted when the clock gained at least (its last time − the real startup) + 10 min afterwards (Focus 1a). Then a producer that may be running is treated as ended. Probe `BootResidual` shows it with the real code.
    - **The design understates it:**
      - It says "the clock was moved forward", but the realistic triggers are automatic: a startup with a wrong hardware clock that w32time corrects later in the same session (flat CMOS battery, BIOS reset, dual-boot RTC in UTC, a 3 h skew here), or a VM resumed from saved state.
      - It says "The app cannot detect that clock change. No independent record of the startup or the clock is checked." That is wrong. Kernel-General event 1 logs every step with its delta, and the kernel keeps their sum since startup (`SYSTEM_TIMEOFDAY_INFORMATION.BootTimeBias`). Measured here: one step since startup, −2135 ms, and `BootTimeBias` −2.135 s (`r5-timechange-events.log`, `r5-clock-probe.log`).
    - **The sleep assumption:** "Sleep … cannot pass" rests on `GetTickCount64` counting sleep. Microsoft's page implies it, by pointing to `QueryUnbiasedInterruptTime` for "the time the system has spent in the working state". This PC has not slept since it started, so it is unmeasured.
    - **This changes the reviewed rule's character.** The 2026-10-20 design relied on a counter reset, which no clock can fake, and listed "old timestamps" among the things that are not proof. The new basis is old timestamps plus the clock.
    - **Why Major, not Critical:**
      - Every check opens the old files with writes and deletes denied, so a producer that still has a file open blocks status, isolation and removal (probe `LiveWriterFence`).
      - The child's lease denies writes while it runs.
      - Removal re-hashes every file.
      - The worst case I can construct from a false acceptance is a refused removal with a stray file left in the private staging folder. I found no path to library or source loss.
      - For Сказка the residual did not occur (Focus 1c).
    - **Why not Minor:** this proof is now the only thing that declares a producer closed, and it gates permanent deletion (ruling 5).
    - **Fix (next cycle):**
      - Before accepting the boot basis, read the System log's Kernel-General event 1 entries since the derived startup. Refuse (`startup_unavailable`) if any forward step after the attempt's last time, or their sum, reaches `BOOT_MARGIN_MS`. `BootTimeBias` can corroborate, but its layout is undocumented, which is the same reason the design set aside `BootIdentifier`.
      - Record the tick count and wall clock on every new attempt, so that future recoveries can use the counter-reset rule and the clock basis stays limited to legacy attempts like Сказка's.
      - Measure `GetTickCount64` against `QueryUnbiasedInterruptTime` across a real sleep on Sergei's PC.
      - Correct the design note's "one case only" and "cannot detect" text.
  - **F28 [Minor]** `audio_jobs.py:55-81`, docstring `:68`. The Iron classifier misses the failure class that 7110748 says the bug produced.
    - **The class:** 7110748's message says that since v0.20.1 every repair was refused at "checking sources" with "Unknown producer artifact is not admitted". `working_lifecycle.planned` raises that as a `BoundaryError`. `source_remedy` requires `ValidationError` and a reason starting "Full audio decode failed: ", so a book that failed this way in 0.20.1–0.21.0 gets no Retry, and the automatic pass skips it (probe `StrandedIronClass`).
    - **The drift:** the docstring says "recorded before the app had the trailing-tag repair". The rule is really "recorded before 0.21.1, as a decode failure".
    - **Scope:** I could not count such books, because the live DB is out of scope. Iron itself failed under 0.19.0, so it is covered.
    - **Fix:** Ender counts them read-only. Whether to offer them the same Retry is Sergei's call.
  - **F8 [Minor], carried, still open.** Unchanged, now at `merge_service.py:2759`.
  - **F23 [Minor], carried, still open.** Unchanged, now at `inplace_m4b.py:516`, `:520`, `:522`.

### 3. Crash / Stability Safety

- Status: Concerns (carried only).
  - Nothing new here:
    - `_finish_recovery_child` catches everything, so a published child is never reset by its cleanup.
    - The removal intent is durable before the first delete, and an interrupted removal resumes (shipped test and my probe).
    - A crash between completion and removal is picked up at startup by `_enroll_completed_without_start`, for a child whose policy removes its original (`merge_service.py:244`).
  - Carried, untouched by this range: **F21 [Minor]** (`inplace_m4b.py:318-322`, `zone_identifier.py:113`).

### 4. Performance

- Status: Pass.
  - At K0 a status read now also opens the old files (no hashing) and reads the machine identity. That is one book, a few handles.
  - About 2.4 GB is hashed three times: at isolation, under the lease, and at removal. The first two run inside the fence's 540 s bound (`producer_recovery.py:127`), and the removal's hash runs unbounded in the worker. That is seconds at any normal disk speed.

### 5. State & Data Safety

- Status: Concerns
- Findings:
  - **F27 [Minor]** `merge_service.py:284-299`, `:301-309`, `:244`; `producer_recovery.py:312`, `:387`; `app.js:703`. Three ways a disposal-bound child ends in a permanent attention state. None loses data.
    - **The frozen policy is ignored:** `_finish_recovery_child` calls `enroll_cleanup` whatever the child's frozen `cleanup_policy`, where `_after_completed_work` checks it first.
      - A boot-basis child whose policy keeps its original (a manually approved M4B, `inplace_m4b.py:194`) gets a source cleanup in `needs_attention` with "Original removal was not enrolled for this job" (probe `PolicyAsymmetry`).
      - The confirmation dialog and the K3 hint also promise "and the original are deleted" for every boot-basis book (`deletionLine`), whatever its policy.
      - The startup path is the opposite case. It runs only for a policy that removes the original (`:244`), so after a crash such a child's old files are never removed.
    - **A refused removal is final.** `_enrollment_attention` writes a `needs_attention` cleanup row. From then on neither `_finish_recovery_child` nor the startup path (`:244`) tries the removal again, and no route re-enrolls it (`/api/audiobook/cleanup` is the historical-only start). So one refusal, even a passing one such as a file held open for a moment, keeps the 2.4 GB and the original for good. It keeps them safely, but for good.
    - **An interrupted removal can be stranded.** If the old folder itself is gone after the `disposing` intent, `DirectoryBoundary` fails every resume, and the row stays `disposing` (probe `InterruptedThenFolderGone`). The original stays because the child's cleanup is never enrolled, although `protected_dependency` (`producer_recovery.py:387`) no longer protects it from `disposing` on.
    - **Also left:** the parent's empty attempt folder and its `ownership.json` remain after `disposed`. `_retire` refuses an `isolated_retained` attempt, and a shipped test asserts the marker stays. It is a few bytes, and it is not mentioned in the CHANGELOG.
    - **Fix:**
      - Gate the enrollment in `_finish_recovery_child` on `cleanup_policy.enabled`, as `_after_completed_work` does, and word the deletion line from the policy.
      - Give a refused or stranded removal a retry: try again at startup while the checkpoint is `isolated_retained`/`disposing`, and accept an absent folder in `disposing` as already removed.
  - **File deletes:** validated before executing (Focus 2).
  - Carried, still open: **F22**, **F6** (attribute half) and **F10 [Minor]**, all in unchanged code: `inplace_m4b.py:99-107`, `:322`, `:62`.

### 6. Input Handling

- Status: Pass.
  - The request shape is exact, the statements must match exactly, and the UUID and candidate identity are validated.
  - An unreadable or zone-less attempt time gives `startup_unavailable`, as does a malformed boot reading (tests and B6–B8).

### 7. Maintainability (no Critical findings on its own)

- Status: Concerns (carried only).
  - Nothing new here: `confirm_origin_and_convert` takes no operation lock, like `retry_blocked_job`. Two simultaneous presses could each save an origin fact, and the latest wins, so this is harmless.
  - Carried: **F9 [Minor]**, unchanged at `inplace_m4b.py:211`.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns.
  - The design note's residual text (F26), the `tag_repair_retry` docstring (F28) and the deletion line (F27) are covered in those findings.
  - The CHANGELOG's two new entries (`:11-12`) are otherwise accurate.
  - Carried, still open: **F24 [Minor]** (`CHANGELOG.md:9`) and **F11 [Minor]** (`inplace_m4b.py:216`).

### 9. Build & Release Hygiene

- Status: Concerns
- Findings:
  - **F29 [Minor]** `tests/test_iron_skazka.py`, `tests/test_iron_skazka_frontend.js`. 13 of the 20 mutation survivors are real gaps (table under Evidence):
    - **The clock reading is untested.** No test calls `windows_boot()`, so dropping its read-consistency check (B11) or using the earlier tick (B12) passes. Two of the five time sources can be dropped, the history (B3) and the ledger rows (B4), because in every fixture the files' write times are the latest.
    - **Removal checks without a case:**
      - the full-hash compare (D15): every "changed bytes" case also moves the write time, so the facts compare catches it first;
      - the single-stream check (D17);
      - the `ownership.json` check (D11);
      - the library roots the service passes (D20): only `dispose` itself is tested with roots.
    - **The crash path of ruling 5:** `_enroll_completed_without_start` can skip the removal (D27) with the suite green. No test restarts the app between a child's completion and its removal.
    - **The dialog text:** changing the label Sergei ticks (S11) passes. The tests pin the text that is sent and the server's copy, not the text that is shown.
    - **Name-rule exactness:** loosening any of the three rules to any hex length, any suffix, or any `tag-repair-*` name (N1–N3) passes.
    - **Fix:** one case for each gap:
      - a time source that is alone the latest;
      - a `windows_boot()` smoke check against the kernel's boot time;
      - an in-place byte change with the write time restored;
      - an alternate data stream on an old file;
      - a changed marker;
      - a service-level removal with a library root around the stage;
      - a restart between completion and removal;
      - the labels compared with `ORIGIN_STATEMENTS`;
      - near-miss names (31 hex digits, `.MP3`, `.tmp`).
  - **F30 [Minor], outside the range.** `tests/test_desktop_host.py:26-33`, `scripts/check-desktop.mjs:13`. The gate is fragile when other runs share the machine, as the process requires (Futaba and I run in parallel).
    - **The fixed port:** the real-host test uses port 5212 and the constant token `'e'*64`. My run 2 failed when another process held 5212: `/api/health` answered with another pid. The test sends all its requests, `POST /api/desktop/quit` included, with that constant token to whatever answers on 5212. Only its pid check kept it from quitting another run's test host. Run alone, the module passes 6/6 (`r5-desktop-host-rerun.log`).
    - **Thin headroom:** the slowest worker took 440 s against the 540 s deadline. The new weights count unlisted modules as 2 s, and worker 0 holds every serial-server module, so its load is underestimated.
    - **Outside the gate:** 31 test modules are not in the gate's inventory, including ones that exercise code this range touches. I ran nine of them on f64d46b and on 7110748: 121 of 123 pass on both, and the same two fail on both (`test_storage_busy` 24-hour expiry, `test_cleanup_scope`). So this range breaks none of them; those two failures are older.
    - **Fix:** take the port from the OS and the token from `secrets`. Weigh the serial modules too.
  - Carried, still open: **F25** and **F18 [Minor]** (`tests/test_inplace_m4b.py`, unchanged), and **F19 [Minor]** (`scripts/release-contract.mjs:73`, unchanged). This file's 2026-10-24 name was free, and it matches `^Docs/BooksArranger_CodeReview_v0\.21\.1_\d{4}-\d{2}-\d{2}\.md$`.
- Verified, no finding:
  - **Gate:** run 3 on the committed tree passed (Evidence).
  - **My mutation baseline:** 152/152 on the pristine copy (`r5-baseline-par.log`).
  - **Version and manifest:** see the header.
  - **Attribution:** none of the four commits in the range has Claude attribution.

## Patterns

The new tests check the proof's arithmetic against a synthetic boot reading. The assumption that the reading can be trusted is never exercised: `windows_boot()` is called by no test (B11 and B12 survive), and nothing in the code reads Windows' own record of clock steps. That is the r4 pattern one level up: a test reaches only as far as its fixture. Here the fixture is the clock, and the real one is measurable.

## Evidence

**Setup:**
- Every run used `git archive` copies of 7110748, or of f64d46b for comparison, under `C:/Users/AnGeLZzZ/AppData/Local/Temp/sn21/r5/`:
  - `gate`, `gate2` and `gate3` for the full gate;
  - `base` for the baseline and as the mutation source;
  - `m/<name>` for each mutant, and `p5` for the probes;
  - `dh` for the desktop-host re-run;
  - `unl-new` and `unl-old` for the suites outside the gate.
- **The runtime:** the worktree's build-cache runtime `c3d7d82c…` (Python 3.14.8, SQLite 3.50.4, its FFmpeg). The full gate uses the repo's pinned `qa-runtime.json` runtime, which lives in the `electron-m1` checkout's build cache (also Python 3.14.8). That runtime is executed, never written: nothing under it changed during my runs (`find -newer`, 0 files).
- The real Iron fixture (`ba-mp3-fixture/fixture.mp3`, `e2deceb3…`) was opted in through `BOOKS_MP3_REAL_FIXTURE`.
- Nothing ran in the worktree, the live DB, Z:, the installed app or `dist/`. The exceptions are read-only: hashing and parsing `release-artifacts.json`, `git` reads, reading the Windows clock, and the System log query. This report is the only file I wrote in the worktree, and it is uncommitted.

**Logs and sources** are in `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/64106cea-b39e-4987-9571-6ad97339dc8a/scratchpad/shared/senua-0211/`:
- **Gate:**
  - `r5-gate-7110748.log`, run 1: every case passed, but the real-MP3 case skipped without the fixture variable, and the gate counts a skip as a failure.
  - `r5-gate2-7110748.log`, run 2: one failure, the port-5212 collision (F30).
  - `r5-gate3-7110748.log`, run 3: `BOOKS_INTEGRATED_CHECKS_PASS`, 1298 Python, 59 Node, 17 front-end scripts, 0 skipped, wall 455 s.
- **Clock:** `r5_clock_probe.py` with `r5-clock-probe.log`, and `r5-timechange-events.log` (System log, Kernel-General event 1).
- **Artifact:** `r5-digest.mjs` with `r5-digest.log`; partition check `r5-patterns.mjs`.
- **Probes:** `test_senua_r5_probes.py` with `r5-probes.log`. Each probe class also re-runs the shipped tests it inherits from. One of those fails only under `BootResidual`'s deliberately shifted clock, as it must.
- **Outside the gate:** `r5-outside-7110748.log` and `r5-outside-f64d46b.log`.
- **Mutations:** `r5-mutate.py` (one exact edit per mutant, refused unless it applies the expected number of times; `r5-mutcheck.py` dry-checks all of them), `r5-run-mutations.sh`, `r5-summarize.sh` and `r5-table.py`, one `r5-mut-<name>.log` per mutant, and `r5-rerun-survivors.sh` with one `r5-mut3-<name>.log` per survivor re-run. The baseline for the mutation sets is `r5-baseline-par.log` (152/152).

**Mutations** (one clause each, on the pristine 7110748 copy; proof, fence and route mutants on the recovery set, Iron and name-rule mutants on the wider set, web mutants on the serial-server set, Node mutants on their own scripts; every survivor re-run on the only other modules that reference producer recovery):

| Mutant | What it breaks | Result |
|---|---|---|
| B1_margin | Boot proof without the 10 min margin | Caught: `no_restart_unreadable_or_inconsistent_times_refuse_and_keep_everything` |
| B2_filetimes | Old files' write times left out of the attempt's times | Caught: `a_file_written_after_the_startup_is_no_proof`, `later_boot_isolates_with_a_recomputed_bound_proof` +1 |
| B3_history | The job's stage history left out | **Survives** |
| B4_ledger | The ledger rows' times left out | **Survives** |
| B5_attemptrow | The attempt row's time left out | Caught: `unreadable_attempt_time_is_unavailable` |
| B6_clockback | No refusal when a recorded time is later than the clock | Caught: `no_restart_unreadable_or_inconsistent_times_refuse_and_keep_everything` |
| B7_uptimesign | A negative uptime accepted | Caught: `no_restart_unreadable_or_inconsistent_times_refuse_and_keep_everything` |
| B8_naive | A time with no zone accepted | Caught: `unreadable_attempt_time_is_unavailable` |
| B9_rederive | `verify_retained` no longer re-derives the stored proof | Caught: `later_boot_isolates_with_a_recomputed_bound_proof` |
| B10_isolatetimes | Isolation proves against a fixed time, not the attempt's | Caught: `a_file_written_after_the_startup_is_no_proof`, `confirm_and_convert_then_verified_removal_and_normal_cleanup` +7 |
| B11_readconsist | `windows_boot` without its read-consistency check | **Survives** |
| B12_firstuptime | `windows_boot` uses the earlier tick reading | **Survives** |
| B13_statuswait | Status reports ready after a failed proof | Caught: `a_file_written_after_the_startup_is_no_proof`, `no_restart_unreadable_or_inconsistent_times_refuse_and_keep_everything` +1 |
| D1_childstate | Removal without a completed child | Caught: `every_refusal_keeps_every_file` |
| D2_validation | Removal without a passed validation | Caught: `every_refusal_keeps_every_file` |
| D3_relation | Removal without the saved retry relation | Caught: `every_refusal_keeps_every_file` |
| D4_consent | Removal without `retained_disposal` | Caught: `every_refusal_keeps_every_file` |
| D5_checkpoint | Removal for a child bound to another checkpoint | Caught: `every_refusal_keeps_every_file` |
| D6_basis | Removal on the checkpoint basis | Caught: `checkpoint_basis_never_removes` |
| D7_stageeq | No check that the folder is `stage_root/<job>/<attempt>` | **Survives** |
| D8_roots | No library-root containment at all | Caught: `every_refusal_keeps_every_file` |
| D8b_rootinside | No "library inside the stage" check | Caught: `every_refusal_keeps_every_file` |
| D8c_stageinside | No "stage inside a library" check | Caught: `every_refusal_keeps_every_file` |
| D9_ledgernames | No check that the fenced names equal the ledger | **Survives** |
| D10_itempath | No check that each path is `stage/<name>` | **Survives** |
| D11_marker | No `ownership.json` check | **Survives** |
| D12_unknown | No unknown-file check | Caught: `every_refusal_keeps_every_file` |
| D13_missing | A missing file accepted before the intent | Caught: `every_refusal_keeps_every_file` |
| D14_facts | No native-identity compare | Caught: `replaced_identity_is_not_removed` |
| D15_hash | No full-hash compare | **Survives** |
| D16_links | No single-link check | **Survives** |
| D17_stream | No single-stream check | **Survives** |
| D18_intent | No durable `disposing` intent before the first removal | Caught: `interrupted_removal_resumes_from_its_durable_intent` |
| D19_casverify | No `verify_retained` inside the intent transaction | **Survives** |
| D20_noroots | The service passes no library roots | **Survives** |
| D21_postcheck | No check that each file is gone | **Survives** |
| D22_enrollfirst | Source cleanup enrolled before the removal | Caught: `confirm_and_convert_then_verified_removal_and_normal_cleanup`, `refused_removal_keeps_the_old_files_and_the_original` |
| D23_earlyclean | Normal cleanup runs during the lease | Caught: `confirm_and_convert_then_verified_removal_and_normal_cleanup`, `refused_removal_keeps_the_old_files_and_the_original` |
| D24_binddisable | A disposal child keeps cleanup disabled | Caught: `confirm_and_convert_then_verified_removal_and_normal_cleanup`, `refused_removal_keeps_the_old_files_and_the_original` |
| D25_offered | A recovery child offered the in-place edit | Caught: `recovery_child_keeps_the_copy_flow` |
| D26_guardany | `retry_intent.guard` accepts removed states for any child | **Survives** |
| D27_startupskip | The startup path skips the removal | **Survives** |
| S1_statements | Server accepts any statements | Caught: `refusals_change_nothing_and_a_failed_proof_keeps_the_statement` |
| S2_httpshape | HTTP accepts any statements value | Caught: `shape_forwarding_and_refusals` |
| S3_httpkeys | HTTP makes `statements` optional | Caught: `shape_forwarding_and_refusals` |
| S5_identity | No candidate/revision binding | Caught: `refusals_change_nothing_and_a_failed_proof_keeps_the_statement` |
| S6_soleblocker | Confirm without `can_confirm_origin` | Caught: `refusals_change_nothing_and_a_failed_proof_keeps_the_statement` |
| S7_unconfirmed | Retry without a saved confirmation is not refused | Caught: `refusals_change_nothing_and_a_failed_proof_keeps_the_statement` |
| S8_scan | Confirm accepted while scanning | Caught: `shape_forwarding_and_refusals` |
| S9_readyonly | Queued although the proof failed | Caught: `refusals_change_nothing_and_a_failed_proof_keeps_the_statement` |
| S10_evidence | Recorded evidence without the statements | Caught: `confirm_and_convert_then_verified_removal_and_normal_cleanup` |
| S11_labeltext | Dialog label text changed | **Survives** |
| S12_clienttext | Page sends other statement text | Caught: node assertion |
| S13_untrusted | A synthetic click confirms | Caught: node assertion |
| I1_marker | No `tag_repair_checked` on a new MP3 failure | Caught: `classifier_marker_and_summary` |
| I2_details | The marker is not copied into the failure | Caught: `classifier_marker_and_summary` |
| I3_classifier | Classifier ignores the marker | Caught: `classifier_marker_and_summary` |
| I4_children | Retry children qualify again | Caught: `classifier_marker_and_summary` |
| I5_once | The automatic pass asks again | Caught: `automatic_pass_requests_once_and_bulk_accepts` |
| I6_origin | The automatic request is not marked automatic | Caught: `automatic_pass_requests_once_and_bulk_accepts` |
| N1_hexlen | Name rule admits any hex length | **Survives** |
| N2_suffix | Name rule admits any suffix | **Survives** |
| N3_generatedany | Ledger admits any `tag-repair-*` name | **Survives** |
| N4_knownname | Staging check refuses the repair names | Caught: `staging_cleanup_alone_also_removes_the_repair_files` |
| N5_disposable | Cleanup role policy refuses the repair names | Caught: `a_needed_tag_repair_converts_and_every_working_file_is_cleaned`, `staging_cleanup_alone_also_removes_the_repair_files` |
| N6_generated | Ledger refuses the repair names | Caught: `a_needed_tag_repair_converts_and_every_working_file_is_cleaned`, `staging_cleanup_alone_also_removes_the_repair_files` |
| G1_drop | The partition drops one module | Caught: node assertion |
| G2_serial | Serial-server modules spread over workers | Caught: node assertion |
| G3_twoworkers | Two workers | Caught: node assertion |

**Totals:** 69 mutants. 49 are caught and 20 survive. Seven survivors are covered by another check by construction: D7, D9 and D10 (the fence record is built with those values and is digest-bound in the proof), D16 (`links` is part of the facts D14 compares), D19 (the intent CAS on the stored proof), D21 (a handle removal either succeeds or raises) and D26 (only a disposal child is ever bound to a removed checkpoint). The other 13 are F29.

## Verdict

- Total Critical: 0
- Total Major: 1 (F26)
- Total Minor: 16 (F27, F28, F29 and F30 new; F21, F22, F23, F24, F25, F6 attribute half, F8, F9, F10, F11, F18 and F19 carried)

No safety-floor item applies: there is no unsafe Electron config, no secret leakage and no source-of-truth destruction. The one new deletion removes only the private staging files fenced and hashed at isolation, after a verified child (Focus 2).

**Verdict:** RELEASE CLEAR

| # | Sev | Dim | file:line | Finding | Next cycle |
|---|-----|-----|-----------|---------|------------|
| F26 | Major | 2 Correctness | `producer_recovery.py:48-75`, `:234`, `:275`; design `:78-90` | The boot proof trusts an unchecked clock. A same-session attempt passes after a forward step of (last time − startup) + 10 min, and the realistic triggers are automatic. Windows logs every step, and the app does not read the log | Refuse the boot basis when Kernel-General event 1 shows a forward step ≥ margin after the attempt; record tick and wall on new attempts; measure sleep; fix the design text |
| F27 | Minor | 5 Data safety | `merge_service.py:292`, `:244`; `producer_recovery.py:312`, `:387`; `app.js:703` | A policy-kept original gets a false "needs attention" and a false deletion promise. A refused removal is never retried. A `disposing` row with its folder gone never finishes | Gate the enrollment on the policy; retry the removal at startup; treat an absent folder in `disposing` as removed |
| F28 | Minor | 2 Correctness | `audio_jobs.py:55-81` | 0.20.1–0.21.0 failures ("Unknown producer artifact is not admitted", `BoundaryError`) are not offered the Iron Retry; the docstring misstates the class | Count them read-only; offering them is Sergei's call |
| F29 | Minor | 9 Hygiene | `tests/test_iron_skazka*.py/js` | 13 of 20 mutation survivors are gaps: two time sources, `windows_boot()`, the hash, stream and marker checks of removal, the service's roots, the startup removal path, the dialog labels, and name-rule exactness | Add one case for each |
| F30 | Minor | 9 Hygiene | `tests/test_desktop_host.py:26`, `scripts/check-desktop.mjs:13` | Outside the range: a fixed port and token let concurrent runs collide, and one could quit another's test host; the slowest worker leaves 100 s of headroom | OS-assigned port and a random token; weigh the serial modules |
| F21 | Minor | 3 Stability | `inplace_m4b.py:318-322` | Carried from the 10-23 report | Carried |
| F22 | Minor | 5 Data safety | `inplace_m4b.py:99-107` | Carried | Carried |
| F23 | Minor | 2 Correctness | `inplace_m4b.py:516` | Carried | Carried |
| F24 | Minor | 8 Drift | `CHANGELOG.md:9` | Carried | Carried |
| F25 | Minor | 9 Hygiene | `tests/test_inplace_m4b.py:630` | Carried | Carried |
| F6 | Minor | 5 Data safety | `inplace_m4b.py:322` | Carried (attribute half) | Carried |
| F8 | Minor | 2 Correctness | `merge_service.py:2759` | Carried | Carried |
| F9 | Minor | 7 Maintainability | `inplace_m4b.py:211` | Carried | Carried |
| F10 | Minor | 5 Data safety | `inplace_m4b.py:62` | Carried | Carried |
| F11 | Minor | 8 Drift | `inplace_m4b.py:216` | Carried | Carried |
| F18 | Minor | 9 Hygiene | `tests/test_inplace_m4b.py:858` | Carried | Carried |
| F19 | Minor | 9 Hygiene | `scripts/release-contract.mjs:73` | Carried | Carried |

Closed in this range: none of the carried findings. This range does not touch them, apart from shifting the `inplace_m4b.py` line numbers by 3 below `:197`.
