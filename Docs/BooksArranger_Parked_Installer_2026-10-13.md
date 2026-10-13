# Books Arranger — restart handoff, 2026-10-13

Work is parked at Sergei's request for a computer restart. Continue the standalone installer and GitHub release; do not restart unfinished probes or assume the installer is accepted.

## Read first

1. This handoff.
2. `Docs/BooksArranger_StandingRules_2026-10-11.md` and `Docs/BooksArranger_Brief.md`.
3. `Docs/BooksArranger_DesktopRelease_UX_2026-10-13.md` (committed setup and updater specification).
4. In the Electron worktree: `Docs/BooksArranger_Electron_M2_2026-10-13.md`, `Docs/BooksArranger_BuildGuard_2026-10-13.md`, and `Docs/BooksArranger_Senua_ParkedHandoff_2026-10-13.md`.

## Branches and installed app

- Canonical checkout: `WIP/Books Arranger`, main. Installed Python app is **v0.15.0**; the Electron candidate has not been applied or installed.
- Electron worktree: `WIP/Books Arranger/scratch/electron-2026-10-13/worktree`.
- Electron branch: `codex/books-electron-m1`.
- Pushed restart WIP checkpoint: **b1c537dac00838851ba82a5a1b6e1d54b9aea092**. Worktree/index were clean, with remote parity verified.
- Candidate package/lock version: **0.16.0**, synchronized. No v0.16.0 tag, GitHub release, accepted installer, or publication exists.
- Last frozen reviewed source: **c25fc10dab9c3cb68080c4c3f4552f13ac65776f**. The newer checkpoint contains unfinished/unreviewed capture and checker changes.
- The old local `Books Arranger Setup 0.14.0.exe` is an unpublished prototype; do not publish or install it as the new build.

## What is implemented, but not accepted for release

- Main v0.15.0 merged into Electron, preserving independent receipt-matched working cleanup, shared exact PCM/concat proof, free-space holds and queue parking.
- Native retained-process host replaces PID-only termination; failed shutdown retains serving/catalog ownership.
- Explicit Existing/New catalog selection, existing folders kept in place, paused startup, no data migration.
- QuickLauncher-style **Check for updates → Download update → Restart to update**, with retry/busy/error states. Normal Quit never installs; installation requires atomic full-idle fencing and exact owned engine exit; restart stays paused.
- Guarded fresh UUID build roots, archive checks, native producer receipts, repeated-build metadata rotation, and exact-new-staging cleanup. Prior artifacts/runtime and unknown files are preserved.
- Local publishing pipeline, exact accepted artifact publication without rebuilding, remote asset/tag checks, and keep-last-four GitHub releases.

Developer evidence is historical, not final QA: 29 Python and 27 Node cases passed before the latest WIP; 20 native build-guard tests and a real supervisor capability probe passed. A **137 Python / 29 Node** graph is planned and **has not been executed** at the parked checkpoint.

## Open release blockers and next steps

1. Review the latest WIP against c25. The shipped `--capture` path at c25 could overwrite an existing file (Critical). The parked fix removes that option, but it is not independently accepted. Preserve the failure/review history.
2. Finish and verify the declared check graph and bundled Python/FFmpeg QA runtime map. Freeze the protocol-2 source, harness, canonical checker, Node/npm/cmd, Koffi and dependency inputs. Use short owned test roots and explicit fixture scaffolding; prior long-path/missing-parent failures must not be dismissed as timing.
3. Get Senua's operational contract clearance for the exact new source/context before executing finite owned checks and the guarded pack. No unchecked screenshot/debug output writes.
4. Run the actual Ender sender and identical independent Futaba receiver. Inspect real log counts, result contents and source/runtime/harness hashes before claiming PASS. Long commands have `timeout: 600000`; never launch duplicate runs.
5. Build and verify the actual NSIS payload, packaged backend/runtime/ASAR versions, protected raw JSON, installer/blockmap/latest.yml and artifact manifest. Complete independent packaged QA and nine-dimension red-team review; wrong-original or data-loss paths always block.
6. Final acceptance index: `Docs/BooksArranger_ReleaseAcceptance_v0.16.0.json`, schema `books-desktop-acceptance-v1`, exact version, explicit dated QA/review filenames. Each report has one machine verdict plus literal `Release source commit: <40hex>` and `Release artifact manifest SHA256: <64hex>`. Product tree excludes only Docs/ and CHANGELOG.md. Publish only the exact accepted artifacts.
7. Sully owns every commit, version bump, tag, push and release. Local `npm run release` is the one publishing path. `gh` is currently unauthenticated; normal GitHub CLI authentication is a final publication prerequisite. Do not substitute ambient tokens, Git credentials, connector publication or CI. Ask Sergei for authentication only after a concrete accepted build is ready.

Use Bash, not PowerShell. Commit explicit file paths, repo-local Gemanoneko no-reply identity, no AI attribution, and push immediately. Preserve unrelated studio/QuickLaunch/Comics work. Clean verified disposable output after appropriate actions; retain unresolved evidence and unique references.

## Disk and data safety

The historical receipt-matched cleanup removed **119,317,276,892 bytes in 136 WAVs** from C:, not originals or recovery. About 152 GB was free at the previous verified apply. Approval A and B persists; do not ask again. B authorized read-only original stream listing and retirement only if the extra streams are proven to be solely Zone.Identifier; this inspection/exception has not been implemented or performed, and existing refusals remain intact.

Never weaken source verification, publication, retirement ownership or 24-hour recovery. Never migrate/rehash frozen data paths or touch Z:/Y: as part of installer QA. Use private fixture roots/profiles/ports. No installer installation, Start-menu switch-over, live data change or publishing occurred during installer development.

## Hook diagnosis (separate work; unchanged)

The Codex studio guard fails before evaluation because its frozen Node fingerprint differs from installed official Node 26.11.1. Actual Node SHA-256 `a619e2e09eb0d50ef4c733d678b4d22689d2afef138cd67fd3fa107b535f8819` matches the official Node checksum; the hook expects `cea6ac365f9bb9586dafd2084d996e092e7d3e7d07ab52d1f76bf53d1fca9bc4`. Python/script pins match. The loader returns exit 1, `Checker byte tamper`; no malicious tampering is established. No hook/config changes were authorized or made. A later repair needs reviewed runtime-pin regeneration and fail-closed bootstrap behavior, not guard disablement.

## Restart shutdown evidence

Supported live shutdown completed successfully in 21.67 seconds. Exact retained owner PID 99136 (Pythonw, loaded v0.15.0) was verified. Jobs were Running with 89 queued; supported pause reached **Paused with 90 queued**, with cleanup, recovery and scanning inactive. Idle-gated shutdown was acknowledged; the native process exited, the instance record was removed, and exclusive port/catalog access was confirmed. Fourteen existing completed database projections and the live source hashes were preserved. No force kill or source/recovery deletion was used.

Verified receipt relative to the canonical checkout: `scratch/electron-2026-10-13/reboot-park/park-70d5a60e2fba4c4f901dc61c1f598bc8.json`. An initial unauthenticated state read was refused before any POST; that failed evidence was preserved, and the corrected authenticated run succeeded.

All review/development private jobs are stopped. On restart, use the normal Start-menu Books Arranger entry for the installed v0.15.0 app; verify its owner/version and paused state before any Start. Continue installer work in the separate Electron worktree. No automatic Start, experimental installer installation, or live switch is authorized by this parking handoff.
