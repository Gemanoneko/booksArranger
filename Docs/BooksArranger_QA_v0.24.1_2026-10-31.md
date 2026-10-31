# Books Arranger 0.24.1 — delta QA, 2026-10-31 (Futaba), build r2 (765a6fe)

**Verdict:** GO

No Blocker. Ruling 77 (folder cleanup safety, the one commit r2 adds) works as ruled on the packaged build, with a positive control on r1 for each of its three parts, and the hidden-app check ran on r2 and the Windows tray list was put back byte for byte. Two Majors in the 75b "Start over for a changed source file" feature are in this release's delta, were found on r1 and are in code r2 does not touch: the press works but the book then stops at "Held — Manual draft retained" instead of going back to automatic processing (M1), and the offer shows up to about 5 minutes after the file is replaced (M2). Neither breaks the daily flow, so the verdict is GO. Jane or Sergei decide whether M1 holds the release or waits for the next cycle.

Release source commit: 765a6fed1bbba5662522898af011158e56c8e9a3

Release artifact manifest SHA256: 5c23fe856d8df656793af93f5e6e897727d1e8726f6696e42d9c676b9e9c8832

Pattern alerts: 1 — "a change on disk, or an earlier fault, shows only after a restart or a long delay" (see P1 below; the 0.24.0 pass saw it three times, 0.24.1 sees it again). Disposition asked of Jane: fix, accept or defer.

This report covers r2 (commit `765a6fed1bbba5662522898af011158e56c8e9a3`, installer SHA-256 `fa11adc4…64ff`). The first pass of the day was on r1 (commit `1f48bebdcb611d7cd427f8c213019ee89cc3bd5d`, installer `9f669a8a…5acd`, manifest `b94c8017…35ef`); its findings carry over for the areas r2 does not change (section C2). r2 differs from r1 only in `storage_cleanup.py`, one line of `merge_service.py`, two test files and the Brief (`git diff 1f48beb 765a6fe`).

## A. Identity (confirmed by hash; the entry check was not re-run)

| Value | r2 (the build this report certifies) | r1 (earlier pass, for the record) |
|---|---|---|
| Source commit | `765a6fed1bbba5662522898af011158e56c8e9a3`; the tool repo's HEAD equals the receipt's `@` hash; the repo's tracked files are clean (one untracked file: Senua's review) | `1f48bebdcb611d7cd427f8c213019ee89cc3bd5d` |
| Installer | `q241\r2\dist\builds\c8f9f07a-1004-4119-8b29-51587040e331\Books-Arranger-Setup-0.24.1.exe`, 174460585 bytes, SHA-256 `fa11adc44580658d0f453c0367918eeb9f3cde828706646d9ed31b46faec64ff` (equals the handoff and the manifest's own entry) | `q241\r1\dist\builds\6a37dc98-e9e1-443e-b0a2-ead2e32617f3\…`, 174456313 bytes, SHA-256 `9f669a8a…5acd` (equals the handoff and the manifest's own entry) |
| Manifest | `q241\r2\dist\release-artifacts.json`, SHA-256 `5c23fe856d8df656793af93f5e6e897727d1e8726f6696e42d9c676b9e9c8832` (equals the handoff); `version` 0.24.1, `source_head` equals the commit, `build_id` `c8f9f07a-1004-4119-8b29-51587040e331`, 304 payload files | `b94c8017f3290f170a2a4a6f9bf6773247d1667a9cb382af18bb9663067135ef` |
| Payload | Installer extracted with 7-Zip into scratch (no install): all 304 files match the manifest's size and SHA-256, none extra; `resources/backend/VERSION` reads 0.24.1 | same check, 304 of 304 |
| QA runtime | The packaged `python.exe` equals the pinned `build-cache/qa-runtime` hash `434b361f…2c6f`; the packaged FFmpeg was first on PATH | same |
| Builder's receipt (read from `q241\r2\logs\ender-entry.log`, not a run of mine) | `Entry-check receipt v2: books-arranger v0.24.1 @ 765a6fed1bbba5662522898af011158e56c8e9a3 (dirty: N) [source:e03e3dae…dd6e; harness:e09c263f…3d64; runtime:f28b5727…f769; checker:6378352e…a07f] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a; personal-folders clean (5 subfolder notes)` | receipt `@ 1f48bebd…`, check pass |

The accepted 0.24.0 build (`q241\main-dist-0.24.0`, installer `452eb75c…879c`, manifest `7932ed43…22a2`, equal to the 0.24.0 acceptance) was used as the "older version" in the 76b and 77b runs.

## B. Method

- The packaged backend, page and shell modules from the verified payload ran on the packaged Python, headless. The engine was started as the shell starts it (`desktop_host.py`, `-I -B`, the shell's minimal environment, the packaged FFmpeg first on PATH), with private roots, catalogs, data folders and ports (5411 to 5476). Every engine was quit through the desktop control route and exited with code 0, except runs I stopped on purpose (named where used).
- Fixtures are real MP3 files cut from the private fixture with real ID3 tags, plus small text and image files for leftovers.
- The page checks ran in a real headless Edge, started only through `scripts/qa/headless-browser.mjs`, against the real engine, through a pass-through proxy of mine that can delay, hold or rewrite a route (the "mock engine" of Judy's section 9, with the real engine behind it). No mouse, no focus. A page click is a DOM click inside the headless page.
- One book used the live public sources (the Tolkien volumes, at the app's own pacing, no cooldown bypass).
- Nothing was installed. Nothing was written on Z: or in the live `data/`. Sergei's own running app (`AppData\Local\Programs\Books Arranger`) was not touched.
- Fault injection for 77b used a deny-listing ACL (`icacls /deny <me>:(RD)`) on private folders, lifted again in every run.

## C1. Results on r2 (what 765a6fe changes)

### 77a. Only known safe leftovers are deleted; anything else keeps the whole folder — PASS

Nine books under one author (two mp3 each), each folder with leftovers; the same library on r2 and on r1.

| Folder holds, besides the audio | r2 | r1 (control) |
|---|---|---|
| `cover.jpg notes.txt info.nfo rip.log album.cue list.m3u Thumbs.db desktop.ini .DS_Store link.url check.sfv` | folder removed | removed |
| `COVER.JPG Notes.TXT` (upper case) | removed | removed |
| `cover.jpg` + `booklet.pdf` | **kept whole** (jpg and pdf both still there) | removed, pdf deleted |
| `cover.jpg` + `extras.zip` | kept whole | removed, zip deleted |
| `cover.jpg` + `book.aaxc` (audio the app does not name) | kept whole | removed, `.aaxc` deleted |
| `cover.jpg` + `README` (no extension) | kept whole | removed |
| `cover.jpg` + `download.part` | kept whole | removed |
| `cover.jpg` + `bonus.mp3.txt` (a name carrying an audio extension) | kept whole | removed |
| `cover.jpg` + `book.epub` | kept whole | removed |

r1 deleted every one of them, which is Senua's M5 happening; r2 deletes only the first two. The author folder and the library root stay in all cases.

### 77c. A durable record of each deleted file — PASS

- Table `source_folder_removed_files`: 13 rows for the two removed folders, one per deleted file, each with the book's job, the folder, the file name, its size and `state: removed`. The 11 files of the first book and the 2 of the second are all there, `Thumbs.db` and `.DS_Store` included.
- A kept folder says why in `source_folder_cleanup_directories`, naming the file: "A file that is not a known leftover keeps the folder: booklet.pdf" (and the same for `extras.zip`, `book.aaxc`, `README`, `download.part`, `book.epub`).
- r1 has no such table and no names (control).
- Minor m4: the `bonus.mp3.txt` folder is kept with "Audio files remain in the folder; retained", which does not name the file. 77a says an unknown file is recorded by name.

### 77b. An unreachable folder is retried later, not recorded as finished — PASS for the sweep; the post-conversion path was not isolated live

- **Sweep of older books (the 76b pass), with a positive control.** The accepted 0.24.0 build converted three books in place; each left a folder holding only `cover.jpg`. The build under test then started on the same folders while one of them could not be listed (deny RD).
  - r2: the two listable folders were cleared (two `removed` rows). The unlistable one was left alone and **nothing was recorded for its book**, so the sweep had not settled it. Twenty seconds after the deny was lifted that folder was removed too and its row `removed`. The final sweep table holds three rows, all `completed`.
  - r1 (control, same run on its own fresh folders): the unlistable folder's book was recorded `kept` for good in the first pass (Senua's M2). After the fault was lifted the folder was still there 200 s later, and the table still said `kept`.
  - I first ran this on a copied catalog; the cleanup then refused every book with "Completed output ancestry changed" because the copy changes the folders' native identities. That run is discarded, and the check above is on folders converted in place. The refusal itself is the safety check doing its job.
- **Post-conversion folder step.** Six books, a listing deny put on each folder the moment its originals were gone. The deny landed before the folder step: the earlier recovery and temporary step failed first ("Originals removed; recovery cleanup needs attention: Destination directory cannot be protected: [WinError 5] Access is denied."), so the retry path of 77b (the `FOLDER_RETRY` marker) was not reached. The books were not recorded as finished: `audiobook_ready` false, no folder-cleanup record at all. That part is as 77b wants. Not exercised live: a fault that begins exactly at the folder step. The repository tests cover it.
- **Observation O1 (not 77, not changed by it).** After the fault was lifted, and after an app restart, those six books kept the same "recovery cleanup needs attention: … Access is denied" line for the 3.5 minutes I watched and stayed not ready. Nothing retried it. A drive dropping during post-processing would look like this. I did not run it on 0.24.0 or r1, so I cannot say whether it is older.

### Hidden-app check on r2 (ruling 76e, same terms as 74a) — PASS

- **Authority.** Ruling 76e (Sergei, 2026-10-31: "Yes") in `Team/Docs/BooksArranger_Rulings_2026-10-24.md`, read in the file, and the coordinator's relay that it covers r2. It allows the hidden-app check to add the tray-history entry for 0.24.1, removed after each run, this release only.
- **Run** (a private copy of the unpacked payload, private profile, data, temp and ports, `--start-hidden`, no mouse). The helper is the committed `BooksArranger_HiddenPackageSmoke_v0.23.0_2026-10-28.mjs` with two constants changed (the work folder and the koffi path; its authorization check is unchanged). Senua did not review the copy.
  - It re-verified the installer, the manifest and all 304 payload files against r2's manifest, source commit `765a6fed…`.
  - The displayed version and the engine version are both 0.24.1.
  - Window close hid the window while the shell and engine kept running.
  - Quit (the app's `--quit` control, which the 0.23.0 acceptance treats as the tray Quit path; I did not click the tray menu) exited the process with code 0.
  - No visible window and no foreground take (`intrusion: null`, a positive control of 22 visible windows).
  - Payload unchanged afterwards, native owner closed (`zero`, active 0), 7.0 s.
- **What the run added.** One new leaf (`8164063835348545584`, pointing at the scratch copy) and its id at the front of the root `UIOrderList`. Windows had also put two ids with no leaf of their own in front of the older ones (the id from my r1 run, and one more that appeared after it): the list read `[mine, stray, r1-id] + the 1280 pre-run bytes`.
- **Removal.** My own cleanup tool, written again from the 74d method because Ender's scratch folder was gone; Senua did not review it: the scratch app copy deleted first (the tool refuses while its exe exists); a read-only check (exactly one new leaf, it is mine, no other key changed, every extra id in front has no leaf, the rest of the list equals the pre-run bytes); then a same-handle `NtDeleteKey` on the verified leaf (no subkeys, `ExecutablePath` equal to the copy) and a compare-and-set write of `UIOrderList` back to the pre-run bytes; read back; then the whole key exported again.
- **End state.** The final export is byte-identical to the export taken before the run (SHA-256 `5df456f6…2c08`, 154 keys, `UIOrderList` 1280 bytes). It is also identical to the export taken before the r1 run, so the key is where it was this morning. No test app process is left.
- **Note for Sergei, not a defect.** Windows prepends ids with no leaf to the list on its own between a run and its cleanup (it happened again), so "put back exactly as it was" is true at the end of a run only.

## C2. Carried from r1 (areas r2 does not change), plus r2 re-runs where r2's code is involved

### 74e and 76b. Leftover source folders — PASS (re-run on r2)

- After conversion (library layout author/book): a book folder holding `cover.jpg` and `notes.txt` is removed; a folder with another book's audio in a subfolder stays until that book is converted and is then cleared by the next pass (20 s on r2, 30 s on r1); a folder that is nobody's source (only `notes.txt`) and an empty sibling folder are untouched; author folders and the library root stay.
- Older books (converted by 0.24.0): on r2 the folders holding only a cover (also `cover.jpg + notes.txt`, and one 0.24.0 left empty) were cleared in the first pass after start; the folder where an unrelated `bonus.mp3` was added and the one with a subfolder were kept. The filed audiobooks were not touched. Same on r1.
- Observation m3: a book folder directly under the source root keeps its `cover.jpg` after conversion (`Solo\cover.jpg`). The code never touches a direct child of the source root (Senua verified the rule). It is the design, but Sergei's rule ("no audio left, delete the folder") does not apply to a book at that depth. Jane to confirm that is acceptable.

### 75a. The list stays current while the engine is busy — PASS (page side), engine side not completed

- Judy's section 9 checks 1 to 9 on the real page (real headless Edge, real engine, proxy holding `/api/inventory` or `/api/state`): 22 of 22 pass. No line for a 4 s list; at 5 s exactly "List from 18:14. The app is busy; this updates by itself."; rows unchanged and no empty frame at any moment when the read is cancelled and asked again; the re-ask keeps text and time; at 10 minutes the escalated sentence in `--warning` (`#FFD58A`); status also silent gives "List from 18:14." and the page-top notice carries the cause, so the busy sentence never shows twice; a list from another day shows the date; the answer clears the line at once and leaves `#message` empty; a filter change during a stall blanks the rows, hides the line and puts the sentence in `#empty` only.
- Layout (Judy asked for the numbers): the line is 23 px high with 8 px margins, so the table moves down **39 px** (her estimate was about 30) once when it shows and once when it clears. The filter toolbar did not move and nothing overlaps the line (the chip strip was not on screen in this filter). Minor m5.
- Not exercised: S8 (the startup load strip up) cannot be forced on a loaded engine.
- The live-sized catalog test (1,572 books, a real queue running, 0.24.0 as control) was not completed. It was abandoned when the build changed to r2, after the catalog was grown and before a measurement. The entry check's tests cover that part. The SQL after-conversion check (Senua's) was exercised only by every conversion in this report finishing and cleaning up.

### 75b. Start over for a stopped book whose source changed — two Majors

Real stops, made on purpose: a book with a damaged middle ("Full audio decode failed … Header missing", the Салимов удел case in miniature) and a book whose destination is blocked by a file. Real replacement of the damaged file while the app ran.

- **M1. The press works, but the book does not go back to automatic processing.**
  - Before the press the row says `Stopped — source file changed`, hint "01.mp3 is not the file this job started with. Start over sends the book back to automatic processing.", one Start over button, no Retry (checked on the page after an engine restart: status, hint, button and the exact tooltip all match Judy's copy; the Retry-all count excludes the row and the chips count it under Other). The engine's data for the row is `startover: automatic`, `release_ok: false`.
  - The press answers 202 (`outcome: automatic`), the job is set aside, nothing is deleted.
  - Then the book sits at "Held — Manual draft retained. Automatic processing holds this book because it has a saved review." No job, no further move for the 4 minutes I watched, and the row offers no Approve button (Choose folder, Edit names, View metadata, Open source folder).
  - It happens on the automatic path (Tolkien, approved by the automatic pass, conversion stopped on the damaged file, file replaced, Start over) and on the manual path (approved by hand).
  - A normal Approve on that row (the engine says `can_approve: true`), then Start as for any Approve, queues it and it converts from the replaced file, filed with its series (`Властелин колец - 1 - The Fellowship of the Ring - Tolkien J. R. R.m4b`).
  - So the way out exists, but it is not the one the hint promises, and the row does not say "press Approve". Judy's spec has the "will hold the book" hint only when the engine says `manual_draft`; here it said `automatic` for a book that automatic processing then held.
  - Repro: any book with a saved review (approved by the app or by hand) whose conversion stops on a bad source file; replace the file; restart the app or wait for M2; Start over.
- **M2. The offer shows late.** After the file is replaced the row keeps reading "Stopped — see details. The conversion stopped. Select the row to read the technical message." with no action: about 100 s with an automatic run active, and **300 s** on a quiet app (polled every 10 s; not shown within 180 s in an earlier run; the engine reuses a quiet app's list for 5 minutes). After an app restart it shows at once. Sergei replaces the file and looks straight away, so he sees nothing to press.
- The press itself uses a fresh look at the files (it works whenever the engine's data says so).

### 74f. Author / reader column — PASS

- Engine: the list row carries the decided author and reader apart from the raw tag. A book whose artist tag is the reader gets `credits: author <real author>, reader <the tag>`; an undecided book `decided: false`.
- Page (real browser): the five cases of Judy's table 3.2 in the wide band, as text: `Author Pratchett Terry` + `Reader …`; author only; `Author Not decided yet` + `Reader …`; `Author Not decided yet` + `Clue …`; `Author Not decided yet`. The raw tag is never shown as the author. "Unknown" is gone from the column. "Not decided yet" is drawn in `--muted` (`#B8C6D5`). The narrow fold reads `Author · Reader: … · n audio files`, `… · n audio files` and `Author not decided yet · n audio files`. (Case 3 has no natural source; it and the other four were fed as the engine's own `credits` shape for five real rows, named here.)

### 74g and 74e wording — PASS

- The Recovery copies panel, with the engine's real payload and a copies-retained payload rewritten from it, shows Status, Original tracks backed up, Space, Recovery location. No "Automatic deletion" row and no "overdue copies" sentence. The rule stays on screen once, in the automatic-policy notice.
- The progress step reads "Removing source folders"; the jobs-help note reads "Source folders retained: …". The grep gate over the packaged web files finds no "24 hours", "overdue copies" or "empty source folders".

### 76a. His Approve or name Save wins — PASS, with two Minors

- Three books: one converting (a 60-minute book), two the automatic pass approved and queued behind it (live sources).
  - His Approve on the row as he saw it (an old revision, the files' fingerprint) with his own title replaced the automatic job; the book was filed as `My Own Hobbit Title - Tolkien J. R. R.m4b`.
  - The same Approve without the fingerprint was refused as before ("Candidate changed; reload evidence before reviewing").
  - His Save names with the fingerprint was accepted ("replanned"); after an Approve the book was filed under his saved title.
  - Approve on the book that was converting: refused with "This book is already converting, so it will finish with the automatic names. Your names were not applied."
- m1: that refusal says "the automatic names" also when the running job is his own earlier Approve (his names).
- m2: after his Save on a book the automatic pass had queued, the book came back "Held — Source membership uncertain" (the reason has nothing to do with his edit) and needed an Approve. By design ("replanned"), but the reason reads wrong.

### 76c. Approve accepts the English name the Goes to line shows — PASS, with a positive control

A catalog holding a rule `Киноко Насу` = `Nasu Kinoko` (written into the private catalog while its engine was stopped, as the repository's own test does), then «Decoration Disorder Disconnection 2» credited «Киноко Насу». The Goes to line reads `Nasu Kinoko\Decoration Disorder Disconnection 2 - Nasu Kinoko.m4b`. Approve with the Author field as shown: **the accepted 0.24.0 build refuses** with "Enter the author's English name, then approve. Nothing was changed."; **0.24.1 accepts** and files under `Nasu Kinoko`.

### Hidden-app check on r1

Same result as on r2 (displayed and engine version 0.24.1, close hides, Quit exits 0, payload unchanged, `intrusion: null`, the tray list restored byte for byte). It was run once on r1 and once on r2.

## D. Findings

**No Blocker.**

### Major

- **M1 — Start over on a changed source file does not send the book back to automatic processing** (75b). See C2. It ends "Held — Manual draft retained" and needs a normal Approve. Fix next cycle, or hold the release if Sergei expects Start over alone to finish Салимов. Ender and Judy: the engine's `startover` value, the hint and the held row.
- **M2 — The Start over offer takes up to 5 minutes to show** (75b). See C2. Restart shows it at once.

### Minor

- m1 76a refusal wording says "automatic names" when the names were his.
- m2 After his Save, a queued book comes back held with an unrelated reason ("Source membership uncertain").
- m3 A book folder directly under the source root keeps its cover (design; Jane to confirm).
- m4 77: the record for a name carrying an audio extension does not name the file.
- m5 The stale line moves the table 39 px, not about 30 (Judy's estimate).

### Observations

- O1 A fault at the recovery-cleanup step stays "needs attention" after the fault is lifted and after a restart (not 77, not compared with 0.24.0).
- The 77b fault at exactly the folder step was not reached live.
- 75a engine-side load test and S8 were not run.
- Carried from 0.24.0, not re-tested: the finished-book-held-open Major (M2 of the 0.24.0 report) still needs a disposition.

### Pattern alert P1

"A change on disk, or an earlier fault, shows only after a restart or a long delay." Seen: 0.24.0 first pass (a moved book not ready until restart, a held file never recovering, a recovered move not ready for 25 s); 0.24.1: the Start over offer (M2) and the recovery-cleanup fault (O1). Each time the engine's reuse of a quiet app's state, or a one-shot record, hides what is true on disk. Disposition needed from Jane: fix, accept or defer.

## E. Limits of this pass

- Test only what changed. For r2 that is ruling 77 and the hidden-app check; everything else is r1's result, valid because r2's diff does not touch it. The two builds differ in `storage_cleanup.py`, so the 74e and 76b results were re-run on r2.
- Live sources were used once (Tolkien) at the app's own pacing. The first-run setup window and the page's Choose folder dialog were not exercised.
- The repository tests were not run (the builder's entry check covers them).
- A tray cleanup tool and the hidden-app helper copy of mine were not reviewed by Senua.
- The tool repo had uncommitted edits in `merge_service.py` and `storage_cleanup.py` for part of the r1 pass (Ender's r2 work). Every test ran on the verified installers' payloads, never on the working tree.

## F. Cleanup and personal folders

- **Removed.** My scratch folders `q241\f1` and `q241\f2` (the extracted payloads of both builds, catalogs, converted audio, drivers, tray exports, screenshots; 1,402 files, about 1.99 GB), one file and one directory at a time with non-recursive primitives. The studio sweep and planner refuse a path under Worktrees that is not a `<Tool>\<purpose>` entry, and `q241` also holds Ender's runs, so I could not use them. `q241\r1`, `q241\r2` and `q241\main-dist-0.24.0` were only read.
- **Left clean.** No headless-browser lease, no test engine or app process, no deny ACL (every one I set was lifted and read back), my scratchpad scripts deleted. The tray key equals its pre-run export (section C1).
- **Handles on dist.** None of my processes ran from, or opened a file in, the repo's `dist/` folder (a scan of running programs found none there), and none holds `q241\r1\dist` or `q241\r2\dist`; I read those only to hash them, and to run the hidden-app helper against r2's manifest, which has ended.
- **Personal folders** (`scripts/qa/personal-folders.mjs`, snapshot taken about two hours into the pass, compared at the end; each browser lease also reported clean when it closed):

```
personal folders: clean (5 subfolder notes) (7 folders, 10 drive roots watched)
  SUBFOLDER D:\SteamLibrary | changed below the depth checked
  SUBFOLDER E:\SteamLibrary | changed below the depth checked
  SUBFOLDER F:\SteamLibrary | changed below the depth checked
  SUBFOLDER H:\SteamLibrary | changed below the depth checked
  SUBFOLDER I:\SteamLibrary | changed below the depth checked
```

Nothing of mine is in a personal folder; the five notes are another program's folders below the depth checked, listed and left alone. The builder's receipt lists the same five.
