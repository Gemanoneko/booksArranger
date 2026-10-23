# Books Arranger 0.21.0 - Release QA (Futaba)

Date: 2026-10-22 (testing ran past midnight into 2026-10-23). Tester: Futaba. Behavior only; construction is Senua's.

**Verdict:** GO

Release source commit: 73215173a8b5c2f8324b89c34a06e470cee4b3a3
Release artifact manifest SHA256: eabc4eb15ec8c0b0ef82a430cc237a22d794fa96aafabe12513fbc96f6f9280c

Blockers: 0. Majors: 1 (M1, below). Minors: 4 (m1 to m4). Data loss found: none.

Why GO: every scenario in Ender's note passed on the pinned build, the in-place output is byte-identical to the copy flow's output on six fixtures (including two realistic ones), every kill point and every Pause restored the original exactly (one exception, m1, a Windows download-marker stream), and a source change before deletion blocked cleanup in every variant I tried. The one Major is real and reproducible but narrow (a failure or crash between the OS rename and the journal write); it loses no data and does not stop other books. Jane and Sergei should decide whether to fix M1 before the first big run on Z:, because that is where a post-rename check is most likely to trip. It is a small fix and I recommend it, but it is not a Blocker by the Blocker/Major/Minor definition (it does not break the core flow).

## What was tested

- Build: worktree `C:/Antigravity Projects/Worktrees/Books Arranger/inplace-m4b`, branch `codex/books-inplace-m4b`, HEAD `73215173a8b5c2f8324b89c34a06e470cee4b3a3`, committed and pushed, tree clean (the only untracked file was Senua's code-review report; mine is also untracked). Build `dist/builds/b2d468ea-74f7-4085-b620-8ba9c0c96ee4/win-unpacked`.
- Pins re-checked before starting: `dist/release-artifacts.json` raw SHA-256 matches the value above; installer SHA-256 `310f0d037ac7d75987eb121b04193a0996ebab07b0a0ccab74ca06c6c0232c56` matches Ender's note; all 271 payload files in `win-unpacked` match the manifest hashes (0 missing, 0 mismatched, 0 extra); `resources/backend/VERSION` reads 0.21.0; `/api/health` reports 0.21.0. The installer was never run.
- Isolation: all data under `C:/baqa21/` (short path; the app's own Windows path-length guard refuses outputs under the deep scratchpad). The Electron launch used `--shell-profile`, `--data-dir`, `--roots-json`, `--port=5212`, `--catalog-mode=new`, `--show-inactive`, `--quiet-errors`. Never touched: the live DB, the installed app, Sergei's profile, `Z:\`, `Y:\`, the codex-books checkout, the qa-0.20.0 and electron-m1 checkouts, the studio-root dirty files. Sergei's installed-app process set was identical before and after (6 processes, PIDs 76176, 80628, 50580, 74992, 47064, 80020) and his 5210 listener (PID 80020) was untouched.
- Harness code: Ender's driver ran unmodified. Everything beyond it (kill matrix, service-level kills, changed-source matrix, edge cases, timing) is my own scripts under the evidence folder, run with the packaged Python against packaged bytes. They wrap product functions from outside; no product file was edited, nothing committed.
- No audio was played. No input was injected into any window.

## 1. Ender's scenarios on b2d468ea

| Scenario | Result |
|---|---|
| `inplace` (service end to end) | PASS, every expected line: `completed`, `existing_m4b_in_place_metadata_edit`, source gone from original path, driver byte proof (`free` reverted gives the original prefix) True, same volume True, cleanup completed (removed 1, no recovery copy), Converted 1 / Approved 1, journal `published`, copy flow on the twin gives the same SHA-256. |
| `compare` | PASS: tags, chapters, streams, cover SHA, full `-xerror` decode, PCM md5, duration all IDENTICAL to the copy flow; PCM md5 equals the untouched original; tags and cover differ from the original. My own `ffprobe` diff of the two outputs differs only in file name. |
| `fallback` | PASS: ALAC, keep-sources policy and foreign `:extra` stream each take `existing_m4b_audio_stream_copy`, original unchanged (bytes and mtime), journal empty, `:extra` stream kept. |
| `fallback` on the superseded build 955f1e71 (negative control) | Prints `DEFECT kept-sources-policy : edited IN PLACE ...`; journal `rolled_back` after the driver's undo. The control fires on the old build and not on b2d468ea, so the keep-sources check discriminates. |
| `crash` (two named points) | PASS: `appended` and `type_patched` killed with TerminateProcess; length 15260 to 17344; original not intact before recovery; after `recover_all` in a fresh process bytes and ns mtime identical; journal `intended` then `rolled_back`. |
| `rehash` | PASS: unchanged `{guard 4, pipeline 0, held 2}` completed; mtime-changed `needs attention: Source changed before working-space admission`, held 0; file-id-changed completes (held 1) and cleanup refuses `Reviewed original file identity changed or cannot be verified`. |

## 2. Beyond the note: crash, Pause and recovery

Fixture copies, packaged bytes, real `TerminateProcess` on the child unless stated.

- Kill matrix at all six fault points in `inplace_m4b.py` (`before_append`, `appended`, `before_type_patch`, `type_patched`, `checked`, `reacquired`): original restored identical (bytes, ns mtime, size) at every point. Journal before recovery: `intended` at the first four (so the intent is durable before the first byte), `written` at the last two; `rolled_back` after.
- Recovery from half-finished rollbacks: truncated-but-type-still-`free`, type-restored-but-tail-present, mtime moved by an outside process: all restored exactly. Running recovery twice is a no-op.
- Pause (stop flag) raised at each of the six points: `Paused` (an `InterruptedError`) is raised, original identical, journal `rolled_back`. This matches the CHANGELOG sentence "a pause ... restores the exact original".
- A reader opening the file mid-edit (handle held from the `checked` step, sharing READ and WRITE but not DELETE): the edit is undone (`rolled_back`) and the copy flow runs; original unchanged. A reader holding the file with FILE_SHARE_READ only before the edit: the book never goes in place and falls back; original unchanged.
- Other ineligibility cases the note leaves to unit tests, all fall back with the original unchanged and an empty journal: hard link (two names), read-only attribute, destination already exists.
- Real kills around the rename, whole `MergeService`, then a fresh service on the same catalog and Start pressed:
  - killed before the rename: file rolled back exactly; job `needs attention: Recorded output is missing, changed, or failed validation`. The copy flow gives the identical result at the equivalent point (control), so this is existing behavior, not a 0.21.0 regression; Retry is needed.
  - killed after the rename and after the journal `published` write: job completes, cleanup completes. Good.
  - killed after the rename but before the journal write: see M1.
- Hostile recovery states (contrived, see m2): foreign larger file at the path is left untouched; a corrupted audio byte, a deleted original and a replaced file all end `unresolved` and are never reported as rolled back.

## 3. Re-hash cut

Driver counts match the note (section 1). Extra variants, MP3 two-source book, source changed at two moments:

| Change | Before conversion (working-space admission) | After the output is built, before deletion |
|---|---|---|
| content flip, mtime moved | `needs attention: Source changed before working-space admission`, nothing published | job completed; cleanup `needs_attention: Source size, timestamp, attributes or alias layout changed/unsupported`; originals kept |
| bytes appended | same refusal | same cleanup refusal, originals kept |
| content flip, size AND mtime preserved (the fingerprint's blind spot) | caught anyway: `Copied bytes do not match the approved source/output hash`, nothing published | job completed; cleanup `needs_attention: Original bytes differ from reviewed sources` (full hash at the removal proof, held 1); originals kept |
| unchanged baseline | completed, cleanup completed, hashes `{guard 4, pipeline 0, held 2}` | |

So a change before deletion still blocks in every variant, including the one the fingerprint cannot see. For a single M4B the same instrumentation shows: in-place 3 review hashes + 2 held read passes (hash-and-plan, byte proof) and no removal-proof hash; copy flow 3 review hashes + 3 held passes + 1 removal-proof hash.

## 4. Apple Books readiness (files read only; no playback)

Fixtures: the note's tiny AAC M4B (moov at end); a 120 s noise-audio M4B with the moov at the FRONT (faststart, the layout of 27 of the 30 real sources the design doc sampled), 40 chapters, JPEG cover, Cyrillic title/author/path, approved cover PNG; a moov-at-end variant with 12 chapters and an approved JPEG cover. Each was run through both flows with identical manifests.

- The in-place output and the copy-flow output are byte-identical on all six fixtures (these three plus the three timing fixtures; same SHA-256). So everything below holds for both flows, and the structure is exactly what the copy flow has published since v0.16.0.
- Structure (my own box parser): `ftyp`(M4A, compat M4A isom iso2), `free`, original `mdat` at its original offset, the old moov re-typed `free`, one live `moov` appended at the end. Exactly one `moov`. Every `stco` entry points inside the `mdat`. Top-level boxes tile the whole file. Original `mvhd`, audio `trak` and chapter text `trak` bytes are carried over; `tref/chap` resolves to track 3 (`text` handler).
- `ilst`: `(c)nam, (c)ART, (c)alb, (c)too, (c)cmt, (c)gen`=Audiobook, `covr` (PNG type 14, or JPEG type 13 when the approved cover is JPEG), `aART`, `stik`=2 (audiobook), `(c)grp`, `soal`, `trkn`. Cyrillic is valid UTF-8 and ffprobe reads it back. Chapters: both `chpl` (count 40 and 12) and the QuickTime text track are present. ffprobe `-show_format -show_chapters -show_streams` output is identical to the copy flow's apart from the file name.
- Full decode of original, in-place and copy-flow outputs (to a hash, no playback) gives the same PCM md5 on both realistic fixtures.
- ffprobe/ffmpeg warnings (`stream 0, timescale not set`, `Unsupported codec ... stream 1`) appear identically on the untouched originals; they come from the fixture's chapter text track, not from the edit.

What an Apple player might handle differently (informational; all identical to the copy flow, none introduced by 0.21.0, none verified on a device):
1. Moov at the end: a book that had its moov at the front loses its faststart layout. Local files are fine; streaming-style readers need an extra seek.
2. The old moov stays inside a `free` box: old tags and the old cover remain in the file (raw `covr` appears twice). Compliant parsers skip it; a tool that scans bytes for `covr`/`ilst` could see stale data. File grows by the size of the new moov.
3. Brand is `M4A ` with `.m4b` extension, not `M4B `; Books relies on extension and `stik`=2. Not tested on a device.
4. Chapter track ids are 1 and 3 (no 2). Harmless.
5. The device field remains "Apple Books sync not checked", which is honest.

## 5. Timing (fixtures only, local C: disk)

Method: the real `MergeService` with Ender's stub research, one book per run in its own fresh library. Clock starts at the approve call and stops (a) when the job reaches `completed` and (b) when queue and source cleanup are idle. The copy flow is the same build with `inplace_m4b.offered()` patched to False from outside, so it also benefits from the re-hash cut; it is not the 0.20.3 build (I was not allowed to touch the qa-0.20.0 checkout). Modes alternated. Both modes publish the same bytes (same output SHA-256 per size). Times include the approve call (1.4 to 3.1 s). Sergei's live app was running on this machine, so expect a few percent of noise.

| Fixture | Audio | Size | Copy flow, job / all done | In-place, job / all done | Speed-up (all done) |
|---|---|---|---|---|---|
| S | 2 min | 3.4 MB | 6.8 / 8.8 s (n=2) | 4.8 / 6.1 s (n=2) | 1.4x |
| M | 30 min | 50 MB | 15.3 / 18.7 s (n=2) | 6.0 / 7.8 s (n=2) | 2.4x |
| L | 3 h | 301 MB | 59.9 / 68.9 s (n=1) | 12.9 / 16.9 s (n=1) | 4.1x |

The saving grows with book size, as expected. These numbers understate the benefit on Z:, where the copy flow's full network copies and recovery copy do not exist on this local disk; I could not measure that and did not touch Z:.

## 6. Shell smoke (packaged unpacked app, isolated)

| Check | Result |
|---|---|
| Launch, positive control | Launcher stayed alive (a collision with Sergei's lock would exit code 0 at once). Only port 5212 bound (engine PID 74368). |
| Shows 0.21.0 | Window title `Books Arranger`; header badge `v0.21.0` (captured with PrintWindow, no activation); `/api/health` version 0.21.0; Source 1 shows the isolated library path. |
| Focus | Foreground stayed `explorer.exe` ("claude - File Explorer") the whole time. Two pollers at 100 ms (75 s covering launch and close, 40 s covering quit): 0 foreground changes to the app. |
| Close window | WM_CLOSE posted to the main window (what the title-bar X sends): window `visible=False`, all 7 processes still alive, engine still listening and healthy. |
| `--quit` (second launch, same `--shell-profile`) | Exit code 0. PIDs before: 56664, 46864, 74368 (Python) and 38272, 41396, 17252, 47988 (`Books Arranger.exe`). After: none; all gone within 6 s (my own focus poller, which runs the packaged Python, outlived it by a few seconds and then exited). Port 5212 free; `web-instance.json` absent; stderr empty. |
| Sergei's app | Process set identical to the pre-test snapshot; 5210 listener unchanged. |

I did not click the tray menu Quit: Sergei's installed app has its own identical tray icon, which the 0.20.3 note says makes a GUI tray Quit ambiguous. `--quit` runs the same `requestQuit`.

## 7. Gate re-run at 7321517

One run, MP3 fixture env (`BOOKS_MP3_REAL_FIXTURE`, fixture SHA-256 `e2deceb3...`), `scratch/0` and `scratch/1` confirmed absent first, started detached and polled so the 600 s tool limit could not interrupt it. Result: `BOOKS_INTEGRATED_CHECKS_PASS`, 1255 Python (batch 0: 686 of 686; batch 1: 569 of 569; 0 skipped, 0 failures, 0 errors) and 57 Node, about 373 s. `test_sources_kept_by_policy_are_never_moved` ran and passed. Worker copies moved to the evidence folder as `futaba-0.21.0-worker0` and `futaba-0.21.0-worker1`; no gate process left running; worktree still clean apart from untracked docs.

## Findings

### Blocker

None.

### Major

**M1. Any failure or crash after the OS rename but before the journal write leaves source cleanup permanently refused.** Status: open.
- Symptom: the book is correctly published and the job is `completed`, but its source cleanup sits at `needs_attention: In-place move receipt is missing; nothing retired`, the queue reads `Needs attention`, the book is not counted as Converted, and pressing Start (after a restart too) does not clear it. The message adds "Remaining originals and temporary files are preserved for recovery", which is untrue: there is no original left. No in-app remedy found. No data is lost and other books are unaffected.
- Repro A (no crash; the exception class `native_io.rename_no_replace` raises when its post-rename proof fails): `futaba-0.21.0-twobooks.py ... --inject`. Two eligible M4Bs; the first rename runs for real and then raises `RenamePostconditionError`. Result: book A job `completed`, cleanup `needs_attention` as above; book B completes and cleans up normally; queue `Needs attention`, `converted_total 1`, `approved_total 2`. Control run without `--inject`: both complete, Converted 2.
- Repro B (real kill): `futaba-0.21.0-svccrash.py orchestrate --points after_rename --peek 60 --resume`. The child parks right after the real rename, is killed with TerminateProcess, a fresh service starts on the same catalog and Start is pressed. Same stuck cleanup. At `--points after_journal` (kill after the `published` write) cleanup completes. With the copy flow forced (`--copyflow`) a kill after its rename completes cleanly, so the stuck state is specific to the in-place path.
- Cause (code read): recovery rewrites such a row as `published` with only `recovered_move` (`inplace_m4b.py:362-363`), but cleanup requires a `rename` receipt (`published_move`, `inplace_m4b.py:390-399`; `_retire_moved`, `source_cleanup.py:410-416`), and the cleanup resume list does not include this reason (`source_cleanup.py:300`).
- Likelihood: the kill window is only a few metadata calls, but the same state follows any exception after the rename, and the design explicitly relies on that path ("recovery and _settle prove the move"). Sergei runs Bitdefender and the real target is an SMB share, which I could not test.
- Suggested fix direction (Ender's call): rebuild the receipt from the destination's recorded identity and size and SHA in `reconcile`, or let `_retire_moved` accept `recovered_move` after verifying the destination; add a real-kill test; fix the message.

### Minor

**m1. A download marker (Zone.Identifier stream) is lost when the edit is rolled back or recovered after the marker was removed.** Status: open. This deviates from "restored exactly" and from the CHANGELOG sentence, though only for that stream; audio bytes, size and ns mtime are exact.
- Repro: `futaba-0.21.0-motw.py`: source with `ZoneId=3` marker. Kill at `checked` (marker not yet removed): restored with marker intact. Kill at `reacquired` (marker removed at `inplace_m4b.py:305-309`): after recovery bytes and mtime are exact, marker gone. The same happens when the in-place edit is undone after success (`futaba-0.21.0-edge.py`, `motw` case: streams `['::$DATA']` after undo).

**m2. Crash recovery changes a file before proving it is the original when the file ID matches.** Status: open, contrived.
- Repro: `futaba-0.21.0-xcrash.py` cases h6 and h7. After a kill at `type_patched`, overwrite the same file in place (same file ID) with foreign bytes of the original size (h6) or the edited size (h7). Recovery writes `moov` over 4 foreign bytes and resets the mtime (h6), or truncates the foreign file to the original size (h7), and only then reports `unresolved: The original bytes could not be proven after the undo`. A replacement by rename (new file ID) is hash-checked first, and a larger file is left untouched (h5). Code: `_undo` hashes only when the identity differs (`inplace_m4b.py:185-192`).
- Related observation: an original deleted after a crash ends `unresolved` forever (h8); how the UI presents that was not checked.

**m3. Progress wording for in-place books is wrong.** Status: open, code read only (not observed in the GUI, since the UI path needs live research). The in-place path reports the stages `creating` and `publishing` (`inplace_m4b.py:287`, `merge_service.py:2685`), which the page labels "Encoding audio" and "Copying audiobook to the library" (`web/app.js:472`). Nothing is encoded or copied.

**m4. Design promise not implemented: "read back unbuffered from the NAS".** Status: unverified, cannot be tested without Z:. Design doc section 3 says the byte proof reads the appended tail unbuffered. `VerifiedFile` opens with `CreateFileW(..., share 1, ..., flags 0x00200000)`: no `FILE_FLAG_NO_BUFFERING` and no write-through (`native_io.py:282`), and the writer only calls `FlushFileBuffers`. On SMB the read-back may be served from the client cache, so it proves less than the document claims. Needs Senua or a NAS check.

### Observations (not findings)

- A kill during publishing leaves the job `needs attention: Recorded output is missing, changed, or failed validation` until Retry; the copy flow behaves identically (control), so this is existing behavior.
- The in-place hold (READ and DELETE, deny-writers) makes the file unreadable to other programs for the few seconds between the edit and the rename; the library file is a valid MP4 throughout.

## Not verified

- Anything on a real network share (`Z:`, `Y:`): SMB rename-by-handle, flush durability, share modes, cache behavior (see m4). First NAS book should be watched by whoever owns that run; I am not suggesting Sergei test it.
- Apple Books or any Apple device (by design); tray-menu Quit by mouse; the optional UI check of a manually approved M4B (section 8 of the note); in-place approval through the real UI (needs live public research, so I drove `MergeService` with the stub).
- Books over 4 GB (`co64`), fragmented MP4, multiple `mdat`: no such fixture was generated; the planner is the existing, already byte-proven one.
- "Library offline" recovery.

## Cleanup status

Worker copies moved to the evidence folder as asked. The isolated folder `C:/baqa21/` (about 1.7 GB, 2,481 files, 862 folders: fixtures, masters and per-run copies, no source of Sergei's) was NOT removed. I tried the studio's disk-hygiene planner once (plan only, no deletion); it refused: "Container must be strictly inside the studio (C:\Antigravity Projects\Studio Illuminati) or the system temp directory (C:\Users\AnGeLZzZ\AppData\Local\Temp)." Hand-writing about fifty literal removal commands would sidestep that method, so I stopped. Jane: please decide how to remove `C:/baqa21` (or authorize it). Nothing from my session is running: no process from either build, ports 5211 and 5212 free.

## Evidence (all in `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/64106cea-b39e-4987-9571-6ad97339dc8a/scratchpad/shared/`, nothing deleted)

- Pins and payload: `futaba-0.21.0-payload-verify.txt`, `futaba-0.21.0-verify-payload.mjs`, `futaba-0.21.0-baseline-procs.txt`, `futaba-0.21.0-sergei-procs-after.txt`.
- Note scenarios: `futaba-0.21.0-s1-inplace.log`, `-s2-compare.log`, `-s3-fallback-b2d468ea.log`, `-s3-fallback-NEGCONTROL-955f1e71.log`, `-s4-crash.log`, `-s5-rehash.log`.
- Crash, Pause, recovery: `futaba-0.21.0-s4b-xcrash.log` (+ `-xcrash-rerun.log`), `-s4c-svccrash.log`, `-s4c-svccrash-peek.log`, `-s4c-svccrash-resume.log`, `-s4c-svccrash-postcondition.log`, `-s4c-svccrash-copyflow-baseline.log`, `-s4d-pause.log`, `-s4e-twobooks.log`, `-s9-edge.log`, `-s9b-motw.log`.
- Re-hash: `futaba-0.21.0-s5b-rehash-changed.log`, `-s5c-m4b-hashcounts.jsonl`.
- Apple structure: `futaba-0.21.0-s2-boxdump.txt`, `-s6-fixture2.log`, `-s6-boxdump-faststart.txt`, `-s6-apple-checks.txt`, `-s6-ffprobe-faststart-inplace.json`, `-s6-ffprobe-faststart-copyflow.json`, `-s6b-fulldecode.txt`, `-s6c-warnings.txt`.
- Timing: `futaba-0.21.0-s7-timing.jsonl`, `-s9c-special-name.log` (hostile folder name `[ ] & # ’` and Cyrillic: in-place completed, same output SHA).
- Shell: `futaba-0.21.0-s8-focus-watch.log`, `-s8-focus-watch-quit.log`, `-s8-procs-after-launch.txt`, `-s8-procs-after-close.txt`, `-s8-windows-open.txt`, `-s8-window-open2.png`.
- Gate: `futaba-0.21.0-gate-run.log`, `futaba-0.21.0-worker0/`, `futaba-0.21.0-worker1/`.
- Helper scripts (kept): the `futaba-0.21.0-*.py`, `.mjs`, `.sh` files in the same folder.

Pattern alerts:

1. Messages that disagree with the state under them, now a fourth instance across three builds (0.20.2 and 0.20.3 bulk-retry wording and counts, per the 0.20.3 report). In 0.21.0: M1's cleanup text says "Remaining originals and temporary files are preserved for recovery" when none exist, and m3's "Encoding audio" and "Copying audiobook to the library" for a path that does neither. Same annoyance in new clothes. Recommended disposition: fix (Judy wording pass, Ender implements); M1's message should change with M1's fix. Disposition: pending Jane.
2. A test file known to cover a shipped fix is still outside the gate. The 0.20.3 report flagged that `tests/test_refused_retry.py` (the three `BulkCapabilityTests`) is not in the gate; at 7321517 `scripts/check-desktop.mjs` and `scripts/python-check-batches.mjs` still do not name it (0 matches). Second build in a row. Recommended disposition: fix (one line for Ender), or an explicit accept recorded by Jane. Disposition: pending Jane.
