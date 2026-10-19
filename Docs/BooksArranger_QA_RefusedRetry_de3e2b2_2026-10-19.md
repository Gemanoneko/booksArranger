# Books Arranger: QA report, interim build `de3e2b2` (refused-Retry, pre-check states, M4B allowances)

Date: 2026-10-19. Futaba (QA). Scope: interim pass on the committed build only. "Start over" is not built (awaiting Sergei) and is out of this pass. Not a release gate: no Senua verdict, no installer, no packaged build.

**Verdict:** GO

Verdict scope: this interim build `de3e2b2` only. No Blocker and no Major found. Three Minor findings on the new work, two Minor notes on older behaviour. Details below.

## Build under test

| | |
|---|---|
| Tool / version | Books Arranger, package.json 0.18.0 |
| Commit | `de3e2b2a7116443d975c499ef8cd66c33e77ce36`, branch `codex/books-electron-m1` |
| Worktree | `C:/Antigravity Projects/Worktrees/Books Arranger/electron-m1/`, clean before and after (`git status` empty) |
| Entry-check receipt | **Not produced.** qa-handoff needs a reviewed protocol-2 context from Ender; none was supplied. Build identity is pinned by full HEAD hash and a clean tree only. Not a substitute for the release receipt. |
| Run on | Electron (unpackaged) with the pinned bundled Python and ffmpeg, isolated profile and port 5212 |

## How it was run (and where it differs from the brief)

- Ender's launch command, with three changes, all scratch-only:
  1. `env -u ELECTRON_RUN_AS_NODE`. This Claude shell exports `ELECTRON_RUN_AS_NODE=1`, which makes `electron .` run as plain Node and crash at `app.isPackaged`. Not a build bug. Anyone running Ender's command from a Claude Code shell hits it.
  2. `--catalog-mode=new` on the first launch only. `new` needs an empty folder, so every later launch used `--catalog-mode=existing` on a catalog copy.
  3. `--remote-debugging-port=9334` (loopback) on most launches, so I could read the real window's DOM, focus and rects. The first two launches, one rescan launch, the first launch of the real-copy catalog and the six idle focus-repeat launches ran without it. 18 launches in all, each quit with the same command plus `--quit`.
- Seeding: 63 synthetic M4B fixtures built from the worktree's own box helpers (read-only import, no bytecode written), scanned by the app, then failed jobs and refusal records written into catalog copies while the app was closed. One real library book (`Звонок-0: Рождение`, 213 MB) was byte-copied from Z: (read only; original size and mtime unchanged afterwards) and used at module level and as one UI row.
- Every state was read from the live window (DOM, `title` attributes, `getBoundingClientRect`, `elementFromPoint`, `document.activeElement`). Hover tooltips are the `title` attributes, not rendered hover.
- Sergei's live instance (port 5210, `Books Arranger.exe`) was never touched: same four PIDs and port before and after.
- A foreground-window watcher ran through the whole pass.

## 1. M4B allowances (`m4b_preservation.py`)

Each shape built from synthetic bytes, read by the app's own background check, shown in the UI.

| Shape | Positive (must pass: "ready to retry") | Near-miss (must still refuse: "Can't convert") |
|---|---|---|
| `moov/iods`, 24 bytes | P02, P03 pass | track reference (N01), URL flag (N02), versioned (N03), duplicate iods (N04) refuse |
| track `udta` with one empty `name` | P04 passes | non-empty name (N05), two names (N06), name plus meta (N07), empty udta (N08) refuse |
| blank-only metadata items dropped | P05 passes (7 items dropped) | non-blank item (N09), typed zeros (N10), two blank children (N11) refuse |
| blank children beside exactly one `data` | P06 passes (3 items) | two data (N12), mean+name+data (N13), data version 1 (N14), data without type (N15) refuse |
| all four together | P07 passes (10 drops) | n/a |
| plain control | P01 passes | n/a |

- 7 of 7 positives pass, 15 of 15 near-misses refuse. Unsupported near-misses read "Can't convert — M4B not supported" with no Retry.
- Receipt: for P05, P06, P07, `stream_candidate` returns `metadata_dropped` with every drop (item, how removed, count, bytes); counts equal the plan's. `profile_proof` (the admission proof) carries the same drops. Iods and track udta are copied, so no drop is recorded for them.
- `verify_candidate` reports `all_retained_bytes_verified` True for all seven positives.
- Real byte copy: v0.18.0 module refuses it ("Unsupported structural box"); this build passes it, drops `aART`, `©grp`, `trkn` blank children, records all three in the receipt, and `verify_candidate` is True. In the UI, seeded in its production state (v0.18.0 refusal), the row reads Checking, then "Stopped — ready to retry" with "Retry was refused in v0.18.0. The app was updated, and this M4B now passes its check.", Retry enabled. That is what the nine refused books should show.
- Not exercised: a full child job run through the conversion pipeline (needs a reviewed candidate and real audio). The job-validation record that carries the receipt was not read end to end; the receipt was checked at module level.

## 2. Refused-retry rows (Judy section 7)

| Check | Result |
|---|---|
| Refused `unsupported_file` row: "Can't convert — M4B not supported", new hint, no Retry in row or panel, View metadata and Source folders present | Pass (S03, K04 for Repair) |
| No `retained`, `structural`, `box` outside Technical detail and the status hover | Pass: none in any status or hint text across all 63 rows |
| Positive control: row with no refusal reads "Stopped — ready to retry", Retry enabled | Pass (P01, 24 more rows) |
| Retry all and Retry selected skip refused rows; dialog count matches | Pass: Retry all (28), dialog "Queue 28 books"; refused rows absent from the group |
| "3 selected · 2 can be retried or repaired · 1 left out" | Pass, exact text. Mixed 9/6/3 also true. Tick on the refused row survives group switches |
| Loop check: forced press on a refused row | Pass: HTTP 409 "This book's status changed. Check the updated status above.", record and timestamp unchanged. Same for pre-check refused, stale+refused and refused Repair rows |
| `working_files`: Retry present and disabled, tooltip exact, hint matches | Pass for the disabled state (real worker refusal, Retry and Repair). See findings 2 and 3 for what happens once it clears |
| Stale record, pressed, refused again | Pass: S05 (stale, check passes) reads ready; a real press gives "Stopped — review changed" with a new record, not stale |
| Legacy v0.18.0 text converted once at startup | Pass: `unsupported_file`, keyed to the v0.18.0 module, stale on this build. Module-level mapping of 13 sample v0.18.0 texts is right (working files, ownership, review changed, file problem, unknown) |
| Focus when a refusal lands on a focused Retry | Pass for the described case (refusal arrives, Retry not pressed from the row): focus moves to "View metadata" of the same row. Note: when Sergei presses Retry on the row, focus ends on the row itself, set by the older v0.16.12 rule. Same row, never the page |
| Contrast | Measured warning 11.18 / 6.23, muted 8.92 / 4.97; row-hover pairs computed from tokens 8.31 / 6.63. All at least 4.5 |

## 3. Pre-check states (Judy follow-up section 4)

| Check | Result |
|---|---|
| Pending: "Stopped — checking the M4B", Checking group, Retry disabled, tooltip = hint, muted | Pass, 59 rows at once. Hint and tooltip identical, exact spec text |
| Pending rows out of Can retry and Retry all; ticked pending row counts as left out | Pass: "2 selected · 0 can be retried or repaired · 2 left out"; Retry selected (0) disabled |
| Forced Retry on a pending row | Pass: 409, nothing queued |
| Checking empties into Can retry, focus on "Can retry", ticks kept, button hidden at zero | Pass |
| Unavailable: "Stopped — can't open the M4B", warning hint, Retry enabled, group Other, not in Retry all, in Retry selected when ticked, Technical detail starts "Source unavailable:" | Pass for missing file, directory path, missing drive |
| Check that throws never reads "checking" | Pass: NUL in path reads can't-open with "Source check failed: ValueError: embedded null character". No re-check bound exists, so that part of the spec line could not be tried |
| Stale + pending / passed / refused | Pass: Checking / ready with "app was updated" hint / M4B not supported |
| "Stopped — try again" only where the check does not cover | Pass (S08) |
| Repair verb | Pass: "Stopped — repair refused"; "Repair after they are cleared" (hint and tooltip); file-problem hint ends "then repair." |
| Group order and Checking tooltip | Pass: "Show books the app is still checking before it offers Retry." |
| Counts conserved | Pass: sum of all groups was 63 at every sample through the pending pass, a real Retry selected on 5 rows (2 on leftover folders, 3 review changed) and a real Retry all on 25 rows ("Queued 25 of 25") |
| Rows never stuck on "checking" | Pass: every pass ended with 0 Checking; every row left it |

## 4. Layout, covering, focus

- Rects measured on all 63 rows plus the pending, Other (disabled working-files Retry with three buttons) and Can retry views, at 1440, 1024, 950, 720 (200% of 1440), 700, 640 and 475 (200% of the window minimum): **0 intersecting rects, 0 buttons under 96 x 32, 0 covered buttons** (`elementFromPoint` per visible button), no page-level horizontal scroll. The strip, with the Checking button, stays one line down to 700 and wraps cleanly at 640 and 475.
- The window never took focus at launch or during any click: `document.hasFocus()` false, window inactive after `--show-inactive`. Foreground log over 18 launches (12 under the main watcher, 6 idle repeats under a second one): the QA window appeared in the foreground **once** (12:39:08, launch 11, for 3 s), straight after the taskbar was clicked and while the machine was switching between five other apps. The six idle repeats and the other eleven logged launches gave no foreground event. I cannot tell a click on the new taskbar button from an activation by the app. Treated as unproven, not a finding; worth one more look on the packaged build.
- Close button (`--close-window`) hides to the tray (documented exception), process stays, page visibility "hidden". `--quit` (same as tray Quit) ends every Electron process and frees 5212 within 1 s, on all 18 launches.

## Findings

| # | Severity | Finding | Repro / evidence |
|---|---|---|---|
| 1 | Minor | The Checking count does not fall as checks finish. It stays flat until the whole background pass ends, then every row flips together. Judy's follow-up says the falling count is the progress signal. | Launch a catalog with unchecked M4B rows. Server `attention_counts.checking` stayed 56 for 37 s, then 0. P01 read "checking" until then although its own check finished in the first seconds. Cause is in the code, not the UI: `_busy()` leaves repair checks out of the quiet token and the pass invalidates status once at its end. On the real library (121 books, minutes of checking) Sergei would see one flat number. |
| 2 | Minor | After the leftover working folder is cleared, the row's Retry takes up to about 5 minutes to enable. Spec says checked live. The server allowed it at once. | Press Retry on a row with a leftover folder, remove the folder, watch the row. Fresh API read said allowed immediately; the open window enabled Retry 4 min 53 s later. Matches `QUIET_MAX_AGE = 300 s` page reuse. A group switch did not refresh it. |
| 3 | Minor | Once working files are gone, the row says the opposite of its button: status "Stopped — waiting for cleanup" and hint "Retry was refused: working files … are still present. Retry after they are cleared." beside an enabled Retry. Judy did not write the cleared-state text. | Seen on the cleared W01 row, and immediately on a seeded `working_files` record with no folder (K05). Tooltip on that Retry reads the normal "Check this book again…". Needs a Judy line. |
| 4 | Minor, older behaviour, not from this build | Below about 950 px the table scrolls sideways inside its own box (table minimum 895 px), so Retry and View metadata sit off-screen until scrolled. The page itself does not scroll. `web/style.css` is unchanged in this build. | 700 px and 200% zoom: table `scrollWidth` 895, `clientWidth` 627 or 647. |
| 5 | Minor, older behaviour, not from this build | On a catalog with no `merge-cache/audio-staging` folder, every M4B Retry is refused as "Stopped — file problem" with "Prior working-file ownership requires attention: An inspected destination ancestor is unavailable". Real catalogs that have run a job have the folder. | Fresh scratch catalog, no leftover folders: Retry all on 25 rows gave 24 file problems. Creating the folder first gave the expected review-changed refusals. |

Notes, no severity: (a) For a row the new pre-check refuses, the hover and panel Technical detail show only the earlier job reason, never the check's own reason (for example "Unsupported object descriptor"), so a near-miss cannot be told apart in the app. Judy specified this line only for "can't open". (b) Judy's optional notes O3 (checkbox tooltip names "the reviewed audiobook queue") and O6 (bulk result line) are unchanged and not built. (c) While unchecked, a repairable book reads "Stopped — checking the M4B" with a disabled Retry, then becomes "Damaged — can repair". Expected by the precedence rule.

Pattern alerts: none

## Not covered

- "Start over" (not built, per brief).
- A live worker refusal of `unsupported_file`: needs a reviewed candidate, which the scratch catalog does not have. That row type was seeded with a typed record (current key). Worker refusals for `working_files` (Retry and Repair), `source_changed` and `file_problem` were produced by the real worker and checked.
- A child job run end to end through the conversion pipeline, and the receipt inside the job's validation record.
- Setup screen (every launch passed `--data-dir`), `--show` (it focuses by design), packaged build, installer, Senua's review.
- The Python unit suite (it writes under the worktree's `scratch/`; Ender's own run stands). The five pure-node frontend tests I ran pass: precheck, refused-retry, retry-selected, attention, retry.

## Scratch left in place (Sergei deletes)

`C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/7be0fa3c-ad7a-444a-aa4a-6a232ded8ba0/scratchpad/shared/futaba-precheck/`, about 605 MB. It holds the fixtures, catalog copies `d0` to `dH`, the driver scripts in `tools/`, evidence JSON in `evidence/`, and two copies of one real book (`real/zvonok0.m4b` and the same bytes under `library/Audiobooks/QA R03 Real Zvonok0/`, 213 MB each). The QA app and the focus watcher are stopped; no QA process is running.
