# Books Arranger v0.16.1 packaged QA on a copy of the real catalog — 2026-10-17

Author: Futaba.

**Verdict:** GO

Pattern alerts: 1 — the stale "local prototype" version label is still open from v0.16.0 (Finding 3). Disposition: defer (Minor), for Jane to confirm.

**Artifact covered:** `dist/builds/7b6d2a35-8394-44d2-85b0-13dfdf589235/Books-Arranger-Setup-0.16.1.exe` in the release-candidate worktree, 172,936,681 bytes, SHA256 `24e67a05aba2322b1fa2db61eaf6ae34b102c9c522d5c92494836127890370cb` (recomputed by me, matches the brief).

Release source commit: 78b442135b70eb2d061a8f5d3571f706a1b256ae
Release artifact manifest SHA256: 21c07853ab5c33e4d388bac0cd53a156f0a990faa86c3c83527ca7aec00d759a

Binding checks I made myself: the worktree HEAD equals the source commit above and equals `source_head` in `dist/release-artifacts.json`; I recomputed the SHA256 of `dist/release-artifacts.json` and it equals the manifest line above; the manifest shows `payload.verified` true, `installer_equivalent` true and product digest `b9c6db7276787c2d5ff6c484975c991fc511cb6e4a869c88a664ae79f5f4de11`. All 219 extracted payload files match the manifest hashes (zero mismatches). The worktree was clean when I started. At the end it shows one untracked file, `Docs/BooksArranger_CodeReview_v0.16.1_2026-10-17.md`, which appeared during my session and which I did not write; it is a Docs file and does not change the artifact.

Scope: packaged app (shipped bytes, extracted with 7za, not installed) against a private COPY of Sergei's real catalog, following `Docs/BooksArranger_RealCatalogCopy_QA_Recipe.md`. Two runs: run 1 is the 10-minute polling run (5 min shown, 5 min hidden to the tray, Quit); run 2 is a relaunch on the same copy (3 min, Quit). The GO covers the shipped app payload on this catalog, idle and Paused. It does not cover the NSIS install flow or anything that starts work (see "Not covered").

## Result per criterion

| # | Criterion | Result |
|---|---|---|
| 1 | Version, bundled runtime, copy adopted, Paused, no auto-run | PASS. `/api/health` and the window label say 0.16.1. Process chain (run 2, native): engine 72944 (owns the 5212 listener) -> python host 11168 -> shell 2296; engine and host images are both the payload's `resources\python\python.exe`. Catalog copy SHA256 equals the real one at copy time (`af65d920...c8d6`). State: audiobook jobs Paused, 194 queued, 134 failed, 0 completed, 0 approved; automatic processing Paused ("Paused after server restart — start to continue saved work"); scan "not scanned"; nothing started by itself in about 14 minutes of total observation |
| 2 | 10 min of polling, shown and hidden | PASS on the recipe gates; one number misses the brief's "about 1 s" (Finding 1). Details below |
| 3 | "Waiting for the engine checkpoint…" never persists; buttons enabled while Paused | PASS. 30 of 30 UI reads (22 in run 1 across shown, hidden and shown-again; 8 in run 2): desktop status panel never visible, the checkpoint text never in the page, "Start automatic processing" enabled, "Start" (scan) and "Resume audiobook jobs" enabled, Stop/Pause disabled as expected for a Paused app. Run 2: health answered 1.4 s after launch and the window was already correct at 5.5 s |
| 4 | Close button (SC_CLOSE) | PASS, matches the documented behaviour. A real `WM_SYSCOMMAND`/`SC_CLOSE` to the app window hid it; one tray icon present; same engine 35636, host 43300 and shell alive; the engine kept answering for the remaining 5 minutes and 11 UI reads while hidden were all correct (page visibility "hidden") |
| 5 | Quit from the UI | PASS, both runs. Real mouse press/release on **Quit Books Arranger**; shell exit code 0; every process in the owner's Job was gone about 7 s after the click (run 1) and about 6 s after it (run 2); port 5212 free (bind succeeds, only TIME_WAIT remnants); `etilqs_*` files 0; private TEMP empty |
| 6 | Relaunch on the same copy | PASS. Same state as run 1 (194 queued / 134 failed / 0 completed / 0 approved; the same automatic run id; Paused). 17 samples over 3 minutes, 0 errors; engine threads 7 -> 4 (max 10); engine private memory 71 -> 103 MB; `etilqs_*` at most 1; Quit again exit code 0 |
| 7 | Real-data fingerprint | PASS. `data` folder: 6,698 files before and 6,698 after; every size and mtime identical; `inventory.sqlite3` SHA256 `af65d92093f5ad14b891dcbc828f67ee5e306574c89cf6796348672998e9c8d6` before and after; changed paths 0. This covers `data/source-recovery` too |

No control from the recipe's §5 "do not click" list was clicked. The only click in either run was the final **Quit Books Arranger**. Start was seen enabled and never pressed.

## Criterion 2 in numbers (run 1, 55 samples every 10 s, 02:11:28 to 02:21:22 UTC+9, 0 errors, no 503)

| Measure | Value | Recipe gate |
|---|---|---|
| Engine threads | first 7, last 7, range 3 to 9 (max minus first = 2) | last minus first at most 5, never above first plus 10: PASS |
| Engine private memory | 62 MB first, 97 MB at about 1 min, 114 MB last, peak 129 MB; growth since 1 min +17 MB | at most 150 MB: PASS |
| Whole owned tree (7 processes) private memory | 269 MB first, 324 MB last, peak 338 MB | not a gate; flat |
| SQLite temp files `etilqs_*` | at most 2 in any sample; 0 after Quit | at most 4: PASS |
| `/api/state` latency, all 55 | p50 1.05 s, p95 1.66 s, max 1.69 s | p95 under 2.0 s, max under 5.0 s: PASS |
| `/api/state` latency after the first minute (49) | p50 1.06 s, p95 1.66 s, max 1.69 s | same |
| Shown (28 samples) / hidden (27 samples) | p95 1.66 s / 1.64 s; max 1.69 s / 1.67 s | same |

The first minute was not slower than the rest (first sample 1.66 s, then 0.06 to 1.15 s), so a sleeping NAS did not visibly skew it. I did not look at the NAS state and did not touch `Z:` myself. Answers are bimodal: 0.06 to 0.4 s when a very recent computation can be reused, otherwise 1.0 to 1.7 s, which is the cost of one status computation on this catalog (the recipe expects 1 to 2 s on the real machine). Flat over 10 minutes, no growth, never a pile-up.

The window's own polling, read from the page's resource timings (read-only):

- Run 2, 3 minutes, shown: `/api/state` 36 requests, p50 0.98 s, p95 1.33 s, max 1.33 s; `/api/inventory` 35 requests, p50 3.63 s, p95 3.94 s, max 3.95 s.
- Run 1, 10 minutes, both paths together: 214 requests (107 and 107), p50 3.2 s, p95 3.8 s, max 4.0 s.
- The desktop status call the shell uses (`booksDesktop.status()`, one read per 30 s from my observer): run 1 median about 0.85 s, range 0.07 to 1.66 s; run 2 range 0.13 to 1.64 s.

Show again after hiding (run 1): a left-click message to the tray icon window made the app window visible in 0.2 s and the UI read was correct 0.4 s after that (gate 5 s).

## Findings

1. **Major (performance, not release-blocking).** Idle polling on the real catalog is slower than the brief's "about 1 s at p95". One `/api/state` computation costs 1.0 to 1.7 s (p95 1.66 s) and the window's `/api/inventory` poll takes about 3.6 s every time, repeating about every 5 to 6 s. The recipe gate (p95 under 2.0 s) is met, nothing accumulates, and every UI read was correct, so this is not a Blocker. It is why the window feels a few seconds behind. Ender to look at what `/api/inventory` does on a 470 MB catalog at idle. Not measured: engine CPU use at idle. Status: open. Owner: Ender.
2. **Minor, informational.** The real catalog carries a saved automatic-processing failure from 2026-10-15 (phase research, `OperationalError: Database error SQLITE_BUSY`, kept durably). The app shows Paused and Start is enabled. It looks like a leftover of the v0.16.0 pile-up, but I cannot prove that. This is data in Sergei's catalog, not a v0.16.1 defect. Status: open, for Jane to mention to Sergei. Owner: Jane.
3. **Minor, cosmetic, carried over (pattern alert).** The version label is still written by two scripts and shows "v0.16.1 · local prototype" instead of "Engine v0.16.1" part of the time: 0 of 10 shown reads in run 1, 3 of 8 shown reads in run 2, and 9 of 11 reads while the window was hidden. After showing the window again the label was correct at the first read. This is Finding 2 of the v0.16.0 report, unchanged. Status: open. Owner: Ender (Judy if the copy needs a decision).
4. **Minor, question.** `/api/health` said `recovery_active: true` 1.4 s after the run 2 relaunch; a read shortly after the run 1 launch said false. I did not follow it, so I cannot say whether it clears by itself. Nothing recovery-related changed on disk (Criterion 7). Owner: Ender to confirm it is a short startup state.

Resolved since v0.16.0: Finding 1 (Paused wording). With a saved run, the label reads "Automatic processing: Paused" at launch, both runs.

Pattern alert, with disposition: the stale version label has now survived two builds. Disposition: defer (low priority, wording-only flash). Needs Jane's confirmation.

## Evidence

- Run 1: shell 68276, python host 43300, engine 35636; run 2: shell 2296, host 11168, engine 72944. Identity checked natively (image path, creation time, parent links); engine and host were the payload's bundled Python.
- Quit timing: run 1 click at 02:21:34, Job members [68276, 64428] at 02:21:40, [] at 02:21:41, shell exit 0. Run 2 click at 02:27:10, Job empty by 02:27:16, shell exit 0.
- Before and after fingerprints of the real data folder, both runs' samples, UI reads and timelines are kept compactly in `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/3c1cc2ef-43a9-4b2a-b1fa-8a242d8fded6/scratchpad/futaba2/evidence-kept/` (2.2 MB), with my small harness scripts in `.../futaba2/tools/`.

## Not covered (be honest about it)

- The NSIS installer itself (install, shortcuts, uninstall, per-user path). I ran the exact embedded payload extracted with 7za.
- Anything that starts work: Start, scan, conversion, research, source cleanup, folder cleanup, recovery purge, update check. By design, none were clicked.
- A real mouse click on the tray icon and the tray menu (Show, Quit). I sent the tray icon's click message to the shell's own notification window, which exercises the app's own click handler, but no physical click was made. Busy-book Quit confirmation was not exercised (idle catalog).
- `Z:\Audiobooks`: the recipe does not fingerprint it and I did not. Nothing that writes there was clicked. The data-folder fingerprint is the proof for the data side.
- Whether the NAS was asleep.
- Hidden-to-tray polling beyond 5 minutes, and memory beyond 10 minutes.

## Method and isolation

- Private extraction of the installer payload; private catalog copy (`inventory.sqlite3` plus covers only, byte-identical at copy time), `--data-dir`, private port 5212, private empty `--roots-json`, private shell profile, private APPDATA, LOCALAPPDATA and TEMP. The real install, real profile and port 5210 were not touched. No Books Arranger process or listener existed before, between or after my runs (checked each time).
- Both runs were launched by my own owner script as its direct child inside a kill-on-close Job object, so ownership is proven by Job membership and parent links; I killed nothing, and every process left on its own after Quit.
- Deviations from the recipe, none touching product code: (a) I added `--remote-debugging-port` on a private loopback port so I could read the window's text and send one real renderer mouse click, instead of taking over the real mouse; (b) the before fingerprint was taken before the catalog copy, not after; (c) the sampler has extra columns (host, shell and tree threads and memory); (d) read-only observer calls: DOM reads, resource timings, `booksDesktop.status()` once per 30 s; (e) hide and show were sent as window messages to my own shell only, with no global input and no focus change (`--show-inactive` windows, no audio).
- Windows were visible during the runs, as agreed.

## Cleanup

Done with the studio-disk-hygiene skill (manifest SHA256 `d3e0c3f30c8ecac20d642423d93464977167fb5d8334faa9a96fc50c17aee79d`, 25 batches, `complete: true`, nothing remaining): my private extraction, catalog copy, covers, profile, APPDATA, LOCALAPPDATA, TEMP and logs under `scratchpad/futaba2/copyqa/` are gone (632 files, 51 folders, 1,488,432,308 logical bytes). Kept: the compact evidence and my scripts named above. A final fingerprint of the real data folder after the cleanup still matches (6,698 files, same catalog SHA256, 0 changes). No Books Arranger process or listener on 5210, 5212 or my debug ports remains.
