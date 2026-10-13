# Books Arranger — Electron packaging, milestone 1 (2026-10-13)

Owner: Ender. Status: built and tested locally, **uncommitted** in worktree `scratch/electron-2026-10-13/worktree` on branch `codex/books-electron-m1` (base `2072cf1`). Nothing was committed, pushed or published. Decisions: Brief § "Sergei decisions — search channels and release stack" and the new § "Desktop app (Electron) — milestone 1".

## What M1 delivers

- An NSIS installer (local build, `--publish never`) that contains the Electron shell, the official Windows embeddable Python, the pinned LGPL FFmpeg and the Python engine.
- The window shows the existing browser UI, served by the bundled engine.
- The close button hides the window to the tray. Conversions continue.
- Tray **Quit**: the book in progress finishes (including its source cleanup), no new book starts, scanning and research stop at their checkpoints, then the engine and the shell exit and every process ends.
- `package.json` is the single version source. The engine reads it; the packaged engine reads a `VERSION` file generated from it at build time. The tracked `VERSION` file is deleted.
- The data folder is outside the install folder and selectable. Dev runs use their own data folder, profile, fixture libraries and port.

Not in M1: publishing, `release.mjs`/keep-last-4, updater, Start-menu switch-over from the old Pythonw entries, data-folder migration, code signing.

## 1. Read-only check — catalog fields holding absolute paths into `data/`

Method: one SQLite backup-API copy of the live catalog (read-only source connection, `mode=ro`, single snapshot, 1.7 s, first attempt, `quick_check` ok), then a scan of every text column in all 34 tables for the live data path in plain, forward-slash and JSON-escaped forms, walking JSON values to name the exact keys. Small JSON/JSONL files under the live `data/` were read (not copied). Scripts: `scratch/electron-2026-10-13/harness/copy_catalog.py`, `path_fields.py`, `path_files.py`.

| Field | Rows with a data path | Points into |
| --- | --- | --- |
| `audio_jobs.manifest` → `$.cover.path` | 25 / 25 | `merge-cache/covers/<uuid>.png/.jpg` |
| `audio_jobs.manifest` → `$.cleanup_policy.recovery_root` | 21 / 25 | `source-recovery` |
| `source_cleanup.intent` → `$.manifest.cover.path`, `$.manifest.cleanup_policy.recovery_root`, `$.recovery_identity` (ancestor chain with native IDs) | 4 / 4 | covers, `source-recovery`, the data folder and its parents |
| `cleanup_members.backup` | 89 / 89 | `source-recovery/<uuid>/<file>.mp3` |
| `owned_artifacts.path` | 89 / 101 | `source-recovery/<uuid>/<file>.mp3` |
| `storage_cleanup_files.path` | 644 / 644 | `merge-cache/audio-staging/…` (555), `source-recovery/…` (88), `chapter-repairs/…` (1) |
| `storage_cleanup_authorizations.path` | 3 / 3 | `merge-cache/audio-staging/…` |
| `storage_cleanup_preserved.path` | 160 / 160 | `merge-cache/audio-staging/…` |
| `audiobook_replacement_retirements.recovery_json` → `$.path`, `$.ancestry` | 3 / 3 | `replacement-recovery/<uuid>/<hash>.m4b` plus native ancestor chain |
| `audiobook_replacements.approval_json` → `$.replacement_manifest.cover.path` | 1 / 1 | `merge-cache/covers/…` |
| Files: `chapter-repairs/*/corrected-artifact.jsonl` → `$.data.cover.path` | 2 files | covers |
| Files: `merge-cache/audio-staging/*/ownership.json` → `$.manifest.cover.path`, `…recovery_root` | 7 files | covers, `source-recovery` |

Not affected: `files`, `book_groups`, `candidate_context`, research tables, `audio_jobs.output`/`journal` (library paths only). The data subfolders themselves (`merge-cache`, `chapter-repairs`, `source-recovery`, `replacement-recovery`, `web-instance.json`) are derived from the `--database` location at runtime, so pointing the engine at another folder works for new work.

What this means for moving the data folder (M2):
- Old rows keep pointing at the old folder. Every consumer that deletes or restores checks the stored path against the *current* derived root and the stored native identity chain (`recovery_identity`, `ancestry`, `parent_identity`), so a moved folder **fails closed** (needs attention, copies preserved) rather than acting on the old location. Reads (`stat`, `exists`) of old paths still happen.
- `audio_jobs.manifest` is hashed (`manifest_hash`) and frozen; rewriting a path there means re-hashing. Native identity chains cannot be rewritten at all — a copied folder gets new file IDs.
- Live state in the copy: 18 pending + 1 running job, 4 completed source cleanups, 1 recovery set still retained, 1 completed replacement. The safe move window is: queue empty, the retained recovery set expired, no replacement or cleanup in progress. Then only historical receipts carry old paths. Alternative: keep using the current folder location with the packaged app (no move at all).

## 2. Installer

- Path: `WIP/Books Arranger/scratch/electron-2026-10-13/worktree/dist/Books Arranger Setup 0.14.0.exe`
- Size: 172,412,860 bytes (164.4 MiB). SHA-256 `66c4b99f76455125faf62ec7f76d687d082d0a9fa2ce931e20c3bf483e5cef2f`. Unsigned. This exact build passed every check in section 3 marked final.
- Installs per user, no elevation, Start-menu shortcut, no desktop shortcut, does not run after install, keeps app data on uninstall. Not executed during M1 (it would write a real HKCU uninstall entry and Start-menu shortcut); every launch test used the identical payload in `dist/win-unpacked`.
- Contents (7-Zip listing of `$PLUGINSDIR/app-64.7z`, 197 files, 552 MiB unpacked):

| Part | Files | Size | Notes |
| --- | --- | --- | --- |
| Electron 44.4.5 runtime (root + `locales`) | 71 | 367 MiB | `Books Arranger.exe`, fuses: run-as-node off, `NODE_OPTIONS` off, app only from asar |
| `resources/app.asar` | 1 | <0.1 MiB | `desktop/main.js`, icon, `package.json` |
| `resources/backend` | 76 | 2.1 MiB | 35 engine modules, `web/`, the two JSON data files (byte-identical to git), generated `VERSION`, precompiled bytecode; no `app.py` (Tk), no Tkinter |
| `resources/python` | 37 | 23 MiB | python.org `python-3.14.8-embed-amd64.zip`, SHA-256 `a93abe45…0a310` (matches python.org), PSF `LICENSE.txt` |
| `resources/ffmpeg` | 11 | 160 MiB | `ffmpeg.exe`, `ffprobe.exe` and their DLLs from BtbN `autobuild-2026-09-30-13-08` `ffmpeg-n8.1.3-9-g29e619e767-win64-lgpl-shared-8.1.zip`, SHA-256 `3e47bda1…6811a` (matches BtbN `checksums.sha256` and the GitHub asset digest); `LICENSE.txt`; `BUILD.txt` with configuration and source link |

FFmpeg license: **LGPL v3 or later** (`--enable-version3`, no `--enable-gpl`, no `--enable-nonfree`; `ffmpeg -L` confirms; `fetch-runtime` refuses a GPL/nonfree build). Every codec and format the engine uses is native (aac, mp3 decode, png, mjpeg, mov/mp4, image2, wav/pcm). Corresponding source: https://github.com/FFmpeg/FFmpeg/commit/29e619e767 — recorded in `BUILD.txt` for the LGPL source offer.

Pins and checksums: `desktop/runtime-pins.json`; npm packages by `package-lock.json` integrity; Electron and electron-builder tool downloads are checksum-verified by their own tooling. All downloads and caches went to `worktree/build-cache/downloads/<item>/` (own folder each). Nothing was quarantined by security software.

## 3. What was launched and tested

All test instances used port 5212, a test Electron profile (`--shell-profile`), fixture library roots in scratch, and `--show-inactive`/`--start-hidden`. A focus watcher sampled the foreground window every 100–250 ms: **our processes never took focus**. Every run ended with zero processes left under `dist/win-unpacked` (Electron, python.exe, ffmpeg.exe, ffprobe.exe). Harness: `scratch/electron-2026-10-13/harness/`; logs: `scratch/electron-2026-10-13/logs/`.

| Check | Data | Result |
| --- | --- | --- |
| Packaged app on the catalog **copy** (`data-copy/`, fixture roots) (final) | 360 MB copy | Engine ready in 0.6–1.1 s; window shows the existing UI (screenshot `tests/copy/window.png`): v0.14.0, 2,336 waiting / 70 held, 19 queued, automatic Paused. The 6 completed jobs show "needs attention" because their stored root differs from the fixture root — the intended fail-closed result. |
| Close button on the copy | — | `WM_SYSCOMMAND/SC_CLOSE` (what the title-bar ✕ sends): window hidden, shell and engine alive, health 200. |
| Quit while idle (copy) | — | Exit code 0 in 1.9–2.0 s; ownership record removed; port closed; no processes left. |
| Conversion + Quit (fixture library, two generated 45-minute books, run three times, last one final) | fresh data folder | Book A encoding; ✕ hides the window and progress keeps advancing (184 s → 728 s of audio). Quit sent mid-book: new work refused (409), book A ran encoding → checking → publishing → source cleanup → temporary cleanup, then the app exited (book done 13.5 s / 24.1 s after Quit, app exited 17.5 s / 29.7 s after Quit, exit code 0). A's M4B published and its 3 MP3s retired with recovery copies; book B's 3 MP3s untouched. Relaunch: Paused, 1 queued, 1 completed, 0 failed — parked state kept. Quit again: exit 0, nothing left. |
| Shell crash (Electron main killed) (final) | quick fixture | The engine noticed its input closing and stopped itself in 0.3 s, removing its own ownership record. |
| Force-end of the whole app (like Task Manager End task) | quick fixture | The record is left behind; the next start moved it aside (`web-instance.stale-<time>-pid<N>.json`) and started normally, then quit cleanly. Before this fix a stale record blocked every later start. (final) |
| Second app on a data folder already in use | quick fixture | Refused with "Books Arranger could not start: This catalog is already open in another Books Arranger window" (exit 1); the first app stayed healthy. (final) |
| Dev run (`electron .`) | `scratch/desktop-dev/` | Port 5212, own data folder, fixture library roots, bundled runtime; `--quit` exits cleanly. |
| Sidecar alone (bundled Python) | quick fixture | Desktop routes need the per-launch desktop token (403 without it or with the page token); body must be `{}`; quit when idle exits in 0.3 s with code 0. |

Deviation to note: one dev-run check sent a single read-only `GET /api/health` to port 5210 (the live app) to confirm the dev instance was a different process. Nothing else touched port 5210, the live app or the live `data/` (except the one read-only catalog backup and reading the small JSON files listed in section 1). The probe is removed from the kept harness.

Not proven here: the literal tray-menu click and the Quit confirmation dialog (both would take focus; the second-launch `--quit` path calls the same Quit function with confirmation already given), the installer itself, and Windows sign-out (`session-end` path).

## 4. Test suite

- Python, full discovery (558 tests): no regression. The failure set matches the pre-change baseline (9 errors from this fresh worktree missing other runs' scratch folders and fixtures consumed by cleanup), plus two known flakes: `test_waiting_uses_earliest_candidate…` fails 1 in 10 on the **unmodified** base code too, and a `test_web` teardown file-lock error passed 3/3 when rerun. One real regression found mid-way (`MergeService.__new__` fixtures lacked `draining`) was fixed by making it a class default; the affected modules pass.
- New `tests/test_desktop_quit.py`, 9 tests, all pass. Positive control: removing the drain check from the job loop makes the drain test fail.
- Real-media modules rerun with the **bundled** FFmpeg 8.1.3 on PATH: same results as with the machine's 8.1.1 (encoding policy, QuickTime chapters, chapter preservation, merge service, automatic media/policy, replacement media pass; the two baseline fixture errors repeat).
- Node frontend checks: all 7 pass.

## 5. Changed and new paths (worktree)

Changed: `.gitignore` (node_modules, build-cache, dist), `app.py` (imports `catalog_lock`/`BASE` from the new module), `web_server.py` (import line, `version()` reads `package.json` then `VERSION`, `--port`), `audio_jobs.py` (`drain()` + loop check), `merge_service.py` (`draining` default, `drain()`, `drained()`, drain-aware `pause()`/`resume()`), `Docs/BooksArranger_Brief.md` (one sentence in Stack and commands, new Decision Log section). Deleted: `VERSION`.

New: `package.json`, `package-lock.json`, `desktop/main.js`, `desktop/icon.png` (placeholder), `desktop/runtime-pins.json`, `scripts/fetch-runtime.mjs`, `scripts/stage-backend.mjs`, `scripts/clean-dist.js` (QuickLaunch copy), `catalog_owner.py`, `desktop_backend.py`, `tests/test_desktop_quit.py`, this doc.

Overlap with the split-books worktree (v0.15.0, uncommitted there): `merge_service.py` (their hunk near line 502; mine near the class header and `pause`/`resume` — no textual overlap), `Docs/BooksArranger_Brief.md` (both append after line 241 — keep both sections), `VERSION` (they bump it to 0.15.0; this branch deletes it — the shipped version moves into `package.json`). I did not touch identity modules.

## 6. Commands

From the repo root: `npm ci` → `npm run fetch-runtime` → `npm start` (dev) or `npm run pack` (installer in `dist/`). Unset `ELECTRON_RUN_AS_NODE` before `npm start` from a VS Code terminal (the packaged exe ignores it). Test flags: `--data-dir=`, `--port=`, `--roots-json=`, `--shell-profile=`, `--start-hidden`, `--show-inactive`, `--capture=`, `--quiet-errors`; a second launch with `--quit` / `--close-window` / no flag drives the running copy.

## 7. For Judy — UI pieces to spec before release (M1 has working placeholders)

1. **Tray.** Icon: placeholder (three spines on the app's dark surface). Tooltip: "Books Arranger"; while quitting: "Books Arranger — quitting after the current book". Left-click opens the window. Menu: "Open Books Arranger" · separator · "Quit". While quitting the last item becomes a disabled "Quitting after the current book…". Open: should the first ✕ show a one-time notice that the app is still running in the tray?
2. **Quit confirmation** (only when a book is converting; idle Quit has no prompt). Title "Quit Books Arranger", message "Quit after the current book?", detail "“<title>” finishes converting first, then Books Arranger closes. Queued books stay queued for next time.", buttons "Quit after this book" / "Cancel".
3. **Quit progress.** Today only the tray shows it. The window keeps the normal jobs panel; any control answers with the engine's "Server is shutting down". Needs an in-window "Quitting after <title>…" state with controls disabled — and a decision on "Cancel quit" / "Quit now" (Sergei question 1).
4. **Update-ready notice** (M2 placeholder). Proposal: when an update is downloaded and the app is idle, a tray item "Restart to update to vX.Y.Z" plus an in-window notice; never during a conversion.
5. **Existing "Stop server" button** in the page ends the engine immediately (the current book restarts later) and the desktop app then closes. Hide or relabel it in the desktop app?
6. **Startup errors**: native dialog "Books Arranger could not start" with the engine's last lines (technical text today).
7. Window: 1280×860, minimum 950×650, menu bar hidden (Alt shows the default menu with DevTools); the page badge still says "local prototype".

## 8. Notes for the next owner

- Packaged default port is 5210 (the studio assignment). While the old Start-menu app runs, the packaged app refuses to start (catalog lock and strict port), by design. Switching over is an M2 step.
- Dev port 5212 is proposed for `Team/Docs/DevPortAllocation.md` (5211 is already bound by `tests/test_merge_http.py`). Not edited — outside this worktree.
- ProcessRules § The close button must always quit the process: this tool's tray Quit waits for the current book (Sergei's ruling) instead of ending immediately; recorded in the Brief Decision Log as the tool's exception. A real hang is still bounded: if the engine stops answering for 90 s while quitting, the shell ends its process tree.
- Scratch kept: `data-copy/` (the one catalog copy, already modified by test startups — do not treat as the live state; delete when QA no longer needs it), `logs/`, `harness/`, `tests/copy/window.png`, `installer-list/app-64.txt`, `worktree/dist`, `worktree/build-cache`, `worktree/node_modules`. Removed with the studio disk-hygiene planner: test Electron profiles, fixture libraries and fixture data folders, and the worktree's unit-test `scratch/` (446,324,216 logical bytes). Left for review: `pristine/` (3.1 MB export of the base commit used for the flaky-test comparison) — the planner refuses it because it contains the repo's `.claude/` folder.
