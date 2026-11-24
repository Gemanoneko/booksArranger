# Books Arranger 0.30.0: QA report (Futaba, 2026-11-19)

**Verdict:** NO-GO

Release source commit: 5dbba45336915df1cf058b3ea1550f324a95d3d5

Why NO-GO, in one paragraph: eight of the ten items pass on real fixtures, and Sergei's real complaint ("I can't exit") did not reproduce. Two findings stop this build. F1: item 5 (Brom) fixes cleanups that have not been refused yet, but the row Sergei actually has, already in Needs attention with "Persisted recovery ancestry changed", is not revived by anything (Resume, Retry cleanup, restart), so item 5 fails on the real-row shape. F2: the freshness cue is on most of the time on an idle app, against Sergei's answer 2 ("only when behind"). No Blocker. Nothing was lost or altered in any original file.

Pattern alerts: none

## 1. What was tested

| Field | Value |
|---|---|
| Tool, version under test | Books Arranger 0.30.0 (package.json still reads 0.29.0; Sully bumps after QA, expected) |
| Source commit | `5dbba45336915df1cf058b3ea1550f324a95d3d5` |
| Checkout the builder ran | `I:\AI Projects\Worktrees\Books Arranger\entry-030` |
| QA ran from | a `git archive` of that exact commit (pinned snapshot, not a live tree) |
| Delta since the last cleared build | the ten items in the brief (Docs/BooksArranger_0.30.0_UX.md; Brief 0.30.0 rows; Backlog bullets dated 2026-11-18) |

## 2. Same-build check (I did not re-run the entry check)

- Handoff HEAD `5dbba45336915df1cf058b3ea1550f324a95d3d5` equals the receipt's `@ <HEAD>`, and the receipt says `(dirty: N)`.
- The receipt line in the builder's log, read from `I:\AI Projects\Worktrees\Books Arranger\entry-030b-run\ender-entry.log` (one occurrence, last line of the run), is byte-for-byte equal to the handoff's line. This is the builder's receipt, not a run of mine:

  `Entry-check receipt v2: books-arranger v0.29.0 @ 5dbba45336915df1cf058b3ea1550f324a95d3d5 (dirty: N) [source:358409020f95e61c5962bb0c3cae7138f0fcc21cc9d17703d06a5d0143e8e14a; harness:1a7c07430d0e10dd7846df9ceb80100bd15d59d8aeef8a2310618c1222bcfc01; runtime:29c21c40220ffbf6ebcece9308cb3b017fda708a25362b04c8902b95b052646c; checker:4bae2cde4e4cdd2f22fb3060571730ec32fec1dd5403ea070086973b18b695e4] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a; personal-folders clean (5 subfolder notes)`

- `entry-exit.txt` is `0`. Context SHA-256 `context/context.json` = `7e13ff71dd43b378fb744e7338f72aa3385d32bb99f896f23dae14a4f27494d8`, equal to the handoff's.
- Builder's own evidence in that log: `npm run check` code 0; 13 Python worker batches whose "Ran N tests" lines sum to 2814 tests (the log carries no failure). Quoted, not re-measured.
- No installer or manifest was in this handoff, so no installer hash was compared.
- Personal-folder listing, copied from the receipt (listed only, never a failure; nothing deleted, moved or changed): `clean (5 subfolder notes)`, 7 folders and 11 drive roots watched:
  - SUBFOLDER D:\SteamLibrary | changed below the depth checked
  - SUBFOLDER E:\SteamLibrary | changed below the depth checked
  - SUBFOLDER F:\SteamLibrary | changed below the depth checked
  - SUBFOLDER H:\SteamLibrary | changed below the depth checked
  - SUBFOLDER I:\SteamLibrary | changed below the depth checked

## 3. Method, and what stands in for the real thing

- Real `BrowserServer` over HTTP (the Quit and restart checks ran the engine as a separate process, started the way the shell starts it), real `Inventory` scans, real ffmpeg audio with Cyrillic tags, the real conversion pipeline. Page text: the real `web/app.js` in a VM with the repo's DOM stand-ins, fed real captured `/api/state` payloads.
- Four QA slices ran in parallel (A items 1-3, B items 4/5/6/10, C item 7, D items 8-9). Each worked in its own folder under `I:\AI Projects\Worktrees\Books Arranger\qa-030-*`.
- Stand-ins, all stated: system Python 3.14.10 and the WinGet ffmpeg 8.1.1 instead of the pinned runtime; public sources stubbed (no network); background passes and retention started by hand in the harness (`start_retention` patched out); elapsed time simulated by clearing limits and `retry_at`; file removal under the same QA disposition owner the gate gives its workers (plain Python cannot remove files without it).
- Source integrity: I diffed the source copies of slices A, B and C against the pinned snapshot (`diff -rq`, scratch excluded): no difference. Slice D's folder was deleted before I could diff; D reports it never edited its source. The `patch_*` scripts only edit each slice's own scenario scripts.
- Machine load: slice A measured CPU before and after every timed run, 55 to 83 % across 32 cores throughout (busy machine, so the Quit numbers are an upper bound).
- Scope guard held: nothing on C:, no port 5210, nothing of Sergei's installed app, `I:\Books Arranger` or `Z:` touched, no Electron, no mouse, no focus, no registry writes. The outbound network was blocked for slice A and its blocked-attempt log was empty.
- A damaged-parts delta (Sergei's 2026-11-19 ruling, fix on main `1a0c031`) is not part of this build and not counted against it. For the record, the current build says: "…Press Reopen draft to replace that file or leave it out."

## 4. Results per item

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Jobs panel: a row per job, named, with a bar; Waiting names its blockers; freshness cue; three counts | PASS on real payloads, with F2 and layout not tested | Brom replay: engine sent `cause: conversion_queue, count: 5`; in 28 of 28 frames the book row, the Waiting item and the queue strip all read "It runs when the whole conversion queue (5 books) finishes." with a Converting row on screen. 5 of 5 real queued actions matched row to Waiting line, including "1 ahead. ", "2 ahead. ", "5 actions waiting, one at a time. First: …". 13 of 13 forced causes matched Judy's table; "app is free" never showed for a known cause. 3 paused cleanups + 1 queued conversion read "1 book waiting to convert · Cleanup paused for 3 books", never "4 books". 508 waiting cleanups showed as one item ("Cleanup waiting: 508 books"), 4 showed as four. Cue at 45 s and "(as of …)" present; at 9 s nothing; "Refreshing…" only while refreshing; unread line hidden after 1 poll, shown after 3 s ("Nothing running that could be read."); a conversion row under 1 s not drawn. Over 1,000 frames: every row drawn with one bar and correct split counts. Page checks were seen to fail on wrong input ("5 books waiting" for 4, a dropped row). |
| 2 | Queued actions survive a restart | PASS | 5 presses queued behind a real 600-file scan (Retry cleanup, Delete, Scan again, Approve, Start scanning), each 202 with blocker `scan`; Quit 0.49 s; all 5 saved in order; back after restart in order. Without paused conversions they ran in order: Retry cleanup done; Delete refused `not_offered` (its file was replaced while closed); Scan again done; Approve done and its job stayed paused (a restored press did not start the queue). Engine killed on purpose with a 6th press: all 6 back, no duplicates, dead owner record set aside. A queued Move is never saved (cleanup/move/delete/move/approve saved 3: cleanup, delete, approve). Update and Quit confirms no longer say actions are dropped. |
| 3 | Quit finishes in about 2 s, jobs paused, research idle ("I can't exit") | PASS, did not reproduce | Quit request to process exit, 1,572-book catalog, jobs paused, research idle: 0.32, 0.58, 0.53 s. Same with a 13-15 s status computation running and the page polling: 2.71, 2.59, 2.61 s. 6,288-book catalog, computation running: 4.17, 4.40 s. Every run exit 0, no forced-exit message, port closed, process gone, nothing killed. `/api/desktop/status` answered in 3-81 ms and listed `waiting_for`. Quit during a book's conversion waits for it by design, names it (`[{conversion, Дюна}]`), refuses presses with 409; `/api/desktop/stop-now` exited in 0.5 s and the book returned paused in the queue. Quit during a real 160 s Approve showed `waiting_for: approval` and exited within 5 s. Not reproduced here: a press still running after 30 s ending `blocked` (only Ender's `test_quit_bound`, with a fake slow press, covers it). |
| 4 | Gone-source check runs in retained-runtime mode | PASS | Sergei's shape (deleted `Ужасы и трэшатинка. Сборник рассказов`, 12 job-less books). Pass off: 26 listed, 21 in Needs attention. Start pass: All candidates 26 to 10 (16 removed: the 12 plus 4 gone held/changed), Needs attention 6. After a scan a deleted book left within 1.0 s of the scan ending. Check again removed exactly the book deleted meanwhile. Controls: books with a job stayed (including a converted book whose folder is gone, and a retained job); root missing keeps all 9; root answering empty keeps all 9; files returned lists the book again; library files byte-identical apart from the test's own deletions; retained staging dir (3 files) and retained job row unchanged. Limit: no positive control showed housekeeping reaching an ordinary job. |
| 5 | Brom-style cleanup passes after two storage moves | FAIL on the real row (F1); PASS otherwise | Two moves replayed through the app's own `MovesReplay`. Cleanups recorded at the old data folder and not yet refused completed after Resume: a paused-midway one (4 originals, 4 copies, 0 of 4 left) and a waiting one (3 originals, 0 of 3 left); recovery copies purged at once (existing design, `HOURS=0`). Negative controls refused with originals kept 3 of 3: a forged recorded ancestry ("Persisted recovery ancestry changed") and a recovery root replaced after the moves. The row Sergei actually has is not revived: see F1. |
| 6 | Refused-after-move jobs return through Retry all, then pass | PASS | 5 books approved at the old data folder, seeded with "Source changed — review required". Guard on plain text comparison (probe-only patch, as positive control): 0 of 5 pass. 0.30.0 comparison: 4 of 5 pass, and the genuinely changed source stays refused. `POST /api/audiobook/retry-all` 202 with 4 targets; the changed job is not targeted. 4 of 4 converted with files on disk, one conversion row at a time. Panel row through the real `app.js`: `Retrying all books | 1 of 4 books | One book at a time`. |
| 7 | Series back-fill and sorting fixes | PASS (7a-7g), 3 Minors | 7a: legacy library built with the real 0.29.0 pipeline (8 books); HP7 held "waits for your approval"; the old "do not share their original parent" reason absent; plan identical over HTTP and `scripts/sorting_moves.py`; listing moved nothing (SHA-256 unchanged); wrong, short, stale digest refused (409), missing or extra fields 400, empty `job_ids` 400; a file planted at the target changed the digest and the old one was refused, nothing moved; on approval the series was written in place (album `Harry Potter - 7 - …`, grouping, track 7) then the verified move; audio MD5 `f949fc995e4c…` before = after, 2 chapters and 0.8 s unchanged, 9 files before and after, identical MD5 multiset, a planted stranger file at a target untouched (SHA equal), no temp files left; old-bug HP1 record looked up again, held for approval, moved after approval. 7b: real `PublicClient` with 429 gave waits 1, 2, 3 then published without a series on try 4; controls "answered no series" published at once, "unreachable" after 4 requests; same through a real automatic run. 7c: `64. Книга 3` and `65. Книга 4` gave series `Harry Potter`, 3 and 4, author `Rowling J. K`, never from the folder; a Stephen King root folder gave no series. 7d: author matrix 12 of 12 plus 5 of 5 (lookalikes not merged). 7e: 10 of 10 and 3 of 3. 7f: Darwin's Blade 1/2 is one book (on 0.29.0, the negative control, two); chapters-restart controls stay separate. 7g: four real M4Bs totalling 32.27 h join with no hold (0.29.0 held them `ask/long`); three 12 h volumes stay separate. Corroboration: `test_series_backfill`, `test_sorting_030`, `test_sorted_wiring`, `test_sort_title` 63 of 63, 0 skipped, 140 s. |
| 8 | Manual conversion repairs a damaged M4B part; Join; undo; Cancel on an accepted Repair | PASS | 8a (manual, pause/resume, automatic, unrepairable) PASS. 8b join (preview, effects, all-or-nothing, a converting part waits or refuses; join, approve, convert with two damaged parts: 600.00 s output against 600.00 s of parts, 10 chapters) PASS. 8c Keep as separate books undoes an unapproved join; refused once approved with a job. 8d Cancel on an accepted Repair or Retry 14 of 15 (the Retry path used a staged request row). |
| 9 | Book metadata line is readable | PASS | 68 of 68 checks: every `scope_view.kind` plus a joined book, Cyrillic from mis-encoded tags, never the `\x1f` key or a raw tag. |
| 10 | Held and Candidate changed filters drop gone books | PASS | Pass off: Held 4, "N held" 4. After the pass: Held 2, "N held" 2 (the two job-less gone books left). Candidate changed 20 to 5 (live books and books with a job remain). A held and a changed book with a job were never hidden. List-only: no library file touched. |

Judy's section 6 acceptance checks, as exercised by QA: 1, 2, 6, 7, 8, 9, 10, 12 on real payloads; 13 injected into a real payload; 3, 4 and 5 not separately verified on real data (check 4 needs a scan beside a conversion, which the engine never allows; Ender's frontend test, run in the entry check, covers it); 11 (layout rects) not measurable headless.

## 5. Findings

### Blocker

None.

### Major

**F1 (item 5). The row Sergei actually has, already refused, is not revived.** A cleanup already in `needs_attention` with "Persisted recovery ancestry changed" stays there on every path.
- Repro (slice B, reproduced in two separate fixture runs):
  1. Replay both storage moves through `MovesReplay`.
  2. Seed one source-cleanup row exactly as 0.29.0's `hold()` writes it: state `needs_attention`, that reason, no hold cause, 37 originals and 37 recovery copies.
  3. Press Resume: the row is unchanged.
  4. Press Retry cleanup, direct and queued: both answer 400 "This hold does not offer Retry cleanup".
  5. Restart the engine, then Resume: still unchanged.
- Expected: item 5 says a Brom-style cleanup passes after two storage moves, and Sergei's own Brom cleanup (`bc5f1302`, refused 2026-11-18 12:09) should pass.
- Actual: state and reason identical at every step; all 37 originals and 37 copies intact (nothing lost); the page row shows `identity_retry: null`, so no button offers a way out.
- Cause, checked by me in the pinned source: `CleanupJobs.__init__` reclassifies only `LEGACY_BUSY` and `RETAINED_HOLD` (`source_cleanup.py` 135-171); the ancestry refusal is raised at 548 and 820; `identity_retry` is eligible only for `LEGACY_IDENTITY_HOLD` (321) or `output_identity_unavailable`; the Retry cleanup refusal is `merge_service.py` 1335.
- Severity: Major for the build (not a regression, no data loss), but it fails a named acceptance item on the real-data shape, so it decides the verdict. Jane to rule whether it is a Blocker for this release. Sent to Ender as a must-fix.

**F2 (item 1). The freshness cue is on most of the time on an idle app.** Against Sergei's answer 2, "only when behind".
- Cause, checked by me: `QUIET_MAX_AGE = 300` (`merge_service.py` 38): while nothing changes the engine reuses the counts for up to 5 minutes, and the cue turns muted at 10 s and warning at 30 s.
- Repro: start the engine on any catalog, press nothing, poll `/api/state` every 2 s, watch `work.snapshot_age_ms`.
- Measured, quiet app, no presses: live-sized catalog over 159 s, warning plus "(as of …)" 51 % of the time, muted 41 %, no cue 8 %; small catalog over 99 s, age still growing, warning 76 %, no cue 2 %.
- Impact: the counts are not stale, the app is just quiet, yet the panel says they are. It will show on every session. Judy and Ender to rule on the cue's trigger (not mine to specify).

### Minor

- **M1 (spec contradiction, item 1).** Check 7 asks for "1 Waiting item", but section 1.6 says a paused queue is a row. The build follows 1.6 (Waiting empty, a paused "Conversion queue" row). Judy to settle the spec.
- **M2 (item 1).** The first research row can read "Researching books · 1 of 27 books · Working", with no book name.
- **M3 (item 1).** Approving a 300-file book runs 162 s alone (86 s and more beside a conversion) showing only "Saving the approval" with a sliding bar and no amount.
- **M4 (item 7, 7a).** The series-language rename in the plan applies only when the book's recorded original language is `Other`. HP1 (`Unknown`) planned `Rowling J. K\Гарри Поттер\…` until a re-lookup, then `Harry Potter`. Approving the early digest writes the Russian folder (recoverable by a later `series_language` move). Repro: cache FantLab cycle 3650 as `{work_name 'Гарри Поттер', work_name_orig 'Harry Potter', lang_code 'en'}` and call `sorting_moves.canonical(db, manifest, rules, {'name':'Гарри Поттер','number':'1','provider':'fantlab','source_url':'https://fantlab.ru/work3650'})`: `Unknown` or `Russian` gives `Гарри Поттер`, `Other` gives `Harry Potter`. Cause is the `original_language == 'Other'` condition in `canonical()`. Worth fixing before the 81-book sweep.
- **M5 (item 7, 7f).** The real Darwin's Blade shape (two albums, no track numbers) is one book but still lands in Needs attention with "Mixed recordings in this group" and "Playback order uncertain"; Sergei must approve it by hand and the wording is misleading for parts the app joined itself. Control (one album, tracks 1/2 and 2/2): no reasons.
- **M6 (item 7, 7a).** `POST /api/sorting-moves/apply` for a refused or unlisted book answers 200 with `results: []`, and `scripts/sorting_moves.py --apply D --job <id>` prints nothing and exits 0: nothing moves (correct) but nothing says why. Repro: apply with the current digest and the job id of the Carrion Comfort book refused "A file with the new name is already there".
- **M7 (hazard, item 7).** `scripts/sorting_moves.py` defaults to `--port 5210`, which is Sergei's live app. QA always passed a private port. By design, but anyone running `--apply` without `--port` aims at his install (the digest gate still applies).
- **M8 (item 8).** The join press answer names the join itself as its blocker when nothing blocks it. Repro: `POST /api/candidate/join {queue:true}` on an idle engine returns 202 with `blocker {operation, action, <the join>}`, 4 of 4 times. Part rows may briefly read "runs when Join … finishes".
- **M9 (item 8, pre-existing).** M4B part-set grouping reads raw tags (`groups._part_sets` uses `item['metadata']['tags']`, not `tag_text.tags()`): mis-encoded album or artist in some parts splits one book into 2 and 3. The same code is in `0f21134`.
- **M10 (item 8).** `/api/audiobook/retry-cancel` with a malformed job id answers 409 `refused`, not 400.
- **M11 (test hygiene, not a product defect).** 8 of 25 tests in `tests/test_source_presence.py` fail when the module is run alone, 5 of 5 runs ("Exact file removal requires one admitted native catalog owner"). Slice C found the same environment property for `test_sorted_wiring` in plain Python: the tests need the disposition owner the gate provides, and pass inside it. The entry check passes because the gate supplies it.

### Observations (no action asked)

- Item 7a, a timing blip: right after the back-fill pass the file can sit at neither path for a moment, because the follow-up move runs on the action-queue thread. It was at the new path with its `book_moves` row `complete` a moment later, nothing lost.
- No existing test covers `_series_waits` carrying over through automatic processing; QA's one-off run matched the lookup-level tests.
- Quit on the 6,288-book catalog with a status computation running took 4.2-4.4 s, above "about 2 s". The ordinary case (paused, idle) is 0.3-0.6 s and the 1,572-book case with a computation running is 2.6-2.7 s. Reported as measured.

## 6. Not tested, and why

- Layout rectangles at 1280, 960, 760, 600 px and 200 % zoom (Judy check 11): not measurable headless. This report is a headless verdict about logic and text, never pixels. If a later build clears, Jane must capture the running jobs panel, the Join dialog and the Book metadata line herself before Sergei sees them.
- The real Electron shell, the tray Quit and "close from every top-level screen": not run (Sergei may be at the machine, no focus checks). Quit was tested through the engine's own desktop quit path with the shell's start-up contract (token, held stdin pipe); the packaged-build launch check stays a release gate.
- A press still running after 30 s ending `blocked`: only Ender's `test_quit_bound` (a fake slow press).
- Item 5 live-activation check (replay no-ops `require_normal_operation`): not exercised; a packaged real-shell run would cover it.
- The withdrawn-during-check race (item 8d): unreachable through the API; Ender's unit test covers it.
- The series "kept when every tag agrees" path (item 8b), and a real file moved into a Cyrillic author folder (item 7d; covered by the matrix on real seed rules only).
- Pinned runtime (Python 3.14.8 embeddable, ffmpeg 8.1 LGPL): system Python 3.14.10 and ffmpeg 8.1.1 were used.

## 7. What a GO needs

1. F1 fixed and re-verified on the real-row shape: seed the row as `hold()` writes it, then Resume, Retry cleanup (direct and queued) and a restart, with the 37 originals and copies intact until the cleanup legitimately removes them.
2. F2 ruled on by Judy and Ender, then fixed: the cue absent on a quiet idle app, present when the counts are really behind.
3. The damaged-parts delta (`1a0c031`) gets its own pass: an unrepairable part says to re-acquire the book, with no Retry and no "Reopen draft"; non-blocking damage with intact audio is not treated as damaged.
4. Lean verification applies: on the next build I confirm it by hash and test only those three plus a short smoke test. Items 1-4, 6-10 are not re-run unless the code they depend on changes.

## 8. Cleanup

All QA output is removed and verified gone: the four slice folders `qa-030-A` to `qa-030-D`, my pinned snapshot `qa-030-src` (2,846 files) and `qa-030-recon`, all under `I:\AI Projects\Worktrees\Books Arranger\`. The studio sweep refused the two folders I removed myself with EBUSY on the top-folder rename (it removed slice B's folder normally), so I removed those file by file, then the emptied directories, confined to those two exact roots after checking they held no junction or link, with no recursive flag. No QA process is left running (checked by command line). Nothing was written to C:, to Sergei's personal folders, to `I:\Books Arranger` or `Z:`, and port 5210 was never used. One item I did not create is left alone: the stuck `qa-9d05455.sweep-…` folder (needs an ACL fix or administrator). This report is not committed.
