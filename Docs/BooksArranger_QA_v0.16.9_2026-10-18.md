# Books Arranger v0.16.9 lean packaged smoke, fresh empty private catalog, synthetic payload for the strip and held rows — 2026-10-18

Author: Futaba.

**Verdict:** GO

**Scope of this GO, read it first.** Same isolated run as v0.16.8: a fresh empty private catalog with private empty roots, **not** a copy of Sergei's real catalog (a launch against a copy would try to finish held source cleanups on the real `Z:`, see v0.16.8 report and Pattern alert 1). This GO covers: version, a responsive status on an empty catalog, the shipped front end's attention strip and "On hold" row (fed a synthetic payload), Quit, and an unchanged real-folder fingerprint around the run. It does **not** cover what v0.16.9 actually changes: the commit list is "SMB file-ID drift no longer flags unchanged sources; two more M4B shapes" (`audio_jobs.py`, `failed_m4b_retry.py`, `m4b_preservation.py`, `review_backend.py`), and none of that runs on an empty catalog. It also does not cover any real-catalog behaviour (backup deletion, first-start purge, held cleanups, status and list speed under a real catalog, real attention rows).

Pattern alerts: 1, carried from v0.16.8, still open.
1. **The real-catalog-copy QA recipe is not safe from v0.16.8 on, so two builds in a row (0.16.8 rebuild, 0.16.9) have had no real-catalog behaviour check.** Cause unchanged: `MergeService._finish_held_cleanups` resumes held source cleanups on its own and `CleanupJobs.run` takes its roots and output paths from the catalog, not from the configured roots. I checked the code diff from the last build I covered (af3a38d) to this one: it touches only `audio_jobs.py`, `failed_m4b_retry.py`, `m4b_preservation.py`, `review_backend.py` and the version files, not `merge_service.py`, `recovery_retention.py`, `source_cleanup.py` or the replacement code, so the v0.16.8 analysis stands. Disposition proposed: **fix, in the process**, waiting on Jane's choice among the three options in the v0.16.8 report (a guarded harness run by Ender, a scrubbed copy, or a watched first live run); until then, no catalog-copy launches. The M4B and file-ID changes in this build are exactly the kind of change that needs real data, so the gap now has a cost.

Release source commit: 0a2bc63709006d5ef8a2e2ac92fbc3444a6844f6
Release artifact manifest SHA256: 9c32a68d676cbb8b3cda4ebc75f27136f6dc03d3227305c947c7abd0abb98ba5

**Artifact covered:** `dist/builds/fcfb5802-7934-4408-a832-b8d0a6ecf6aa/Books-Arranger-Setup-0.16.9.exe` in the electron-m1 worktree. SHA256 `8469f8c9caa3d5735082745b24d4ed5d7c38ea049cb4c7f073b9cc31c9f565d5`, recomputed by me, equals the brief.

Binding checks, made myself: worktree HEAD `0a2bc63709006d5ef8a2e2ac92fbc3444a6844f6` equals `source_head` in `dist/release-artifacts.json`; the SHA256 of that manifest, recomputed by me, equals the manifest line above; the manifest says version 0.16.9, `payload.verified` true, build id `fcfb5802-7934-4408-a832-b8d0a6ecf6aa`, 223 payload files. The installer extracted with 7za to a private folder; **223 of 223 payload files match the manifest, mismatch `[]`**. `git status` in the worktree was empty when I checked (before this report was added).

## Result per check

One launch, 2026-10-18 08:43 UTC. New empty catalog (`--data-dir` an empty private folder, `--catalog-mode=new`), all three roots private and empty, private shell profile, APPDATA, LOCALAPPDATA and TEMP, port 5213, private debug port 19227, `--show-inactive --quiet-errors`. The shell was my own child process.

| # | Check | Result |
|---|---|---|
| 1 | Version v0.16.9 | **PASS.** `/api/health` says 0.16.9, first answer 1.8 s after launch; window badge "v0.16.9". |
| 2 | Status stays responsive | **PASS on an empty catalog only.** "Automatic processing: Idle", "0 converted out of 0 approved books · Completed · 0 queued · 0 need attention", "Nothing running". 12 `/api/state` calls: 12 x 200, 3 to 4 ms; `/api/health` 2 to 10 ms. Not a load test. |
| 3 | Attention strip renders | **PASS with a synthetic payload.** Made-up `/api/state` (retry 5, repair 2, other 1, unsupported 1), Status "Output needs attention": "All · 9", "Can retry · 5", "Can repair · 2", "Other · 1", "M4B not supported · 1"; "Retry all (5)" hidden in the All view, shown and enabled after the "Can retry" filter click (the only button I clicked besides Quit); 0 overlapping controls; 0 px horizontal overflow; header "9 need attention". Screenshot `strip-synthetic.png`. Proves the front-end code, not the server's payload. |
| 4 | Held row "On hold — reason", no bar, no clock (re-checked, same as v0.16.8 rebuild) | **PASS.** Held cleanup row: "Removing originals: Synthetic held book", step "On hold — Download marker native identity differs", bar hidden, no detail, time text empty in both reads 2.5 s apart; the running conversion row beside it keeps its bar (30%) and "0:20 elapsed". 0 overlaps. Screenshot `jobs-synthetic.png`. |
| 5 | Quit exits cleanly | **PASS.** One real renderer mouse press on "Quit Books Arranger" (hit-tested first); shell exit code 0 **0.42 s** after the click. Afterwards the Books Arranger and python process sets equal the pre-launch ones, nothing listens on 5213 or 19227, 0 `etilqs` files. Sergei's app kept listening on 5210 (PID 38128); I sent it no request. |
| 6 | Real fingerprint unchanged | **PASS.** Read-only fingerprint (names, sizes, modification times) of the real `data\source-recovery` (0 files, 3 folders), real `data\replacement-recovery` (0 files, 0 folders) and `Z:\Audiobooks` (9,056 files, 742 folders, 740,097,142,247 bytes), taken right before and right after the run: **all three digests identical, 0 lines differ.** |

## Findings

1. **Informational: the real folders changed a lot since my last fingerprint, by Sergei's own app, not by this run.** At the v0.16.8 rebuild check the real `source-recovery` held 946 files (98.3 GB) and `replacement-recovery` 3 files (3.9 GB); both are empty now, and `Z:\Audiobooks` went from 9,119 to 9,056 files. Sergei's app was restarted in between (new process IDs, 5210 now PID 38128). That fits the backup deletion and the finishing of held cleanups that v0.16.8 does on its own. Only the window around my own run is compared, and that window is clean. I did not check whether the app deleted anything it should not have; that is outside this smoke.
2. **Process, see Pattern alert 1.** No new finding on the build itself.

## Not covered

- Everything this build changes: the SMB file-ID drift fix (unchanged sources no longer flagged) and the two additional M4B shapes, on real data or any data.
- Every real-catalog behaviour: recovery copies deleted after verification, the first-start purge, held cleanups finishing, Keep files on real rows, folder jobs, fast status under load, list and filter speed, real attention rows, real Retry and Repair buttons.
- The synthetic checks prove the page renders the payload shape I assumed (`state.activities`, `audiobook_jobs.attention_counts`), not that the server sends it.
- Widths below the default window (1264 x 821), hide-to-tray, the NSIS installer and the tray menu's own Quit, light theme. One launch only.

## Method and isolation

- Private extraction of the installer payload (hash-verified); no catalog copy was made or launched this time. The synthetic payload is injected in the page by wrapping `fetch` for `/api/state`; nothing on disk changes. Inputs: Status select and the "Can retry" filter button by script, Quit by a real mouse press; the harness has no code path that clicks Start, Resume, Pause, Retry, Retry all or Repair.
- The session scratchpad `shared/` folder had been cleared, so I rewrote my harness (`tools/smoke-empty.mjs`) and fingerprint script (`tools/fingerprint.py`) from the same design as the v0.16.8 run; the checks are the same.
- I did not clean up, as briefed.

## Evidence

Under `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/3c1cc2ef-43a9-4b2a-b1fa-8a242d8fded6/scratchpad/shared/ba-v0169-qa/`: `evidence/result-empty.json` (all reads, timings, process sets, quit), `evidence/jobs-synthetic.png`, `evidence/strip-synthetic.png`, `evidence/real-before.json` and `real-after.json` (each with a `.lines.txt` of every name, size and modification time), shell logs; tools `tools/smoke-empty.mjs`, `tools/fingerprint.py`; payload in `payload/`.
