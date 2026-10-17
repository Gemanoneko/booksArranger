# Books Arranger v0.16.5 lean packaged QA on a copy of the real catalog, private empty roots — 2026-10-17

Author: Futaba.

**Verdict:** GO

Pattern alerts: 1.
1. The stale "local prototype" version label is still open (sixth build in a row: v0.16.0 to v0.16.5). My one window read of this run, taken within the first minute after launch with the window shown, reads "v0.16.5 · local prototype" instead of "Engine v0.16.5". I took too few reads to say whether it only happens while hidden to the tray, as in v0.16.4. The engine itself reports 0.16.5 (`/api/health`). Disposition: defer (Minor, wording only), for Jane to confirm.

**Why GO, and the one gap.** Checks 1 and 2 passed cleanly. **Check 3 was NOT performed, and the GO does not cover it.** With the three private empty library roots the brief required, the window's book list is empty ("Files cataloged 0", 0 rows in every filter), because the catalog's books are recorded under `Z:\Audiobooks`. The needs-attention book (job 644da7fc, candidate 421d037d) therefore never appears, so I could not open its details panel or see its Retry button. This is a consequence of the safety rule, not a defect in the build. Seeing that row needs the Audiobooks root set to the real `Z:\Audiobooks`, as in my v0.16.4 run, which the brief forbade, so I did not do it. If Jane wants check 3, that is the decision to take.

**Artifact covered:** `dist/builds/6b286397-be7e-4d5c-a420-41104061deac/Books-Arranger-Setup-0.16.5.exe` in the electron-m1 worktree, SHA256 `5bbf9bb91d9e94c6c8cc0b225ac6279e9e4198961e8b4017723e4d8dc820df5b` (recomputed by me, matches the brief).

Release source commit: 9e1664ff50522a1afc92790f69f2efcba3240675
Release artifact manifest SHA256: 1c08d7c10f02af7064a1c6b3b89ddc64d0f8e547c2070e2b2c89eda71f2376a3

Binding checks I made myself: worktree HEAD equals the source commit above and equals `source_head` in `dist/release-artifacts.json`; I recomputed the SHA256 of `dist/release-artifacts.json` and it equals the manifest line above; the manifest says version 0.16.5, `payload.verified` true, build id `6b286397-be7e-4d5c-a420-41104061deac`. All 219 payload files extracted from the installer with 7za match the manifest (`mismatch []`). The worktree had no uncommitted changes when I looked (before this report).

## Result per check

| # | Check | Result |
|---|---|---|
| 1 | Cleanup rows 2f5ad6d7 and b50234b5 read "paused" with one hold each; version 0.16.5; Paused and responsive | PASS. Before launch (read-only, on the copy): both rows `needs_attention`, reason "database is locked"; no holds table existed (states: 56 completed, 16 needs_attention). About 2 s after launch (15:14:41 UTC), read-only from outside: both rows `paused`, reason empty, updated 15:14:41.435 and 15:14:41.436; `source_cleanup_holds` exists with exactly 2 rows, one per cleanup id, each `prior_state needs_attention`, `prior_reason database is locked`, `cause legacy catalog busy`. States after: 56 completed, 14 needs_attention, 2 paused (the other 14 untouched). `/api/health` says 0.16.5. The window showed "Automatic processing: Paused", "Paused after server restart — start to continue saved work", audiobook jobs "Paused · 297 queued · 128 need attention", Quit enabled. Responsive: `/api/health` answered in 3 ms, `/api/state` answered 200, window reads returned at once |
| 2 | Quit works and the process exits cleanly within seconds | PASS. Click on Quit Books Arranger at 15:16:35.47 UTC (about 116 s after launch); my shell process exited with code 0 at 15:16:39.82 UTC, **4.35 s after the click**. Process tree before the click: shell, three Electron child processes, two engine python processes and one conhost; after the exit: none. No listener left on 5212 (only TIME_WAIT sockets), 0 `etilqs` temp files in the private temp folder. Sergei's app (v0.16.4 on 5210) kept answering `/api/health` afterwards |
| 3 | Retry button visible and overlapping nothing on book 644da7fc | NOT PERFORMED (see above). Not clicked, not seen |

The only control I used in the window was Quit Books Arranger. I changed the list filter (read-only) to look for the book; I clicked no Start, Resume, Retry, scan or cleanup control.

## What I know about the book, from the catalog copy only

Job 644da7fc-f2a1-4bcf-a44d-61c8cc11f9a9, candidate 421d037d-a51f-4574-b88e-817e21735ceb, state "needs attention", stage "queued", reason "Working cleanup requires attention: Legacy attempt still contains working inputs; exact retirement review required before another snapshot", last updated 2026-10-16 23:58 UTC. That is the database row, not what the window would show; it says nothing about the Retry button.

## Findings

1. **Minor, carried over (pattern alert 1). Stale version label.** See above. Status: open. Owner: Ender (Judy if the copy needs a decision). Disposition: defer.
2. **Informational. Coverage gap on check 3.** See above. Not a product finding.

## Not covered (be honest about it)

- **Check 3** (Retry button on the needs-attention book), for the reason above.
- Everything from the full v0.16.4 pass: the one-time hash and `/api/state` latency, second-launch behaviour, hide-to-tray, C4 and C5 proof. Not asked for in this lean pass; private roots also mean the book check on `Z:` never ran. I took no real-data fingerprint and no SMB counters. The recipe says a copy engine still makes read-only metadata reads of the real `source-recovery` files and `is_dir` checks on `Z:` from catalog paths even with private roots; I did not measure those.
- Start and anything that starts work; the NSIS installer; a real mouse press on Quit (I used a script click on the button inside the window, and at click time the button's top edge was above the visible window area, y about -244 px, which I did not investigate); the tray menu's own Quit item.

## Method and isolation

- Private extraction of the installer payload, hash-verified; private `--data-dir`, private port 5212, private `--roots-json` (all three roots private and empty), private shell profile, APPDATA, LOCALAPPDATA and TEMP; a private `--remote-debugging-port` on 19223 to read the window. Launched as my own child by a small node launcher that records the PID, exit code and exit time.
- Catalog copy: the real app (v0.16.4, converting) was running, so the recipe's C1 could not hold. I made one plain `cp` of the real `inventory.sqlite3` (488,235,008 bytes, mtime 18:12 unchanged across the copy, `-wal` 0 bytes before and after) plus the cover images, read-only on the source. The copy's SHA256 equals the real file's at copy time (`cc81e42e...84f977b57`) and `PRAGMA quick_check` on the copy is `ok`. I never opened the real catalog with any process of mine, copied no `-wal`, `-shm`, `-journal`, lock, instance or recovery file, and touched nothing of Sergei's running app (PIDs 66040, 6064, 74420, 76820 and its engine on 5210 left alone).
- Database reads of the copy were read-only (`immutable` before launch, `mode=ro` while running).
- **I did not clean up**, as briefed. Left on disk under `scratchpad/shared/ba-v0165-qa/`: the payload (about 580 MB), the catalog copy (488 MB), profile, temp, evidence and my tools. No Books Arranger process or listener of mine remains (5212 and 19223 free).

## Evidence

- `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/3c1cc2ef-43a9-4b2a-b1fa-8a242d8fded6/scratchpad/shared/ba-v0165-qa/evidence/`: `launch.json`, `exit.json` (code 0, exit time), `quit-click.json`, `tree-before-quit.txt`, `extract.log`, shell stdout and stderr. Tools in `.../ba-v0165-qa/tools/` (`launcher.mjs`, `ev.mjs`, `q4.py` is the hold and state query, `find.js` the filter search).
- Process identity: shell 20296 (my child), engine 46344 (owner of the 5212 listener).
