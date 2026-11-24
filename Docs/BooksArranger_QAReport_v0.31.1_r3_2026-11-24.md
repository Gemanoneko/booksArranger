# Books Arranger 0.31.1: QA report, round 3 (Futaba, small delta pass)

Date: 2026-11-24, about 19:15 to 20:45 local. Build tested: the unpacked packaged build of the 0.31.1 candidate (still labelled 0.31.0), source HEAD `534d0c9fe2e5d1891210344a1c9d4c02405f564c`, branch `ender/0.31.1-stuck-load`. Left uncommitted. Round 2 is `BooksArranger_QAReport_v0.31.1_r2_2026-11-24.md` (GO on `b497778`).

**Verdict:** GO

This GO covers Books Arranger 0.31.1 at HEAD `534d0c9fe2e5d1891210344a1c9d4c02405f564c`. The two changes on top of `b497778` (Senua's r2-m1 and r2-m2) do what they say in the running app, and the two smoke tests pass. No Blocker, no Major, no new Minor. It is a behavior verdict only; Senua's RELEASE CLEAR is separate.

Counts: Blocker 0, Major 0, Minor 0 new. Pattern alerts: none (section 6).

## 1. Hash check (compared only; the entry check was not re-run)

| Item | Handed over | Found | Match |
|---|---|---|---|
| Entry log `q0311g\logs\ender-entry.log` SHA-256 | `4e97d048…9d04` | `4e97d0489440656a7d072f4e4a1d607fe6740dfb4652f33a4a7bf612701c9d04` | yes |
| Context `context\context.json` SHA-256 | `a20d36a3…bee6` | `a20d36a34aa0e95d68a42d46cb91d181b4f282029af5fdb7a2b1fccbe352bee6` | yes |
| Installer `…\c78606a2-…\Books-Arranger-Setup-0.31.0.exe` SHA-256 | `04210388…ea78` | `04210388472db37b975d869b5b6f6f60954161d220078a1d3f6d8424699bea78` | yes |
| `dist\release-artifacts.json` SHA-256 | `3d8d0967…b85a` | `3d8d09672e2609c668c369cec4e64160857bdcf7dc018034469c7c11d537b85a` | yes |
| Unpacked `Books Arranger.exe` SHA-256 | `a89a32e8…4c61` | `a89a32e8a8a634eba16e5a403f87ee1be58faa021c48b059c071e24c119d4c61` | yes, same shell exe as rounds 1 and 2 |
| Source HEAD | `534d0c9…` | `534d0c9fe2e5d1891210344a1c9d4c02405f564c`; `git log b497778..HEAD` shows 2 commits (`515aeaa`, `534d0c9`), 3 files changed (`merge_service.py`, one test, the Brief) | yes |
| Receipt, line 6 of the log | `534d0c9…, dirty: N, check pass` | read in full: `Entry-check receipt v2: books-arranger v0.31.0 @ 534d0c9fe2e5d1891210344a1c9d4c02405f564c (dirty: N) … check pass`. The failed run `ender-entry-failed-foreign-c.log` sits beside it and was not read as evidence. | yes |

## 2. How it was run

Same rules and method as round 2. The run folder was `futaba-0311c` under `I:\AI Projects\Worktrees\Books Arranger\` (section 8), with the harness rebuilt. Sergei's copy (shell 125832, host 114640, engine 83536, port 5210) was never touched; the same six PIDs and the listener were there at the start and the end.

- **Engine lane.** The packaged python and packaged `resources\backend`, my own launcher, every non-loopback network call refused at the socket level. Finished books were made through the page's own manual route (real scan, real conversion, real cleanup); the dot-folder move used the app's own destination route (the Choose folder move).
- **Instrumentation.** Two pass-throughs in my launcher, neither changing behavior: a gate that blocks the source cleanup of one named book while a gate file exists (used only to keep the queue busy for part (b)), and a logger that records each time the recovery sweep's loop goes to sleep and the timeout it asked for (2, 20 or 60 s). The first logger I tried (on a function inside the pass) logged nothing while the queue was busy, because the sweep defers its pass then; I replaced it with the sleep logger.
- **Shell smoke test.** The unpacked exe with my own installation config and a debug port; the page's `/api/state` answer replaced by the engine's own 503 body once the engine reported loaded; a read-only foreground logger beside it.

## 3. Results

### (a) r2-m1: a book whose path runs through a dot-folder, renamed in place, is not removed: PASS
Lane V, 12 finished books. Book 01 and Book 04 were moved by the app's own Choose folder route into `Sorted\.hack__Sign\` (I created the empty folder; the app moved the books and recorded the new paths, row paths `.hack__Sign\Fixture Book 01 - …m4b`). Engine stopped, then by hand: Book 01 renamed in place to `Vol 1.m4b` (inside the dot-folder), Book 04 deleted (inside the dot-folder), Book 02 deleted (plain folder, the control "beside it"), Book 03 renamed in place (plain folder). Relaunch, launch pass:

| Book | By hand | Result |
|---|---|---|
| 01 `.hack__Sign\…` | renamed in place | **not removed**, state `completed`. Log: `finished book not at its recorded path; it was in a folder the search does not enter, so it is never removed` |
| 04 `.hack__Sign\…` | deleted | **not removed** (same rule, same log line) |
| 02 plain folder | deleted | **removed** (tombstone 1, job `removed`). Log: `Finished book removed from the list (not found; library and source files untouched)` |
| 03 plain folder | renamed in place | **found** by file ID (`relinked` 1). Log: `found again after a rename outside the app` |

Totals after: `11 converted out of 11 approved`, jobs `completed 11, removed 1`. So the new rule keeps a book that ran through a skipped folder whether it was renamed or deleted there (not just the case in the brief); a plainly deleted book in a normal folder is still removed, and a renamed one is still found. Book 01 renamed in the dot-folder is not found either, because the search never enters it: it simply stays as it was.

### (b) r2-m2: the sweep rhythm after a Start (lane V)
Each time the recovery sweep's loop goes to sleep, I recorded the timeout it asked for. A conversion was kept running by holding the cleanup of one new book at my gate (the queue worker stays alive while it is held).
- **While a conversion runs:** Resume audiobook jobs pressed, then pressed again with Book 14 converting. After that second press the sweep slept **60 s each time**: at +0.6 s (woken by the press), +60.6 s and +120.6 s, never 20 s. (Round 2's code asked 20 s for the whole run.)
- **When idle:** the first Resume, with the queue about to start, gave `wait=20` (check waiting, queue idle), then `wait=60` 1.4 s later once the conversion was running. A second, clean press with the queue idle gave `wait=20` at +0.3 s and `wait=60` at +1.5 s, once the check had started. So the 20 s rhythm shows exactly while a Start's check waits to start with the queue idle, and goes back to 60 s as soon as it starts.
- After the held conversion was released the sweep kept its 60 s rhythm (the next sleep ended at +56.6 s); the queue was idle and 13 of 13 converted within 3 s.

### Smoke 1: a hand-moved book is still found
Book 05 moved by hand into `Elsewhere` while the engine ran, Resume audiobook jobs pressed: `relinked` went 0 to 1, engine log `finished book found again after a move outside the app`. It took about a minute this time (round 2 saw 3 s on one press and about a minute on another; the Brief says "within about a minute when nothing converts").

### Smoke 2: the stuck-load state
`Working · Loading finished. Preparing the library status.` at 0.2 s; `Waiting · … taking longer than usual (10 s). The engine is still answering.` at 10.3 s; `Stuck · Loading finished, but the library status has not arrived after 1 min 0 s…` at 60.9 s with Restart Books Arranger and Copy details only, warning style on, no moving stripe; Start automatic processing's tooltip `Automatic processing can start when the library status is ready.`; Ready after the 503 was released.

## 4. Findings
Blocker: none. Major: none. Minor: none new.

One observation, not counted: in the first smoke run the foreground logger recorded my shell window (PID 53820) as the foreground window for 1.25 s, 43 s after loaded, between two Chrome windows (Chrome came straight back; the Chrome window had not closed). It was not at the Stuck transition and it did not repeat: a second full run at 120 ms polling showed only Chrome and WhatsApp changing, no Books Arranger window. It is the same kind of single, short blip as round 1's one event. The shell calls its focus-taking `showWindow` only from the tray and a second instance, and neither ran, so I cannot attribute it to the app and I do not count it. Listed so it is not a surprise.

## 5. Not retested (said plainly)
- Anything not touched by these two commits: round 2's results stand for the rest (the large-catalog purge, Resume and Start automatic processing finds, M1, M2, M3, m1, the "Original changed" release, Minors 1 to 3).
- Senua's r2-m1 for a skipped folder beginning with `#`, `@` or `$`, or a hidden or system folder: the rule is one test (`part[:1] in '#@.$'` and the hidden or system attribute); I exercised the dot case the brief asked for.
- Still BLOCKED, unchanged: Restart Books Arranger with a book converting (the native question needs a click) and pressing Copy details (clipboard).

## 6. Pattern alerts
Pattern alerts: none. Round 2's PA-1 was closed there; this round both changes were exercised through the real presses and the real launch pass.

## 7. Personal-folder listing (list only; nothing deleted or moved)
`node scripts/qa/personal-folders.mjs check --since <snapshot taken at the start>`: `personal folders: clean (5 subfolder notes) (7 folders, 10 drive roots watched)`. The notes are `SteamLibrary` on D:, E:, F:, H: and I: "changed below the depth checked" (not mine). `I:\Books Arranger\` (Profile, Data), `Z:\`, port 5210 and Sergei's installed copy were not written to. The tool repo was read only (HEAD `534d0c9`).

## 8. Disposal
- Stopped: the lane engine by its own shutdown route, both shells by their own `--quit`; ports 5341, 5351, 5352 and the debug ports not listening, checked; no process of mine remains; Sergei's six are as at the start.
- The run folder `futaba-0311c` (85.47 MB) was swept: dry run planned exactly that one item; the first `--apply` removed 0 (a transient hold right after the processes ended, I think), the second removed it (`removed 1 item(s), 85.47 MB`). Gone from `Worktrees\Books Arranger\`.
- Left, not mine: `ender-0311` and `q0311g` (Jane sweeps them after the release).
