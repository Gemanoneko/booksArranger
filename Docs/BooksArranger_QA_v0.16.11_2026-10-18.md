# Books Arranger v0.16.11 lean packaged smoke, fresh empty private catalog, synthetic payload for the strip and held rows — 2026-10-18

Author: Futaba.

**Verdict:** GO

**Scope of this GO, read it first.** Same isolated run as v0.16.8 to v0.16.10: a fresh empty private catalog with private empty roots, **not** a copy of Sergei's real catalog (a launch against a copy would try to finish held source cleanups on the real `Z:`, see the v0.16.8 report). This GO covers: version, a responsive status on an empty catalog, the shipped front end's attention strip and "On hold" row (fed a synthetic payload), Quit, and an unchanged real-folder fingerprint around a run. It does **not** cover what v0.16.11 changes: series lookup from Goodreads with a FantLab fallback (`public_research.py`) and finishing the orphaned temporary-file cleanup of finished books (`merge_service.py`, new `_finish_temporary_cleanups`); both need real books, and the series lookup needs the network. It also does not cover any other real-catalog behaviour.

Pattern alerts: 2, both open, both carried.
1. **Fourth build in a row (0.16.8 rebuild, 0.16.9, 0.16.10, 0.16.11) with no real-catalog behaviour check, because the catalog-copy recipe is not safe from v0.16.8 on, and this build adds another automatic deletion path.** Cause unchanged (`_finish_held_cleanups` resumes held source cleanups by itself; `CleanupJobs.run` takes its roots from the catalog, not from the configured roots). New in this build: `MergeService._finish_temporary_cleanups` runs on the retention thread, once per run, for every finished book whose temporary-file cleanup has no record or stopped early, and calls `_prune_completed`. I did not read `_prune_completed` or what paths it can reach, so I cannot say whether a catalog copy could make it touch real files; that is one more thing the recipe would have to prove. The code diff from the last build I covered (1dea749) is `merge_service.py`, `public_research.py` and the version files; nothing in `recovery_retention.py` or `source_cleanup.py`. Disposition proposed: **fix, in the process**, still waiting on Jane's choice among the three options in the v0.16.8 report (a guarded harness run by Ender, a scrubbed copy I can launch, or a watched first live run); until then, no catalog-copy launches.
2. **The real folders change under Sergei's live app, so a fingerprint pair can differ without my run** (third time: first v0.16.8 build, v0.16.10, now here). Disposition proposed: **accept**, with the rule I used: repeat until a pair taken around my own run is identical, and attribute any difference (my engine has no catalog, private roots, and its own recovery folders are empty).

Release source commit: 2befe71e64ad482834f0b7cb159d91eb1cba6bd2
Release artifact manifest SHA256: e8e0aa44d6790d4e71428a911efd14a0fbe7e7a308e497cdef5516d4f033bf5b

**Artifact covered:** `dist/builds/8102e126-aa3a-458a-abf1-1ed2f223b519/Books-Arranger-Setup-0.16.11.exe` in the electron-m1 worktree. SHA256 `f92fbfca58e54d17e66e27d8d6f97ed83793ba9451e4db293de6c58fe4984712`, recomputed by me, equals the brief.

Binding checks, made myself: worktree HEAD `2befe71e64ad482834f0b7cb159d91eb1cba6bd2` equals `source_head` in `dist/release-artifacts.json`; the SHA256 of that manifest, recomputed by me, equals the manifest line above; the manifest says version 0.16.11, `payload.verified` true, build id `8102e126-aa3a-458a-abf1-1ed2f223b519`, 223 payload files. The installer extracted with 7za to a private folder; **223 of 223 payload files match the manifest, mismatch `[]`**. `git status` in the worktree was empty when I checked (before this report was added).

## Result per check

Two launches on 2026-10-18 (about 11:49 UTC, the second at 11:49:38 UTC), identical setup: new empty catalog (`--data-dir` an empty private folder, `--catalog-mode=new`), all three roots private and empty, private shell profile, APPDATA, LOCALAPPDATA and TEMP, port 5213, private debug port 19227, `--show-inactive --quiet-errors`; the shell was my own child process. Both runs gave the same results for checks 1 to 5; times below are from the second run.

| # | Check | Result |
|---|---|---|
| 1 | Version v0.16.11 | **PASS.** `/api/health` says 0.16.11, first answer 1.1 s after launch (1.7 s in the first run); window badge "v0.16.11". |
| 2 | Status stays responsive | **PASS on an empty catalog only.** "Automatic processing: Idle", "0 converted out of 0 approved books · Completed · 0 queued · 0 need attention", "Nothing running". 12 `/api/state` calls: 12 x 200, 3 to 6 ms (same in the first run); `/api/health` 2 to 10 ms. Not a load test. |
| 3 | Attention strip renders | **PASS with a synthetic payload.** Made-up `/api/state` (retry 5, repair 2, other 1, unsupported 1), Status "Output needs attention": "All · 9", "Can retry · 5", "Can repair · 2", "Other · 1", "M4B not supported · 1"; "Retry all (5)" hidden in the All view, shown and enabled after the "Can retry" filter click (the only button I clicked besides Quit); 0 overlapping controls; 0 px horizontal overflow. Screenshot `strip-synthetic.png`. Proves the front-end code, not the server's payload. |
| 4 | Held row "On hold — reason", no bar, no clock | **PASS.** "Removing originals: Synthetic held book", step "On hold — Download marker native identity differs", bar hidden, time text empty in both reads 2.5 s apart; the running conversion row beside it keeps its bar (30%) and "0:20 elapsed"; 0 overlaps. Screenshot `jobs-synthetic.png`. |
| 5 | Quit exits cleanly | **PASS.** One real renderer mouse press on "Quit Books Arranger" (hit-tested first); shell exit code 0 **0.45 s** after the click (0.35 s in the first run). Afterwards the Books Arranger and python process sets equal the pre-launch ones, nothing listens on 5213 or 19227, 0 `etilqs` files. Sergei's app kept listening on 5210 (PID 45068); I sent it no request. One python process (PID 33528, not mine, already gone when I looked) appeared during the first run; my own engine's PID was gone after Quit. |
| 6 | Real fingerprint unchanged | **PASS on the second run; the first run's pair differed by one file, attributed to Sergei's app.** Read-only fingerprint (names, sizes, modification times) of the real `data\source-recovery`, `data\replacement-recovery` and `Z:\Audiobooks`. **Second run, pair taken right before and right after (14:49:32 to 14:50:05 local):** `source-recovery` 0 files, 3 folders; `replacement-recovery` 0 files, 0 folders; `Z:\Audiobooks` 9,056 files, 750 folders, 740,292,972,317 bytes; **all three digests identical, 0 lines differ.** **First run:** `Z:` went from 9,057 to 9,056 files (740,686,015,283 to 740,292,972,317 bytes, down 393,042,966): one file gone, `Richard Laymon\<Cyrillic title>.m4b`, 393,042,966 bytes, modification time 2024. Attributed to Sergei's running app finishing a cleanup: my engine had an empty catalog and private empty roots; its own `source-recovery` and `replacement-recovery` hold 0 files in both runs (removing an original first copies it into the engine's own recovery folder); and the second run's walk shows `Z:` stable straight after. Each walk of `Z:` takes 30 to 55 seconds, so timing alone cannot separate it from my 25-second run. |

## Findings

1. **Process, see Pattern alert 1.** No finding on the build itself.
2. **Informational.** The real `source-recovery` and `replacement-recovery` are still empty (0 files), as at v0.16.9 and v0.16.10; Sergei's app was restarted again since then (5210 is now PID 45068).

## Not covered

- Everything this build changes: Goodreads series with FantLab fallback (network lookups, matching, what the UI shows for a series), and the orphaned temporary-file cleanup of finished books; on real data or any data. I did not watch for network calls from my launch.
- Every real-catalog behaviour: recovery copies deleted after verification, the first-start purge, held cleanups finishing, Keep files on real rows, folder jobs, fast status under load, list and filter speed, real attention rows, real Retry and Repair buttons.
- The synthetic checks prove the page renders the payload shape I assumed (`state.activities`, `audiobook_jobs.attention_counts`), not that the server sends it.
- Widths below the default window (1264 x 821), hide-to-tray, the NSIS installer and the tray menu's own Quit, light theme.

## Method and isolation

- Private extraction of the installer payload (hash-verified); no catalog copy was made or launched. The synthetic payload is injected in the page by wrapping `fetch` for `/api/state`; nothing on disk changes. Inputs: Status select and the "Can retry" filter button by script, Quit by a real mouse press; the harness has no code path that clicks Start, Resume, Pause, Retry, Retry all or Repair.
- Harness and fingerprint script are the ones I rewrote for v0.16.9 (`tools/smoke-empty.mjs`, `tools/fingerprint.py`), copied unchanged. Each launch used a new empty data folder (a non-empty one is refused by `--catalog-mode=new`); I moved the first run's folder aside rather than deleting it.
- I did not clean up, as briefed.

## Evidence

Under `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/3c1cc2ef-43a9-4b2a-b1fa-8a242d8fded6/scratchpad/shared/ba-v0171-qa/`: `evidence/result-empty.json`, `evidence/jobs-synthetic.png`, `evidence/strip-synthetic.png`, `evidence/real-before.json` and `real-after.json` (the second, counting pair; each with a `.lines.txt` of every name, size and modification time), shell logs; `evidence/attempt1/` (the first run with its differing pair); tools in `tools/`; payload in `payload/`; the first run's empty data folder is `emptydata-run1/`.
