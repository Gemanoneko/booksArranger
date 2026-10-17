# Books Arranger v0.16.4 packaged QA on a copy of the real catalog, real Z:\Audiobooks root — 2026-10-17

Author: Futaba.

**Verdict:** GO

Pattern alerts: 2.
1. The stale "local prototype" version label is still open (fifth build in a row: v0.16.0, v0.16.1, v0.16.2, v0.16.3, v0.16.4; Finding 3). It is now narrower: only while the window is hidden to the tray (14 of 17 hidden reads, 0 of 33 shown reads). Disposition: defer (Minor, wording only), for Jane to confirm.
2. The `/api/state` latency target (p95 under 2.0 s) has now been missed on four builds in a row (v0.16.1 1.66 s, v0.16.2 3.44 s, v0.16.3 3.15 s, v0.16.4 3.87 s on this run; Finding 1). This pass adds a visible tail: 4 of 91 sampler polls hit the engine's 4.0 s ceiling and returned 503. The brief accepts the p95 as known catalog cost. Disposition: accept for this release as briefed, with the follow-up owned by Ender (root cause: status computation cost on a 485 MB catalog), for Jane to confirm. If the catalog grows, the 4.0 s ceiling is what turns slowness into the v0.16.3 failure again.

**Why GO.** The v0.16.3 Blocker is fixed and I could not reproduce any part of it. Quit was honoured on all five launches, including twice in the middle of the one-time hash (at +29 s and +55 s): click to process exit 3.4 s and 4.9 s, exit code 0, every owned process gone, port 5212 free, 0 temp files, and the NAS reads stopped with the process. Over 18 minutes of the first launch, with the full hash running, the window never showed "Waiting for the engine checkpoint…", never showed "unavailable", and Start and Quit were enabled on every read (50 window reads over five launches, 0 with a state problem). The hash ran at 30.6 MiB/s on average (peak 34.2) for 14.0 minutes and read 25.0 GiB, against 100 MiB/s and 42.3 GiB in v0.16.3. The second launch read 0 MiB from the share and showed the full Ready count at once. Z: and the real data folder are unchanged, with 0 bytes written to the share. None of the NO-GO criteria in the brief fired. The one thing I want Jane to read before relying on this GO is Finding 1: occasional 503s on `/api/state`.

**Artifact covered:** `dist/builds/fda054e7-1abd-4a1a-8102-40c512e18f9c/Books-Arranger-Setup-0.16.4.exe` in the release-candidate worktree, 172,948,408 bytes, SHA256 `758a0d08faf0e4483dc27f1035404bbbf6bd1b8b47852b13859bf27639cd16a4` (recomputed by me, matches the brief and the manifest).

Release source commit: b6cae4c21dc667eaafa27bd74a50504d7de54d13
Release artifact manifest SHA256: 69d1272b3b181b91a03181828a496cb77328a81307114380b2f30d6b3fa6973c

Binding checks I made myself: the worktree HEAD equals the source commit above and equals `source_head` in `dist/release-artifacts.json`; the worktree was clean when I started (a Senua code-review file for v0.16.4 appeared later, untracked, not mine, not touched); I recomputed the SHA256 of `dist/release-artifacts.json` and it equals the manifest line above; the manifest says version 0.16.4, `payload.verified` true, product digest `1b642bd1dd1884732bab0bf641702c5c4583c533e6595ab46a5672f63a63b682`, build id `fda054e7-1abd-4a1a-8102-40c512e18f9c`. All 219 extracted payload files match the manifest hashes (zero mismatches). I extracted the payload myself with 7za into `scratchpad/shared/payload-0.16.4` (none was left by Ender). The only change I made in the worktree is this report file.

Scope: packaged app (shipped bytes, extracted, not installed) against private COPIES of Sergei's current real catalog (SHA256 `a201bbbd8efe282fb66670c551d55964288d478bdea43af36b218ed048ecc4fe`, equal to the real file at copy time and equal to the v0.16.3 run's; `-wal` absent; the 0-byte `-journal` beside the real catalog is old and was not touched). Audiobooks root = the real `Z:\Audiobooks`; Podcasts and Ebooks private and empty. Sergei's app was not running at any point (no Books Arranger process or listener before, between or after my runs). Five launches on my private port 5212, each a cold start:

| Run | Catalog copy | What I did | How it ended |
|---|---|---|---|
| 1 | A, fresh | first launch, Quit at about +93 s (coarse timing; superseded by run 1b) | Quit honoured, exit code 0 |
| 1b | A2, fresh | first launch, Quit at +54.8 s (hash running) | Quit honoured, click to exit 4.91 s, exit code 0 |
| 2 | B, fresh | first launch, full one-time hash, 18 min; window shown 10 min, hidden to tray 8 min, shown again; Quit at +1112 s | Quit honoured, click to exit 4.66 s, exit code 0 |
| 3 | B again | second launch, Quit at +58.6 s | Quit honoured, click to exit 0.90 s, exit code 0 |
| 4 | A2 again | relaunch of the interrupted copy, Quit at +28.8 s (hash resumed and running) | Quit honoured, click to exit 3.41 s, exit code 0 |

The GO covers the shipped payload on this catalog, idle and Paused. It does not cover the NSIS install flow, Start or anything that starts work (see "Not covered").

## Result per criterion (your six checks)

| # | Check | Result |
|---|---|---|
| 1 | Two cold starts, health, version 0.16.4, Paused | PASS on five cold starts. Engine health answered after 5.3, 4.4, 4.3, 4.2, 4.1 s. First moment the window showed the correct state (Engine v0.16.4, "Automatic processing: Paused", no checkpoint panel, Start enabled): 13.6, 12.6, 12.6, 11.5, 12.1 s. `/api/health` and the window both say 0.16.4. Queue "Paused", automatic "Paused", same saved run id `96cbe916-3b2b-4858-b386-89d493cb4f24` and 324 queued on every launch |
| 2 | First launch, one-time hash, 10+ min: success rate, p95, Start, checkpoint message, threads, memory, Ready count | PASS with one caveat (Finding 1). Run 2, 18 min, 91 sampler polls: **87 of 91 answered (95.6 %)**, 4 returned 503 "Status is still updating; retrying" each after the 4.0 s ceiling (15:39:01, 15:39:15, 15:40:43, 15:44:32); longest run of consecutive failures 2 polls, never a streak. Answered polls: p50 1.50 s, p95 3.87 s, max 4.21 s. The window's own `/api/state` requests (page resource timings, 64 requests): p50 2.08 s, max 3.34 s, none reached the 4.0 s ceiling, so the page never saw a 503. Window: 50 reads over five launches, **0** with the checkpoint panel or text, 0 with Start disabled, 0 with Quit disabled, 0 "unavailable", 0 not-Paused. API `can_start` true on 87 of 87 answered polls. Engine threads 7 first, 4 last, max 12 (growth at most 5). Engine private memory 172 MB first, 321 MB at +60 s, 251 MB last, peak 359 MB: growth from the 1-minute mark to the end **-70 MB**. SQLite temp files at most 1. Ready count: the first window read of a first launch (+17 s) shows 0, then 4 at +47 s, then it climbs (5, 8, 10, 13, 16, 21, 29, 36, 42) to **42** of 479 approved at about +14 min, when the hash ends, and stays there (59 completed rows); it is never 0 after the first half minute. Desktop `booksDesktop.status()`: n 50, p50 1.75 s, p95 3.76 s, max 4.02 s, never "unavailable". System CPU average 13.5 %, peak 20.7 % |
| 3 | Quit at about 60 s mid-check: within seconds, clean exit, port freed; repeat on the second launch | PASS. Run 1b (first launch, hash running, Quit at +54.8 s): exit 4.91 s after the click, exit code 0, owner's Job empty, port 5212 free, 0 `etilqs` files. Run 4 (Quit at +28.8 s, hash running): 3.41 s. Run 2 (Quit after the hash, +1112 s): 4.66 s. Second launch, run 3 (+58.6 s): 0.90 s, exit code 0. The NAS reads stopped with the process (run 1b: last read at 15:30:45.98, process gone 15:30:47.28, click at 15:30:42.4). The Quit button was enabled and was clicked on the first attempt in every run. Slower than Ender's 0.5 s; see Observation A |
| 4 | Second launch: no full re-hash, status normal | PASS. Run 3 (copy B after its completed first launch): **0 MiB read from the share for the whole launch** (SMB read counter 0 in all 31 samples), Ready count 42 at the first window read, health 4.2 s, 6 of 6 sampler polls answered (p50 2.74 s, max 3.46 s), Start enabled. A first launch that was cut off by Quit keeps what it had verified: run 4 showed 4 converted at its first read and the hash resumed at 28.6 MiB/s |
| 5 | Close button hides to tray | PASS (run 2). A real `SC_CLOSE` to the app window at 15:41:22 (about 10 min after launch) hid it; one tray icon present; the engine kept answering for 8 minutes while hidden (all hidden reads normal except the label, Finding 3); a tray left-click message showed the window again in 0.2 s and the window read good (Engine v0.16.4, Paused, Start enabled, no panel) 3.5 s later, inside the recipe's 5 s |
| 6 | C5: Z: and real data folder unchanged, 0 bytes written | PASS. See "C5 in numbers" |

No control from the recipe's §5 "do not click" list was clicked in any run. The only click in each run was **Quit Books Arranger**. Start was seen enabled in every read and never pressed.

## The one-time hash, measured

Measured from the machine-wide SMB client counters (`\SMB Client Shares(_Total)\Read Bytes/sec`, 2 s interval, one logger for the whole pass, 809 samples).

| Measure | v0.16.4 (run 2) | v0.16.3 (my report, run 3) |
|---|---|---|
| Active window (reads at or above 1 MiB/s) | 15:31:08 to 15:45:08, **14 min 0 s** | 7 min 7 s |
| Read rate while active | **mean 30.6 MiB/s, p95 32.4, peak 34.2** | mean 102, peak 113 |
| Total read | **25.0 GiB** (books on file: 26.3 GiB) | 42.3 GiB |
| Bytes written | **0** | 0 |

The cap holds (at or just above 32 MiB/s only in single 2 s samples), the minute-by-minute profile is flat at 30 to 31 MiB/s from +1 min until the end, and nothing is read after the check ends. The per-launch total (25.0 GiB) is slightly under the recorded size of finished books (26.3 GiB); one finished book is missing on `Z:` (Finding 4), which may explain part of it. I did not trace the rest.

## C5 in numbers

- **Real data folder** (`WIP/Books Arranger/data`): before and after, 3,190 files, catalog SHA256 `a201bbbd...cc4fe` identical, size and mtime of every file compared, **0 changed paths**. The real catalog was not opened by any process of mine; only copies were. The before and after fingerprints are byte-identical files (SHA256 `3a38e8d9...89383`).
- **`Z:\Audiobooks`**: size and mtime snapshot of every file under the root before and after, 9,453 files each time, **0 changed**. The 59 existing finished books (the `final_path` of each completed job): identical size and mtime before and after. The one other row, a finished book missing on the share both before and after, is the one in Finding 4.
- **SMB client write counter**: 0 Write Bytes/sec in every one of 809 samples (about 27 minutes, covering all five launches), machine-wide, so it also rules out anyone else writing to the share in those windows. Maximum write rate 0 B/s.
- Limits: I have no process-level record of file opens (no Process Monitor, no admin trace). Reads are shown by the SMB read counter, not by a per-process trace. A stat snapshot cannot show a write that restored the same size and mtime; with a zero write counter I do not regard that as credible.

## Findings

1. **Major (carried over, now with a visible tail). `/api/state` p95 is 3.87 s and some polls return 503 at the 4.0 s ceiling.** Sergei's app was stopped and the machine was quiet (CPU 13.5 % average). In run 2: 4 of 91 sampler polls returned 503 "Status is still updating; retrying" after 4.0 s (4.4 %), never more than 2 in a row, each followed by normal answers; answered polls p50 1.50 s, p95 3.87 s, max 4.21 s. The window's own polls never exceeded 3.34 s and the window never degraded, so the effect is visible to a script poller and not to Sergei in this run. This is the same failure class as v0.16.3 (54 % of polls failed, window degraded for 7 minutes), at about a twelfth of the rate and without the window consequences; the brief lists the p95 as known and accepted, and it does not meet the NO-GO wording (a streak). I judge it GO, but it is the first thing that would turn into a NO-GO if the catalog grows or the machine is busier: p95 sits just under the ceiling. Ender measured 0 of 76 503s; my sampler ran next to the window's own polling and my status calls through the window, which his harness may not have had, and that may account for the difference, but I have not isolated it. I did not run a v0.16.3 control, so the 54 % versus 4.4 % comparison is across two separate runs. Status: open (accepted for this release per brief, follow-up owned by Ender).
2. **Minor. The first `/api/state` poll after a cold start returns 503 in 3 of 5 launches.** My harness's first call, about 16 to 18 s after launch (runs 1, 1b, 4: 503 "Status is still updating; retrying"; runs 2 and 3 answered after 4.14 s and 3.30 s). It is the first cold computation exceeding the same 4.0 s ceiling. The window recovered by itself every time (first good read 11.5 to 13.6 s). Status: open. Owner: Ender, together with Finding 1.
3. **Minor, cosmetic, carried over (pattern alert 1). Stale version label while hidden to the tray.** Run 2: the label reads "v0.16.4 · local prototype" instead of "Engine v0.16.4" on 14 of 17 reads while the window was hidden (from about 90 s after hiding until shown again), and 0 of 33 reads while shown or just shown again; showing the window again restored "Engine v0.16.4". In v0.16.3 it also appeared on shown reads (5 of 16), so it has narrowed. Fifth build in a row. Status: open. Owner: Ender (Judy if the copy needs a decision). Disposition: defer.
4. **Minor, informational. One finished book is still missing on `Z:`.** `Z:\Audiobooks\Rollins James\Sigma Force - 9 - The Eye of God - Rollins James.m4b` does not exist (a read-only stat before the runs; same as in my v0.16.3 report). The background check flags it and it drops out of "completed" in the copy (60 completed rows in the real catalog, 59 in the copy after the check). Not caused by this build or by me (0 changes under `Z:\Audiobooks`). Sergei may want to know.
5. **Minor, informational, carried over. "42 converted" versus 59 completed rows.** The Ready count settles at 42 of 479 approved on the first launch and is the same 42 at once on the second launch, and it was 42 in v0.16.3. It is stable and reproducible, but I still cannot tell whether 42 is the right figure when 59 jobs are completed (not every completed job necessarily belongs to a currently approved book). For Ender to confirm.
6. **Observation A (not a finding). Quit took 4.7 to 4.9 s in two runs, 0.9 s in the idle second launch, and Ender measured 0.5 s.** All are within the "seconds" asked for and all exit with code 0. In both slow runs the click came right after a status computation of 3 to 4 s (the harness reads state immediately before Quit), so I suspect Quit waits for the computation in flight; unconfirmed. My harness measures click-to-process-exit, which may be stricter than Ender's number.

Not rechecked this time: the saved SQLITE_BUSY failure from 2026-10-15 in Sergei's catalog (Finding 2 of my v0.16.1 report), still for Jane to mention to Sergei.

## Not covered (be honest about it)

- **Start and anything that starts work** (Start, scan, conversion, research, source cleanup, folder cleanup, recovery purge, update check). By design, none were clicked. Ender's "Start re-check 1.2 s" and my v0.16.3 Finding 5 (Start re-verifies every finished book, about 28 GB) are therefore not confirmed by me.
- **The tray menu's own Quit item.** It needs a real mouse. I used the in-window Quit with a real renderer mouse press, and a tray left-click message only to show the window again.
- **The NSIS installer** (install, shortcuts, uninstall). I ran the exact embedded payload extracted with 7za.
- **Sergei's real machine conditions.** The NAS was awake and answering (full walk of 9,453 files in 38 to 39 s). A sleeping NAS was not tested.
- **Hidden-to-tray polling beyond the 8 minutes of run 2**, and memory beyond about 18 minutes.
- **A v0.16.3 control on this run's conditions.** Comparisons to v0.16.3 are against my earlier report, not a same-day control.

## Method and isolation

- Private extraction of the installer payload (hash-verified); private catalog copies (A and A2 for the Quit runs, B for the full first launch and its relaunch), private `--data-dir`, private port 5212, private `--roots-json` (Audiobooks real, Podcasts and Ebooks private and empty), private shell profiles, private APPDATA, LOCALAPPDATA and TEMP. The installed app, the real profile and port 5210 were not touched. Nothing of mine listened on 5212 or my debug port 19222 before a run, and nothing is left after.
- Deviations from the recipe, none touching product code: (a) `--remote-debugging-port` on a private loopback port, so I could read the window text and send one real renderer mouse press on Quit; (b) a typeperf logger on the SMB client counters, 2 s interval, one process for the whole pass, stopped by its PID when I finished (it is mine, verified by start time); (c) the harness starts the app as its own child inside a private kill-on-close Job; (d) hide and show were sent to my own shell only, no global input, no focus change, windows visible during runs; (e) my sampler also logs HTTP status, the Ready count and `can_start` per poll, and my launcher timestamps the process exit to 50 ms.
- Run 1 was my first attempt at the Quit-at-60-s check; its Quit came at about +93 s because my harness first finishes a 60 s sampling window, and its timing is only coarse (click to exit between 2 and 7 s). I replaced it with run 1b (+54.8 s) on a fresh copy and kept run 1 as an extra data point.
- Other `python.exe` processes from the worktree runtime appeared during the pass (not mine; Senua's review was in progress); I touched none.
- **I did not clean up**, as briefed: Sergei removes the scratchpad by hand. Left on disk: my working folder `scratchpad/futaba5/` (3.3 GB: three catalog copies of 485 MB each, profiles, temp, evidence, my tools) and `scratchpad/shared/payload-0.16.4/` (556 MB, the verified payload). No Books Arranger process or listener of mine remains (5212, 5210 and 19222 free; typeperf stopped).

## Evidence

- `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/3c1cc2ef-43a9-4b2a-b1fa-8a242d8fded6/scratchpad/futaba5/evidence/`: per run timeline, samples, shell and Job records, shell stdout and stderr; `smb-all.csv` (the SMB counters for the whole pass); real data fingerprints before and after; `Z:` snapshots before and after (`z-before.json`, `z-after.json`); the extract log. My tools are in `scratchpad/futaba5/tools/` (`an2.py` is the analysis behind the numbers above, `quitt.py` the Quit timing).
- Process identity, run 2 (the full first launch): shell 9584, engine 52740 (owner of the 5212 listener), launched as my own direct child inside a kill-on-close Job.
