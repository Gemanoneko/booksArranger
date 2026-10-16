# Books Arranger v0.16.0 packaged smoke QA — 2026-10-16

Author: Futaba.

**Verdict:** GO

Pattern alerts: none

**Artifact covered:** `dist/builds/46781019-c587-4ba3-9e0c-4c6161be11b4/Books-Arranger-Setup-0.16.0.exe` in the release-candidate worktree, 172,929,911 bytes, SHA256 `b556f61062d2d48b70581ac4c76be04304f7c3c6a9b0797e185c7d276119c15e` (recomputed by me, matches the brief).

Release source commit: 8d6272593645226af711e2eb21a2c0d731d6d3d3
Release artifact manifest SHA256: 1a2f49cee6eaba6a3a0a7dd8d91c19a707dcaf7db01435cceb2694164d470a19

Binding checks I made myself: the worktree HEAD equals the source commit above and equals `source_head` in `dist/release-artifacts.json`; I recomputed the SHA256 of `dist/release-artifacts.json` and it equals the manifest line above; the manifest shows `payload.verified` true and product digest `3ea85ac7eb3727daf0f6e04fbcaba3d3a8b9ea8c6faf659802f10db47b0e9709`. The worktree had no changes when I started. At the end it shows one modified file, `Docs/BooksArranger_CodeReview_v0.16.0_2026-10-15.md`, which I did not touch; it is a Docs file and does not change the artifact.

Scope: lean packaged smoke, one clean pass, from the shipped bytes. Not a full real-use pass: no library, no conversion. The GO covers the shipped app payload, not the NSIS install and uninstall flow (see "Not covered").

## Result per check

| # | Check | Result |
|---|---|---|
| 1 | Installer SHA256 | PASS, matches |
| 2 | Launch, version, backend, bundled runtime | PASS. Renderer `engineVersion` 0.16.0, `/api/health` application "Books Arranger" version 0.16.0, not closing; engine and host run the bundled `resources/python/python.exe` from the payload |
| 3 | First run: New catalog in a private folder, start state | PASS with a wording note (finding 1). Chosen through the real setup screen with real mouse input. Catalog created only after Create. App opened with nothing running or scanning, automatic processing "Idle" (not literally "Paused") |
| 4 | Close button (SC_CLOSE) | PASS and matches the documented behaviour. It hides the window to the tray; the same engine, host and shell survive (same instance id, same PIDs), and a tray icon exists while the window is hidden |
| 5 | Quit from the UI | PASS. Engine, python host and shell all gone, shell exit code 0, port 5212 free again |
| 6 | Relaunch on the same profile | PASS. Same catalog opened, settings file untouched, nothing running. Catalog database and both sentinel files unchanged (identity and full SHA256) |
| 7 | Anything confusing or broken | No Blocker, no Major. Two Minor (findings 1 and 2) |

Also checked, not asked for: closing the first-run Setup screen (before any catalog) exits the process with code 0 and no engine was ever started.

## Evidence (final pass, 2026-10-16 17:21-17:22 UTC)

- Process chain on the first launch: engine PID 62756 (owns the private HTTP listener) -> python host PID 51816 -> Electron shell PID 79240, verified natively by image path, creation time and parent link.
- After SC_CLOSE: the main window was hidden, the same chain was still alive, health instance id unchanged. Tray icon present while hidden (one status icon found on the shell's window).
- After the in-window "Quit Books Arranger" button (real mouse click on `#shutdown`): shell exited 0 in about 2 s on an idle catalog; engine, host and shell PIDs all confirmed not running; binding 5212 succeeded.
- Relaunch: a new chain (engine 77100, host 45400, shell 17360), `desktop-settings.json` byte-identical, `Idle`, `converting false`, `scanning false`. Quit again, same result.
- Sentinels written between the two launches (one in `smoke-preservation`, one in `source-recovery`) and `inventory.sqlite3`: native file identity and SHA256 unchanged after the relaunch.
- Nothing was left running afterwards (no process under the private payload, no listener on 5212).

## Findings

1. **Minor, wording and expectation.** A brand-new catalog starts with "Automatic processing: Idle", not "Paused" (`automatic_processing.py` reports Idle when there is no saved run; Paused is set for a saved run after a restart, `automatic_processing.py` line 87). The safety property holds: nothing converts or scans until Start. But the check list and handoff say "starts Paused", which is not literally true for a fresh catalog. The Paused-after-restart path with saved work was NOT exercised here (my private catalog has no saved run). It matters when the real catalog is adopted at the apply step, so that step should confirm it. Status: open, wording only. Owner: Ender or Judy if the label should read Paused.
2. **Minor, cosmetic, intermittent.** The version label under the title is written by two scripts, `web/app.js` line 223 ("v0.16.0 · local prototype") and `web/desktop-ui.js` line 12 ("Engine v0.16.0"); the update area is also built by the second one. In 2 of 10 first reads right after load the stale "v0.16.0 · local prototype" text showed (once with the Download update and Restart to update buttons also visible); every re-read 4 s later showed "Engine v0.16.0" with only "Check for updates". A flash of stale "local prototype" text in a release build. Status: open, not release-blocking. Owner: Ender (Judy if the copy needs a decision).

## Not covered (be honest about it)

- The NSIS installer itself: install, shortcuts, uninstall registration, the per-user path, no-elevation and no-auto-run. I ran the exact embedded app payload extracted with 7za (219 files, hashes identical to the manifest's `win-unpacked` tree and all 48 manifest runtime files), because a private install could not be proven safe for the real machine's shortcuts and registry. The pipeline's post-release packaged-build smoke is where the real install gets exercised.
- Existing folder -> Browse -> pick a folder end to end. The Browse button does open the real native "Choose data folder" dialog (seen visible, owned by the app shell), but the prepared UI Automation helper could not find that dialog, so no folder was picked through it. Not a product defect that I can show; a harness limit. Selection through that dialog has not been checked by anyone.
- Tray menu clicks (Quit from the tray, Show), busy-book Quit confirmation and drain, conversion, scanning, automatic start, update check and install, device sync, a real library, Sergei's real catalog.
- Paused-after-restart with saved work (finding 1).

## Method and isolation

- Shipped app run from a private extraction of the installer payload. Nothing was installed. Private profile, private LOCALAPPDATA, APPDATA and TEMP, empty private library roots, new empty catalog, private port 5212, remote debugging on a private ephemeral port. The real install location, shortcuts, registry, profile, catalog and port 5210 were not touched. Single-instance lock is per profile (`app.setPath('userData')` runs before `requestSingleInstanceLock`), so it cannot collide with another copy.
- Harness: the prepared `packaged-ui-smoke.mjs`, `native-window.py`, `private-files.py`, `choose-folder.ps1` (hashes equal to the handoff pins), copied to a private directory and bound to this artifact. They carry no kill, delete or global input path, which I confirmed by reading them. They were not Senua-reviewed; that is a deviation from the harness README. I bound the plan and set its flags myself.
- Deviations from the prepared driver, all in my private copy only, no product code touched: (a) accept automatic state `Idle` as well as `Paused` and log the real status, because the driver's `Paused`-only check failed on the genuine fresh-catalog state (this was the first failed run, harness assumption, not a product failure); (b) retry the native picker, which never found the dialog (runs 2 and 3, harness limit); (c) replaced the picker phase with a Setup-screen close test; (d) added post-Quit liveness checks for engine, host and shell PIDs, a tray-icon probe while hidden, and visible-text captures. Five driver runs in total: runs 1 to 3 stopped at harness limits (a) and (b); runs 4 and 5 passed in full; run 5 is the final pass above.
- In the three stopped runs the app exited on its own when the controller died; nothing was left behind, and I killed no process.
- Windows were visible during the runs (setup screen and main window), as agreed. No audio.

## Environment note

Read-only observations at the start of QA: PID 86660 and a listener on port 5210 were not visible from my session. I did not touch either and take no position on why. Worth a glance by whoever coordinates the live catalog.

## Cleanup

My private extraction, profiles, catalogs, logs and driver copies under `scratchpad/futaba/` are removed after this report, since no run showed a product failure.
