# Books Arranger v0.16.10 lean packaged smoke, fresh empty private catalog, synthetic payload for the strip and held rows — 2026-10-18

Author: Futaba.

**Verdict:** GO

**Scope of this GO, read it first.** Same isolated run as v0.16.8 and v0.16.9: a fresh empty private catalog with private empty roots, **not** a copy of Sergei's real catalog (a launch against a copy would try to finish held source cleanups on the real `Z:`, see the v0.16.8 report). This GO covers: version, a responsive status on an empty catalog, the shipped front end's attention strip and "On hold" row (fed a synthetic payload), Quit, and an unchanged real-folder fingerprint around a run. It does **not** cover what v0.16.10 changes: "retry and repair jobs no longer fail the start-of-book source check" (`audio_jobs.py` and the Retry/Repair admission in `merge_service.py`); that needs a real catalog with real attention rows, and none of it runs on an empty one. It also does not cover any other real-catalog behaviour.

Pattern alerts: 2, both open.
1. **Third build in a row (0.16.8 rebuild, 0.16.9, 0.16.10) with no real-catalog behaviour check, because the catalog-copy recipe is not safe from v0.16.8 on.** Cause unchanged (`_finish_held_cleanups` resumes held source cleanups by itself; `CleanupJobs.run` takes its roots from the catalog, not from the configured roots). I read the code diff from the last build I covered (0a2bc63) to this one: `audio_jobs.py`, `merge_service.py` (only the Retry/Repair admission, `_queue_next_same` and the job-only-fields comparison) and the version files; nothing in `recovery_retention.py`, `source_cleanup.py`, the cleanup or purge code, so the v0.16.8 analysis stands. This build's own fix is on exactly the path that needs real rows. Disposition proposed: **fix, in the process**, still waiting on Jane's choice among the three options in the v0.16.8 report (a guarded harness run by Ender, a scrubbed copy I can launch, or a watched first live run); until then, no catalog-copy launches.
2. **New: the real folders change under Sergei's live app, so a fingerprint pair can differ without my run.** It happened again here (first run, below) and on the first v0.16.8 build. Disposition proposed: **accept**, with the rule I used: repeat until a pair taken around my own run is identical, and attribute any difference (my engine has no catalog, private roots, and its own recovery folders are empty).

Release source commit: 1dea7494bf158a17e225381747e799606e00d89e
Release artifact manifest SHA256: aaf2b0cac455eb4419cd0138dcf7d15d08d0e1772cc0d752ba9161cc86a6778c

**Artifact covered:** `dist/builds/e10961b5-abe1-41fd-b4e9-51e8ebdafe98/Books-Arranger-Setup-0.16.10.exe` in the electron-m1 worktree. SHA256 `b9cbfc40ebd42bdf74460d688dfcd9e4d936b6006237c6060823fc00e188305e`, recomputed by me, equals the brief.

Binding checks, made myself: worktree HEAD `1dea7494bf158a17e225381747e799606e00d89e` equals `source_head` in `dist/release-artifacts.json`; the SHA256 of that manifest, recomputed by me, equals the manifest line above; the manifest says version 0.16.10, `payload.verified` true, build id `e10961b5-abe1-41fd-b4e9-51e8ebdafe98`, 223 payload files. The installer extracted with 7za to a private folder; **223 of 223 payload files match the manifest, mismatch `[]`**. `git status` in the worktree was empty when I checked (before this report was added).

## Result per check

Two launches on 2026-10-18 (10:19:59 UTC and 10:21:24 UTC), identical setup: new empty catalog (`--data-dir` an empty private folder, `--catalog-mode=new`), all three roots private and empty, private shell profile, APPDATA, LOCALAPPDATA and TEMP, port 5213, private debug port 19227, `--show-inactive --quiet-errors`; the shell was my own child process. Both runs gave the same results for checks 1 to 5; times below are from the second run.

| # | Check | Result |
|---|---|---|
| 1 | Version v0.16.10 | **PASS.** `/api/health` says 0.16.10, first answer 1.1 s after launch (1.8 s in the first run); window badge "v0.16.10". |
| 2 | Status stays responsive | **PASS on an empty catalog only.** "Automatic processing: Idle", "0 converted out of 0 approved books · Completed · 0 queued · 0 need attention". 12 `/api/state` calls: 12 x 200, 3 to 5 ms (first run: 3 to 6 ms); `/api/health` 2 to 10 ms. Not a load test. |
| 3 | Attention strip renders | **PASS with a synthetic payload.** Made-up `/api/state` (retry 5, repair 2, other 1, unsupported 1), Status "Output needs attention": "All · 9", "Can retry · 5", "Can repair · 2", "Other · 1", "M4B not supported · 1"; "Retry all (5)" hidden in the All view, shown and enabled after the "Can retry" filter click (the only button I clicked besides Quit); 0 overlapping controls; 0 px horizontal overflow. Screenshot `strip-synthetic.png`. Proves the front-end code, not the server's payload. |
| 4 | Held row "On hold — reason", no bar, no clock | **PASS.** "Removing originals: Synthetic held book", step "On hold — Download marker native identity differs", bar hidden, time text empty in both reads 2.5 s apart; the running conversion row beside it keeps its bar (30%) and "0:20 elapsed"; 0 overlaps. Screenshot `jobs-synthetic.png`. |
| 5 | Quit exits cleanly | **PASS.** One real renderer mouse press on "Quit Books Arranger" (hit-tested first); shell exit code 0 **0.38 s** after the click (0.30 s in the first run). Afterwards the Books Arranger and python process sets equal the pre-launch ones, nothing listens on 5213 or 19227, 0 `etilqs` files. Sergei's app kept listening on 5210 (PID 55096); I sent it no request. |
| 6 | Real fingerprint unchanged | **PASS on the second run; the first run's pair differed by one file, attributed to Sergei's app.** Read-only fingerprint (names, sizes, modification times) of the real `data\source-recovery`, `data\replacement-recovery` and `Z:\Audiobooks`. **Second run, pair taken right before and right after:** `source-recovery` 0 files, 3 folders; `replacement-recovery` 0 files, 0 folders; `Z:\Audiobooks` 9,056 files, 745 folders, 740,196,598,134 bytes; **all three digests identical, 0 lines differ.** **First run:** `Z:` went from 9,057 to 9,056 files (740,393,216,974 to 740,196,598,134 bytes, down 196,618,840): one file gone, `Philip K. Dick\<Cyrillic title>.m4b`, 196,618,840 bytes, modification time 2019. I attribute it to Sergei's running app finishing a cleanup, because: my engine had an empty catalog and private empty roots; removing an original always first copies it into the engine's own recovery folder, and my engine's `source-recovery` and `replacement-recovery` hold 0 files; and two later walks (a third one with nothing of mine running, and the second run's pair) show `Z:` stable afterwards, so it was one event. The timing alone cannot separate it from my 25-second run, because each walk of `Z:` takes about 30 seconds. |

## Findings

1. **Process, see Pattern alert 1.** No finding on the build itself.
2. **Informational.** The real `source-recovery` and `replacement-recovery` are still empty (0 files), as at v0.16.9; Sergei's app was restarted again since then (5210 is now PID 55096).

## Not covered

- Everything this build changes: Retry and Repair jobs passing the start-of-book source check (the `m4b_repair` binding, `retry_admission_hold`, queue-next for Repair), on real data or any data.
- Every real-catalog behaviour: recovery copies deleted after verification, the first-start purge, held cleanups finishing, Keep files on real rows, folder jobs, fast status under load, list and filter speed, real attention rows, real Retry and Repair buttons.
- The synthetic checks prove the page renders the payload shape I assumed (`state.activities`, `audiobook_jobs.attention_counts`), not that the server sends it.
- Widths below the default window (1264 x 821), hide-to-tray, the NSIS installer and the tray menu's own Quit, light theme.

## Method and isolation

- Private extraction of the installer payload (hash-verified); no catalog copy was made or launched. The synthetic payload is injected in the page by wrapping `fetch` for `/api/state`; nothing on disk changes. Inputs: Status select and the "Can retry" filter button by script, Quit by a real mouse press; the harness has no code path that clicks Start, Resume, Pause, Retry, Retry all or Repair.
- Harness and fingerprint script are the ones I rewrote for v0.16.9 (`tools/smoke-empty.mjs`, `tools/fingerprint.py`), copied unchanged. The second run used a new empty data folder (a non-empty one is refused by `--catalog-mode=new`).
- I did not clean up, as briefed.

## Evidence

Under `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/3c1cc2ef-43a9-4b2a-b1fa-8a242d8fded6/scratchpad/shared/ba-v0170-qa/`: `evidence/result-empty.json`, `evidence/jobs-synthetic.png`, `evidence/strip-synthetic.png`, `evidence/real-before.json` and `real-after.json` (the second, counting pair; each with a `.lines.txt` of every name, size and modification time), shell logs; `evidence/run1/` (the first run, with its differing pair and the third `Z:` walk `real-after2.json`); tools in `tools/`; payload in `payload/`; the first run's empty data folder is `emptydata-run1/`.
