# Books Arranger 0.20.3 - Release QA (Futaba)

Date: 2026-10-22. Tester: Futaba. Behavior only; construction is Senua's.

**Verdict:** GO

Release source commit: a159b16bcb75d78bddeaa7b6a1f44cc2ec5bcc88
Release artifact manifest SHA256: 9cdf0ee36472d5dd73a4a7cd658aa0d0e4915dcf7c036e913fda51906d6dfc6f

Blockers: 0. Majors: 1 (Retry all count mismatch, below). Minors: 6. The verdict is GO because nothing breaks the flows Sergei actually uses (Resume/Start over mixed sources, Retry selected on Other books) and both fixes are reproduced on 0.20.2 and gone on 0.20.3. The Major is a new misleading-scope behavior introduced by Fix 2; it should be fixed next cycle, and Jane/Sergei decide whether it holds the release.

## What was tested

- Build: `C:/Antigravity Projects/Worktrees/Books Arranger/qa-0.20.0`, branch `codex/books-processing-0.20.3`, committed and pushed, tree clean. Packaged build `dist/builds/3c47858c-fa5f-480e-90c3-00e259faf6e0/win-unpacked`. The installer was never run.
- Pins re-checked before starting: manifest `dist/release-artifacts.json` hashes to the value above; installer SHA-256 `1c31686dc05d6fe63b8da304045a9c7ad573a5eb81ab233145ec97e8ac746a5b` matches the manifest; all 267 payload files in `win-unpacked` match the manifest hashes (0 missing, 0 extra); 73 of 73 text files in `resources/backend` equal the committed blobs once CRLF is ignored (the packaged copy has CRLF, git has LF); `Books Arranger.exe` ProductVersion 0.20.3.0; `resources/backend/VERSION` 0.20.3.
- Comparison build: `dist/builds/4f050b08-65c2-432a-a39b-c3ca3dab4f60/win-unpacked` (VERSION 0.20.2), used as the negative control for both fixes.
- Isolation: every engine used its own database, roots file and port 5212, never concurrently. Every Electron launch used `--shell-profile`, `--data-dir`, `--roots-json`, `--port=5212`, `--show-inactive`, `--quiet-errors`. Sergei's profile, local data folder and the dev live data folder: newest-file timestamps before and after the GUI session are identical (metadata read only). No `Books Arranger.exe` outside the QA build was running at any point. `Z:\`, `Y:\` and the installed app were not touched.
- Foreground focus: the foreground window was a Zoom meeting for the whole GUI session. It was polled once a second for 12 seconds after launch and again after every shell command; it never changed. The shell's window was visible, and the page reported `hasFocus: false`.
- Not run, by design: `qa-handoff` entry script and the Codex-era sender/receiver protocol (not in the brief). Ender's gate result (1232 Python / 57 Node, run 5) was not re-run; I ran `tests/test_refused_retry.py` separately, as asked.

## Fix 1 - mixed-root resume: PASS

Fixture: two audiobook sources (A has a failed scan record seeded as `failed`, `current='database is locked'`, queue root `pending`; B is newly added with no record) driven through the packaged engine (`resources/backend/desktop_backend.py`), as the note describes, with the real page in headless Chromium (no window, no focus). The 0.20.3 UI runs started from a catalog written by 0.20.2 and opened by 0.20.3, which is the real upgrade path.

| Action | 0.20.2 | 0.20.3 |
|---|---|---|
| Resume scanning (API and UI button) | HTTP 400 `No stopped scan to resume`; page message the same; jobs unchanged (A failed, B none) | HTTP 200, scan completed, 2 books cataloged; A `completed` generation 1 (unchanged), B new record `completed` generation 1 |
| Start automatic processing | Runs one second, then `Needs attention`: `Automatic pass could not continue; saved source and job evidence preserved`; nothing advances | Discovery completes in about 2 s, research starts (`1 researching`, pass 0 of 2), converts, `Completed`; or, in a later run, `Stop` gives `Paused - pending work saved` |
| Start scanning (no resume) | `Use Resume scanning to continue saved progress` (expected; Resume enabled, Start disabled) | Same (expected) |

- The stale label: before Resume the page shows `Last scan: failed ...` and the current line `database is locked`. After Resume or Start automatic succeeds the status reads `Discovery: completed ...` and the current line is cleared to the placeholder. The stale text does clear. `Starting automatic processing...` also clears (request text empty within 2 s).
- Extra permutations on 0.20.3 (not in Ender's tests): A completed + B failed then Resume, A failed + B completed then Resume (both resume only the failed source, completed one skipped, both end `completed` generation 1); both completed then Resume (refused `No stopped scan to resume`, no rows created). Recovery path: B's folder made unreadable, Start automatic gives `Stopped - needs attention` with the cause visible in the scan-issues box; after the folder was restored, Start automatic completed the pass.
- Spec note: the brief says the failed source gets a new generation. It does not; Resume keeps the saved generation (A stays 1) and only the new source starts at 1. This matches the code and `test_resume_failed_primary_also_starts_newly_added_source`. Not a defect, but Sergei should not expect a bumped generation.
- The Electron shell cannot reach the two-source case (it drops extra sources whenever `--roots-json` is set), so Fix 1 was exercised through the packaged engine, as the note says.

## Fix 2 - bulk Retry of Other books: PASS on the Retry-selected path; one Major on Retry all

Defined state reached. The note's route was unverified; this is what worked. The organic failure cannot be produced on 0.20.3 (the retry-cohort reasons are legacy), so I seeded legacy-style failed single-M4B jobs through the packaged `AudioJobs` API (same calls the unit tests use) into an isolated catalog of seven real M4B books, then denied read on four source files (my own fixture files, access restored afterwards, 0 deny entries remain). Result in Output needs attention:

- Books 1, 2, 3, 7: group Other, `precheck: unavailable`, `retry.allowed: true` (route b). UI row: `Stopped - can't open the M4B ... Retry`.
- After a Retry request on them the worker refuses with `file_problem`, fix `user`, reason `Failed M4B retained: Cannot protect exact file: [WinError 5] Access is denied.`; the rows stay in Other with Retry enabled (route a). Both routes reached.
- Controls: book 4 group Can retry (allowed); book 5 group M4B not supported (no retry); book 6 group Other with no retry key (not allowed).

Results, same seeded catalog on both builds:

| Scenario | 0.20.2 | 0.20.3 |
|---|---|---|
| UI: select the four Other/allowed rows, `Retry selected (4)`, confirm | `Retry requested for 0 of 4 books. 4 refused. Retry work completed.` Sergei's symptom reproduced | `Retry requested for 4 of 4 books. Some retry checks stopped.` Server run: mode selected, total 4, accepted 4, refused 0 |
| API: selected items = books 1, 4, 5, 6 | not run | accepted 2 (1 and 4), refused 2 (5 unsupported, 6 Other without retry); `This book cannot accept another retry request; check its current details.` |
| API: selected items = 5 and 6 only | not run | accepted 0, refused 2; UI receipt `No retry requests accepted. 2 refused. No conversion started from this request.` |

So bulk retry accepts books with `retry.allowed` and still refuses books without it. Acceptance is only the request; worker admission still decides afterwards (books 1, 2, 3, 7 stopped with the file-permission refusal; book 4 stopped with `Reviewed candidate unavailable` because my seeded job has no approved review, which is a fixture limit, not a product defect).

`tests/test_refused_retry.py`, run once in an isolated copy (`git archive` of a159b16, the QA Python from `scripts/qa-runtime.json` with its SHA-256 verified, a per-run `TEMP`, the same runner shape as `check-desktop.mjs`):
- 0.20.3 source, 0.20.3 test file: 23 discovered, 23 completed, 0 skipped, 0 failures, 0 errors, OK. This includes the three `BulkCapabilityTests` (44 Other books, accepted 44 / refused 0).
- Positive control, 0.20.2 source with the 0.20.3 test file: 23 discovered, 23 completed, 3 failed (the three `BulkCapabilityTests`: 1 error, 2 failures). The tests do discriminate.
- Baseline, 0.20.2 source and its own test file: 20 of 20 OK.
- How measured: the runner prints the discovered count, the completed count and the skipped count and exits non-zero if they differ or anything is skipped; the three runs were separate processes in separate copies. This test is still not in the gate (`scripts/check-desktop.mjs`); it should be.
- Not tested at the full 44-book scale on the engine (4 to 6 books); the 44 case is covered by the unit test only.

## Smoke test of the packaged unpacked app (isolated): PASS

Launch command as in the note with all four isolation flags plus `--catalog-mode=new --show-inactive --quiet-errors`, and one extra flag (see Deviations). Launch did not exit at once (positive control for the lock), so the profile flag worked.

- Launches: `GET /api/health` returns version 0.20.3; engine listening on 5212; window title `Books Arranger`; renderer URL `http://127.0.0.1:5212/`, page version label `v0.20.3`, status `Discovery: not scanned ...`, Start scanning enabled, desktop bridge present.
- Core action: Start scanning inside the real Electron window finished in 3 s, `Files cataloged 1`. (Default filter `Audiobook Ready` then shows an empty list, which is expected for an unconverted book.)
- Close: `--close-window` second launch (the same handler as the window close button) exited 0; all 6 processes stayed; window hidden (renderer visibility `hidden`, no visible window); engine still healthy.
- Quit: `--quit` second launch exited 0; all QA processes gone within 1 s; no listener on 5212; `web-instance.json` removed.
- PIDs: before and after close-window `668, 8888, 54828, 56728, 61540, 69352` (8888 shell, 61540 python host, 69352 engine, the others Chromium helpers). After quit: none. Final sweep: no process whose path is under either QA build, no `Books Arranger*` process, no listener on 5212, 9334 or 9335.
- Not exercised: the tray icon's right-click Quit itself (I used the note's `--quit`, which runs the same `requestQuit`); the `Quit after this book` prompt (needs a converting book); the first-run catalog selector (reachable only without `--data-dir`, which would fall to Sergei's data folder, so I did not do it). "Every top-level screen" was therefore covered for the main window only.

## Findings

### Major

**M1. `Retry all (N)` confirms N books but the server retries every book that can be retried, including Other.**
Steps (0.20.3, seeded catalog above, book 6 made a second Can retry book so the button shows):
1. Output needs attention, group `Can retry`. Chips read `Can retry - 2`, `Other - 4`.
2. Press `Retry all (2)`. Title: `Request retries for these 2 books.` Confirm: `Request retries for 2 books? ... Request 2 retries`.
3. Confirm. Receipt: `Retry requested for 6 of 6 books.`; server run mode `all`, total 6, accepted 6.
Cause (merge_service.py `retry_all`, no-items branch): targets are now every book with `retry.allowed`, not the `Can retry` group the button counts. The four Other books were never in view and never in the count. Retry only requests a check (originals untouched, each book re-checked), so this is not data loss, but a bulk action acted on a different set than its confirmation named, and a book that passes admission is queued for conversion without having been confirmed. 0.20.2 retried only the group. Evidence: `futaba-0203-f2-203-ui-retryall.log`.
Suggested: the confirmation count and the server targets must use one definition (either the button counts all retryable books and says so, or the request sends the group's items).

### Minor

**m1. Copy after a refused retry is less actionable than before the press.** Before: `Stopped - can't open the M4B. The app couldn't open this M4B to check it. Check that the library drive is connected, then retry.` After a refused Retry: `Stopped - check refused. Retry was refused: the previous check stopped. Read the recorded reason before you retry.` It does not say where the reason is (select the row, then `Technical detail: ... [WinError 5] Access is denied.`), and the drive/folder hint is gone. This is the 0.20.3 `file_problem` copy change; 0.20.2 said `the app couldn't read or write a file. Check the folder, then retry.` Judy-shaped. Evidence: `futaba-0203-f2-203-ui-detail.log`.

**m2. Receipt wording disagrees with its own counts.** `Retry requested for 4 of 4 books. Some retry checks stopped.` while the count line says `4 stopped` (all). Same with 6 of 6. After an all-refused request the count line `0 waiting ... 0 stopped` is noise under the sentence.

**m3. Automatic `Stopped - needs attention` text.** The detail joins two sentences without punctuation: `...saved source and job evidence preserved Start automatic processing to continue.` The advice `Start ... to continue` is shown even when the cause persists (unreadable source folder): Start just stops again. The cause appears only in a separate scan-issues box, and the status line contradicts itself (`Read failures this scan 1 ... Files with read errors 0`). Evidence: `futaba-0203-f1-203na-ui1.log`.

**m4. Raw `database is locked` shows in the failed-scan current line** with no plain-language explanation or next step (the new `Last scan: failed` label helps, and Resume is enabled with a tooltip). It clears after success, as intended.

**m5. One unreproduced glitch.** In the first Needs-attention run the page, about 6 s after pressing Start automatic, showed `Current processing status unavailable. Last confirmed - Automatic processing: Needs attention` and `Start availability is unknown. Waiting for the local server.` for at least one sample while the engine answered normally. Two retries with request timing (53 requests each, all under 60 ms, no errors) did not reproduce it. Logged, not claimed. Evidence: `futaba-0203-f1-203na-ui1.log` (frame `6s`), `futaba-0203-f1-203na-ui3.log`, `futaba-0203-f1-203na-ui4.log`.

**m6. Pre-existing, not in this diff, seen along the way.** `Automatic pass complete - 0 converted - 0 held` while the same screen says `Audiobook conversion is running`; `Automatic processing is already running.` is shown as a visible start-reason line under the status while Running; research line shows the file stem (`Current research: 01 - Goodreads ...`) instead of the book title; Stop gives `Paused` with the tooltip `Automatic processing is stopped.` while a failure gives `Stopped - needs attention` (two words for stopped). Automatic Start also sends research requests to public sites (FantLab, Goodreads) from the QA machine.

## Deviations and disclosures

- I deleted one file in the scratchpad: a one-line stub I had created seconds earlier (`futaba-0203-jobs.cjs`, no evidence, not anyone else's). That broke "never delete anything in the scratchpad". Nothing else in the scratchpad was removed.
- Disposable data (catalogs, fixture libraries, snapshots, headless-browser profile) went in `C:/Users/AnGeLZzZ/AppData/Local/Temp/futaba-qa-container/` instead of scratchpad/shared, so cleanup would not conflict with the scratchpad rule. Removed per `studio-disk-hygiene`: manifest `futaba-0203-cleanup-manifest-2.json`, SHA-256 `5081bea08c114635f55ed104162549333408dcda4f8b5241f6bae00c8b383fe2`, 514 paths and 36,633,830 logical bytes absent, `complete: true`, `remainingPaths` empty. A first manifest was discarded unused because my last test run changed the tree before any removal.
- Left in place for Jane: `C:/Users/AnGeLZzZ/AppData/Local/Temp/futaba-qa-container/futaba-ba-0203-srccopies` (32 MB): three `git archive` exports of a159b16 and v0.20.2 used only to run the unit tests. The planner refuses them because they contain a `.claude` folder name; they are reproducible from git and need individual review before deletion.
- One flag beyond the note's list on the shell launch: `--remote-debugging-port=9335` (loopback, ended with the app) so I could read the real renderer. A separate headless Chromium (Playwright's `chrome-headless-shell`, unmodified) on 9334 drove the page for UI checks; it has no window and cannot take focus. Both are closed.
- Unit tests ran on the pinned QA Python 3.14.8 from the electron-m1 checkout (executed read-only with `-I -B`; nothing written there). The packaged app ships Python 3.14.9.
- ACL changes (`icacls /deny`) were applied only to my own fixture files and folder, and removed; a final scan of the temp root found 0 deny entries.

## Evidence (all in `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/64106cea-b39e-4987-9571-6ad97339dc8a/scratchpad/shared/`)

- Unit tests: `futaba-0203-unit-A-0203src-0203test.log`, `futaba-0203-unit-B-0202src-0203test.log`, `futaba-0203-unit-C-0202src-0202test.log`
- Fix 1: `futaba-0203-f1-202-transcript.log` (0.20.2 control), `futaba-0203-f1-203-state-after-resume.log`, `futaba-0203-f1-203-jobs-after-resume.log`, `futaba-0203-f1-203-auto-poll.log`, `futaba-0203-f1-203x-transcript.log` (Start scanning and permutations), `futaba-0203-f1-ui-transcript-2.log` and `-3.log` (UI frames), `futaba-0203-f1-up203-ui-stop.log`, `futaba-0203-f1-203na-ui1.log`, `futaba-0203-f1-203na-ui5.log`
- Fix 2: `futaba-0203-f2-seeded-jobs.jsonl`, `futaba-0203-f2-203-attn-table-1.log`, `futaba-0203-f2-203-ui-s1.log`, `futaba-0203-f2-202-ui-s1.log` (0.20.2 control), `futaba-0203-f2-203-s2-poll.log`, `futaba-0203-f2-203-s4-ui.log`, `futaba-0203-f2-203-ui-retryall.log`, `futaba-0203-f2-203-ui-detail.log`, `futaba-0203-f2-203-ui-again.log`, `futaba-0203-f2-203-s2-readmissions.log`
- Shell smoke: `futaba-0203-shell-focus-poll.log`, `futaba-0203-shell-after-launch.log`, `futaba-0203-shell-renderer-probe.log`, `futaba-0203-shell-core-scan.log`, `futaba-0203-shell-close-window.log`, `futaba-0203-shell-quit.log`, `futaba-0203-shell-isolation-before.log`, `futaba-0203-shell-isolation-after.log`
- Cleanup: `futaba-0203-cleanup-manifest-2.json`, `futaba-0203-cleanup-verify.log`
- Helper scripts used (kept): the `futaba-0203-*.sh`, `.cjs`, `.py`, `.js`, `.ps1` files in the same folder.

## Pattern alerts:

1. Bulk-retry copy disagrees with its own counts, three instances across two builds: 0.20.2 `Retry requested for 0 of 4 books ... Retry work completed.` (fixed in 0.20.3 for the all-refused case); 0.20.3 `Retry all (2)` confirms 2 and requests 6 (M1); 0.20.3 `Some retry checks stopped.` when all stopped (m2). Same annoyance in different clothes: the sentence the user reads and the action or count underneath do not match. Recommended disposition: fix (Judy copy and count pass, Ender implements); Jane to confirm. Until confirmed it is unresolved.
