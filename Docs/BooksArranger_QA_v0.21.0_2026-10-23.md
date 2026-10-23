# Books Arranger 0.21.0 - Release QA, delta pass on 196ce38a (Futaba)

Date: 2026-10-23. Tester: Futaba. Behavior only; construction is Senua's. This pass supersedes the 2026-10-22 pass (b2d468ea / 7321517) for the build named below.

**Verdict:** GO

Release source commit: c08c3bc9c391aa29f9351b235e1140cd6132793b
Release artifact manifest SHA256: 5526d9e9582a75a32a83814c429a526451bbebbdf69d839eacdf837fec9fcf38

Blockers: 0. Majors: 1 (M1, a regression from fix F4). Minors: 2 (m1, m2). Data loss found: none. Pattern alerts: 1 (below).

Why GO: all four c296a1e fixes (F1 to F4) work on the pinned build, and each scenario fails on the b2d468ea negative control exactly where it should. The core scenarios (in-place end to end, fallbacks including keep-sources, crash recovery at both write steps, the re-hash cut) pass unchanged. The shell opens as v0.21.0, hides to the tray on close, and `--quit` leaves zero processes. Every probe I added to attack the new recovery code left the user's file intact or untouched. The one Major is real, reproducible, and was introduced by the F4 fix: a damaged in-place journal row now stops the engine from starting, where b2d468ea started fine. It cannot be reached by the app's own writes (the row is inserted whole), so it does not break the core flow and is not a Blocker. The fix is small and the consequence if it is ever hit is severe, so I recommend Jane and Sergei fix M1 before release. That call is theirs.

## 1. Build identity (checked before any test)

- Worktree `C:/Antigravity Projects/Worktrees/Books Arranger/inplace-m4b`, HEAD `c08c3bc9c391aa29f9351b235e1140cd6132793b`, tree clean when I started (the only untracked file now is Senua's code-review report, plus this one).
- `dist/release-artifacts.json` raw SHA-256 `5526d9e9582a75a32a83814c429a526451bbebbdf69d839eacdf837fec9fcf38`: matches. Build `196ce38a-ac60-4a23-8168-088f63957393`. Partial build `2603f716` was never used.
- Installer `Books-Arranger-Setup-0.21.0.exe` SHA-256 `1baf072b...4d8244` equals the manifest entry. The installer was never run.
- Payload: all 271 files under `win-unpacked` hash to the manifest, 0 missing, 0 mismatched, 0 extra (checked again after all my launches). `resources/backend/VERSION` reads 0.21.0; the engine reports 0.21.0.
- Packaged modules `audio_pipeline.py`, `audio_jobs.py`, `source_cleanup.py`, `merge_service.py`, `inplace_m4b.py` are identical to the c08c3bc blobs (the working tree stores some of them CRLF; compared with CR stripped).
- Digest spot-check, with the repo's own `productTree()` from `scripts/release-contract.mjs` over `git ls-tree` (`ba-0.21.0-digest-check.mjs`): c08c3bc and c296a1e both give `4c5b50db73f047cae8d8bba7da6fc06c6701e9a98243f3b296db58ee8b90b797`, equal to the manifest's `product_digest`; 7321517 gives `35d15e59...` (different, as expected). `git diff --stat c296a1e c08c3bc` is two Docs files. Ender's claim holds. I did not run the gate, as instructed.

## 2. The four delta scenarios, build under test and negative control

Driver: the handoff's `ba-0.21.0-qa-driver.py`, unmodified. Fresh roots `C:/baqa21b` (196ce38a) and `C:/baqa21n` (b2d468ea).

| Scenario | 196ce38a | b2d468ea (control) |
|---|---|---|
| F1 `cover` (4100x4100 = 16.8 MP) | Copy flow alone refused; in-place attempt then fallback refused with the same text, note `[{'fallback': 'Selected cover dimensions are invalid or too large'}]`; original unchanged, journal `[]` | `DEFECT in-place attempt, then copy-flow fallback : produced existing_m4b_audio_stream_copy with the 16.8 MP cover` |
| F2 `kill-after-rename` | Source gone from original path, final exists, journal `publishing` with no receipt; after engine start `published` with receipt `books-in-place-recovered-move-v1`; after Start job completed, cleanup completed removed 1, `converted_total 1 approved_total 1`, queue Completed | `published` receipt `None`; cleanup `needs_attention removed 0 | In-place move receipt is missing; nothing retired`; `converted_total 0`, queue Needs attention |
| F3 `rewritten` (file overwritten in place after crash) | Job needs attention with "...The file at the original path is not the edited original; it was not changed"; journal `unresolved`; file left exactly as found (bytes and ns mtime): True | Job `pending`; journal `unresolved` "The original bytes could not be proven after the undo"; file left as found: **False** (the old undo wrote into it) |
| F4 `startup` (a) killed at `appended` | Job pending, queue Paused, journal `rolled_back`, original identical | Same (positive control, as designed) |
| F4 `startup` (b) killed at `type_patched`, library offline | Job needs attention "...The edited original is missing and its destination does not hold it", journal `unresolved`; library back, next start: journal `rolled_back`, original identical (bytes, ns mtime) | Job `pending` "Interrupted book restarts on explicit resume" at the offline start; the edit is journaled but never shown on the book |

All four discriminate. Logs: `ba-0.21.0-futaba-delta-196ce38a.log`, `ba-0.21.0-futaba-delta-NEG-b2d468ea.log` in the evidence folder (path in section 8).

## 3. Regression on 196ce38a (same driver)

- **In-place end to end** (`inplace`): research reasons `[]`; job completed, selection `existing_m4b_in_place_metadata_edit`; source gone from the original path, final at `audio/John Writer/A Book - John Writer.m4b`; driver byte proof `free -> prefix equals original: True`; same volume True; cleanup completed removed 1, recovery deleted, restore_available False; `converted_total 1 approved_total 1`; journal one `published`; the copy flow on an identical twin chose `existing_m4b_audio_stream_copy` and its output SHA equals the in-place output.
- **Byte-identical against the copy flow** (`compare`, plus my independent check): every driver line `IDENTICAL` (tags, chapters, streams, cover SHA, full `-xerror` decode `ok`, PCM md5 `12b94a90...`, duration); audio PCM equals the untouched original; tags changed and cover replaced. Independent check: packaged `ffprobe -show_format -show_chapters -show_streams` on both outputs, filename stripped, `diff` shows no difference; SHA-256 of the two files is `3e85c4696a542c1bd89ea4c2183e0d0c07d2b4917b5dc1bba0cbb684c2f3e129` for both (22,664 bytes; the original is 15,260).
- **Fallbacks** (`fallback`): ALAC, keep-sources policy and foreign named stream (`:extra`) each chose `existing_m4b_audio_stream_copy`, original unchanged (bytes and mtime) True, journal `[]`; both streams kept on the foreign-stream original. Keep-sources is the 8ba3af9 blocker's case: clean.
- **Crash recovery at each write step** (`crash`): `appended` and `type_patched` each killed by TerminateProcess on the child's own handle (length 15,260 to 17,344), original not intact before recovery, then after recovery identical (bytes, ns mtime), journal `rolled_back`.
- **Re-hash cut** (`rehash`): unchanged: job completed, counts `{'guard': 4, 'pipeline': 0, 'held': 2}`, cleanup completed; mtime changed: needs attention "Source changed before working-space admission", `held 0`; file ID changed: completed, `held 1`, cleanup needs_attention "Reviewed original file identity changed or cannot be verified". All as the note expects.
- **Cover gate does not over-refuse** (my probe `x-cover-ok`): 1400, 3000 and 4000 (exactly 16.00 MP) px squares give the same result in the copy flow alone and in an in-place session (copy flow, in-place edit); only 16.8 MP is refused, in both. Originals unchanged.
- **Repeat engine start** after the post-rename kill (twice more on the F2 catalog): journal, completed job, cleanup completed removed 1 and counts are identical each time.

## 4. Shell smoke (isolated, `ba-0.21.0-futaba-shell-smoke.py`)

Flags on the one launch: `--shell-profile`, `--data-dir`, `--roots-json`, `--port=5212`, `--catalog-mode=new`, `--show-inactive`, `--quiet-errors`, all under `C:/baqa21sh`. Pre-checks: no listener on 5212, no process under the build, QA launch did not exit at once (no single-instance collision).

- **Version:** the window (screenshot `shell-smoke-window.png`) shows the `v0.21.0` badge; the engine's own state reports `0.21.0`. The page also states "Closing this window keeps Books Arranger running in the tray" and has a Quit Books Arranger button.
- **Close sends it to the tray:** WM_CLOSE posted to the window. Afterwards the window exists but is not visible, the main process is alive, all 6 build processes are still running, 5212 still listens, `/api/health` still answers. The tray's notify-icon host window exists. I did not click the tray (Sergei's own app is running, so there are two identical icons); `--quit` runs the same `requestQuit`.
- **`--quit`:** PIDs just before: python 17448 (host), Books Arranger.exe 20760, 29440, 39032 (main), 77416, python 75348 (engine, the 5212 listener). The second launch with the same profile plus `--quit` exited 0 after 0.1 s; zero processes under the build 1.2 s later; main process exit code 0; no listener on 5212; `web-instance.json` absent.
- **No focus steal:** the foreground window handle and PID (Chrome, HWND 527184, PID 22428) were identical before launch, after the window showed, after the checks, and after close. Only Chrome's own tab title changed during the run (the machine was in use). No input was injected into any window; no audio.
- **Sergei's app untouched:** the installed-app process set is unchanged (Books Arranger.exe 76176, 80628, 50580, 74992; python 47064, 80020) and his 5210 listener (PID 80020) was never touched. Its short-lived ffmpeg child changed PID (43048 to 69692), which is its own retries running.

## 5. Findings

### M1 - Major - regression from F4: a damaged in-place journal row stops the engine from starting

Present on 196ce38a, **not** on b2d468ea.

Repro (harness `ba-0.21.0-futaba-probes.py`, a copy of the handoff driver plus extra scenarios; scenario `x-garbage`):
1. Queue a book and mark its attempt running; a child edits it in place and is killed at `appended`.
2. Damage the journal row: `UPDATE inplace_edits SET intent='{}'` (or `'null'`, or SQL NULL).
3. Start the engine (construct `AudioJobs` on that catalog, as the engine does).

Observed on 196ce38a:
- `intent='{}'`: `KeyError: 'path'` at `inplace_m4b.py:387` (`reconcile`), out of `audio_jobs.py:374` (`_recover`); the engine does not start.
- `intent='null'` or SQL NULL: `TypeError` at the same line; the engine does not start.
- `intent='not json'` is handled (book raised to needs attention with the parser's message), as F4 intends.

Control on b2d468ea, same four damaged rows: engine starts; the book is `pending`. b2d468ea's `_recover` wrapped the call in `except Exception: pass`; c296a1e narrowed it to `(ValueError, OSError, sqlite3.Error)`, and `reconcile`'s own handler is `except (ValueError, OSError)`, so the `KeyError` or `TypeError` from reading `intent['path']` is caught by neither and propagates out of the `AudioJobs` constructor. `BoundaryError` and `Unresolved` are `ValueError` subclasses, so real file-system and proof failures are covered; only a row of the wrong shape (or an unexpected bug) escapes.

Reach: the app writes the row whole, with the full intent JSON, in one `transaction(...)` (`inplace_m4b.py:64-77`), so I found no normal-use route to it; it takes a hand-edited, corrupted or future-schema row. The consequence if it happens is the whole app failing to start, with no in-app way out. How the shell presents a failed engine start was not tested. Status: open. Suggested direction for Ender (not done by me): restore a broad catch around the startup recovery call, or treat a malformed row as unresolved inside `reconcile`, and add the damaged-row cases to `RecoveryWiringTests`.

### m1 - Minor - the needs-attention wording stays stale or raw after the original is already restored

Repro: `startup` scenario (b), or `x-locked`.
- Library offline at start: the book reads "...could not be undone yet: The edited original is missing and its destination does not hold it". Put the library back and start again: the journal reads `rolled_back` and the original is identical, but the book still reads "could not be undone yet" (the old reason text also stays beside `rolled_back`). The handoff lists this as expected until Retry; I am recording only that Sergei would be told something untrue.
- File held open by another program (read share, e.g. a player or scanner): the text shown is the raw OS error "Cannot protect exact file: [WinError 32] The process cannot access the file because it is being used by another process." Handled safely (file untouched, undone on the next start after release) but the wording is code-shaped. UX-shaped: for Judy. Status: open.

### m2 - Minor - a book stuck after a hard kill mid-edit has a circular hint and no working exit

Found through my full-service probes (`x-retry-offline`, `x-retry-foreign`, `x-online`); identical on b2d468ea, so not caused by the four fixes. The original is intact in every variant.
Repro: a child runs scan, automatic approval and the in-place edit and is killed at `type_patched`; then restart the engine (library present or offline) and, for the online case, press Start.
- The book ends at needs attention. `attention_summary` gives Retry `allowed: False` with "Working files from an earlier attempt are still present. Retry after they are cleared."
- `retry_blocked_job` is refused on every press (8 presses over 24 s). `clear_working_files` answers `cleared: True, already: True` (nothing to clear) and Retry is still refused. `prepare_producer_recovery` raises "Historical local origin is not confirmed; all old files are retained". The attempt's receipt stays `producing`.
- Cause from the source: for an M4B job `_working_state` counts only `.m4b`/`.wav` (merge_service.py:2144-2170), and an in-place attempt dies before staging any audio, so Clear sees nothing; `admission_clear` (working_lifecycle.py:602) refuses while any receipt is not `retired`. Even with audio staged, `_working_classify` blocks any attempt whose producer did not close ("did not close cleanly; its files are kept"), so this is the existing rule for killed attempts. For an in-place book the hint just says to clear files that nothing offers to clear.
- Foreign bytes in the file (the `rewritten` case) end in the same place, by design: the file is never touched.
Not verified at the shell UI (I drove the same service calls the UI reads, not the window). Not run: the copy-flow equivalent. Status: open; Jane/Sergei to decide accept or defer.

## 6. Extra probes beyond the handoff, all on 196ce38a (harness `ba-0.21.0-futaba-probes.py`)

| Probe | Result |
|---|---|
| `x-tamper`: kill after the rename, then flip one byte of the moved file (size unchanged) | Journal `unresolved` "...destination does not hold it"; job needs attention "Recorded output is missing, changed, or failed validation"; no cleanup record, nothing retired. The F2 proof reads content, not size. |
| `x-newid` (a): file replaced by a byte-identical copy of the edited file (new file ID) | Recovered: original identical, journal `rolled_back` |
| `x-newid` (b): file replaced by the pristine original (restored from backup, new ID) | Recovered: original identical, `rolled_back` |
| `x-newid` (c): file replaced by foreign bytes of the edited length (new ID) | Left exactly as found, journal `unresolved`, book needs attention |
| `x-locked`: another program holds the edited file open (read share) at engine start | Book needs attention, file untouched; after release the next start undoes the edit (original identical) (wording: m1) |
| `x-garbage` with `intent='not json'` or a bad `detail` column | Handled; the engine starts (`intent='{}'`, `'null'`, SQL NULL are M1) |

## 7. Not tested, and why

- A GUI click on the tray's Quit (Sergei's app is running, so two identical tray icons); `--quit` was used instead.
- How the shell presents a failed engine start (M1) and what the window offers on a stuck book (m2).
- Apple Books sync (the device field still reads "Apple Books sync not checked").
- The copy-flow equivalent of m2; the in-process rename postcondition case (a gated service test); `RecoveryWiringTests` (gated tests, not rerun by me).

## 8. Evidence, isolation and cleanup

- Evidence (all in `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/64106cea-b39e-4987-9571-6ad97339dc8a/scratchpad/shared/`, nothing deleted there): `ba-0.21.0-futaba-delta-196ce38a.log`, `ba-0.21.0-futaba-delta-NEG-b2d468ea.log`, `ba-0.21.0-futaba-regress-196ce38a.log`, `ba-0.21.0-futaba-regress2-196ce38a.log`, `ba-0.21.0-futaba-spot/` (ffprobe JSON), `ba-0.21.0-futaba-probes-196ce38a.log`, `ba-0.21.0-futaba-probes-retry*-196ce38a.log`, `ba-0.21.0-futaba-prepare-196ce38a.log`, `ba-0.21.0-futaba-start-offline-*.log`, `ba-0.21.0-futaba-online-*.log`, `ba-0.21.0-futaba-garbage-NEG-b2d468ea.log`, `ba-0.21.0-futaba-cover-ok-196ce38a.log`, `ba-0.21.0-futaba-idempotent-196ce38a.log`, `ba-0.21.0-futaba-shell-smoke-196ce38a.log`, `shell-smoke-window.png`, `ba-0.21.0-futaba-payload-check.txt`, `ba-0.21.0-futaba-digest.txt`; scripts `ba-0.21.0-futaba-probes.py` (built by `ba-0.21.0-futaba-build-probes.py` from the unmodified driver plus `ba-0.21.0-futaba-probe-extra.py`) and `ba-0.21.0-futaba-shell-smoke.py`.
- QA data folders left in place (short paths, outside every library, the install folder and the repo): `C:/baqa21b` 16 MB (196ce38a driver and probe runs), `C:/baqa21n` 1.7 MB (b2d468ea delta control), `C:/baqa21s-196ce38a` 1.3 MB and `C:/baqa21s-b2d468ea` 2.2 MB (start/online/garbage comparisons), `C:/baqa21sh` 8.3 MB (shell smoke profile, data and library). Total about 30 MB. Safe to delete.
- Never touched: the installer, the live DB, the installed app, Sergei's profile, `Z:\`, `Y:\`, the other checkouts, `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20`. No repo file edited, nothing committed. Every session I opened is closed; at the end no process of mine remains under any build folder and port 5212 has no listener. (Four python.exe and one ffmpeg.exe under `build-cache/builds/c3d7d82c-...` belong to someone else's run; I left them alone.)

## 9. Pattern alerts

Pattern alerts: 1.

- **In-place path versus the copy flow's gates.** Two builds in a row let the in-place path skip a check the copy flow always runs: 8ba3af9 (keep-sources policy, a Blocker) and 7321517 (the cover size and decode checks on fallback, F1). This pass found no third instance (ALAC, foreign stream, keep-sources, cover sizes 1.4 to 16.8 MP), and c296a1e's own fix introduced a different gap (M1: a narrower error handler). The recurring shape is "a new fast path forgets a gate or a safety net the old path had". Disposition requested from Jane: proposed **fix**, as a parity test that every `create_private` check also runs after an in-place fallback and after any recovery step. Ender and Senua own the form.
