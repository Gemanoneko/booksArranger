# Books Arranger 0.31.1: QA report, round 2 (Futaba, regression and delta pass)

Date: 2026-11-24, about 17:30 to 18:50 local. Build tested: the unpacked packaged build of the 0.31.1 candidate (still labelled 0.31.0), source HEAD `b497778ac9306353aa02bc6c324bcd7667d3fef0`, branch `ender/0.31.1-stuck-load`. Left uncommitted. Round 1 is `BooksArranger_QAReport_v0.31.1_2026-11-24.md` (NO-GO on `7ed4d62`, two Majors).

**Verdict:** GO

This GO covers Books Arranger 0.31.1 at HEAD `b497778ac9306353aa02bc6c324bcd7667d3fef0`. Both round 1 Majors and Minors 1 to 3 are fixed and held in the running app, Senua's M1, M2, M3 and m1 behave as described, and the stuck-load state and the removal still work. No Blocker, no Major and no new Minor is open. It is a behavior verdict only; Senua's RELEASE CLEAR is separate. Not retested are listed in section 5.

Counts: Blocker 0, Major 0, Minor 0 new. Pattern alerts: 1 (section 6).

## 1. Hash check (compared only; the entry check was not re-run)

| Item | Handed over | Found | Match |
|---|---|---|---|
| Entry log `q0311f\logs\ender-entry.log` SHA-256 | `fe568d18…4166` | `fe568d18b6713fa178bb6877e7f708f1ca29a4090878283b128e29b9a46f4166` | yes |
| Context `context\context.json` SHA-256 | `32be781e…9013` | `32be781e90e5e7a5b03b64cdf65867e514b1bfa65ac5e855a86e89abfbeb9013` | yes |
| Installer `…\d4150b9f-…\Books-Arranger-Setup-0.31.0.exe` SHA-256 | `b70ab9e8…4bd6` | `b70ab9e8e2c67d4b448598f037ebc03e11377992a0ea3e00510318f8ed594bd6` | yes |
| `dist\release-artifacts.json` SHA-256 | `b4e91191…4eef` | `b4e91191ceb1782db7c102ca38c643c2e8245762d9f90a3250ab4a5bc8474eef` | yes |
| Unpacked `Books Arranger.exe` SHA-256 | `a89a32e8…4c61` (unchanged) | `a89a32e8a8a634eba16e5a403f87ee1be58faa021c48b059c071e24c119d4c61` | yes, same shell exe as round 1 |
| Source HEAD | `b497778…` | `b497778ac9306353aa02bc6c324bcd7667d3fef0`, `git log 7ed4d62..HEAD` shows 4 commits (`b5a3fa6`, `df68c35`, `8dc256a`, `b497778`); `status --short` showed only untracked docs | yes |
| Receipt, line 3 of the log | `b497778…, dirty: N, check pass` | read in full: `Entry-check receipt v2: books-arranger v0.31.0 @ b497778ac9306353aa02bc6c324bcd7667d3fef0 (dirty: N) … check pass` | yes |

The 3,225 Python and 285 node counts were not re-counted (lean verification).

## 2. How it was run

Same rules and same method as round 1, with the harness rebuilt (the old run folder, with my scripts, went with the sweep). Everything lived in `I:\AI Projects\Worktrees\Books Arranger\futaba-0311b\` (section 8). Sergei's copy (shell 125832, host 114640, engine 83536, port 5210) was never touched; the same six PIDs were there at the start and at the end.

- **Engine lanes.** The packaged python and packaged `resources\backend` of this build, my own launcher, every non-loopback network call refused at the socket level. Finished books were made through the page's own manual route over HTTP (real scan, real ffmpeg conversion, real source cleanup), as in round 1. The jobs line and the Technical details text were read from the real page in leased headless Edge (no window, no focus; one DOM click on a row's View metadata button to open the details).
- **Presses.** Start was tested through the real routes the page's buttons call: `POST /api/audiobook/resume` (Resume audiobook jobs) and `POST /api/automatic/start` (Start automatic processing).
- **Shell spot check.** The unpacked exe with my own installation config and a debug port; the page's `/api/state` answer replaced by the engine's own 503 body once the engine reported loaded; a read-only foreground logger beside it.
- **Instrumentation, fixture build only.** As in round 1: pass-through wrappers around five packaged functions that block only while a gate file exists. No gate existed during any observed pass.

## 3. Results

| # | Item | Result |
|---|---|---|
| Major 1 | Post-launch cleanup on a large catalog, status reads stay fast | **FIXED** |
| Major 2 | A hand-moved book found through the real Start press | **FIXED** |
| Minor 1 | Removed books out of the look-up count | **FIXED** |
| Minor 2 | Start automatic processing tooltip in State 1 | **FIXED** |
| Minor 3 | Refusal logs once per change; refused books stay in lists and totals | **FIXED** |
| M1 | A book with an unfinished move or a replacement link is never removed | **PASS** (seeded records, see caveat) |
| M2 | A book renamed by hand in place is found by file ID; detail line | **PASS** |
| M3 | Removal wording "library files untouched" | **PASS** |
| m1 | The brake's "over half" counts all finished books | **PASS** |
| Spot | Stuck-load state; removal; "Original changed" release | **PASS** |

### Major 1: large catalog (lanes R and Q)
Same recipe as round 1: one converted book with 40 source parts, its 40 recovery copies held, the catalog padded with 140,000 synthetic `owned_artifacts` rows to **349.1 MB** (round 1: 349 MB). Relaunch with the holds off, latency watched from before the engine was up.
- All 40 recovery files were gone **6 s after launch**. Round 1: the first file went at 6 min 25 s.
- First status at 4.9 s. Over 150 s (282 samples) `/api/state` was 25 ms median, 28 ms at the 95th percentile, 120 ms worst; `/api/health` 2 ms median, 7 ms worst; no 503s, no errors. Round 1 on the same catalog size: `/api/state` 1.7 to 2.1 s per read throughout the purge.
- The engine used 19.3 CPU-seconds in the 150 s. Round 1 used 215 CPU-seconds in the first five minutes alone.
- Not reproduced here: the exact many-snapshot discharge (still not producible through the real pipeline, as in round 1); Ender's own figures for it were not re-run.

### Major 2: the real Start press (lane Q, 24 real finished books)
- Book 09 moved by hand into a new subfolder while the engine ran. With no press, nothing changed after 15 s. Resume audiobook jobs pressed: `relinked.count` was 1 **3 s later**, and the totals stayed `24 converted out of 24` throughout (in round 1 they dropped to 25 of 26 and stayed there).
- Book 10 moved by hand, then Start automatic processing pressed: found within about a minute (`relinked` 2 at the 65 s mark, "within about a minute when nothing converts" as the Brief says). Page: `Checking what is left · 0 need attention · 24 converted out of 24 approved books · 24 background look-ups left · 2 moved books found, new locations saved`.
- Not changed, by the Brief's design: Start scanning does not re-check finished books (the Brief's "Start" is the two presses above).

### Minor 1
After two removals: `work.background.series` `left 22, total 22` for 22 books (round 1: 26 for 24). The series table still holds the two `deferred` rows of the removed jobs; they are no longer counted.

### Minor 2
In every State 1 sample, Working and Stuck, `#start-automatic` has the title `Automatic processing can start when the library status is ready.` (round 1: `Start availability is unknown. Waiting for the local server.`), and the line under it says the same.

### Minor 3 (lane Q, brake)
11 of the 21 finished books deleted, relaunch:
- The page kept `20 converted out of 21 approved books` and `Showing 1–20 of 20 candidates`: a refusal changed nothing in the lists or totals (round 1: `13 of 24`, `Showing 1–13`). Note shown, calm look.
- The refusal was logged **once in 90 s** (round 1: every 20 s). Its wording: `Missing finished books were not removed: 11 of 21 finished books are missing at once. Check that the library drive is connected.`

### M1: records that hold a book (lane Q)
Seeded into the stopped catalog: a `book_moves` row in state `rename_intent` for Book 14 (cloned from a real found move), and an `audiobook_replacements` row naming Book 15 as the parent. The three books' m4b files were then deleted (Book 16 as a control with no record). After relaunch: Book 14 and Book 15 stayed `completed` (not removed, no tombstone); the log says `finished book not at its recorded path; left as it is: it is linked to a replacement`; Book 16 was removed.
- Caveat: these are my seeds, not a real unfinished move or a real replacement. My first replacement row named a job that does not exist, and the engine refused to load the catalog ("Replacement history job unavailable"): a consistency check, not a finding. The second pointed at another real job and loaded.

### M2: renamed by hand in place (lane Q)
Book 11's m4b renamed in its own folder (`Fixture Book 11 - Fixture Author 11.m4b` to `Renamed By Hand.m4b`), Resume pressed: found about 40 s later, engine log `finished book found again after a rename outside the app`, row `relinked {was, now}`. Technical details on the real page: `… Was in …\Fixture Book 11 - Fixture Author 11.m4b. Now in …\Renamed By Hand.m4b. Matched by file ID, size and hash.` A plain move (Book 09) still reads `Matched by name, file ID, size and hash.`

### M3
`… · 2 missing books removed from the list, library files untouched`. Engine log: `Finished book removed from the list (not found; library and source files untouched)`. The 22 other files were byte-identical afterwards.

### m1: over half of all finished books
After the 11-of-21 refusal, 5 of the 11 files were restored with the engine running, leaving 6 missing (6 of 21, under half). Within 7 s all 6 were removed (`removed 6`, `removal_refused` false). The round 1 rule counted only the books checked in that pass (the 11 unconfirmed) and would have kept refusing.

### Spot checks
- **Stuck-load state (real shell):** `Working · Loading finished. Preparing the library status.` at 0.5 s; `Waiting · … taking longer than usual (10 s). The engine is still answering.` at 10.7 s; `Stuck · …` at 60.3 s with Restart Books Arranger and Copy details (no Restart engine, no Try again), warning style on, no moving stripe; Technical details in the spec's five lines; Ready after the 503 was released. The foreground logger saw no Books Arranger window take focus in this run.
- **Removal:** two books removed at launch with the new wording, the brake and the restore as above.
- **"Original changed since checked" release:** the entry left Needs attention by itself about 37 s after the hold lifted, its recovery copy was deleted (5 files to 4, retention `deleted`), the two ordinary sets were untouched, the altered original stayed in place.

## 4. Findings
Blocker: none. Major: none. Minor: none new.

## 5. Not retested (said plainly)
- Senua's m2, m3, m4 and m5 (the output listing kept whether complete or not, the 30 s re-check while removing, the retained-run job exclusion, the rest): no behavior of theirs was handed over to test, and I did not exercise them.
- A real unfinished move and a real replacement job for M1 (seeded records only).
- The rest of item 5 from round 1 beyond the "changed" release (Keep files, the removed book's leftovers, the 3-per-pass spacing); the changed code was not reported to touch their behavior, and `recovery_retention.py` changed by four lines.
- Still BLOCKED from round 1, unchanged: Restart Books Arranger with a book converting (the native question needs a click) and pressing Copy details (clipboard).
- Real shell window at narrow widths, the 10-minute and 1-hour expiries, the exact many-snapshot discharge: as in round 1.

## 6. Pattern alerts
Pattern alerts:

- **PA-1 (round 1 recurrence, disposition proposed: accept as closed for this build).** The Start gap came from a path tested at a lower level. This time it was driven through the real presses (`POST /api/audiobook/resume` and `/api/automatic/start` on a real engine), and the Brief says the fix is tested that way; I confirmed it end to end. The rule still stands for the next new behavior: one test per press through the real route. Jane to confirm the disposition.
- **P1 (page picture honest at the edges).** The two round 1 cases (a hand-moved book vanishing from Ready, a refused removal leaving books in no list) are gone in this build: totals and lists stay put until a book is removed. Disposition: accept as closed.

## 7. Personal-folder listing (list only; nothing deleted or moved)
`node scripts/qa/personal-folders.mjs check --since <snapshot taken at the start>`: `personal folders: clean (1 subfolder note) (7 folders, 10 drive roots watched)`, the note being `C:\System Volume Information` "changed below the depth checked" (system, not mine). Every leased headless browser ended with `personal folders clean`. `I:\Books Arranger\` (Profile, Data), `Z:\`, port 5210 and Sergei's installed copy were not written to. The tool repo was read only (HEAD `b497778`).

## 8. Disposal
- Stopped: every lane engine by its own shutdown route (ports 5321, 5322, 5323, 5331 not listening, checked), the shell by its own `--quit`, every leased Edge (`list`: no leases). No process of mine remains; Sergei's six are as at the start. One command of mine passed a stdin-fed `python -` line, which the studio forbids; it was stopped (TaskStop) within seconds and nothing ran from it.
- Round 1's run folder `futaba-0311` (764.45 MB), which was locked last time, was swept on the first try this round: dry run planned exactly that one item, `--apply` removed it (`removed 1 item(s), 764.45 MB, stuck 0`).
- This round's run folder `futaba-0311b` (501.46 MB: lanes, logs, my scripts, temp) swept the same way: dry run planned exactly one item, `--apply` removed it (`removed 1 item(s), 501.46 MB, stuck 0`). Both are gone from `Worktrees\Books Arranger\`.
- Left, not mine: `ender-0311` and `q0311f` (Jane sweeps them after the release).
