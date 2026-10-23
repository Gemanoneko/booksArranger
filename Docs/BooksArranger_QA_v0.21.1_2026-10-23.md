# Books Arranger 0.21.1 - Release QA on build 6f88e700 (Futaba)

Pass run 2026-10-23. Tester: Futaba. Behavior only; construction is Senua's. Brief: look for what breaks or gets in the way, not a balanced review.

**Verdict:** GO

Release source commit: f64d46b74fe92af164f9189b2cb8c93ee44ac590
Release artifact manifest SHA256: 9a5b6ed94d580164bc68b5521f2ef936bf155d6b6b39d9bfa3ecca1cfd4472cb

Blockers: 0. Majors: 0. Minors: 5 open (m-1, m-2 and m-7 carried; m-5 and m-6 new or newly characterised). Closed on this build: M-1, m-3, m-4. Data loss found: none. Pattern alerts: 2 (last section).

**Why GO.** Every 0.21.1 fix works on the pinned packaged bytes, and every delta scenario fails on the 0.21.0 negative control (e0469868) exactly where it should. The generated matrix runs 457 subtests with 0 failures on 6f88e700 and 49 of 49 failing subtests plus a `KeyError: 'identity'` on the control. My two earlier probes now pass: `x-identity` starts the engine in all three cases (the control does not start in case A), and the 26-shape garbage probe starts the engine in 26 of 26 with no raw exception. The core flow (in-place end to end, byte-identical to the copy flow, fallbacks including keep-sources, a real kill at every write step, the re-hash cut) is unchanged, also on a 4-hour book. The shell shows v0.21.1, close hides it to the tray, `--quit` leaves zero processes, and nothing of mine took the foreground. Nothing I attacked lost or damaged audio bytes: every file I left alone was left exactly as found, and every file I undid came back byte-identical, now including its download marker and write time.

**What is not closed.** Nothing blocks. Three things are worth Sergei's attention because they are visible: a book can sit at "needs attention" with a text that is no longer true after its file was restored (m-5, with m-1 and m-2 the same family; pattern alert 1), a book whose journal row is damaged is deliberately left as the kill left it and has no way out in the app (m-6), and `x-schema` still stops the engine from starting when the journal table lacks its `intent` column (m-7, known, hand-edit reach).

## 1. Build identity (checked before any test)

- Worktree `C:/Antigravity Projects/Worktrees/Books Arranger/inplace-m4b`, HEAD `f64d46b7...`, `git status` clean when I started and clean before this report was written.
- `dist/release-artifacts.json` raw SHA-256 equals the pin in the header: checked first, and again after every launch. Build `6f88e700-e375-4957-ba30-2d579bc257cb`. The partial build `2603f716` was never used.
- Installer `Books-Arranger-Setup-0.21.1.exe` (173,687,419 bytes) SHA-256 `c6d6bb49...c63e0` equals the manifest entry. The installer was never run.
- Payload: all 271 files under `win-unpacked` hash to the manifest, 0 missing, 0 mismatched, 0 extra, before and after all launches. `resources/backend/VERSION` reads 0.21.1; the `app.asar` `package.json` reads 0.21.1. All 73 packaged backend `.py`/`.json` files equal their f64d46b blobs (CR stripped).
- Product digest recomputed with the repo's own `productTree()`: f64d46b gives `d9d11c58...f07c3`, equal to the manifest's `product_digest`; e78b747 gives the old `a0640e1a...`.
- Driver `ba-0.21.1-qa-driver-f64d46b.py` SHA-256 `408510e6...` and the frozen matrix test file SHA-256 `9a412506...` match the handoff (the driver prints `equal True` for the latter). Every scenario printed the packaged module path under `6f88e700.../win-unpacked` and `VERSION 0.21.1` (the control prints `0.21.0`).
- I did not run the gate, as instructed.

## 2. The 0.21.1 delta scenarios: build under test and negative control

Roots `C:/baqa211/n` (6f88e700) and `C:/baqa211/c` (e0469868). Logs: `ba-0.21.1-futaba-<scenario>-6f88e700.log` and `...-NEG-e0469868.log`.

| Scenario | 6f88e700 | e0469868 (control) |
|---|---|---|
| `matrix` (F15, F16, M-1, F20) | `tests 2 \| subtests 457 \| failing 0 \| errors 0 \| failures 0`, 26.6 s | `subtests 49 \| failing 49 \| errors 1 \| failures 50`, incl. `ERROR ... KeyError: 'identity'` and the startup cases failing on "In-place journal intent is missing" |
| `null-keys` (F16) | At start: Other `pending`, journal `rolled_back`, original restored True; Attempt NULL `needs attention ... The journal record of this edit is damaged; the file was not changed`; Job NULL `pending`; both NULL-key rows stay `intended`, both files left as the kill left them True. Attempts: runner got only Other (sha `ff0a94ef15e4`); Job NULL (found by its source path) and Attempt NULL both damaged | All three books `needs attention ... In-place journal intent is missing`; Attempt NULL's file changed (False) |
| `root-vs-folder` (F17) | root-hidden: `pending`, `intended`, then `rolled_back`, original identical True. folder-renamed: `needs attention ... The edited original is missing and its destination does not hold it`, `unresolved`, moved file left as the kill left it True | root-hidden: the same (no-regression case). folder-renamed: `pending`, `intended`, never settles |
| `marker` (m-3) | A, B, C, D, E all: `bytes and ns mtime identical: True`, streams `['::$DATA', ':Zone.Identifier:$DATA']`, marker bytes True. E: `the edit undid itself and the copy flow ran`, the changed marker kept | marker gone in A-D (`marker bytes as expected: False`); E `DEFECT: the edit removed a marker that changed after its intent` |
| `bad-values` (m-4) | Positive control `rolled_back`, identical True; all six bad rows `unresolved` damaged; each copy `left exactly as found: True` (6 of 6) | Each copy changed (False, 6 of 6), reasons `Cannot preserve recovery timestamps/attributes` and `The original bytes could not be proven after the undo` |
| `startup` (b) | Folder renamed: `needs attention ... missing ...`, `unresolved`. After the folder is back: `rolled_back`, original identical True; the job keeps its needs-attention state and the stale reason (as the handoff says) | per handoff |
| `offline` | restart: as startup (b). attempt: `needs attention` at start, then the runner saw the original's sha256 (`ff0a94ef15e4`), `rolled_back`, identical True, job `pending` | per handoff |

All five delta scenarios discriminate. The new F17 expectations for `startup`(b) and `offline` match what the handoff prints, line for line.

**My x-identity probe** (`ba-0.21.1-futaba-x-identity-*.log`): (A) kill after the rename, intent without `identity`: the engine **starts** (0.2 s), the row is `unresolved` "The journal record of this edit is damaged; the file was not changed". (B) row `published`, detail `null`, no `identity`: cleanup reads "In-place move receipt is missing; nothing retired" (not the raw `'identity'`), output exists, original absent. (C) `identity` null: damaged, engine starts. Control: (A) `ENGINE DID NOT START (rc 1) | KeyError: 'identity'`, (B) raw `'identity'`, (C) completes. M-1 is closed.

**My 26-shape garbage probe** (`x-garbage`; one book per shape, killed at `appended`, then an engine start): **26 of 26 start on 6f88e700, 0 raw exceptions** (the control also starts 26 of 26; it fails differently, below). Differences from 0.21.0, by design of F15/F16/m-4:

| Shapes | 0.21.0 | 0.21.1 |
|---|---|---|
| xix job_id NULL, xx attempt_id NULL (intent intact) | file undone, book reads "In-place journal intent is missing" | file left as the kill left it, book reads damaged (xix: `pending` until an attempt) |
| xxi-xxiv `modified` / `attributes` out of range | file cut back and type patched, then fails ("Cannot preserve recovery timestamps/attributes"); mtime not restored | nothing written, damaged |
| xv destination with a NUL, xvi `identity` removed | file **restored** (original identical True) | damaged, **file left as the kill left it** (see m-6) |
| i-iv, vi-xiii, xxv | damaged or raw reasons | damaged (xxv "unexpected length", xiv "outside the configured library", xxvi raw "[WinError 5] Access is denied." unchanged) |

## 3. Regression on 6f88e700 (same driver, plus my harness)

- **In-place end to end** (`inplace`): research reasons `[]`; completed, selection `existing_m4b_in_place_metadata_edit`; source gone from the original path, final at `audio/John Writer/A Book - John Writer.m4b`; driver byte proof `free -> prefix equals original: True`; same volume; cleanup completed removed 1, recovery deleted, restore_available False; `converted_total 1 approved_total 1`; journal one `published`; the copy flow on the twin chose `existing_m4b_audio_stream_copy` and its output SHA equals the in-place output.
- **Byte-identical to the copy flow** (`compare`, plus my own check): every line `IDENTICAL` (tags, chapters, streams, cover SHA, full decode ok, PCM md5 `12b94a90...`, duration); audio equals the untouched original. Independent check: both outputs are 22,664 bytes with SHA-256 `3e85c469...f129` (the same SHA as the 0.21.0 output), and the packaged `ffprobe -show_format -show_chapters -show_streams` JSON is equal with the file name removed.
- **Fallbacks** (`fallback`): ALAC, keep-sources policy and foreign named stream each chose `existing_m4b_audio_stream_copy`; original unchanged (bytes, mtime) True; journal `[]`; both streams kept on the foreign-stream original.
- **A real kill at each write step**: `crash` (`appended`, `type_patched`) and my `x-points`: a real kill (TerminateProcess on the child's handle) at all six named steps `before_append`, `appended`, `before_type_patch`, `type_patched`, `checked`, `reacquired`. Every one: original identical (bytes, ns mtime) after one engine start, journal `rolled_back`. `kill-after-rename`: `publishing`, then `published` with `books-in-place-recovered-move-v1`, job completed, cleanup completed removed 1, `converted_total 1`, queue Completed.
- **Re-hash cut** (`rehash`): unchanged: completed `{'guard': 4, 'pipeline': 0, 'held': 2}`; mtime changed: needs attention "Source changed before working-space admission", `held 0`; file ID changed: completed, `held 1`, cleanup needs_attention "Reviewed original file identity changed or cannot be verified".
- **F1 cover** (`cover`): 4100x4100 (16.8 MP) refused in the copy flow alone and after an in-place fallback, same text, note `[{'fallback': ...}]`, original unchanged, journal `[]`. My `x-cover-ok`: 1400, 3000 and 4000 (16.00 MP) px covers are produced in both modes, no over-refusal.
- **F2** `kill-after-rename` (above). **F3** `rewritten`: needs attention "...not the edited original; it was not changed", `unresolved`, file left exactly as found True.
- **Damaged scenarios** (`damaged`): (a) no `startup-child FAILED`, five damaged jobs `needs attention ... damaged`, the intact one `pending`, original identical True; (b) `reached their runner: ['67800b38']` (the other book), damaged book damaged; (c1) job completed, `cleanup ('completed', 1, '')`, journal `published` with `books-in-place-recovered-move-v1`; (c2) `cleanup ('needs_attention', 0, 'In-place move receipt is missing; nothing retired')`, `converted_total 0`.
- **Torn append** (`torn-append`): length 17344 == planned, head is the original; after start `pending`, `rolled_back`, original identical True. My `x-torn` T1-T9: T1, T3, T6-T9 recovered; T2, T4, T5 left exactly as found and `unresolved`, as designed.
- **Cover changed** (`cover-changed`): both runs `refused: Selected cover changed — review required`, original unchanged; control notes `[]`, journal `[]`; in-place notes `[True, {'rolled_back': ...}]`, one `rolled_back` row. My `x-cover-variants` (deleted, locked, emptied, replaced, touched, at `checked` and `appended`): copy flow and in-place agree on the outcome, the in-place edit always rolls back, original unchanged.
- **Real-size and awkward input** (through the whole service, each compared with the copy flow on an identical twin):
  - 4.0 h, 118.6 MB, moov at the end: in-place completed in 28.6 s (copy flow 70.0 s); output SHA equals the copy flow's; full decode ok; PCM md5 equals the original's; 12 chapters; cleanup completed removed 1.
  - 1.0 h, 29.7 MB, moov at the FRONT: in-place 17.2 s (copy flow 24.6 s); SHA equal; decode ok; PCM md5 equal.
  - Five books in one run (`x-many`): all five in-place, cleanup completed 1 each, `converted_total 5 approved_total 5`, journal five `published`.
  - Names with brackets, ampersand, doubled spaces, umlauts (`x-unicode`): both in-place, converted 2 of 2. New `x-names`: emoji, CJK, RTL, combining marks, a 255-character path, punctuation, dots and doubled spaces: each killed at `appended` and recovered, original identical True, journal `rolled_back` (the exhaustive shape check does not call a real row damaged).
- **The old probes that did not change:** `x-tamper` (one flipped byte after the rename: `unresolved`, nothing retired), `x-newid` (a, b recovered; c left as found), `x-missing` (deleted or renamed original inside its folder: "missing" `unresolved`; replaced by a directory: raw "[WinError 5] Access is denied." as before), `x-nocover`, `x-schema` (m-7), `x-perf` (below).
- `x-perf`: 5000 closed rows 0.3 s; +300 open rows in a visible folder 7.6 s and 6.3 s. That looks 4x slower than my 0.21.0 numbers (1.9 s), but the control run now, on the same busy machine, gives 5.5 s and 5.2 s, so it is machine load (Sergei's app and someone's build-cache Python and ffprobe processes were running), not a regression.

## 4. Extra attacks on the new fixes (my harness, `ba-0.21.1-futaba-probes-f64d46b-v5.py`)

All on 6f88e700; the marker probes were also run on the control to prove they can fail.

| Probe | Result |
|---|---|
| `x-upgrade`: a real 0.21.0 build (its Python, its backend) is killed at `appended`, `type_patched` and `reacquired` on a book with a marker; 0.21.1 recovers the catalog | Rows have no `zone_marker` in the intent (0.21.0 shape) and are not read as damaged. All three: `rolled_back`, bytes and ns mtime identical True, marker bytes identical True (at `reacquired` the marker is restored from the old removal receipt). A 0.21.0 kill-after-rename recovers through 0.21.1 and completes, cleanup removed 1 |
| `x-marker-real27`: the exact 27-byte marker seen on Sergei's real library files (`[ZoneTransfer]\r\nZoneId=3\r\n\0`) | In-process undo, real kill at `reacquired`, and a successful edit followed by an explicit undo: marker identical True each time. Control: False each time |
| `x-marker-shapes`: markers of 1 byte, 8192 bytes (the limit), UTF-16 with BOM, bytes holding NULs; 8193 bytes and 0 bytes | Undo and real kill restore each exactly (bytes, ns mtime, marker). 8193 and 0 bytes: not eligible, fallback note `Unknown download marker size preserved`, the copy flow keeps the book, original unchanged |
| `x-undo-partial`: a crash inside the undo: only the cut; cut + marker; cut + marker + wrong write time; cut + type still `free` | Each prefix is finished by the next engine start: bytes, ns mtime and marker identical True, `rolled_back`. Control: the marker is lost in the two cases that lack it |
| `x-attrs-mtimes`: write times 1980, 1969, 1601 + one tick, 2100, 3000 and 100-ns remainders; attributes NORMAL (0x80) and ARCHIVE (0x20) | Real kill + start, and in-process undo: bytes, ns mtime, marker and attributes identical, 8 of 8 each way |
| `x-marked-service`: a downloaded book through scan, approval, in-place edit, move and cleanup, against the copy flow on a twin with the same marker | Completed, in-place selection, `zone_marker_removed True`, cleanup removed 1, converted 1; the output has no marker, the copy flow's output has none either, and the two outputs are byte-identical. (My first run failed on my own fixture: the twin's write time moved when I marked it; rerun in `C:/baqa211/n2`.) |
| `x-moved-offline` (F17, moved world): kill after the rename, library root hidden at engine start and at Start, then back | Output intact throughout, journal stays `publishing` while hidden (no false "missing"), `published` with the recovered-move receipt after it returns. But the book never settles, see m-5. **Identical on 0.21.0** |
| `x-moved-folder`: kill after the rename, the output's folder renamed inside the visible library, then back | Nothing deleted or retired while it is missing; output intact; after it returns `published`, but the book stays needs attention, see m-5. Identical on 0.21.0 |
| `x-renamed-back`, `x-damaged-exit` (full service): what Start, Retry and Clear do for a restored or a damaged book | m-5, m-6 |

## 5. Shell smoke test (isolated; `ba-0.21.1-futaba-shell-smoke-6f88e700.py`)

Sergei's installed 0.21.0 was RUNNING (Books Arranger.exe 50364, 65684, 68556, 72844; python.exe 32940, 62276; the listener on 5210 is 62276). Every QA launch used `--shell-profile`, `--data-dir`, `--roots-json`, `--port=5213`, `--show-inactive`, `--quiet-errors`, and `--catalog-mode=new` on the first launch, all under `C:/baqa211/shell` (and `shell2`). I read the code first: `--shell-profile` sets `userData` (`desktop/main.js:53-54`) before `requestSingleInstanceLock()` (`:551`), so my instance has its own lock and `--quit` can only reach my own main process. Updates are user-initiated only. The QA launch did not exit at once, so there was no lock collision. The isolation flags worked, so I did not stop GUI launching.

- **Version:** the window (screenshot `shell-smoke-window-6f88e700.png`, which I looked at) shows the `v0.21.1` badge and the text "Closing this window keeps Books Arranger running in the tray"; the engine's own state field reads `0.21.1`.
- **Close sends it to the tray:** WM_CLOSE posted to the window. Afterwards the window exists but is not visible, the main process is alive, all 6 processes are still running, 5213 still listens and `/api/health` answers. I did not click the tray icon (input injection could take focus); `--quit` runs the same `requestQuit`.
- **`--quit`:**
  - Run 1, PIDs just before: Books Arranger.exe 12160, 34336, 50192, 57260 (main); python.exe 8460 (the 5213 listener), 53284.
  - Run 2 (with the focus sampler), PIDs just before: Books Arranger.exe 512, 7400, 37948 (main), 69008; python.exe 9516, 80556 (the listener).
  - Both: the second launch (same flags plus `--quit`) exited 0 after 0.1 s, zero processes under the build 1.2 s later, main exit code 0, no listener on 5213, `web-instance.json` absent.
- **No focus steal:** run 2 sampled the foreground window every 50 ms from launch to the end of `--quit`: one window the whole time (`System tray overflow window.`, PID 67048), **0 samples owned by any process of the build** (6 PIDs seen). In run 1 the foreground changed from VS Code to a chat app, Jami (PID 66232); none of the six build PIDs, so not mine, the machine was in use. No input was injected into any window; no audio.
- **Sergei's app untouched:** the same six PIDs before and after each run; 5210 still listening on 62276.
- **M-1 in the shell** (`ba-0.21.1-futaba-shell-m1-6f88e700.py`, a sqlite-backup COPY of the control's M-1 catalog under `C:/baqa211/shm1`, original only read): on 0.21.0 this exited with code 1 within 7 s and `Books Arranger could not start: 'identity'`. On 0.21.1 the main process stays up, the window is visible, health answers, `--quit` exits 0 in 0.1 s and nothing is left.

## 6. Findings

### m-1 - Minor - needs-attention wording stays stale or code-shaped (carried, unchanged)

Repro (`x-locked`): another program holds the edited file open (read share) at engine start. The book reads "...could not be undone yet: Cannot protect exact file: [WinError 32] The process cannot access the file because it is being used by another process." After the program lets go, the next start undoes the edit (original identical True, journal `rolled_back`) but the book still reads "could not be undone yet". Safe; the wording is the problem. UX-shaped, for Judy. Status: open.

### m-2 - Minor - a book stuck after a hard kill mid-attempt has a circular hint and no exit I could reach (carried; unchanged)

Repro (`x-online`, `x-nullstate`, `x-offline-start`, `x-batch`): a child runs the whole service and is killed mid-edit; the next start undoes the edit, then press Start. The book ends at needs attention ("Working cleanup requires attention: A prior producer is not durably closed; another attempt is not admitted"); Retry is refused ("Working files from an earlier attempt are still present. Retry after they are cleared."); Clear answers "cleared, already". The original is intact in every variant. The copy flow does the same (`x-copyflow-kill`, `x-batch-copyflow`), so it is the existing rule for killed attempts, not caused by in-place or by 0.21.1. Caveat unchanged: my catalogs carry no desktop-host origin facts (`producer_recovery` reads `origin_unproved` / `unsupported`), so whether the real shell offers the "prepare recovery" path is **not verified**; I could not exercise it without the network. Status: open; Jane and Sergei to accept or defer.

### m-5 - Minor - after a hidden or renamed location comes back, recovery restores the file but the book keeps a false "missing" reason and never settles (new facts; the present-world half is the handoff's known §13 item)

Repro A, present world (`x-renamed-back`; `startup` (b); `offline`):
1. A book is killed mid-edit (`type_patched`) and its folder is renamed inside the visible library.
2. Engine start: `needs attention | ...could not be undone yet: The edited original is missing and its destination does not hold it`, journal `unresolved`. (0.21.0 said `pending` here when the book sat in a subfolder; F17 changed that on purpose.)
3. Rename the folder back and start again: the journal is `rolled_back` and the original is identical (bytes, ns mtime) True, but the book still reads "...The edited original is missing...". Start does nothing, Retry is refused ("Working files from an earlier attempt are still present"), Clear says "cleared, already".

Repro B, moved world (`x-moved-offline`, `x-moved-folder`): kill right after the rename, hide the library root (or the output's folder), press Start, bring it back, start and press Start again. The output is intact throughout and recovery proves the move ("published" with `books-in-place-recovered-move-v1`), but the job stays "needs attention | Recorded output is missing, changed, or failed validation", cleanup reads "An inspected destination ancestor is unavailable" (or has no record), and `converted_total` stays 0 although the book is in the library and the original is gone. **Identical on 0.21.0**, so not new in this patch.

Consequence: nothing is lost, but the app keeps saying "missing" about a file that is back. Needs a rule: when recovery settles a row, the book's own state follows it (pattern alert 1). Status: open; UX-shaped, for Judy and Sergei.

### m-6 - Minor - a book whose journal row is damaged is left as the kill left it, with no way out in the app; 0.21.1 now does this for rows 0.21.0 could still undo

Repro (`x-damaged-exit`, `x-garbage` xv, xvi, xix, xx):
1. Kill a book at `type_patched` and replace the row's intent with `{}` (or remove its `identity`, or put a NUL in `destination`, or set `attempt_id` NULL).
2. Start the engine: the book reads "...could not be undone yet: The journal record of this edit is damaged; the file was not changed", journal `unresolved`.
3. Press Start, Retry, then Clear working files: all refuse (Retry "Working files from an earlier attempt are still present"; Clear "cleared, already"). The book stays at needs attention for good.

For `identity` removed, a NUL destination and NULL key columns, 0.21.0 **restored the original** (original identical True; the control log shows it); 0.21.1 leaves the file as the kill left it because the exhaustive check refuses any row it cannot read in full. In the `x-damaged-exit` run (killed at `type_patched`) that file is the finished edit minus its checks: 22,664 bytes, the old movie atom retyped `free` and the new one at the end; the packaged ffprobe reads its tags and duration, and a full `-xerror` decode of the audio succeeds with PCM md5 `12b94a90...`, equal to the original's. I did not check the other kill points for playability. That is what F15 and F16 ask for ("nothing is written for a damaged row"), so this is a trade-off, not a defect in the fix: safe, but sticky. Reach: a hand-damaged or future-schema row only. Status: open; suggest accept for 0.21.1 and decide later whether an explicit "forget this edit" action is wanted (Sergei's call).

### m-7 - Minor - a journal table without its `intent` column still stops the engine (carried; the handoff's `x-schema`, §13)

Repro (`x-schema`): create `inplace_edits` without the `intent` and `detail` columns, add one open row, start the engine: `ENGINE DID NOT START (rc 1) | KeyError: 'intent'`, original untouched. Same symptom as the closed M-1 (the app does not start), but the reach is table-shape damage by hand; the app always creates the full table (`ensure()`), and the table first shipped in 0.21.0. Status: open; fix with the table-level matrix in pattern alert 2.

### Closed on this build (regression-verified against f64d46b)

- **M-1** (`identity` unchecked, the engine did not start): closed; `x-identity` A/B/C, `matrix` and the 26-shape probe above; the shell starts on the M-1 catalog.
- **m-3** (the download marker not given back): closed; `marker` A-E, `x-marker-real27`, `x-marker-shapes`, `x-undo-partial`, `x-upgrade`, `x-marked-service`.
- **m-4** (bad `modified`/`attributes` written to before failing): closed; `bad-values` 6 of 6, `x-garbage` xxi-xxiv, `x-attrs-mtimes`.
- **Senua's F15, F16, F17, F20**: behaviour confirmed by `matrix`, `null-keys`, `root-vs-folder`, `startup`/`offline` and the end-to-end cleanup runs (F20: cleanup retires an in-place book through the native rename receipt: `x-batch` journals `published` with `books-native-no-copy-rename-v1` for the book that finished, and `inplace`, `x-many` and `x-big` complete cleanup with removed 1).

## 7. Not tested, and why

- A GUI click on the tray's Quit or the tray menu (input injection could take focus); `--quit` was used.
- A library on a network share (Sergei's Z: and Y:, never touched). In particular: whether creating or restoring the `Zone.Identifier` stream behaves on an SMB share that reports a separate file index for a named stream (a comment in `zone_identifier.py` records exactly that on Z:); offline and reconnect are simulated by hiding or renaming a folder.
- A real in-place edit through the shell UI (public research is a local stub in every scenario); whether the real shell offers the producer-recovery "prepare" path for a stuck book (m-2 caveat); how the shell UI words a damaged-record or restored book.
- The installer, an upgrade over the installed 0.21.0 (`x-upgrade` covers 0.21.0 journal rows read by 0.21.1 backend bytes, not the installer), a copy of the live catalog, Apple Books sync (the device field still reads "Apple Books sync not checked"), power loss and sleep (simulated by killing the process and by truncating or zero-filling the file), a volume without alternate data streams.
- The gate and its 36 gated tests (skipped by instruction; it passed, 1278 Python and 57 Node).

## 8. Evidence, isolation and cleanup

- Evidence, all in `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/64106cea-b39e-4987-9571-6ad97339dc8a/scratchpad/shared/`: logs `ba-0.21.1-futaba-*-6f88e700.log` and `*-NEG-e0469868.log`; `ba-0.21.1-futaba-shell-smoke-6f88e700.log`, `...-6f88e700-focus.log`, `...-shell-m1-6f88e700.log`, `shell-smoke-window-6f88e700.png`; payload, digest and process snapshots (`ba-0.21.1-futaba-payload-check-*.txt`, `...-digest-f64d46b.txt`, `...-backend-vs-blob.txt`, `...-procs-*.txt`); scripts `ba-0.21.1-futaba-probes-f64d46b-v5.py` (built by `ba-0.21.1-futaba-build-probes-f64d46b-v5.py` from the unmodified driver plus `ba-0.21.0-futaba-probe-extra*-f2de1ed.py` and `ba-0.21.1-futaba-probe-extra7`, `extra8`, `extra9`, `extra10`), the three shell scripts and `ba-0.21.1-futaba-env.sh`. I deleted nothing there. Superseded builds of my harness (`...-v2`, `-v3`, `-v4`) stay as written; v2 and v1 built a dispatch table with a missing key or a broken string, which is a harness bug, not a product result.
- Two harness slips of mine, neither a product result: (1) `compare` must be run with `--work` pointing at the `inplace` folder (the driver prints it); I first ran it with `--root` and it stopped on a missing `outputs.json`, then reran it correctly. (2) One `python -` heredoc, a one-line `print` to check the shell was responsive; it exited at once, but the brief said not to use that form, and I did not use it again.
- QA data folders, left in place (short path, outside every library, the install folder and the repo): **`C:/baqa211` is 667 MB in all**: `n` 625 MB (the 6f88e700 runs; most of it is the 4-hour fixture and its copies), `c` 17 MB (the e0469868 control), `n2` 0.8 MB, `shell` 8.3 MB, `shell2` 8.3 MB, `shm1` 8.4 MB. The disk had 44 GB free.
- Never touched: the installer, the live DB, the installed app, Sergei's profile, `Z:\` and `Y:\`, the other checkouts, `codex-books-2026-10-20`. No repo file edited, nothing committed; this report is the only file I added to the repo, uncommitted. Every session I opened is closed; at the end no process of mine remains under either build folder, port 5213 has no listener, and Sergei's six processes and the 5210 listener are as I found them. (Python, ffmpeg and ffprobe processes under `build-cache/builds/c3d7d82c-.../runtime` belong to someone else's run, were there at my baseline, and I left them alone.)

## 9. Report file name

`scripts/release-contract.mjs` (`acceptanceIndex`) accepts `Docs/BooksArranger_QA_v<version>_<YYYY-MM-DD>.md`. This file, `Docs/BooksArranger_QA_v0.21.1_2026-10-23.md`, matches, and no earlier 0.21.1 report exists, so the date needs no workaround. I ran the repo's own `reportPin`, `reportManifest` and `acceptanceIndex` on it (`ba-0.21.1-futaba-report-check.mjs`): it parses with one verdict line, one source pin and one manifest hash. Sully's acceptance index should name this path.

Pattern alerts: 2. Dispositions are proposed; Jane confirms.

- **The book's own state does not follow the journal after a successful recovery (now four faces in one release line).** m-1 (file in use, 0.21.0), m-5 present world (a renamed folder that comes back, the handoff's §13), m-5 moved world (a library outage at Start leaves "Recorded output is missing", `converted_total` 0), and the m-2 circular hint. In each, recovery settles the journal row correctly and never touches the job's own reason or state. Proposed disposition: **defer** to the next patch as one fix, not four (when recovery or `clear()` settles a row to `rolled_back` or `published`, the in-place reason on the book is cleared or re-evaluated), with Judy on the wording; **accept** for 0.21.1 because every instance is safe and rare. Jane and Sergei decide.
- **Damaged-journal handling is closed per field, not per table (third consecutive cycle with a finding here).** c296a1e narrowed a catch-all (M1), f2de1ed validated a list of fields (M-1), f64d46b generated the matrix over every field the edit writes (F15, F16). What the matrix still does not cover is the table itself: a `state` of NULL or an unknown value hides the row from recovery (`x-nullstate`, xvii: the file stays half-edited and the book falls into m-2), and a table without its `intent` column stops the engine (m-7). Proposed disposition: **accept** for 0.21.1 (hand-edit reach only, no data lost), and **defer** to the next patch a table-level generated case set (each column NULL or of another type, `state` outside the open set, a column absent) in the same style as `DamagedRowTests`, with the engine-start assertion first. Until then the next round will probably find the next column.
