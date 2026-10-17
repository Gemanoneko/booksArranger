# Books Arranger v0.16.2 packaged QA on a copy of the real catalog — 2026-10-17

Author: Futaba.

**Verdict:** GO

Pattern alerts: 1 — the stale "local prototype" version label is still open (third build in a row: v0.16.0, v0.16.1, v0.16.2; Finding 4). Disposition: defer (Minor, wording-only flash), for Jane to confirm.

**GO carries one explicit exception, for Jane to accept or overrule.** The recipe's `/api/state` latency gate (p95 under 2.0 s) is NOT met in absolute terms on this machine today: p95 3.44 s in the 10-minute run (max 4.10 s, which does meet the max gate). I ran the shipped v0.16.1 payload on the same catalog copy, in the same hour, under the same load: p95 3.19 s. The status path that v0.16.2 touches is therefore no slower than the build Sergei is running now, and every pile-up signature (threads, memory, temp files, errors) stays flat. I judge the miss to be environmental (see Finding 1). It is a judgement; a strict reading of the recipe gate gives NO-GO. A re-run after Sergei's conversion finishes would settle it.

**Artifact covered:** `dist/builds/ace099b6-d69d-42be-8da3-47ffa8a29751/Books-Arranger-Setup-0.16.2.exe` in the release-candidate worktree, 172,937,209 bytes, SHA256 `a485118afcbc4cacdf76504d90910922b85388fc0cc63605866b2a90be5a8356` (recomputed by me, matches the brief).

Release source commit: d8349715dd03afe2cc12ea9db59cffd4c4c38fd0
Release artifact manifest SHA256: 03c2c9dce5e834df2ec18890a9411e34e84eaeb87e1dd1e0f62e93f811d347cb

Binding checks I made myself: the worktree HEAD equals the source commit above and equals `source_head` in `dist/release-artifacts.json`; the worktree was clean when I started; I recomputed the SHA256 of `dist/release-artifacts.json` and it equals the manifest line above; the manifest shows `payload.verified` true and `installer_equivalent` true, shell and backend version 0.16.2, product digest `02b319443f2e8f57756eafe67c46e1615b351311723ac7a836c1778fa3bff0fa`. All 219 extracted payload files match the manifest hashes (zero mismatches). The only change I made in the worktree is this report file (untracked, a Docs file, not part of the artifact).

Scope: packaged app (shipped bytes, extracted with 7za, not installed) against a private COPY of Sergei's real catalog, following `Docs/BooksArranger_RealCatalogCopy_QA_Recipe.md`, with the deviations listed under "Method and isolation". The decisive difference from the v0.16.1 run: **Sergei's real v0.16.1 was running and converting on port 5210 the whole time**, so the machine was loaded, the real data folder kept changing, and the copy is of a live catalog. Four runs, all on my private port 5212: run 1 (v0.16.2, 10 minutes, 5 shown and 5 hidden to the tray, Quit), run 2 (v0.16.2 relaunch on the same copy, 3 minutes, Quit), a control run (v0.16.1 payload, same copy, 4 minutes, Quit) and run 3 (v0.16.2 again, 4 minutes, Quit). The GO covers the shipped app payload on this catalog, idle and Paused. It does not cover the NSIS install flow or anything that starts work (see "Not covered"). It does not exercise the fix itself, which only matters while a book is converting.

## Result per criterion

| # | Criterion | Result |
|---|---|---|
| 1 | Version 0.16.2, bundled runtime, copy adopted, Paused | PASS. `/api/health` and the window label say 0.16.2 ("Engine v0.16.2"). Process chain (native, run 1): engine 74512 owns the 5212 listener, its parent python host 72992, its parent my shell 74260; engine and host images are both the payload's `resources\python\python.exe` (same check passed in all four runs). Copy adopted: window shows the copy's 328 queued and 166 need attention (the 0.16.1 report had 194 and 134; Sergei's real queue has moved on). Automatic processing "Paused" ("Paused after server restart — start to continue saved work"), same saved run id `96cbe916-...` in all four runs; scan "not scanned"; nothing started by itself in about 24 minutes of total app lifetime across the four runs |
| 2 | 10 min of polling, shown and hidden | PASS on threads, memory, temp files, errors. **Latency p95 gate not met (Finding 1; control run shows the same on v0.16.1).** Numbers below |
| 3 | "Waiting for the engine checkpoint…" never persists; Start enabled | PASS. 40 of 40 UI reads on v0.16.2 (22 in run 1 across shown, hidden and shown-again; 8 in run 2; 10 in run 3): desktop status panel never visible, the checkpoint text never in the page, "Start automatic processing" enabled and never clicked. First correct window: 14.9 s after launch in run 1 (first launch on a fresh copy), 7.5 s and 8.2 s on relaunch. Health answered in 4.2 to 4.3 s in every run |
| 4 | Close button (SC_CLOSE) | PASS, matches the documented behaviour. A real `WM_SYSCOMMAND`/`SC_CLOSE` to the app window at the 5-minute mark hid it; one tray icon present; same engine, host and shell alive; the engine kept answering for the remaining 5 minutes and 11 UI reads while hidden were all correct (page visibility "hidden"). A tray left-click message made the window visible in 0.2 s and the first UI read after was correct |
| 5 | Quit from the UI | PASS, all four runs. Real mouse press/release on **Quit Books Arranger**; shell exit code 0; every process in my owner's Job gone by the time the shell exit was seen; port 5212 free afterwards; `etilqs_*` files 0; private TEMP empty. Click to exit about 16 s (run 1), 10 s (run 2), 13 s (control, v0.16.1), 11 s (run 3). Gate is 30 s. Slower than the 6 to 7 s of the quiet 0.16.1 run, but the control is in the same range, so load again |
| 6 | Relaunch on the same copy | PASS. Run 2, 3 and the control all came back with the same state as run 1: Paused, 328 queued, 166 need attention, same automatic run id, `can_start` true. 17 samples over 3 minutes, 0 errors; engine threads 7 -> 4 (max 9); engine private memory 63 -> 120 MB; Quit exit code 0 |
| 7 | Real-data isolation | PASS with a stated limit: no PID-level proof (see "Real data folder: what I can and cannot prove"). Nothing changed that a copy engine would have a reason to touch |

No control from the recipe's §5 "do not click" list was clicked in any run. The only click in each run was the final **Quit Books Arranger**. Start was seen enabled and never pressed.

### What the status says for the queue while idle and Paused

Still **Paused**, never Running or Pausing. In `/api/state`, `audiobook_jobs.state` was `Paused` in all 88 samples of the three v0.16.2 runs (50 + 17 + 21), and `automatic_processing.state` was `Paused` in all of them. The window's queue line read, in all 40 UI reads on v0.16.2 (shown, hidden and shown-again): "0 converted out of 0 approved books · Paused · 328 queued · 166 need attention"; the automatic line read "Automatic processing: Paused". The v0.16.1 control reads identically, so this idle answer does not tell the two builds apart: the fix only changes the answer while a worker is active between two books, which an idle Paused app cannot show (see "Not covered").

## Criterion 2 in numbers

Run 1 (v0.16.2, 50 samples every 10 s, 10:12:54 to 10:22:48 local, 0 errors, no 503):

| Measure | Value | Recipe gate |
|---|---|---|
| Engine threads | first 7, last 6, range 3 to 9 (max minus first = 2) | last minus first at most 5, never above first plus 10: PASS |
| Engine private memory | 70 MB first, 118 MB at about 1 min, 148 MB last, peak 154 MB; growth since 1 min +30 MB | at most 150 MB: PASS |
| Whole owned tree (7 processes) private memory | 299 MB first, 366 MB last, peak 370 MB | not a gate |
| SQLite temp files `etilqs_*` | at most 2 in any sample; 0 after Quit | at most 4: PASS |
| `/api/state` latency, all 50 | p50 2.34 s, p95 3.44 s, max 4.10 s | p95 under 2.0 s: **FAIL**; max under 5.0 s: PASS; no errors: PASS |
| Shown (26 samples) / hidden (24) | p95 3.35 s / 3.49 s; max 3.44 s / 4.10 s | same |

The same numbers for the other runs, and for my v0.16.1 numbers from the quiet morning run, side by side:

| Run | Build | Samples | Threads first -> last (max) | Engine MB: first, 1 min, last (growth) | `etilqs` max | `/api/state` p50 / p95 / max |
|---|---|---|---|---|---|---|
| Quiet, no other load (my v0.16.1 report) | 0.16.1 | 55 | 7 -> 7 (9) | 62, 97, 114 (+17) | 2 | 1.05 / 1.66 / 1.69 s |
| Run 1 | 0.16.2 | 50 | 7 -> 6 (9) | 70, 118, 148 (+30) | 2 | 2.34 / 3.44 / 4.10 s |
| Run 2 (relaunch) | 0.16.2 | 17 | 7 -> 4 (9) | 63, 90, 120 (+30) | 2 | 0.73 / 3.01 / 3.01 s (after the first minute, 11 samples: 0.60 / 1.86 / 1.86 s) |
| Control, same copy, same hour | 0.16.1 | 20 | 8 -> 4 (10) | 65, 97, 143 (+46) | 1 | 2.55 / 3.19 / 3.19 s |
| Run 3 | 0.16.2 | 21 | 7 -> 4 (9) | 70, 141, 123 (-18) | 2 | 1.82 / 3.51 / 3.96 s |

Read: threads, memory and temp files are flat on every run and match the quiet v0.16.1 run. Latency is a different regime today for both builds: v0.16.1 and v0.16.2 sit in the same 2 to 4 s band on the same copy, and the two builds are not separable with this much noise. System-wide CPU averaged 26.5 % in the control and 21.4 % in run 3 (peaks 48.9 % and 32.7 %), with Sergei's conversion running; I added the CPU column after runs 1 and 2, so those two have none. Nothing accumulated in any run, and nothing ever errored.

The window's own polling (page resource timings, read-only), v0.16.2: `/api/state` p50 1.7 to 1.8 s, p95 2.5 s; `/api/inventory` p50 7.1 to 7.4 s, p95 8.1 to 8.6 s, max 9.6 s (run 1: 62 and 61 requests; run 2: 19 and 19; run 3: 25 and 24). The control (v0.16.1) shows the same: `/api/state` p50 1.75 s, `/api/inventory` p50 6.8 s, max 7.6 s. The desktop status call (`booksDesktop.status()`, one read per 30 s from my observer): run 1 median about 2.0 s, range 0.05 to 2.7 s (quiet v0.16.1 run: median 0.85 s, range 0.07 to 1.66 s).

## Findings

1. **Major (performance, not release-blocking; carried over and now worse under load).** The recipe latency gate is missed on this machine today by both builds (v0.16.2 p95 3.4 to 3.5 s, v0.16.1 p95 3.2 s; gate 2.0 s), and the window's `/api/inventory` poll takes about 7 s per request (3.6 s in the quiet run), repeating every few seconds. I cannot split the causes: Sergei's live conversion (CPU, disk and the shared `Z:` NAS), the larger catalog (328 pending and 166 need attention against 194 and 134 earlier), and the engine's own cost all moved at once. What I can say: the same code path was just as slow in v0.16.1 on the same copy, nothing accumulates, and every UI read was correct. This is Finding 1 of my v0.16.1 report, unchanged in kind. Status: open. Owner: Ender (what does `/api/inventory` do on a 485 MB catalog at idle, and does `/api/state` scale with the queue size). I did not look at the NAS state and did not touch `Z:` myself.
2. **Minor, informational.** Under load, Quit takes 10 to 16 s from the click to the shell's exit (6 to 7 s on a quiet machine). Within the 30 s gate; reported so a slow Quit on Sergei's machine during a conversion is not a surprise. Status: open, no owner needed unless it grows.
3. **Minor, informational (copy-only effect, matches the v0.16.1 report).** The private roots hide the catalog's `Z:` groups, so the copy engine reclassified the 55 completed audio jobs of the snapshot as "needs attention" (completed 55 -> 0, needs attention 96 -> 151; pending 328 unchanged), which is why the window says "0 converted out of 0 approved books". Expected with `--roots-json`; nothing of this reaches the real catalog.
4. **Minor, cosmetic, carried over (pattern alert).** The version label is still written by two scripts and shows "v0.16.2 · local prototype" instead of "Engine v0.16.2" part of the time. v0.16.2 runs: 14 of 28 shown reads (1 of 10, 5 of 8, 8 of 10), 8 of 11 reads while hidden, 0 of 1 right after showing again. The v0.16.1 control showed it 0 of 10 times this time (it was 0/10, 3/8 and 9/11 in my earlier run), so it flickers in both builds and is not a v0.16.2 regression. Status: open. Owner: Ender (Judy if the copy needs a decision).
5. **Minor, question, carried over.** `/api/health` said `recovery_active: true` 4.3 s after the first launch of run 1 (false in the three later launches). I did not follow it, so I cannot say whether it clears by itself. Owner: Ender to confirm it is a short startup state.

Not rechecked this time: the saved SQLITE_BUSY failure from 2026-10-15 in Sergei's catalog (Finding 2 of my v0.16.1 report), still for Jane to mention to Sergei.

Pattern alert, with disposition: the stale version label has now survived three builds. Disposition: defer (low priority, wording-only flash). Needs Jane's confirmation.

## Real data folder: what I can and cannot prove

The recipe's before/after fingerprint cannot be used as written, because Sergei's real instance (and another agent, deleting legacy working files) write to the real folder while I test. I used a different method and I am stating what it does and does not prove.

- **Method.** A passive change watcher (ReadDirectoryChangesW, read-only, no writes) on the real data folder from 10:11:22 to 10:38:23 local, covering all four runs and the copy step; every event is classified by path. Plus a size-and-mtime fingerprint of every file before (3,146 files) and after (3,193 files). The watcher saw 224,070 events and lost none (overflow 0).
- **What changed in the real folder.** Only three kinds of path: (a) the live catalog files (`inventory.sqlite3` and its `-wal` and `-shm`; the catalog hash moved from `e5d00d05...` to `b301c3ef...`, as expected for a live catalog); (b) `merge-cache/audio-staging` (851 events: Sergei's conversion and the other agent's deletions; tolerated as briefed); (c) outside those, only `merge-cache/covers/*.stdout` and `*.stderr` (ffmpeg cover logs: 44 files created, 22 `.stdout` and 22 `.stderr`, 8 removed, plus rewrites of the `.stdout` files) and six new `source-recovery/<id>/00000.m4b` backups (12 recovery-folder adds in all, 57 modifies, **0 removes**). Every other path in the folder is unchanged: no event on `web-instance*.json`, the lock file, `replacement-recovery`, `chapter-repairs`, or `desktop-settings`, and no delete inside `source-recovery`.
- **Why I attribute (c) to Sergei's own conversion and not to my copy engine.** The first cover-log event (10:12:21) is 13 seconds before I launched anything. The six new recovery folders arrive about every 4 minutes (10:12:54, 10:18:14, 10:22:38, 10:28:36, 10:30:56, 10:33:37), the cadence of finished books, each holding a book-sized `00000.m4b` with an old modified time (a moved original, as the live app's inline cleanup does). None of the six cleanup ids exists in my copy catalog after four engine runs. My private covers folder has 0 `.stdout`/`.stderr` files, and my private `source-recovery` stayed empty. My engine cannot convert or clean up without a click.
- **What I cannot prove.** I have no PID-level record of file opens (no Process Monitor, no Sysinternals handle tool, no admin for the USN journal). The watcher shows what changed and when, not who did it. At least three other `python.exe` processes from the worktree's runtime (not mine) were alive at various times, so even exclusion by process is not clean. The read-only metadata checks the recipe expects on the real `source-recovery` and on `Z:` leave no change event and cannot be seen this way. So this is strong circumstantial isolation, not proof; if Jane needs proof, it needs an elevated trace or running when Sergei's app is closed.
- **Catalog copy.** Copied while Sergei's app was running (recipe condition C1 not met, by the brief's design): `inventory.sqlite3` was not rewritten during the copy (size and mtime identical before and after, `-wal` at 0 bytes at both ends), and the copy's SHA256 equals the real file's right after (`e5d00d0580a7610fda273b301056f1243e0357caf38f910b793732934a4c5b06`). `PRAGMA quick_check` on the copy: ok. The copy therefore misses only anything committed after 10:11:58, which does not matter for an idle test. I copied the catalog and 522 cover images only (no `source-recovery`, `audio-staging`, `replacement-recovery`, `chapter-repairs`, lock or `web-instance` files).
- **Sergei's instance.** Not touched: his shell 39476, host 55944 and engine 75476 (listener on 5210) were the same processes, with the same PIDs, before my first step and after my last. I did not use port 5210 or the installed app.

## Evidence

- Process identity per run (native: image path, parent links, Job membership): run 1 shell 74260, host 72992, engine 74512; run 2 shell 59204, host 67804, engine 39704; control (v0.16.1) shell 69436, host 52364, engine 60288; run 3 shell 39668, host 67692, engine 66340. Launched by my owner script as its direct child inside a kill-on-close Job; I killed nothing of the product, every process left on its own after Quit.
- Compact evidence kept at `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/3c1cc2ef-43a9-4b2a-b1fa-8a242d8fded6/scratchpad/futaba3/evidence-kept/` (about 2.8 MB for the whole `futaba3` folder, originals included): samples, timelines and per-run analyses for run1, run2, ctl161 and run3; real-folder fingerprints before and after; the watcher's event log and counts (`watch/`); Sergei's process list before, after and at the end; the hashes. My scripts are in `.../futaba3/tools/` (including the watcher `watch_real.py`).

## Not covered (be honest about it)

- **The fix itself.** The false "Paused" between books only appears while a book is converting and its cleanup hands over to the next book. I did not start work (the brief forbids it), so this QA cannot show that the false pause is gone. That rests on the nine regression tests that came with commit 3360cf0 and on Sergei's live run. The idle Paused answer is verified as unchanged.
- The NSIS installer itself (install, shortcuts, uninstall, per-user path). I ran the exact embedded payload extracted with 7za.
- Anything that starts work: Start, scan, conversion, research, source cleanup, folder cleanup, recovery purge, update check. By design, none were clicked.
- A real mouse click on the tray icon and the tray menu (Show, Quit). I sent the tray icon's click message to the shell's own notification window, which exercises the app's own click handler, but no physical click was made. Busy-book Quit confirmation was not exercised (idle catalog).
- `Z:\Audiobooks`: not fingerprinted by me and not touched by me. Whether the NAS was asleep or busy.
- Real-folder isolation at the process level (see above).
- Hidden-to-tray polling beyond 5 minutes, and memory beyond 10 minutes. Run 1 is the only 10-minute run; runs 2, 3 and the control are 3 to 4 minutes.

## Method and isolation

- Private extraction of the installer payload (and, for the control, the v0.16.1 installer, SHA256 `24e67a05aba2322b1fa2db61eaf6ae34b102c9c522d5c92494836127890370cb`, recomputed, equal to my v0.16.1 report); private catalog copy, `--data-dir`, private port 5212, private empty `--roots-json`, private shell profile, private APPDATA, LOCALAPPDATA and TEMP. The real install, real profile and port 5210 were not touched. Before each run nothing of mine listened on 5212 or my debug port; after the last run nothing of mine is left.
- Deviations from the recipe, none touching product code: (a) Sergei's real instance was running, so the real-folder fingerprint was replaced by the watcher method above (C1 and C4 as written could not hold); (b) I added `--remote-debugging-port` on a private loopback port (19222) so I could read the window's text and send one real renderer mouse click; (c) the sampler has extra columns (host, shell and tree threads and memory, queue and automatic state, system CPU from run 3 on); (d) read-only observer calls: DOM reads, resource timings, `booksDesktop.status()` once per 30 s; (e) hide and show were sent as window messages to my own shell only, with no global input and no focus change (`--show-inactive` windows, no audio); (f) a control run of the v0.16.1 payload, added because the latency gate failed.
- Windows were visible during the runs, as agreed.
- One mistake of mine, before the first run: a command in my setup (`python3 -` with an empty script) started an interactive Python stub (PID 69604, child of my own shell) that hung. When the coordinator asked me to check for leftovers I verified its parent chain, ended only that process, and confirmed no other process of mine remained. It touched no product file and nothing of Sergei's.

## Cleanup

Done with the studio-disk-hygiene skill (manifest SHA256 `35356fd609cda9f82f82baf8ed51bc70ff4a9559b418b6b5c5c3e7ec35d36716`, 41 batches, `complete: true`, `remainingPaths` empty): my private extraction of both installers, the 485 MB catalog copy and covers, profile, APPDATA, LOCALAPPDATA, TEMP and logs under `scratchpad/futaba3/copyqa/` are gone (1,073 files and 61 folders; 2,316,417,430 absent logical bytes, which is the recorded size of the planned files, not measured free disk space). Kept: the compact evidence and scripts named above. No Books Arranger process or listener of mine remains on 5212 or 19222; Sergei's instance is untouched.
