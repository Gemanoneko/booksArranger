# Books Arranger 0.31.1: QA report (Futaba, candidate build, lean pass)

Date: 2026-11-24, about 15:50 to 17:20 local. Build tested: the unpacked packaged build of the 0.31.1 candidate (still labelled 0.31.0), source HEAD `7ed4d624c67e21d9d6090f35fa3c771fac52a967`, branch `ender/0.31.1-stuck-load`. Left uncommitted (Sully commits it).

**Verdict:** NO-GO

This NO-GO covers Books Arranger 0.31.1 at HEAD `7ed4d624c67e21d9d6090f35fa3c771fac52a967`. No Blocker is open, but two Majors are, and each contradicts something this release says it does. The stuck-load state, Restart Books Arranger, moved and missing finished books, the brake, the Keep files wording and the recovery-copy releases all pass. What flips this to GO: Jane's disposition on the two Majors (section 4), fix or an explicit accept.

Counts: Blocker 0, Major 2, Minor 4. Pattern alerts: 1 (section 6).

## 1. Hash check (compared only; the entry check was not re-run)

| Item | Handed over | Found | Match |
|---|---|---|---|
| Entry log `q0311d\logs\ender-entry.log` SHA-256 | `e69198f3…e259a` | `e69198f3f88d1e581edccebb1b62b89e8e73f2581e5e57162871c9fc0ffe259a` | yes |
| Context `context\context.json` SHA-256 | `88ed36ed…4ed4d` | `88ed36ed5c4d2eee106b3a3ca80d6e8c3371c2598e097f784779ed0ef28f34ca` | yes |
| Installer `Books-Arranger-Setup-0.31.0.exe` SHA-256 | `53cf0771…75ff` | `53cf0771c38aecb9a2a7ee0a51133ed9501a97c9046f2aec99be2eab2d3d75ff` | yes |
| `dist\release-artifacts.json` SHA-256 | `bd9c07c4…ce56` | `bd9c07c40ea4ec99db70c52603425f54f2e71727d3609a150fc22c92c85fce56` | yes |
| Unpacked `Books Arranger.exe` SHA-256 | `a89a32e8…4c61` | `a89a32e8a8a634eba16e5a403f87ee1be58faa021c48b059c071e24c119d4c61` | yes |
| Source HEAD | `7ed4d624…` | `7ed4d624c67e21d9d6090f35fa3c771fac52a967` (read only: `rev-parse`, `status --short` showed only two untracked docs) | yes |
| Receipt line (line 8 of the log) | `books-arranger v0.31.0 @ 7ed4d62… (dirty: N) … check pass` | read in full, same, `personal-folders clean (5 subfolder notes)` | yes |

Test and gate counts were not re-run or re-counted (lean verification).

## 2. How it was run

Everything lived in one run folder, `I:\AI Projects\Worktrees\Books Arranger\futaba-0311\` (see section 8), with TEMP pointed inside it. Sergei's copy (shell 125832, host 114640, engine 83536, port 5210) was never touched. Its six processes had the same PIDs at the start and at the end.

- **Shell lane (items 1, 2).** The unpacked exe, started with my own `--installation-config` (my own profile, data and temp folders), my own port and `--show-inactive`, plus `--remote-debugging-port`. I read the real page through DevTools: evaluate and network only, no mouse, no keyboard, no window calls. The "stub engine that answers 503 after loading finished" was done at the page's network layer: the real engine answers, and once it reports loaded (the page's own `loaded()` rule) the page's `/api/state` answer is replaced by the engine's own 503 body `{"error":"Status is still updating; retrying"}`. Real shell, real preload, real page, real engine. Runs S3 (lifecycle), S4 (Restart Books Arranger), S5 (Quit in Stuck), S6 and S7 (release).
- **Focus.** A read-only foreground-window logger (never sets focus) ran beside every shell run.
- **Layout (check 7).** Leased headless Edge (studio helper), the real page served by a real engine, only the shell's preload API stubbed in-page.
- **Engine lanes (items 3 to 7).** The packaged python and packaged `resources\backend`, started by my own launcher, every non-loopback network call refused at the socket level (nothing left the machine). Finished books were made by the page's own manual route over HTTP (cover search, source and order confirm, review and approve, Resume): real scan candidates, real ffmpeg conversion, real source cleanup. Automatic processing cannot approve synthetic books offline (it holds them), so I did not use it. The jobs line and note were read from the real page in headless Edge.
- **Instrumentation, fixture build only.** My launcher wraps five packaged functions in pass-throughs that block only while a gate file exists in my lane folder: the recovery purge (`RecoveryRetention.due`, `_purge_recovery_now`), the two release sweeps, the source cleanup for one named book, and the working-file discharge. They exist so recovery sets pile up and one original can be changed between conversion and cleanup. During every observed pass the gates were absent and the packaged functions ran unmodified.

## 3. Results by the brief's items

| # | Item | Result |
|---|---|---|
| 1 | Post-load stall shows the loading-finished state, Waiting at 10 s, Stuck at 60 s | **PASS** |
| 2 | Restart engine not offered after loading; refused restart shows its reason; Restart Books Arranger relaunches without taking focus | **PASS**, with two parts BLOCKED (below) |
| 3 | Moved books found at next launch or Start, jobs line "N moved books found, new locations saved" | **PASS at launch. FAIL at Start (Major 2)** |
| 4 | Missing books removed from lists and totals with the message; brake; offline or empty root | **PASS** |
| 5 | Recovery copies released (published incl. Keep files, removed books, "Original changed since checked"), leaves Needs attention, 3 per pass | **PASS**, throttle partly isolated |
| 6 | Keep files wording (section 9) | **PASS** for the live "changed" row; the two audiobook-group hints checked as page strings only |
| 7 | Post-load cleanup performance on a large catalog | **FAIL (Major 1)** |

### Item 1: the stuck-load state (S3, S7, Edge)
Times are since the shell's `loadedAt`; the strip text is quoted from the page.
- 0.8 s: `Working · Loading finished. Preparing the library status.` Detail `loaded in 0 s · preparing status 0:00 · engine answered 0 s ago`. No Step line, no moving stripe, no spinner (0 running animations), no buttons.
- 10.9 s: `Waiting · Loading finished. The library status is taking longer than usual (10 s). The engine is still answering.` No buttons.
- 60.6 s: `Stuck · Loading finished, but the library status has not arrived after 1 min 0 s. The engine is answering but still says the status is not ready. Your files are not touched. You can restart Books Arranger to try again.` Warning style on, bar still all done, action row = Restart Books Arranger then Copy details (Restart engine and Try again hidden), announcer "The library status has not arrived after 1 min 0 s. Restart Books Arranger is available." Technical details: `Loading finished: <ISO> (took 0 s)`, `Library status: not received for 62 s`, `Last status reply: Status is still updating; retrying`, `Engine answered: 0 s ago`, `State: stuck`.
- Placeholders read "preparing…" then "not ready yet." at Stuck; empty list "Preparing your books…" then "Your books are not ready yet."
- Tooltips: library, view, search, filter, previous and next all read `Not yet: Books Arranger is preparing the library status. This works as soon as it is ready.`; a press on an inert control wrote it to the message line, and it cleared at Ready.
- Reload mid-wait (at 20 s): the first sample after reload (about 1 s later) was State 1 at 20 s (same clock), not Step 1. The first second after a reload could not be observed.
- Release of the 503 (S7, first list delayed 4 s): Waiting, then `Working · Loading finished. Showing your books.` at 1.04 s, then Ready at 4.33 s. No Step line at any point. With the first list answering at once (S6, empty catalog) the strip went Waiting to Ready in 0.32 s with no intermediate line: by design it only shows while the first list is on its way.
- Check 7 layout, leased headless Edge, Stuck state with and without the note, at 1249, 960, 640 (200% zoom, device scale 2), 480 and 360 px, light and dark: 0 overlaps (line boxes compared), 0 horizontal scroll, 0 clipped text. Restart Books Arranger 174 x 41 px (spec 96 x 32). Contrast: text 11.18, detail and note 13.87, primary button 9.16, Copy details 8.02. Light and dark are identical (the page has one dark theme), so nothing changed there.
- The strip has 4 segments and `aria-valuemax` 5 (spec section 7, known, not counted).

### Item 2: Restart engine, refusals, Restart Books Arranger
- Restart engine and Try again were hidden in every State 1 sample.
- Refused press: Restart engine was un-hidden by script and pressed (the true race cannot be timed), the real shell answered `loaded`, and the page showed `Loading had already finished, so nothing was restarted.` under the strip, focus moved to the Status filter, and the announcer did not say "Restarting the engine." The other reasons (restarting, quitting, admission, unsafe) were not exercised.
- Restart Books Arranger (S4, nothing converting): within 40 ms the button read `Restarting…`, `aria-disabled` true, title `Restarting Books Arranger…`; the announcer said `Restarting Books Arranger.` after the shell accepted; a second press in the same tick was answered by the note `Books Arranger is already closing.` The old main process exited 0.46 s after the press. The new copy was up 5.4 s later with the original arguments plus `--show-inactive` (command line read), showed `running 0:01` and `last load took 0 s`, and no question appeared (nothing blocked the close).
- Quit in Stuck (S5, the page's Quit Books Arranger): every process of the lane gone in 1.38 s.
- Focus: the foreground logger never showed the new copy or the relaunch taking focus (S4, S5, S6, S7 clean). One event in S3, see Minor 4.

### Item 3: moved books (F1, F2; 26 real finished books and 6)
- Three books moved by hand into subfolders (`Author\Series X`, `Author\Books\Vol 1`, `Author\Saga`) and two into a sibling folder (`Elsewhere`): at the next launch `/api/state` `relinked.count` was 5 within 1.4 s of loading, totals stayed 26 of 26, each recorded as a completed move of strategy `found`, the engine log has one line per find, and the files' bytes were identical afterwards.
- Page, one find: `Checking what is left · 0 need attention · 26 converted out of 26 approved books · 1 moved book found, new location saved`. The part is not carried into the next launch (a relaunch with no change showed 0).
- Per book: `relinked {at, was, now}` on the row, `move` null (no move line), output path updated. The page string for the Technical details line is in the packaged page and matches the spec; I did not open the details panel.
- Not verified: the 10-minute expiry, the burst restart, the 1,200 number format (unit level only), the Technical details panel rendering.
- **Start: see Major 2.**

### Item 4: missing books (F1, F2)
- Two finished books deleted: `24 converted out of 24 approved books · 2 missing books removed from the list, no files touched`; `24 book candidates found`; list `Showing 1–24 of 24`; 24 other files byte-identical, none added; one normal-level engine log line per removed book (title, recorded path); a tombstone per book and job state `removed`.
- Two moved and one deleted in one pass: `5 converted out of 5 approved books · 2 moved books found, new locations saved · 1 missing book removed from the list, no files touched`. Found first, removed second, each with its own wording.
- Brake, more than 10 (F1, 11 of 24 missing): nothing removed, `13 converted out of 24`, note `Missing books were not removed. Check that the library drive is connected.` under the status line and above the candidate counts, 15 px, weight 400, text colour, `role=status`, calm look. Restoring the 11 files while the engine ran cleared the note and gave 24 of 24 about 15 s later. Two books removed earlier stayed removed although I restored their files too (a reappeared file does not bring them back).
- Brake, 3 or more over half (F2, 4 of 6 missing, well under 10): nothing removed, same note.
- Offline root (output root renamed away) and empty root (root present, empty): nothing removed, `0 converted out of 6`, same note, engine log `6 finished book(s) could not be checked (output folder unavailable)`. Putting the root back cleared it.

### Item 5: recovery copies (F1, F6, F7, F8)
- Published books: after a real conversion and cleanup the recovery folder holds 0 files and all 26 retention rows read `deleted`.
- Removed book (F6, one m4b deleted with a set held): its set was released and its staging folder reduced to its ownership marker, same as the other books.
- "Original changed since checked" (F7, one original altered after conversion, size and modified time kept to the nanosecond, so the app's own cleanup met `Original bytes differ from reviewed sources`): attention count `changed: 1`; about 27 s after the release hold lifted the entry left Needs attention by itself (`changed: 0`), its only recovery copy was deleted (retention `deleted`), the altered original and the finished m4b stayed.
- Keep files included (F8, same recipe, Keep files pressed first): its recovery copy was still released about 58 s after the hold lifted, and the kept record stayed.
- Throttle (F6, 8 held sets): batches of 3, 3 and 2 by the catalog's per-set deletion times. The second batch came under a second after the first because that run also removed a deleted book, and a removal wakes the sweep by design. A clean 20 s spacing without a removal, and "after the first status" as a separate timing, were not isolated (it would need a second 8-set lane).

### Item 6: Keep files wording (F7, F8, live page)
- Group hint "Original changed since checked": `The app left this original in place. Recovery copies are not kept.` Exact.
- Keep files tooltip: `Keep this book's originals and folder as they are, and stop flagging it. It does not keep recovery copies.` Exact.
- Press: no dialog, the row left the group (`Nothing needs your attention`, `0 need attention`), details line `You chose to keep this book's originals and folder as they are. This does not keep recovery copies.` Kept row hint in All candidates: `Kept at your choice: originals and folder stay as they are.` Exact. The pending face (Keeping…) was too brief to catch.
- The "Audiobook missing" and "Audiobook not verified" hints are in the packaged page (`attentionCopy`) and match the spec, but no live row of those groups was produced.

### Item 7: large catalog (P1, P2)
See Major 1.

## 4. Findings

### Blocker
None.

### Major

**Major 1. Recovery-copy purge after launch costs seconds per file on a large catalog: 6 min 25 s for a 40-file set.**
Repro: lane P1, one converted book with 40 source parts, its 40 recovery copies held, catalog padded to 349 MB by adding 140,000 synthetic rows to `owned_artifacts` (a table the reference check reads; the brief's figure is 379 MB). Relaunch with the holds off, watch from the first request.
- First status at 6.8 s. Then the engine process used one full core (CPU time climbed 12.5 s per 12.5 s) for 6 min 25 s. The first recovery file went at 6 min 25 s after launch and all 40 were gone 5 s later, so the time was all before the deletion.
- Throughout, `/api/health` answered in 32 ms median, 100 ms worst, and there were no 503s or errors, but `/api/state` took 1.7 to 2.1 s per read at every 40 s step (3.2 s worst). The same catalog quiet, afterwards: 25 ms.
- Control, lane P2: the identical 40-file set on the unpadded 4.6 MB catalog was purged within 6 s of launch. So the cost scales with catalog size per file, about 9.6 s per file at 349 MB.
- Meaning: the once-per-book reference check fixed `_discharge_published`, but the recovery-copy purge path appears to still read the reference tables for each file. 0.31.1 also releases every retained set at first launch (Keep files included), so Sergei's first launch may spend a long time here with slow status reads. The padding is synthetic and his tables are smaller, so the size on his catalog is not known; the scaling is.
- Not profiled: I did not profile where the time goes (reading the code points at the per-file reference scan; Ender and Senua to confirm).
- BLOCKED part: the exact `_discharge_published` many-snapshot case from the brief could not be produced. The real pipeline clears staged snapshots at conversion (staging holds only the ownership marker, with and without my holds), so I could not leave 40 snapshots for it. Ender's 272 s to 14.7 s figure is not re-run.

**Major 2. A finished book moved by hand while the app is running is not found at Start; only a relaunch finds it.**
The spec (section 8.1, checks 8.5.1 and 8.5.2), the Brief's decision row ("found at the next launch or Start") and the hand-over all say launch or Start.
Repro (F1): with the engine running and the launch pass long past, move Fixture Book 09 into a new subfolder. Press, one at a time, Start scanning, Resume audiobook jobs, then Start automatic processing; watch more than 8 minutes (the 300 s output-listing cache had expired by the second and third press). `relinked` stayed 0 and nothing was recorded. A relaunch found it: `… 26 converted out of 26 approved books · 1 moved book found, new location saved`.
- Meanwhile the page shows `25 converted out of 26 approved books`, `Showing 1–25 of 25`, `0 need attention`: the book vanishes from Ready with no explanation until the next launch.
- Cause, from reading the code (not fixed): `MergeService.resume` calls `_resume_guarded(..., recheck=False)`, so `AudioJobs.resume(settle=False)` runs no finished-book check, and the idle pass skips any book already checked this launch (`_published_seen`). `MergeService.resume`'s own docstring says "A Start never hashes unrelated completed books", the opposite of the Brief and the spec. The page also has no button labelled just "Start".
- Either Start has to re-check, or the spec, Brief and checks should say "next launch". If Sergei accepts launch-only, this drops to Minor (doc drift).

### Minor

1. **Removed books are still in the series look-up count.** After the two removals, `26 background look-ups left` with 24 books on the list. The series look-up table still has two `deferred` rows whose jobs are `removed` (the gap-fill look-up skips them, as the Brief says). A count that includes books he asked not to see anywhere in the app.
2. **State 1: Start automatic processing keeps a wrong tooltip.** `Start availability is unknown. Waiting for the local server.` while the engine is answering. The spec swaps the line under it (`Automatic processing can start when the library status is ready.`) but not this title.
3. **A refused removal logs every 20 s with no end.** `Missing finished books were not removed: 11 of 11 finished books checked are missing at once…` repeated at about 21 s spacing for as long as the books or the drive stay away (about 4,000 lines a day), and each pass lists the output folder again. The denominator is "checked this pass", not all finished books. Also, while removal is refused the missing books are in no Ready list and not flagged (0 need attention); only the note explains it.
4. **One unexplained foreground event.** In S3, 61.3 s after loaded, the foreground window changed from a Godot game window to my S3 shell window (PID 108052) and back to a Godot window 20 s later. It did not repeat in the next three Stuck transitions (S4, S5, S7), the shell only calls its focus-taking `showWindow` from the tray and a second instance, and neither ran then, so I cannot attribute it to the app and I am not counting it as one. It may be Windows handing focus back when the previous window closed. Listed so it is not a surprise.

## 5. Not verified (said plainly)
- BLOCKED, needs Sergei's OK: Restart Books Arranger with a book converting (the native question takes focus and needs a click), and Cancel in it.
- Not pressed: Copy details (it would overwrite Sergei's clipboard); I only checked that it shows.
- The other refusal reasons of 2.2, the engine-silent sub-states of State 1 (3 s and 10 s), the engine-silent line in 8.5.6, a real "Loading finished" strip over a non-empty catalog at the first list (done with a delayed list instead).
- The 10-minute and 1-hour expiry of the status parts, the burst restart, the 1,200 number format.
- The details panel's Technical details line and the "Recovery copies deleted automatically." panel text (API data and page strings only).
- The "Audiobook missing" and "Audiobook not verified" groups live, and the pending face "Keeping…".
- The exact many-snapshot discharge (Major 1), and the 3-per-pass spacing without a removal.
- Real shell window behaviour at narrow widths (layout was done in Edge, not in the Electron window: viewport emulation did not take effect there). The page is dark-only, so light and dark are the same.
- Real library, the NAS, Sergei's profile and install: never touched, by design.

## 6. Pattern alerts
Pattern alerts:

- **PA-1 recurs (open since 0.29.0, disposition: fix or accept).** A path that is tested at a lower level but behaves differently in the running app. Here the Start check: Ender's tests call `AudioJobs.resume` with its check on, but a real Start goes through `MergeService.resume` with the check off, so the entry check passes and Major 2 only shows in the real app. Same family as the 0.29.0 B-1, M-1 and M-2. Proposed: one test per new behaviour that drives the real press (the HTTP route or the real engine), not the inner call. Jane to disposition: fix, accept or defer.
- **P1 (from the 0.31.0 rounds) touched again.** The page's picture honest only at the edges the build tests: a book moved while running disappears from Ready with 0 need attention and no word (Major 2), and a refused removal leaves books in no list (Minor 3). Disposition unchanged, Jane's.

## 7. Personal-folder listing (list only; nothing deleted or moved)
`node scripts/qa/personal-folders.mjs check --since <snapshot taken at the start>`: `personal folders: listed (1 new, 1 removed, 13 subfolder notes) (7 folders, 10 drive roots watched)`.
- NEW `C:\Users\Public\Desktop\Bitdefender.lnk`, created 2026-11-24 16:43:31 (inside my run window; not mine, made by the security software).
- REMOVED `C:\Windows.old`, there at the start, gone at the end (Windows housekeeping, not mine).
- SUBFOLDER notes for `C:\ProgramData`, `C:\System Volume Information`, `C:\Windows`, and `SteamLibrary` and `System Volume Information` on D:, E:, F:, H: and I:: "changed below the depth checked". Not mine.
The leased headless browsers each ended with `0 left; personal folders clean`. `I:\Books Arranger\` (Profile, Data), `Z:\`, port 5210 and Sergei's installed copy were not written to. The tool repo was read only: HEAD `7ed4d62`, `status --short` shows two untracked docs that are not mine (this report is the third, uncommitted, as asked).

## 8. Disposal
- Stopped: every lane engine by its own shutdown route (ports 5291 to 5309 not listening, checked), every shell by its own `--quit` or the page's Quit, every leased Edge (`list`: no leases). No process of mine remains; Sergei's six are as at the start.
- The run folder `I:\AI Projects\Worktrees\Books Arranger\futaba-0311\` (764 MB: lanes, logs, my scripts, the temp folder) **was not removed. STUCK.** The studio sweep (`node scripts/studio-sweep.mjs --project "Books Arranger" --path "…\futaba-0311" --apply`, dry run first: exactly one item planned) answered `KEPT … [in use or locked (rename refused: EPERM)]` on each of four tries, minutes apart. Renaming any child of the folder works; renaming the folder itself fails with "Access is denied", its ACL is normal and no process of mine references it (I looked by command line). So something outside my processes holds a handle on the folder (the security software is my guess, unproven). I did not work around the sweep (no direct delete). Jane's sweep after the release should take this literal path; run it first as a dry run. Nothing in it is needed: this report holds the numbers.
- Everything else is inside that folder (the headless lease folders lived in my own temp folder, already ended). The `illuminati-headless` folder in `C:\Users\AnGeLZzZ\AppData\Local\Temp` dates from 14 and 18 November, not mine, left.
- Left alone: `ender-0311`, `q0311d` (Jane sweeps them), and `I:\AI Projects\futaba-translations-v0172-qa` (not mine).
