# Books Arranger v0.16.6 lean packaged QA on a copy of the real catalog, private empty roots — 2026-10-17

Author: Futaba.

**Verdict:** GO

Pattern alerts: 1.
1. The stale "local prototype" version label is still open (seventh build in a row: v0.16.0 to v0.16.6), and this run found its cause. In the shown window the label flipped between two texts across three reads: "v0.16.6 · local prototype" about 12 s after launch, "Engine v0.16.6" about 4 s later, then "v0.16.6 · local prototype" again about 10 s after that. Two code paths write the same element: `web/app.js` line 224 (`v${state.version} · local prototype`, on every state render) and `web/desktop-ui.js` line 12 (`'Engine v'+value.engineVersion`, on every shell status render). Whichever ran last wins. The engine itself reports 0.16.6 (`/api/health`). Disposition: defer (Minor, wording only), for Jane to confirm. Owner: Ender, Judy if the copy needs a decision.

**Why GO, and what the GO does not cover.** Checks 1 and 3 passed. Check 2 passed on layout and overlap, but **I did not see the "Nothing running" idle line**: this catalog copy carries a saved, paused source-cleanup row, so the rows area was never empty (details below). I also never saw a running row, because I clicked nothing that starts work. That is the live check you said you will do afterwards.

**Artifact covered:** `dist/builds/7c105c0c-e0dc-4dbf-9530-3a9dccd90e9d/Books-Arranger-Setup-0.16.6.exe` in the electron-m1 worktree, SHA256 `073f15f4dc1f1613bd756370f2bea159b19177e0215185155f70baaabbe2f004` (recomputed by me, matches the brief).

Release source commit: c823724a2f6fa83cf3f8d874568019178462700b
Release artifact manifest SHA256: e45899b533b30a8b693a2d1116566de4ad3d1746fcd73a4384f272b69f3e6f1c

Binding checks I made myself: worktree HEAD equals the source commit above and equals `source_head` in `dist/release-artifacts.json`; I recomputed the SHA256 of `dist/release-artifacts.json` and it equals the manifest line above; the manifest says version 0.16.6, `payload.verified` true, build id `7c105c0c-e0dc-4dbf-9530-3a9dccd90e9d`. All 219 payload files extracted from the installer with 7za match the manifest (`mismatch []`). The worktree had no uncommitted changes when I looked (before this report).

## Result per check

| # | Check | Result |
|---|---|---|
| 1 | Version 0.16.6, Paused, responsive | PASS, with one observation. Launched 16:46:08.7 UTC. `/api/health` first answered 6.5 s later and says version 0.16.6; the window showed "Automatic processing: Paused" and "Paused after server restart — start to continue saved work"; the audiobook status line reads "Paused · 290 queued · 133 need attention". Responsive: `/api/health` 8 ms and 2 ms; `/api/state` 200 both times, but **220 ms on the first call and 4,482 ms on the second**, about 17 s after launch while the engine still reported `recovery_active: true`. Two samples only, so I cannot say whether that is a one-off (first computations after launch, possibly the NAS metadata reads the recipe warns about) or a repeat. It is under the recipe's 5.0 s max, but close. Watch it in the live check |
| 2 | Audiobook jobs panel: Pause/Resume above the rows area; idle text; nothing overlaps | PASS on layout, idle text NOT SEEN. Order top to bottom in the panel: heading y 825, status line 866, Pause/Resume toolbar 896 (40 px high), rows area 944 (136 px high, the spec's 2-row reservation), "approved total" help 1094, pause help 1122. The toolbar ends at 936, above the rows area at 944, in all three reads. Pause is disabled and Resume enabled (Paused). Overlap test on every visible part of the panel (status, toolbar, both buttons, rows area, help lines) at all three reads: 0 overlaps; no horizontal overflow (0 px); the panel clears the section above (ends y 781, panel starts 797) and below (panel ends 1186, next starts 1201). The toolbar kept the same offset from the panel top (99 px) in all reads, and the rows area stayed 136 px while the second row disappeared, so nothing above the help text moved; the panel's bottom edge moved 6 px (389 to 383 px high), inside the help text, which the spec allows to move. **Why the idle line was not seen:** the copy has a saved paused cleanup row, so the window shows "Removing originals: Самая страшная книга 2022, 22 of 22 files, Paused - Removing original files, 0:00 elapsed" with a muted, nearly full bar, and for the first ~10 s a second row "Checking finished books, 24 of 75 books". Per the spec's paused-with-rows rule that is correct, and `#jobs-idle` is hidden then. So "Nothing running" and the spec's "Paused. Resume continues pending books." were not exercised |
| 3 | Quit exits cleanly within seconds | PASS. One real renderer mouse press on "Quit Books Arranger" (sent through the private debug port, no global input) at 16:46:35.49 UTC; my shell process exited with code 0 at 16:46:38.43 UTC, **2.95 s after the click**. Process tree before the click: shell 71740, three Electron children, two engine python processes (64984 owns the 5212 listener) and one conhost. After the exit none of those PIDs exist, no listener on 5212 or my debug port 19224, 0 `etilqs` files in the private temp folder. Sergei's app (v0.16.5, listener 5210, PID 39108) is still listening and its four Books Arranger processes are still there; I sent it no request |

The only control I used in the window was Quit Books Arranger. I clicked no Start, Resume, Pause, Retry, scan or cleanup control.

## Findings

1. **Minor, carried over (pattern alert 1). Stale and flipping version label.** See above. Status: open. Disposition: defer.
2. **Informational. `/api/state` 4.5 s on one of two samples.** See check 1. Not enough samples to call it a defect; worth a look in the live check.
3. **Informational. "need attention" went 133 to 193 within about 15 s** while the "Checking finished books" row ran (24 of 75 books). Most likely an effect of the private empty library roots on a copy (finished books are not found under the configured root, so they read as needing attention); I did not investigate. It happened on the copy only. If the live run on the real root shows the count moving after launch, that is worth reporting.
4. **Informational, for Judy and Ender. Paused row shows "0:00 elapsed" and a nearly full bar** for a cleanup at 22 of 22 files that is paused. The spec says elapsed "freezes when paused"; after a restart there may simply be no start time to count from. Not investigated.
5. **Informational. Coverage gap on the idle text and running rows.** See above. Not a product finding.

## Not covered (be honest about it)

- The "Nothing running" and "Paused. Resume continues pending books." texts, and any running progress row (bars, step text, ETA, indeterminate segment, 3 s "Done" removal, the "+N more running" line). The live check covers these.
- Panel widths below 560 px (the spec's wrapping rule); I read the window at its default size, 1266 x 823 px.
- Everything from the full v0.16.4 pass (one-time hash, second-launch behaviour, hide-to-tray, C4 and C5 proof), the book list and details panel (private roots, so the list is empty), Start and anything that starts work, the NSIS installer, the tray menu's own Quit item. No real-data fingerprint and no SMB counters were taken. The copy engine still makes read-only metadata reads of the real `source-recovery` files and `is_dir` checks on `Z:` from catalog paths even with private roots; I did not measure them.

## Method and isolation

- Private extraction of the installer payload (hash-verified); private `--data-dir`, private port 5212, private `--roots-json` (all three roots private and empty), private shell profile, APPDATA, LOCALAPPDATA and TEMP; a private `--remote-debugging-port` 19224 to read the window. Launched as my own child by a small node harness (`tools/smoke.mjs`) that records the PID, the exit code and the exit time, and kills only its own tree if something fails (it did not need to).
- Catalog copy: **the v0.16.5 copy under `scratchpad/shared/` was not on disk** (the folder `ba-v0165-qa` does not exist; only `ba-v0165` with Ender's edit scripts), so I made a new one the same way as v0.16.5: one plain `cp` of the real `inventory.sqlite3` (493,064,192 bytes) plus the cover images, read-only on the source, with the real `-wal` at 0 bytes before and after the copy. The copy's SHA256 equals the real file's at copy time (`2cbe24a91e751bf637e5b1d9b75e3daa75e749e4e2166391ef5685ea90e679bb`) and `PRAGMA quick_check` on the copy is `ok` (opened read-only and immutable). I never opened the real catalog with any process of mine, copied no `-wal`, `-shm`, `-journal`, lock, instance or recovery file, and did not touch Sergei's running app.
- Window reads were script reads of the page through the debug port (text, element rectangles); one screenshot of the panel region. Three reads, at about 12 s, 16 s and 26 s after launch.
- **I did not clean up**, as briefed. Left on disk under `scratchpad/shared/ba-v0166-qa/`: the payload (about 580 MB), the catalog copy (493 MB), profile, temp, evidence and my tool. No Books Arranger process or listener of mine remains (5212 and 19224 free).

## Evidence

- `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/3c1cc2ef-43a9-4b2a-b1fa-8a242d8fded6/scratchpad/shared/ba-v0166-qa/evidence/`: `result.json` (all three window reads, timings, process tree before and after, listeners), `panel.png` (screenshot of the Audiobook jobs panel), `launch.json`, `extract.log`, shell stdout and stderr. Tool: `.../ba-v0166-qa/tools/smoke.mjs`.
- Process identity: shell 71740 (my child), engine 64984 (owner of the 5212 listener).
