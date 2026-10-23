# Books Arranger 0.21.0 - Release QA, final delta pass on e0469868 (Futaba)

Pass run 2026-10-23. Tester: Futaba. Behavior only; construction is Senua's. This pass supersedes the c08c3bc / 196ce38a pass (`BooksArranger_QA_v0.21.0_2026-10-23.md`) for the build named below. The file name carries 2026-10-24 for a format reason, explained in section 9.

**Verdict:** GO

Release source commit: f2de1ed87e2af0842660f97c8c20a275a71ab502
Release artifact manifest SHA256: 5940e820ffc6ea86024e8950a2012d550020487c959a2f355fa5fd682f59af99

Blockers: 0. Majors: 1 (M-1, open). Minors: 4 (m-1 and m-2 carried, m-3 and m-4 new). Data loss found: none. Pattern alerts: 2 (last section).

**Why GO.** Every f2de1ed fix works on the pinned build, and each delta scenario fails on the 196ce38a negative control exactly where it should. The core flow (in-place end to end, byte-identical to the copy flow, fallbacks including keep-sources, a real kill at every write step, the re-hash cut) passes, also on a 4-hour book, a moov-first book, five books in one run and awkward file names. The shell shows v0.21.0, close hides it to the tray, `--quit` leaves zero processes, and it never took focus. Nothing I attacked lost or damaged audio bytes: every file I left alone was left exactly as found, and every file I undid came back byte-identical.

**What is not closed: M-1.** The original M1 ("a damaged journal row stops the engine from starting") is fixed for every shape the handoff lists and for 26 shapes I tried, but one key is still unchecked: a row whose intent lacks `identity` stops the engine when the move is provable. Same symptom as M1, same consequence (the app does not start), same low reach (only a hand-damaged row after a crash that follows the rename). It is not new in f2de1ed (196ce38a fails the same way). It is a Major, not a Blocker, so the verdict stays GO under the Blocker rule I gave last time, and I recommend fixing it. Whether to hold the release for it is Jane's and Sergei's call. Holding means a new build, a new manifest hash and fresh dual clearance, because my pin above names this exact manifest.

## 1. Build identity (checked before any test)

- Worktree `C:/Antigravity Projects/Worktrees/Books Arranger/inplace-m4b`, HEAD `f2de1ed8...`, `git status` clean when I started. Senua's untracked code-review report (`Docs/BooksArranger_CodeReview_v0.21.0_2026-10-24.md`) appeared during my pass; I did not read it, so this verdict is independent of hers.
- `dist/release-artifacts.json` raw SHA-256 matches the pin in the header (checked first, again after all launches). Build `e0469868-d1e8-4bb0-a31c-6b27112a10e5`. Partial build `2603f716` never used.
- Installer `Books-Arranger-Setup-0.21.0.exe` (173,681,999 bytes) SHA-256 `80a8310d...78fda` equals the manifest entry. The installer was never run.
- Payload: all 271 files under `win-unpacked` hash to the manifest, 0 missing, 0 mismatched, 0 extra, before and after all launches. `resources/backend/VERSION` reads 0.21.0. All 73 packaged backend `.py`/`.json` files equal their f2de1ed blobs (CR stripped); `VERSION` is generated.
- Product digest with the repo's own `productTree()` (`ba-0.21.0-digest-check.mjs`): f2de1ed gives `a0640e1a...930b0a2`, equal to the manifest's `product_digest`; caccf5f and c08c3bc give `4c5b50db...` (the old one). The driver prints the packaged module path and VERSION for every scenario; every one was under `e0469868.../win-unpacked`.
- I did not run the gate, as instructed.

## 2. The f2de1ed delta scenarios, build under test and negative control

Driver: the handoff's `ba-0.21.0-qa-driver-f2de1ed.py`, unmodified (SHA-256 `0922a0bc...`). Roots `C:/baqa21c` (e0469868) and `C:/baqa21e` (196ce38a).

| Scenario | e0469868 | 196ce38a (control) |
|---|---|---|
| `damaged` (a) startup, 6 books | No `startup-child FAILED`. Five damaged-intent jobs `needs attention | ...The journal record of this edit is damaged; the file was not changed`; the intact job `pending | Interrupted book restarts on explicit resume`; journal: intact row `rolled_back`, five `unresolved`; original identical True | `startup-child FAILED: TypeError ... unsupported operand type(s) for |: 'NoneType' and 'dict'`; engine does not start |
| `damaged` (b) `clear()` | `reached their runner ['583b57ef']` (the other book); other `pending`, damaged `needs attention` with the damaged reason | `reached their runner []`; both books `needs attention | expected str, bytes or os.PathLike object, not NoneType` |
| `damaged` (c1) cleanup, intent intact, detail `null` | job completed, `cleanup ('completed', 1, '')`, `converted_total 1`, journal `published` with `books-in-place-recovered-move-v1`; output exists True, original path absent True | `cleanup ('needs_attention', 0, "'NoneType' object has no attribute 'get'")`, `converted_total 0` |
| `damaged` (c2) cleanup, intent `{}` | `cleanup ('needs_attention', 0, 'In-place move receipt is missing; nothing retired')`, `converted_total 0`; output exists, original absent | `cleanup ('needs_attention', 0, "'path'")` (raw KeyError) |
| `torn-append` | length 17344 == planned 17344, head is the original; after start `pending`, journal `rolled_back`, original identical (bytes, ns mtime) True | `needs attention ...not the edited original`, journal `unresolved`, original identical **False** |
| `offline` (restart) | folder hidden: `pending`, journal `intended`; folder back: `rolled_back`, identical True | hidden: `needs attention ...missing and its destination does not hold it`, `unresolved`; stays needs attention after the folder returns |
| `offline` (attempt) | start `pending`/`intended`; then runner saw the original's sha256 (`ff0a94ef15e4`), journal `rolled_back`, identical True | start `needs attention`; the later `clear()` still undoes it |
| `cover-changed` | both runs `refused: Selected cover changed — review required`, original unchanged; control notes `[]`, journal `[]`; in-place notes `[True, {'rolled_back': ...}]`, one `rolled_back` row | `DEFECT in-place edit : produced existing_m4b_in_place_metadata_edit although the selected cover changed` |

All four scenarios discriminate. Logs: `ba-0.21.0-futaba-r8-<scenario>-e0469868.log` and `...-NEG-196ce38a.log`.

**My M1 garbage probe, re-run** (`x-garbage`, harness `ba-0.21.0-futaba-probes-f2de1ed.py`): one book per damaged shape, each in its own catalog, killed at `appended`, then an engine start. 26 shapes (intent not JSON, `{}`, `null`, SQL NULL, `[]`, `"x"`, `5`; size as string or bool; type_offset -1; path an int, with a NUL, a directory; root unrelated; destination with a NUL; identity key removed with the original still in place; state, job_id, attempt_id NULL; detail garbage; `modified` and `attributes` out of range or negative; size 2**70). **e0469868: the engine started in 26 of 26.** 196ce38a (control): 7 of 26 did not start (`{}`, `null`, SQL NULL, `[]`, `"x"`, `5`, size as string), exactly the family of my original M1. In no case was a file left damaged; see m-4 for the one thing the undo does not restore. The one shape that still stops the engine is not in this list because it needs a crash after the rename: M-1.

## 3. Regression on e0469868 (same driver)

- **In-place end to end** (`inplace`): research reasons `[]`; job completed, selection `existing_m4b_in_place_metadata_edit`; source gone from the original path, final at `audio/John Writer/A Book - John Writer.m4b`; driver byte proof `free -> prefix equals original: True`; same volume True; cleanup completed removed 1, recovery deleted, restore_available False; `converted_total 1 approved_total 1`; journal one `published`; the copy flow on an identical twin chose `existing_m4b_audio_stream_copy` and its output SHA equals the in-place output.
- **Byte-identical to the copy flow** (`compare`, plus my own check): every line `IDENTICAL` (tags, chapters, streams, cover SHA, full `-xerror` decode `ok`, PCM md5 `12b94a90...`, duration); audio PCM equals the untouched original; tags changed and cover replaced. Independent check with the packaged `ffprobe -show_format -show_chapters -show_streams` on both outputs: JSON equal (file name removed), and both files have SHA-256 `3e85c469...f129` (22,664 bytes; same as the c08c3bc output).
- **Fallbacks** (`fallback`): ALAC, keep-sources policy and foreign named stream each chose `existing_m4b_audio_stream_copy`; original unchanged (bytes, mtime) True; journal `[]`; both streams kept on the foreign-stream original.
- **Crash recovery at each write step**: the driver's `crash` (`appended`, `type_patched`) and my `x-points`, a real kill (TerminateProcess on the child's handle) at all six named steps `before_append`, `appended`, `before_type_patch`, `type_patched`, `checked`, `reacquired`, plus `kill-after-rename`. Every one: original identical (bytes, ns mtime) after one engine start, journal `rolled_back` (for `kill-after-rename`: `published` with the recovered-move receipt, cleanup completed removed 1, `converted_total 1`, queue Completed). Repeating the engine start on the post-rename catalog gave the same result.
- **Re-hash cut** (`rehash`): unchanged: completed, `{'guard': 4, 'pipeline': 0, 'held': 2}`, cleanup completed; mtime changed: needs attention "Source changed before working-space admission", `held 0`; file ID changed: completed, `held 1`, cleanup needs_attention "Reviewed original file identity changed or cannot be verified". As expected.
- **F1 cover** (`cover`): 4100x4100 (16.8 MP) refused in the copy flow alone and after an in-place fallback, same text, note `[{'fallback': ...}]`, original unchanged, journal `[]`. My `x-cover-ok`: 1400, 3000 and 4000 (16.00 MP) px covers give the same result in both modes (copy flow, in-place edit); no over-refusal.
- **F2 kill-after-rename** (above). **F3 `rewritten`**: needs attention "...not the edited original; it was not changed", journal `unresolved`, file left exactly as found True. **F4 `startup`** (a) recovered and (b) offline: pending then `rolled_back`, original identical, with the F13 expectation.
- **Real-size and awkward input** (my probes, all through the whole service and compared with the copy flow on an identical twin):
  - 4.0 h, 118.6 MB, moov at the end: in-place completed in 18.8 s (copy flow 49.0 s); output SHA equals the copy flow's; full decode ok, PCM md5 equals the original's; 12 chapters; cleanup completed.
  - 1.0 h, 29.7 MB, moov at the FRONT (faststart): in-place 10.8 s (copy flow 17.6 s); SHA equal; decode ok; PCM md5 equal. The old moov becomes a `free` box at the front, as in the copy flow's output.
  - Five books in one run (`x-many`): all five in-place, cleanup completed 1 each, `converted_total 5 approved_total 5`, queue Completed, journal five `published`.
  - Folder and file names with brackets, an ampersand, doubled spaces and non-ASCII letters (`x-unicode`): both books in-place, converted 2 of 2.

## 4. Shell smoke test (isolated, `ba-0.21.0-futaba-shell-smoke-e0469868.py`)

Every launch used `--shell-profile`, `--data-dir`, `--roots-json`, `--port=5212`, `--show-inactive`, `--quiet-errors`, and `--catalog-mode=new` on the first launch, all under `C:/baqa21c/shell`. Pre-checks: no `Books Arranger.exe` anywhere on the machine (Sergei's installed app is quit; no tray icon of his), no listener on 5210 or 5212, no process under the build; the QA launch did not exit at once, so there was no single-instance collision.

- **Version:** the window (screenshot `shell-smoke-window-e0469868.png`) shows the `v0.21.0` badge; the engine's own state field reads `0.21.0`. The page says "Closing this window keeps Books Arranger running in the tray" and has a "Quit Books Arranger" button.
- **Close sends it to the tray:** WM_CLOSE posted to the window. Afterwards the window exists but is not visible, the main process is alive, all 6 processes under the build are still running, 5212 still listens, `/api/health` answers. The notify-icon host window exists. I did not click a tray icon (input injection could take focus; `--quit` runs the same `requestQuit`).
- **`--quit`:** PIDs just before: `Books Arranger.exe` 5872, 6232, 29336 (main), 38340; `python.exe` 51672 (host), 55056 (engine, the 5212 listener). The second launch (same profile plus `--quit`) exited 0 after 0.1 s; zero processes under the build 1.1 s later; main process exit code 0; no listener on 5212; `web-instance.json` absent. After the whole pass no process of mine remains under either build folder.
- **No focus steal:** the foreground window (Outlook, HWND 4785422, PID 57304) was identical before launch, after the window showed, after the display checks and after close. No input was injected into any window; no audio. Sergei's app untouched (none was running before or after).

Separate launch for M-1 (`ba-0.21.0-futaba-shell-m1-e0469868.py`), same isolation flags plus `--catalog-mode=existing`, on a sqlite-backup COPY of the M-1 catalog under `C:/baqa21c/shm1` (the original under `x-identity/A` was only read): the main process exited with code 1 within 7 s, no window, no tray icon, nothing left running, nothing listening. The message (in the app's own log, because of `--quiet-errors`; a second `--quit` launch printed the same on stderr): `Books Arranger could not start: 'identity'`. (Foreground "unchanged: False" in that run is the same Chrome window, HWND 527184 PID 22428, whose tab title changed while Sergei's machine was in use.)

## 5. Findings

### M-1 - Major - M1 is not fully closed: a journal row whose intent lacks `identity` still stops the engine when the move is provable

Present on 196ce38a too, so it is not new in f2de1ed; it is the part of M1 the fix left open. Status: open.

Repro (harness scenario `x-identity`, case A):
1. A child runs scan, automatic approval and the in-place edit and is killed right after the OS rename (the driver's `killed_after_rename`). The journal row is `publishing`, the book is at its final path.
2. Remove one key from the row's intent JSON: `identity` (`UPDATE inplace_edits SET intent=<the same JSON without "identity">`).
3. Start the engine (construct `AudioJobs`, as the engine does).

Observed on e0469868 (and on 196ce38a): `KeyError: 'identity'` at `inplace_m4b.py:412` (`_prove_move`), from `reconcile` (`:430`), `recover_all` (`:444`), `AudioJobs._recover` (`audio_jobs.py:374`). `_recover` catches only `(ValueError, OSError, sqlite3.Error)` (`:376`), so the engine does not start. In the isolated shell the app exits with `Books Arranger could not start: 'identity'` and has no window (section 4). Case B (row set to `published`, detail `null`, intent without identity): startup is fine, but cleanup shows the raw reason `'identity'` instead of the new "In-place move receipt is missing; nothing retired", and `converted_total` stays 0. Case C (identity present but null): handled, cleanup completes. Log: `ba-0.21.0-futaba-r8-x-identity-e0469868.log`, traceback `...-x-identity-A-traceback-e0469868.log`.

Cause (from the source): `identity` is the only intent key recovery reads that the `_SHAPE` check (`:68-69`) does not cover, and it is read only on the "the move happened" path (`_prove_move`, `:412`), so the undo path (original still in place) never touches it, which is why my case xvi passes. `reconcile` (`:435`) and `confirm_move` (`:512`) catch only `ValueError`/`OSError`. Related, lower reach: a catalog whose `inplace_edits` table lacks the `intent` column stops the engine with `KeyError: 'intent'` (`x-schema`).

Reach: the app writes the row whole, with `identity`, in one transaction (`inplace_m4b.py:318-324`), so no normal-use route reaches it; it needs a hand-edited, corrupted or future-schema row after a crash that follows the rename. The consequence when it is reached is the app not starting, with a one-word message and no in-app way out.

Suggested direction for Ender (not done by me): check `identity` with the rest of the shape and treat any row that fails inside `_prove_move` as `unresolved` in both handlers; and add a mutation test that deletes each key and flips each type of a valid intent, in both world states (original present; original moved), and asserts that `recover_all` and cleanup never raise.

### m-1 - Minor - needs-attention wording stays stale or code-shaped (carried, unchanged)

Repro: `x-locked`. Another program holds the edited file open (read share) at engine start: the book reads "...could not be undone yet: Cannot protect exact file: [WinError 32] The process cannot access the file because it is being used by another process." After the program lets go, the next start undoes the edit (original identical, journal `rolled_back`) but the book still reads "could not be undone yet". F13 fixed the same stale text for the offline-folder case; the file-in-use case is unchanged. Safe (file untouched, undone later); the wording is the problem. UX-shaped, for Judy. Status: open.

### m-2 - Minor - a book stuck after a hard kill mid-attempt has a circular hint and no exit I could reach (carried; now shown to be the existing rule for killed attempts)

Repro (`x-online`, `x-nullstate`, `x-batch`): a child runs the whole service and is killed mid-edit; restart the engine and press Start. The book ends at needs attention ("Working cleanup requires attention: A prior producer is not durably closed; another attempt is not admitted"); Retry is refused ("Working files from an earlier attempt are still present. Retry after they are cleared."); Clear answers "cleared, already" (nothing to clear); `prepare_producer_recovery` raises "Historical local origin is not confirmed; all old files are retained". The original is intact in every variant.

New in this pass:
- **Identical in the copy flow on this build** (`x-copyflow-kill`, `x-batch-copyflow`: the same book forced down the copy flow and killed mid-attempt): same needs-attention text, Retry refused, Clear refused ("Some working files weren't cleared..."), producer recovery `unsupported`, cause `origin_unproved`. So it is the existing rule for killed attempts, not caused by in-place or by f2de1ed.
- **Caveat:** my catalogs carry no desktop-host origin facts, so whether the real shell offers the "prepare recovery" capability (the UI has one) is not verified. The harness answer is "unsupported".
- **Batch effect** (`x-batch`: three books approved when the machine died during the second book's edit): after the restart the first Start flags the interrupted book and the queue stops with the third book still pending; a second Start runs it (`converted 2 of approved 3`, the interrupted one stays stuck). The copy flow does the same (`x-batch-copyflow`, two books). My first harness run of this probe waited for the pending book and timed out after 300 s, which is how I found it.

Status: open; Jane and Sergei to accept or defer.

### m-3 - Minor - a rolled-back or crash-recovered in-place edit does not give back the download marker it removed (new)

Real-world M4Bs downloaded by a browser carry a `:Zone.Identifier` stream. The in-place edit removes it (`inplace_m4b.py:347-351`), journals its bytes (`zone_marker`), and the undo never restores it.

Repro (`x-marker`): fixture with `[ZoneTransfer] ZoneId=3`.
- (B) The selected cover file changes at the `reacquired` step, after the marker is gone: the edit refuses "Selected cover changed — review required", original bytes and mtime identical, streams now `['::$DATA']`: the marker is gone.
- (C) Control: the copy flow refuses the same change and the original keeps `[::$DATA, :Zone.Identifier:$DATA]`.
- (D) A real kill at `reacquired`, then an engine start: bytes and mtime identical, marker gone.

The new final cover check (`:360`) sits after the marker removal, so a cover that changes during the edit is a new, reachable way to lose the marker; a failing byte proof (`:356`) already did the same. Consequence: the file no longer says it was downloaded; its audio and bytes are intact and the book is kept. Status: open; reasonable to accept for 0.21.0.

### m-4 - Minor - a damaged `modified` or `attributes` value passes the shape check, and the undo writes before it fails on it (new)

Repro (`x-garbage` xxi to xxiv): the row's `modified` is 2**70 or -5, or `attributes` is 2**70 or -1 (ints, so they pass), after a kill at `appended`; start the engine. The engine starts (good), but the undo has already cut the file back to its original length and put the `moov` type back before `restore_metadata` fails: bytes equal the original, mtime and attributes are not restored. The book reads "...could not be undone yet: Cannot preserve recovery timestamps/attributes" (or "Unsupported recoverable source attributes", or "The original bytes could not be proven after the undo"), and a later attempt would see a changed mtime ("Source changed"). No audio bytes are lost. Reach: hand-damaged row only. Status: open.

## 6. Extra probes beyond the handoff, all on e0469868 (harness `ba-0.21.0-futaba-probes-f2de1ed.py`)

| Probe | Result |
|---|---|
| `x-torn` T1 full-length random or 0xFF tail; T3 half-written zero tail; T6 torn type bytes; T7 type is `free` but the append never reached disk; T8 `free` plus half a tail | Recovered: original identical, journal `rolled_back` |
| `x-torn` T2 tail 100 bytes longer than planned; T4 one byte of the original extent flipped; T5 file shorter than the original | Left exactly as found, `unresolved`, book needs attention (by design: only the head proof and the length bound decide). Note T1 and T9 show a foreign tail of exactly the planned length is cut; that is F12's decision |
| `x-tamper`: kill after the rename, one byte flipped in the moved file | Journal `unresolved`; job "Recorded output is missing, changed, or failed validation"; no cleanup record, nothing retired |
| `x-newid` (a) byte-identical copy of the edited file, new file ID; (b) pristine original restored from a backup, new ID | Recovered, original identical |
| `x-newid` (c) foreign bytes of the edited length, new ID | Left exactly as found, `unresolved` |
| `x-locked`: another program holds the file open at start | Needs attention, file untouched; next start after release undoes it (m-1) |
| `x-missing`: folder visible, original deleted, or renamed in its folder | Raised "The edited original is missing and its destination does not hold it", `unresolved`: F13 did not swallow a real loss. Original replaced by a directory: raised with the raw "[WinError 5] Access is denied" |
| `x-cover-variants`: cover deleted, locked exclusively, emptied, replaced by another PNG, or touched (same bytes) at `checked` or `appended` | Copy flow and in-place agree on the outcome (refused or produced); the in-place edit always rolls back, original unchanged. Deleted and locked covers surface as raw `FileNotFoundError` / `PermissionError` in both flows; an emptied cover reads "Select one usable JPEG or PNG cover" in-place (the copy flow after the in-place rollback sees the changed file from its start) |
| `x-nocover`: manifest with no cover, `cover: None`, cover path missing | Same exception in the copy flow and in-place (in-place notes `fallback`); original unchanged |
| `x-perf`: 5000 closed journal rows, then 300 open ones in a visible folder | Engine start 0.2 s, 0.2 s, 1.9 s |
| `x-nullstate`: journal row state set to NULL after a kill at `type_patched` | The row is invisible to recovery; the file stays in its valid half-edited state (new tags, old moov as `free`); after Start the book ends at needs attention (m-2). Bytes intact |
| `x-garbage` xix and xx: NULL job_id or attempt_id with a valid intent | The file is undone, but the row can never be settled, and the running books read "...could not be undone yet: In-place journal intent is missing" |
| `x-offline-start`: library away, Start pressed, library back, Start again | Start while away: book needs attention (m-2 text), journal `intended`; after the library returns, the next engine start undoes the edit (`rolled_back`); the book stays needs attention (m-2) |

## 7. Not tested, and why

- A GUI click on the tray's Quit or the tray menu (input injection could take focus); `--quit` was used.
- A real in-place edit through the shell UI against the network (public research is a local stub in every scenario). A real library on a network share (offline and reconnect are simulated by renaming the folder).
- Whether the real shell offers the producer-recovery "prepare" path for a stuck book (m-2 caveat), and how the shell UI words a damaged-record book.
- The installer, an upgrade over an installed 0.20.x, a copy of the live catalog, Apple Books sync (the device field still reads "Apple Books sync not checked"), power loss and sleep (simulated by killing the process and by zero-filling or truncating the file).
- `RecoveryWiringTests` and the 36 gated tests (not rerun by me; the gate passed on an idle machine, run 8).

## 8. Evidence, isolation and cleanup

- Evidence, all in `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/64106cea-b39e-4987-9571-6ad97339dc8a/scratchpad/shared/`: logs `ba-0.21.0-futaba-r8-*-e0469868.log` and `*-NEG-196ce38a.log`, `ba-0.21.0-futaba-shell-smoke-e0469868.log`, `ba-0.21.0-futaba-shell-m1-e0469868.log`, `shell-smoke-window-e0469868.png`, `ba-0.21.0-futaba-payload-check-e0469868.txt`, `...-payload-check-after-e0469868.txt`, `ba-0.21.0-futaba-digest-e0469868.txt`, `ba-0.21.0-futaba-procs-baseline-e0469868.txt`, `ba-0.21.0-futaba-spot-e0469868/` (ffprobe JSON); scripts `ba-0.21.0-futaba-probes-f2de1ed.py` (built by `ba-0.21.0-futaba-build-probes-f2de1ed.py` from the unmodified driver plus `ba-0.21.0-futaba-probe-extra*-f2de1ed.py`), `ba-0.21.0-futaba-shell-smoke-e0469868.py`, `ba-0.21.0-futaba-shell-m1-e0469868.py`. I deleted nothing there. Two of my own logs were overwritten by their reruns under the same file name (`ba-0.21.0-futaba-r8-x-batch-e0469868.log` and `...-x-many-e0469868.log`); what they held was a harness timeout and failed runs of a research stub of mine that lacked per-book pages, not product results.
- QA data folders, left in place (short paths, outside every library, the install folder and the repo): `C:/baqa21c` 626 MB (e0469868 runs, both shell profiles `shell` and `shm1`; 459 MB of it is the 4-hour fixture and its copies), `C:/baqa21e` 9.5 MB (196ce38a control). About 636 MB in all. Safe to delete (the studio's delete guard blocked my own `rm -rf`, so I did not remove anything).
- Never touched: the installer, the live DB, the installed app, Sergei's profile, `Z:\` and `Y:\`, the other checkouts, `codex-books-2026-10-20`. No repo file edited, nothing committed; this report is the only file I added to the repo, uncommitted. Every session I opened is closed; at the end no process of mine remains under either build folder and ports 5210 and 5212 have no listener. (Python, ffmpeg and ffprobe processes under `build-cache/builds/c3d7d82c-.../runtime` belong to someone else's run, were there at my baseline, and I left them alone.)

## 9. Report file name

`scripts/release-contract.mjs` (`acceptanceIndex`) accepts `Docs/BooksArranger_QA_v<version>_<YYYY-MM-DD>.md`. The requested `..._2026-10-23b.md` does not match (the `b`). `..._2026-10-22.md` and `..._2026-10-23.md` are taken by the committed superseded reports (7321517 and c08c3bc), and I did not overwrite history, so this file uses `2026-10-24`, the date Senua's untracked code-review report already uses. The date in the name is format-only; the pass ran on 2026-10-23. I ran the repo's own `reportPin`, `reportManifest` and `acceptanceIndex` on this file (`ba-0.21.0-futaba-report-check.mjs`); it parses with one verdict line, one source pin and one manifest hash. Sully's `BooksArranger_ReleaseAcceptance_v0.21.0.json` should name this path.

Pattern alerts: 2. Dispositions are proposed; Jane confirms.

- **A damaged-row handling is fixed one field at a time (second round in a row).** c296a1e narrowed a catch-all to `(ValueError, OSError, sqlite3.Error)` and I found M1; f2de1ed validates a list of fields and I found one it left out (M-1: `identity`, plus the same two-exception whitelist in `reconcile` and `confirm_move`). The recurring shape is "recovery reads one key more than the shape check covers, or raises one exception class more than the handler catches". Proposed disposition: **fix**, by closing M-1 and adding the delete-each-key / flip-each-type mutation test over both world states named in M-1; Ender and Senua own the form. Until then the next round will probably find another key.
- **The in-place path leaves a different state behind than the copy flow's refusal does (third instance across this release).** 8ba3af9 (keep-sources policy, a Blocker) and 7321517 (cover checks on fallback) skipped a gate the copy flow runs; f2de1ed's parity test now covers the refusal guards, and this pass found no missing guard. What it does not compare is the state of the original after a refusal: m-3 (the download marker is gone after an in-place refusal and kept after the copy flow's), and m-4 (the undo writes before it validates its own timestamps). Proposed disposition: **accept** m-3 and m-4 for 0.21.0 and **defer** the fix to the next patch, extending the parity test from "same refusals" to "same state of the original after each refusal"; Jane and Sergei decide.
