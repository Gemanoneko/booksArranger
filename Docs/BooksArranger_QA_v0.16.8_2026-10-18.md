# Books Arranger v0.16.8 lean packaged smoke, fresh empty private catalog, synthetic payload for the strip and held rows — 2026-10-18, updated for the rebuild

Author: Futaba.

**Verdict:** GO

**Scope of this GO, read it first.** v0.16.8 deletes recovery copies and finishes held source cleanups by itself on first start. I could not prove that a launch against a copy of Sergei's real catalog would leave the real files alone, and I found a path where it would not (section "Why I did not launch against the catalog copy"), so **I did not launch against the catalog copy**, on either build. As instructed, I launched with a fresh empty private catalog and private empty roots. This GO covers: version, a responsive status on an empty catalog, the shipped front end's attention strip and "On hold" row (fed a synthetic payload), Quit, and an unchanged real-folder fingerprint around the run. It does **not** cover any real-catalog behaviour of this build: the backup deletion after verification, the first-start purge, held cleanups finishing, status and list speed under a real catalog, or real attention rows.

Pattern alerts: 1 new (carried from the first v0.16.8 build, still open on the rebuild).
1. **NEW, process and safety: the real-catalog-copy QA recipe is no longer safe from v0.16.8 on.** The recipe's safety argument (private roots, recovery purge refuses paths outside the copy) holds for recovery copies but not for originals. `MergeService._finish_held_cleanups` (`merge_service.py`, runs automatically on the retention thread) resumes every source cleanup held with reason "Download marker native identity differs" or "Unknown download marker contents preserved"; `CleanupJobs.run` (`source_cleanup.py`) takes its library root and output path from the stored intent in the catalog (the real `Z:\Audiobooks`), not from the configured roots, so private empty roots do not stop it. A read-only look at a fresh copy of the real catalog found exactly **3 such held cleanups**. **On the rebuild** (af3a38d) I read the code diff against 65a1d14: it only adds "Keep files" gates, so automatic purges and held-cleanup resumes now skip a book recorded in `kept_files`; the copy has **no `kept_files` table**, so its 3 held rows are not protected and the conclusion stands. Disposition proposed: **fix, in the process**: no catalog-copy launches of 0.16.8 or later until Ender provides a guarded or scrubbed way to do it (Findings 1); Jane to confirm. The earlier `/api/state` alert (closed on the 0.16.7 rebuild) was not re-checked: an empty catalog cannot show it.

Release source commit: af3a38d04c78eed2bfbe468144352fd3bdc66afb
Release artifact manifest SHA256: d7d75936943c32264208a5bbd45491ad78a1197aed50fd84ca183594064d129a

**Artifact covered (rebuild):** `dist/builds/f418bbcd-aa3f-40ed-a4a9-46d9490acf8c/Books-Arranger-Setup-0.16.8.exe` in the electron-m1 worktree. SHA256 `e2f57b011c7c825f68e4407ea78b031f02449e00475d5177f51ba85e1a39aced`, recomputed by me, equals the brief.

Binding checks, made myself: worktree HEAD `af3a38d04c78eed2bfbe468144352fd3bdc66afb` equals `source_head` in `dist/release-artifacts.json`; the SHA256 of that manifest, recomputed by me, equals the manifest line above; the manifest says version 0.16.8, `payload.verified` true, build id `f418bbcd-aa3f-40ed-a4a9-46d9490acf8c`, 223 payload files. The installer extracted with 7za to a private folder; **223 of 223 payload files match the manifest, mismatch `[]`**. `git status` in the worktree was empty when I checked (before this edit).

**First v0.16.8 build (superseded, not covered by this verdict):** installer in `dist/builds/6e8105c1-4d56-45be-a75d-65abf9c0aa49/`, source commit 65a1d144d743ef9c4c83f1759b86fd93dfb53bcd, manifest SHA256 `029546ade7b7d150efe5b0026399d1b1ea23149cd006f04c8dac8138021d9563`; its GO record is kept below.

## Rebuild: result per check (artifact f418bbcd, commit af3a38d)

One launch, 2026-10-18 07:12 UTC, same harness and same isolation as the first build: new empty catalog (`--data-dir` an empty private folder, `--catalog-mode=new`), all three roots private and empty, private profile and temp, port 5213, debug port 19227.

| # | Check | Result |
|---|---|---|
| 1 | Version v0.16.8 | **PASS.** `/api/health` says 0.16.8, first answer 1.8 s after launch; window badge "v0.16.8". |
| 2 | Status stays responsive | **PASS on an empty catalog only.** "Automatic processing: Idle", "0 converted out of 0 approved books · Completed · 0 queued · 0 need attention", "Nothing running". 12 `/api/state` calls: 12 x 200, 4 to 5 ms (p50 4, p95 5); `/api/health` 2 to 9 ms. Not a load test. |
| 3 | Attention strip renders | **PASS with a synthetic payload.** Same made-up `/api/state` as before (retry 5, repair 2, other 1, unsupported 1), Status "Output needs attention": "All · 9", "Can retry · 5", "Can repair · 2", "Other · 1", "M4B not supported · 1"; "Retry all (5)" hidden in the All view, shown and enabled after the "Can retry" filter click; 0 overlapping controls; 0 px horizontal overflow; header "9 need attention". Screenshot `strip-synthetic2.png`. Proves the front-end code, not the server's payload. |
| 4 | Held row: "On hold — reason", no bar, **no clock** | **PASS (the clock is fixed).** Held cleanup row: "Removing originals: Synthetic held book", step **"On hold — Download marker native identity differs"**, progress bar hidden, no detail text, **time text empty** (the first build showed "0:49 elapsed"). Read twice 2.5 s apart: still empty both times. The running conversion row beside it, as a control, keeps its bar (30%), step text and "0:20 elapsed". 0 overlaps between the rows or with the panel. Screenshot `jobs-synthetic2.png`. |
| 5 | Quit exits cleanly | **PASS.** One real renderer mouse press on "Quit Books Arranger" (hit-tested first); shell exit code 0 **0.44 s** after the click. Afterwards the Books Arranger and python process sets equal the pre-launch ones, nothing listens on 5213 or 19227, 0 `etilqs` files. Sergei's app kept listening on 5210 (PID 68264); I sent it no request. |
| 6 | Real fingerprint unchanged | **PASS.** Read-only fingerprint (names, sizes, modification times) of the real `source-recovery` (946 files, 192 folders, 98,303,617,179 bytes), real `replacement-recovery` (3 files, 1 folder, 3,900,201,934 bytes) and `Z:\Audiobooks` (9,119 files, 740 folders, 742,135,138,413 bytes), taken right before and right after the run: **all three digests identical, 0 lines differ.** |

## Why I did not launch against the catalog copy

(Unchanged from the first v0.16.8 build; the rebuild's diff does not change it, see Pattern alert 1.)

What the code does, from reading it:

| Path | What it deletes | Does a catalog copy stay inside its own data folder? |
|---|---|---|
| `RecoveryRetention.purge` (`recovery_retention.py`) | Original-track backups in `source-recovery` | **Yes.** `location` is the engine's own `data\source-recovery\<id>`; every backup must have `path.parent == location` or it raises "Recovery native correspondence is unavailable" before `_prepare` or `_dispose` runs. A copy's stored backup paths point into the real data folder, so they are refused. |
| `ReplacementRetirement.purge_recoveries` (`replacement_retirement.py`) | Recovery copies of three former outputs | **Yes.** `path.parent` must equal `<own data>\replacement-recovery\<id>`, else "Former-output recovery is outside its owned folder". |
| `CleanupJobs.run`, started by `_finish_held_cleanups` | **Original source files**, after copying them to the engine's own recovery folder | **No.** Root, output and cover paths come from the stored intent in the catalog, not from the configured roots. Runs on its own once per launch for the held rows, unless the book is in `kept_files` (new in the rebuild). |

What the copy holds (a fresh read-only copy of the real catalog taken 2026-10-18, 511,397,888 bytes, `quick_check` ok, opened only with `mode=ro&immutable=1`, never launched): `source_cleanup` 182 completed and **3 needs_attention with the two "held for marker metadata" reasons**; `recovery_retention` 179 retained and 3 deleted; 1 completed replacement with 3 removed former outputs; no `kept_files` table. A launch against the copy would be expected to try the 3 held cleanups on the real `Z:`. I cannot prove otherwise, so the instruction applied: fresh empty private catalog, UI and Quit only.

## Rebuild: findings

1. **Major (process), see Pattern alert 1.** Options for Jane to decide (I did none of them; "rewrite nothing"): (a) Ender runs the purge and held-cleanup code under a guarded harness on a throwaway copy; (b) a scrubbed copy of the catalog (the held rows neutralized and stored paths remapped into a private tree) that I can launch; (c) the first live run on Sergei's own machine is the real test of the destructive behaviour, watched on purpose.
2. **Closed on the rebuild: the held row's elapsed clock** (first build, Minor). The time text is now empty on a held row and stays empty.
3. **Informational, for the recipe:** `--data-dir` on an empty folder needs `--catalog-mode=new`; a non-empty folder from an earlier run is refused, so each run needs a new empty folder.

## Rebuild: not covered, method, evidence

- **Not covered:** the same list as the first build: every real-catalog behaviour (recovery copies deleted after verification, the first-start purge, held cleanups finishing, the new Keep-files gates on real rows, folder jobs, fast status under load, list and filter speed, real attention rows, real Retry and Repair buttons); the synthetic checks prove the page renders the payload shape I assumed, not that the server sends it; widths below the default window (1264 x 821 this time), hide-to-tray, the NSIS installer and the tray menu's own Quit, light theme. One launch only.
- **Method:** as in the record below. The synthetic payload is injected in the page by wrapping `fetch` for `/api/state`; nothing on disk changes. Inputs: Status select and the "Can retry" filter button by script, Quit by a real mouse press; the harness has no code path that clicks Start, Resume, Pause, Retry, Retry all or Repair. I did not clean up, as briefed.
- **Evidence**, under `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/3c1cc2ef-43a9-4b2a-b1fa-8a242d8fded6/scratchpad/shared/ba-v0168-qa/`: `evidence/result-empty2.json`, `evidence/jobs-synthetic2.png`, `evidence/strip-synthetic2.png`, `evidence/real-before3.json` and `real-after3.json` (each with a `.lines.txt`); tool `tools/smoke-empty2.mjs`; payload in `payload2/`. The first build's evidence is in `evidence/build1/`, `evidence/try1/` and the un-suffixed files.

## Record of the first v0.16.8 build (65a1d14), superseded by the rebuild above

Everything below is the report as filed on the first build. Its verdict was GO with the same scope; its pins were `65a1d144d743ef9c4c83f1759b86fd93dfb53bcd` and manifest `029546ade7b7d150efe5b0026399d1b1ea23149cd006f04c8dac8138021d9563`. Its Finding 2 (the held row's elapsed clock) is closed by the rebuild.

## Result per check

| # | Check | Result |
|---|---|---|
| 1 | Version v0.16.8 | **PASS.** `/api/health` says 0.16.8, first answer 1.1 s after launch; the window badge reads "v0.16.8". |
| 2 | Status stays responsive | **PASS on an empty catalog only.** "Automatic processing: Idle", jobs line "0 converted out of 0 approved books · Completed · 0 queued · 0 need attention", idle line "Nothing running". 12 `/api/state` calls: 12 x 200, 3 to 5 ms; `/api/health` 2 to 13 ms. This is not a load test; the build's "fast status under load" is not exercised. |
| 3 | Attention strip renders | **PASS with a synthetic payload.** I fed the shipped page a made-up `/api/state` (attention counts retry 5, repair 2, other 1, unsupported 1) and set Status to "Output needs attention". Strip: "All · 9", "Can retry · 5", "Can repair · 2", "Other · 1", "M4B not supported · 1". "Retry all (5)" is hidden in the All view and shows, enabled, after clicking the "Can retry" filter button (the only button I clicked besides Quit); 0 overlapping strip controls; 0 px horizontal overflow; header says "9 need attention". Screenshot `strip-synthetic.png`. This proves the front-end code, not that the server sends such counts. |
| 4 | Held rows show "On hold — reason", no bar | **PASS with a synthetic payload.** Held cleanup row: "Removing originals: Synthetic held book", step text **"On hold — Download marker native identity differs"**, progress bar hidden, no detail text, row styled as attention. The running conversion row next to it, as a control, keeps its bar (30%), "Step 3 of 5 - Encoding audio". No overlaps between the two rows or with the panel's other parts. Screenshot `jobs-synthetic.png`. Observation (Finding 2): the held row still shows an "elapsed" clock. |
| 5 | Quit exits cleanly | **PASS.** One real renderer mouse press on "Quit Books Arranger" (private debug port, hit-tested first); shell exit code 0 **0.36 s** after the click. Afterwards the Books Arranger and python process sets equal the pre-launch ones, nothing listens on my port 5213 or debug port 19227, 0 `etilqs` files. Sergei's app kept listening on 5210 (PID 68264); I sent it no request. |
| 6 | Real fingerprint unchanged | **PASS for the run, with a caveat on a first attempt.** See the next section. |

## Real-folder fingerprint (read-only: names, sizes, modification times)

Folders: the real `data\source-recovery`, the real `data\replacement-recovery`, and `Z:\Audiobooks`.

**The run that counts (second launch, before and after taken seconds around it):** `source-recovery` 942 files, 188 folders, 97,430,276,218 bytes; `replacement-recovery` 3 files, 1 folder, 3,900,201,934 bytes; `Z:\Audiobooks` 9,119 files, 738 folders, 742,114,732,323 bytes. **All three digests identical before and after; 0 lines differ.**

**First attempt, not a test:** I launched with `--data-dir` pointing at an empty folder and without `--catalog-mode=new`; the app refused to start ("This folder does not contain a recognized Books Arranger catalog") and exited with code 1 two seconds after launch, creating nothing. The fingerprints around that attempt differed, and I checked why: `source-recovery` gained one file (a 739,304,702-byte `00000.m4b` in a new set folder) and `Z:` lost one 739,304,702-byte m4b with the same size and the same 2020 modification time, and gained a 399,137,894-byte "The Invited" m4b whose modification time is 06:57:12 UTC. The sizes add up exactly (Z: total down by 340,166,808 bytes). That is Sergei's own running app converting a book and moving its original into the real recovery folder. It cannot have been mine: my app had exited at 06:53:45 UTC, 3.5 minutes before that file was written, and it had no catalog to act on. Sergei's app is live (its process IDs changed since my last session), so the real folders move on their own; only a window around my own run can be compared, and that window is clean.

## Findings

1. **Major (process), see Pattern alert 1.** A catalog-copy launch of 0.16.8 or later is not safe as the recipe stands. Options for Jane to decide (I did none of them; "rewrite nothing"): (a) Ender runs the purge and held-cleanup code under a guarded harness on a throwaway copy; (b) a scrubbed copy of the catalog (the 3 held rows neutralized and stored paths remapped into a private tree) that I can launch; (c) the first live run on Sergei's own machine is the real test of the destructive behaviour, with that run watched on purpose.
2. **Minor, for Judy and Ender. The held row still shows an "elapsed" clock** ("0:49 elapsed" in `jobs-synthetic.png`); a code comment in `web/app.js` says a held row has "no bar, count or clock". The code freezes the clock on held rows, which may be the intent. In my run the clock read 0:52 then 0:50 because my made-up payload moved `step_started_at` on every poll, so I cannot say whether it stays frozen with real data.
3. **Informational, for the recipe.** `--data-dir` on an empty folder needs `--catalog-mode=new` to create a catalog; without it the app exits with code 1 and a plain message.
4. **Informational.** The scratch folders from my 0.16.7 runs were gone from the session scratchpad when I started (I did not delete them), so the evidence paths named in the v0.16.7 report no longer exist.

## Not covered

- Every real-catalog behaviour of this build: recovery copies deleted after verification, the first-start purge of the 179 retained sets, the 3 held cleanups finishing, folder jobs, "fast status under load", list and filter speed, real attention rows, real Retry and Repair buttons.
- The synthetic checks prove the page renders a payload of the shape I assumed (`state.activities`, `audiobook_jobs.attention_counts`); they do not prove the server produces it.
- Widths below 1266 x 823, hide-to-tray, the NSIS installer and the tray menu's own Quit, light theme. One launch only.

## Method and isolation

- Private extraction of the installer payload (hash-verified); a new empty catalog (`--data-dir` an empty private folder, `--catalog-mode=new`); `--roots-json` with all three roots private and empty (Audiobooks too); private shell profile, APPDATA, LOCALAPPDATA and TEMP; port 5213; private `--remote-debugging-port` 19227; `--show-inactive --quiet-errors`. The shell was my own child process, launched by a node harness that records PID, exit code and exit time and kills only its own tree on failure (it did not need to).
- The catalog copy was a plain `cp` of the real `inventory.sqlite3` (the real file's size and modification time were identical before and after; its `-wal` was 4,696,832 bytes, so the copy is the last checkpointed state, not byte-equal to the live file). It was read with `mode=ro&immutable=1` to count rows and was never launched against. No `-wal`, `-shm`, lock, instance or recovery file was copied.
- The synthetic payload was injected in the page by wrapping `fetch` for `/api/state`; it never leaves the page and changes nothing on disk. Inputs: Status select and the "Can retry" filter button by script, Quit by a real mouse press. The harness has no code path that clicks Start, Resume, Pause, Retry, Retry all or Repair.
- I did not clean up, as briefed.

## Evidence

Under `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/3c1cc2ef-43a9-4b2a-b1fa-8a242d8fded6/scratchpad/shared/ba-v0168-qa/`:

- `evidence/result-empty.json` (all reads, timings, process sets, quit), `evidence/jobs-synthetic.png`, `evidence/strip-synthetic.png`, shell logs; `evidence/try1/` (the refused first launch).
- `evidence/real-before2.json` and `real-after2.json` (the counting pair), `real-before.json` and `real-after.json` (the first attempt), each with a `.lines.txt` of every name, size and modification time.
- Tools: `tools/smoke-empty.mjs`, `tools/fingerprint.py`; the unused catalog copy is `data/inventory.sqlite3`.
