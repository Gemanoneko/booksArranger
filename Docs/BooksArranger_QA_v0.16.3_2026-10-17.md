# Books Arranger v0.16.3 packaged QA on a copy of the real catalog — 2026-10-17

Author: Futaba.

**Verdict:** NO-GO

Pattern alerts: 2.
1. The stale "local prototype" version label is still open (fourth build in a row: v0.16.0, v0.16.1, v0.16.2, v0.16.3; Finding 7). Disposition: defer (Minor, wording-only flash), for Jane to confirm.
2. The `/api/state` latency target (p95 under 2.0 s) has now been missed on three builds in a row, each time with a different excuse (v0.16.1 quiet 1.66 s, v0.16.2 loaded 3.44 s, v0.16.3 quiet 3.15 s; Finding 4). Disposition: fix, with a named owner (Ender, root cause), for Jane to confirm. Not "accept".

**Why NO-GO: one Blocker.** Quit does not quit while the new background check of finished books is running. I clicked **Quit Books Arranger** about 65 s after launch on the real library. The window said "Books Arranger is still running: The engine did not confirm a safe Quit. Try Quit again when it responds", went into the quit panel with every control disabled, and the app was still running 9 min 55 s later, when my own harness deadline ended it. The cold-start fix itself works: the engine answers health in 4 to 5 s on every run, against 286.6 s in v0.16.2. But for about 7 minutes after every launch on this library the window is degraded (Finding 2) and Quit is unreliable (Finding 1). A hotfix whose whole point is "it starts" should not ship with a close button that does not close. This is Finding 1, and the ProcessRules rule that the close button must always quit the process.

**Artifact covered:** `dist/builds/f5a13513-2440-4f9e-9424-f153803ab708/Books-Arranger-Setup-0.16.3.exe` in the release-candidate worktree, 172,939,487 bytes, SHA256 `12c17d1efc70a4de08104734499e02fa1a8884c8daf5d9ced3ca4952806096db` (recomputed by me, matches the brief).

Release source commit: 950857617e96a0ab2ef780c3cb7b15846a5b3d67
Release artifact manifest SHA256: 299f15d6b48a280c327372debb393523ca38b56d70a813878e2cc3ceb7e6ce89

Binding checks I made myself: the worktree HEAD equals the source commit above and equals `source_head` in `dist/release-artifacts.json`; the worktree was clean when I started (a Senua code-review file for v0.16.3 appeared later, untracked, not mine, not touched); I recomputed the SHA256 of `dist/release-artifacts.json` and it equals the manifest line above; the manifest says version 0.16.3, `payload.verified` true, product digest `9b791328643e8f0b11691144e84811b5cdec33f6e7043380d9073f7f181ec7a1`. All 219 extracted payload files match the manifest hashes (zero mismatches). The only change I made in the worktree is this report file.

Scope: packaged app (shipped bytes, extracted with 7za, not installed) against a private COPY of Sergei's current real catalog (SHA256 `a201bbbd8efe282fb66670c551d55964288d478bdea43af36b218ed048ecc4fe`, equal to the real file at copy time, `quick_check` ok, `-wal` absent). Sergei's app was not running at any point (no Books Arranger process or listener before, between or after my runs). Four launches on my private port 5212, each its own cold start:

| Run | Library roots | Data | What I did | How it ended |
|---|---|---|---|---|
| 1 | private empty roots (as briefed) | copy A | 2 min observation, Quit | Quit, exit code 0, about 13 s |
| 2 | real `Z:\Audiobooks` + private empty Podcasts and Ebooks | copy B | observation | ended by my own harness guard after 213 s (see "Method"), not by a product Quit |
| 3 | same as run 2 | copy B again (relaunch) | 7 min observation, hidden to tray at +156 s, shown at +459 s, Quit | Quit after the check ended, exit code 0, 14.8 s |
| 4 | same as run 2 | copy B again (relaunch) | Quit at +65 s, while the check was running | **Quit did not complete**; ended by my deadline at 600 s |

The GO/NO-GO covers the shipped payload on this catalog, idle and Paused. It does not cover the NSIS install flow, Start or anything that starts work (see "Not covered").

## Result per criterion (your six checks)

| # | Check | Result |
|---|---|---|
| 1 | Cold start to window ready, 2 cold starts, well under 180 s | PASS on the number, with the caveat in Finding 2. Four cold starts: engine health answered after **5.2 s** (run 1), **4.1 s** (run 2), **4.1 s** (run 3), **5.2 s** (run 4). First moment the window showed the correct state (version label, "Paused", no checkpoint panel, Start enabled): 11.8 s (private roots), 29.3 s, 29.4 s, 36.3 s (real root). All far under 180 s. "Ready" is not stable on the real library, see check 2 |
| 2 | Version 0.16.3, Paused, Start enabled, no "Waiting for the engine checkpoint…" persisting | **PARTIAL FAIL on the real library.** Version 0.16.3 (`/api/health` and "Engine v0.16.3"), Paused (queue "Paused", automatic "Paused", same saved run id `96cbe916-3b2b-4858-b386-89d493cb4f24` in all four runs) PASS. But with the real root, run 3's 16 window reads show the checkpoint panel and text in **9 of 16**, Start disabled in **10 of 16**, Quit disabled in 6 of 16, and the "Last confirmed" banner in 7 of 16, all while the check runs. It does not persist forever: it cleared after the check ended (read right after showing the window again, +459 s: panel gone, Start and Quit enabled). With private roots (run 1) it was clean from 11.8 s |
| 3 | During the background check: status latency, threads, memory; Quit mid-check | Latency and 503s: Finding 2. Threads 13 first, 5 last (min 4, max 13), no growth. Engine private memory 331 MB first, 323 MB last, peak 355 MB (private-roots run: 74 to 130 MB; the real library is bigger in memory). SQLite temp files at most 1. **Quit mid-check: FAIL (Finding 1)** |
| 4 | Close button hides to tray | PASS (run 3). A real `SC_CLOSE` to the app window at +156 s hid it; one tray icon present; the engine kept answering; a tray left-click message showed the window again in 0.2 s |
| 5 | Relaunch: state preserved, Paused | PASS. Runs 3 and 4 relaunched on the copy that run 2 had been cut off mid-check: same Paused state, same automatic run id, 324 queued, same window text. The catalog came back consistent: 59 completed, 324 pending, 97 needs attention |
| 6 | Real-data fingerprint unchanged | PASS. Real data folder before and after: catalog SHA256 `a201bbbd...cc4fe` identical, 3,190 files, **0 changed paths**. Extra, because the engine was pointed at the real `Z:\Audiobooks`: a size and mtime snapshot of every file under `Z:\Audiobooks` (9,453 files) before and after, **0 changed**; the machine-wide SMB client write counter read **0 bytes written** in every sample of runs 2, 3 and 4 |

No control from the recipe's §5 "do not click" list was clicked in any run. The only click in each run was **Quit Books Arranger** (runs 1, 3, 4). Start was seen enabled and never pressed.

## Did the background check read and hash `Z:`? How long?

Yes, but only when the engine's Audiobooks root equals the catalog's root (`Z:\Audiobooks`). With the briefed private empty roots it does not, and that is why v0.16.2's copy test missed the failure.

- **Private roots (run 1):** `_output_valid` in `merge_service.py` returns False at once when a finished book's recorded root differs from the configured Audiobooks root, so no file is opened. Observed: all 60 completed rows became "needs attention" with reason "Recorded output is missing, changed, or failed validation" within the first seconds (window showed "0 converted" from the first read, 15 s after launch). The engine's I/O never touched `Z:` in any way I could see; the check was done before I could sample it.
- **Real `Z:\Audiobooks` root (runs 2, 3, 4):** the machine's SMB client counters (`\SMB Client Shares(_Total)\Read Bytes/sec`, 2 s interval) show reads from +4 s after launch. Run 3 (the complete one): reads from +4 s to +427 s (7 min 7 s), mean 102 MiB/s while active, peak 113 MiB/s, which is the NAS's speed ceiling. Total read **42.3 GiB** (43,362 MiB), against 26.3 GiB (28.29 GB) of recorded finished books. The check found the catalog right on 59 books and flagged exactly 1 (Finding 6).
- **It reads about 1.6 times the data of the books.** That is more than one pass over 59 books. I cannot say from outside which code path reads the rest; the window's own `/api/inventory` and `/api/state` polls also call the same validation (merge_service.py around lines 861 and 992). For Ender.
- It is read-only: 0 bytes written to the share in every sample, and the share's file snapshot is unchanged.

## Criterion 3 in numbers

Run 1 (private roots, idle, no `Z:` work, 19 samples every 5 s, 0 errors):

| Measure | Value |
|---|---|
| Engine threads | first 7, last 4, range 4 to 10 |
| Engine private memory | 74 MB first, 125 MB last, peak 130 MB |
| `/api/state` latency | p50 1.57 s, p95 3.15 s, max 3.15 s (gate p95 under 2.0 s: **not met**) |
| SQLite temp files | at most 1; 0 after Quit |

Run 3 (real root, background check running, 50 samples, about 7.5 min):

| Measure | Value |
|---|---|
| `/api/state` answers | **27 of 50 polls failed with HTTP 503 "Status is still updating"**. The 23 that answered: p50 2.45 s, p95 4.02 s, max 7.29 s |
| The window's own polls (page resource timings, final read) | `/api/state`: 24 requests, p50 3.86 s, max 4.04 s (the 4 s ceiling is the engine giving up with a 503). `/api/inventory`: 13 requests, p50 22.1 s, max 53.5 s |
| Desktop status (`booksDesktop.status()`) | phase flips between "running" and "unavailable"; one read took 4.9 s. "unavailable" is what puts "Waiting for the engine checkpoint…" on screen |
| Threads, memory, temp files | flat, see check 3 |
| System CPU | average 19 %, peak 46 % |

Answer to "does the background `Z:` hashing affect it": **yes, badly.** Idle with private roots (no `Z:` work) the engine answers every poll with p50 1.6 s. With the check running, more than half the polls fail and the rest are slower. When the check ends (+427 s) the window recovers by itself.

Status counters during the check: the window's "N converted out of 479 approved books" climbs 4, 8, 11, 13, 14, 18, 26, 35, 39, 42 as the books are validated, and stays at 42 afterwards while 59 rows are completed. I cannot tell whether 42 is the correct final figure (not every completed job necessarily belongs to a currently approved book). For Ender to confirm.

## Findings

1. **Blocker. Quit mid-check does not quit (run 4; the ProcessRules close-button rule).** Repro: launch the packaged app against the real catalog with the real `Z:\Audiobooks` root; wait for the window (about 35 s); click **Quit Books Arranger** (it was enabled, clicked once with a real renderer mouse press). Result: the shell wrote "Books Arranger is still running: The engine did not confirm a safe Quit. Try Quit again when it responds." and "Request timed out"; the window showed the quit panel ("Waiting for the engine checkpoint…") with Start, every other control and Quit disabled; the engine kept hashing at about 100 MiB/s for the 3.9 minutes my SMB counter ran afterwards; the shell and engine were still alive at my 600 s deadline, 9 min 55 s after the click, when my launcher ended my own process tree. The check should have finished by then (run 3: 7 min 7 s), so this is not just "waiting for it to finish". I did not read the window between +4 min and the deadline, so I do not know whether Quit became available again once the hashing stopped. I did not test the tray menu's Quit (it needs a real mouse). **Quit after the check ended works (run 3: click to exit 14.8 s, exit code 0, every process of my owner's Job gone, port 5212 free, 0 temp files)**, so the window of failure is the first ~7 minutes after launch on this library. I stopped here, as briefed. This is one observation of a failure that its mechanism explains: while the check runs every engine request is slow (Finding 2), and the shell's Quit request times out. Status: open. Owner: Ender (Quit must work whatever the engine is doing; the check must stop for it, as the code comment on `close()` intends). Needs my regression check.
2. **Major. The window is degraded for the whole check (about 7 minutes per launch on this library).** Engine health in 4 to 5 s is real, but the page is not usable: 54 % of `/api/state` polls fail with 503, the desktop status keeps flipping to "unavailable" (checkpoint panel in 9 of 16 reads), Start and Quit are disabled about half the time, and the page's `/api/inventory` call takes 20 s or more. v0.16.2 never got this far (hard failure), so this is not a regression, but it is what "the window should be ready in seconds" does not deliver on Sergei's library. The likely cause is that the hashing saturates the NAS (about 100 MiB/s) while the same engine's status path needs `Z:` metadata and also validates books itself (42.3 GiB read against 26.3 GiB of books). That is a hypothesis from the numbers, not something I traced. Status: open. Owner: Ender.
3. **Major (process, not product). The briefed private-roots method cannot test this fix.** With private roots the check ends in milliseconds because of the root comparison, so a clean run proves nothing about the hashing path. I followed the brief for run 1 and then deviated for runs 2 to 4 (see "Method"). Status: open. Owner: Ender, to put "Audiobooks root equal to the catalog's, other roots private" into `BooksArranger_RealCatalogCopy_QA_Recipe.md`, with the NAS read-only note.
4. **Major, carried over. Latency target missed again, with no other load.** Sergei's app was stopped, the machine was quiet (CPU 10 % average in run 1), and idle polling still took p50 1.57 s, p95 3.15 s with private roots. One observation that may help Ender: the engine's logical read counter rose by 42.8 GiB in 121 s at idle in run 1 (about 350 MiB/s, roughly 2 GiB per 6-second sample; it counts cache hits too), which looks like each status or inventory computation reading most of the 485 MB catalog again. Status: open, same as Finding 1 of my v0.16.1 and v0.16.2 reports. Owner: Ender.
5. **Minor, by code reading, not exercised. Start repeats the full hash.** `AudioJobs.resume()` (Start) re-verifies every completed book synchronously under the queue lock before the worker begins; the v0.16.3 diff leaves that loop unchanged, so this is not new. On this library that is about 28 GB at 100 MiB/s, roughly 5 to 7 minutes of nothing happening after Start, on top of the 7 minutes of degraded window. I did not press Start (forbidden), so this is unconfirmed. Status: open. Owner: Ender to confirm; Jane to tell Sergei before he presses Start.
6. **Minor, informational. One finished book is missing on `Z:`.** The check correctly flagged exactly one of the 60 completed rows as "needs attention": `Z:\Audiobooks\Rollins James\Sigma Force - 9 - The Eye of God - Rollins James.m4b` does not exist today (my read-only stat before the run confirms it). Not caused by this build or by me (0 changes under `Z:\Audiobooks`). Sergei may want to know.
7. **Minor, cosmetic, carried over (pattern alert 1).** The version label is written by two scripts and shows "v0.16.3 · local prototype" instead of "Engine v0.16.3" part of the time: 5 of 16 reads in run 3, and not at all in run 1 of this pass. Fourth build in a row. Status: open. Owner: Ender (Judy if the copy needs a decision). Disposition: defer.

Not rechecked this time: the saved SQLITE_BUSY failure from 2026-10-15 in Sergei's catalog (Finding 2 of my v0.16.1 report), still for Jane to mention to Sergei.

## Real data folder: what I can and cannot prove

This time the recipe's before and after fingerprint works as written, because nothing live was running: no Books Arranger process of Sergei's, and nobody else writing to the data folder.

- Real data folder: 3,190 files before, 3,190 after, catalog SHA256 identical, 0 changed paths (size and mtime of every file).
- `Z:\Audiobooks`: 9,453 files, size and mtime before and after, 0 changed. The SMB client write counter was 0 in every one of the about 460 samples I took across runs 2, 3 and 4 (machine-wide, so it also rules out anyone else writing to the share in those windows).
- Limit: I have no process-level record of file opens (no Process Monitor, no admin trace). The read side is shown by the SMB read counter, not by a per-process trace. A stat snapshot cannot show a write that restored the same size and mtime; I regard that as not credible here, with the zero write counter.
- Other worktree-runtime `python.exe` processes (not mine, started by another agent's commands) appeared late in the pass; I touched none. They started after runs 2 and 3.

## Not covered (be honest about it)

- **Start and anything that starts work** (Start, scan, conversion, research, source cleanup, folder cleanup, recovery purge, update check). By design, none were clicked. So Finding 5 is unconfirmed.
- **Quit mid-check beyond 9 min 55 s, and whether it recovers once the hashing stops.** One observation only (run 4). The tray menu's Quit was not tried.
- **A v0.16.2 control on the real root.** Not run (it takes 286 s to start and the brief says v0.16.2 failed live). I therefore cannot say what v0.16.2 would have shown if it had started.
- **The NSIS installer** (install, shortcuts, uninstall). I ran the exact embedded payload extracted with 7za.
- **Sergei's real machine conditions** (NAS asleep or busy, other users). The NAS was awake and answering at about 100 MiB/s.
- **Hidden-to-tray polling beyond the 5 minutes of run 3.** Memory beyond 10 minutes.
- **A real mouse click on the tray icon and its menu.** I sent the tray icon's click message to the shell's own notification window.

## Method and isolation

- Private extraction of the installer payload; private catalog copies (A for run 1, B for runs 2 to 4), private `--data-dir`, private port 5212, private `--roots-json`, private shell profile (A, B), private APPDATA, LOCALAPPDATA and TEMP. The installed app, the real profile and port 5210 were not touched. Nothing of mine listened on 5212 or my debug port 19222 before a run, and nothing is left after.
- Deviations from the brief and recipe, none touching product code: (a) runs 2 to 4 use the real `Z:\Audiobooks` as the Audiobooks root (Podcasts and Ebooks stay private and empty), because the brief's premise that the check reads `Z:` is only true with the real root (Finding 3). This puts the real library path in the engine's configuration; nothing runs without a click, the saved automatic run stays Paused, recovery purge refuses while jobs are pending (324 are; per the recipe's analysis, which I did not re-derive), and the before and after snapshots above show nothing changed; (b) `--remote-debugging-port` on a private loopback port, so I could read the window's text and send one real renderer mouse press on Quit; (c) a typeperf logger on the SMB client counters, 2 s interval, to see the `Z:` traffic (the engine's own I/O counter cannot tell the share from local reads); (d) the harness starts the app as its own child inside a private kill-on-close Job; (e) hide and show were sent to my own shell only, no global input, no focus change, windows visible during runs.
- **Run 2 was cut short by my own guard, not by the product.** My harness stopped after three consecutive failed `/api/state` polls and found the Quit button disabled; it waited 45 s, then closed my Job, which ended my own processes. I loosened that guard for runs 3 and 4 (503s are the finding, not a crash) and added a Quit retry. Run 2 is therefore counted only for its startup numbers and its UI reads.
- Windows were visible during the runs, as agreed.
- I stopped after run 4 on the Blocker, as briefed, and did not repeat it.

## Evidence

- Compact evidence at `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/3c1cc2ef-43a9-4b2a-b1fa-8a242d8fded6/scratchpad/futaba4/evidence-kept/` (about 1.6 MB): per run timeline, samples, shell and Job records, shell stdout and stderr (the Quit refusal text is in `run4/shell-stdout.log`); SMB counter logs and summaries for runs 2, 3 and 4; real data fingerprints before and after; `Z:` snapshots before and after (gzip); roots files; hashes; my scripts in `tools/`.
- Process identity, run 4 (the Blocker): shell 672, engine 33156 (owner of the 5212 listener), launched as my own direct child inside a kill-on-close Job; the engine health reported `recovery_active: false`.

## Cleanup

Done with the studio-disk-hygiene skill, manifest SHA256 `1c3a93ed4c8c5917cc5ea551052a384811313682914e2706865972839ee94879` (58 batches, 1,472 files and 85 folders planned). `verify` result: `complete: true`, `remainingPaths` empty, 1,557 absent paths, 2,894,719,097 absent logical bytes (the recorded size of the planned files, not measured free disk space). Gone: my private extraction of the installer, both 485 MB catalog copies and their covers, both profiles, APPDATA, LOCALAPPDATA, TEMP and the run logs under `scratchpad/futaba4/copyqa/`. Kept (1.7 MB): the compact evidence in `scratchpad/futaba4/evidence-kept/` and my scripts in `scratchpad/futaba4/tools/`; the manifest sits outside the removed root at `scratchpad/futaba4-hygiene-copyqa-manifest.json`. No Books Arranger process or listener of mine remains (5212 and 19222 free, typeperf finished). Sergei's installed app was never running and was not touched.
