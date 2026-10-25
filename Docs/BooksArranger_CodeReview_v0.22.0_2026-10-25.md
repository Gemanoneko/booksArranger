# Code Review — Books Arranger v0.22.0

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-25
Tool: Books Arranger (Electron / Python)
Release: v0.22.0
Commit range: b467308c00d11452f7b3adf8952c20589fc33b8b..7490b39524ec702ece35c3d5ca657d366c229786 (tag v0.21.2 .. 7490b39, 84 commits; first certified to 9b8ab23, extended by the deltas 9b8ab23..b946ee7, 6 commits, b946ee7..01581a6, 17 commits, and 01581a6..7490b39, 19 commits)
Release source commit: 7490b39524ec702ece35c3d5ca657d366c229786
Release artifact manifest SHA256: c8b910ced753088904208ea0fbee8db26dbbfc003155a1f2acb1ed88fb5b34fc
Reviewed source: C:/Antigravity Projects/Worktrees/Books Arranger/review-0220f (detached worktree at 9b8ab23), review-0220c (at b946ee7), rv0220d (at 01581a6) and rv0220f (at 7490b39, for the final delta); each removed after its review
Files changed: whole range 121 files, +13791 / -489; delta 9b8ab23..b946ee7 8 files, +238 / -22; delta b946ee7..01581a6 31 files, +1938 / -123; delta 01581a6..7490b39 50 files, +2433 / -354 (git diff --shortstat). At 9b8ab23: product code and scripts 29 files, +3480 / -229; tests 59 files, +3049 / -143.
  Docs and CHANGELOG: 10 files, +3036 / -1. package.json and package-lock.json: version only.
  New since my early review (bc3362d..9b8ab23, 5 commits): 19 product files, +860 / -108. part_sets.py +196 (new), groups.py +180/-21,
  local_identity.py +93/-6, merge_service.py +87/-28, public_research.py +59/-8, web/app.js +56/-20, author_rules.py +45,
  audio_pipeline.py +44/-1, split_books.py +19, web_server.py +15/-5, gate scripts +22/-7, smaller edits in 6 more.
Stand-down dimensions: none
```

**What this report certifies.** The whole range from the `v0.21.2` tag to 9b8ab23. It folds in:
- the cancelled 0.21.3 (d0e6962 and before), whose findings F1–F8 I recorded in `Docs/BooksArranger_CodeReview_0.21.3-changes_2026-10-24.md` and re-checked in my early review (all fixed in 4d89eb1);
- my early 0.22.0 pass (`Docs/BooksArranger_CodeReview_0.22.0-early_2026-10-24.md`, up to bc3362d), whose G1–G6 and m1–m9 are re-checked below;
- five new commits: 1e0cb03 (G1–G6, m1–m5, m7–m9, Approve's destination check), ac08aa2 (M4B part joining, `part_sets.py`, ruling 19 for bare-numbered sets), 663429f (copy, fifth gate worker), d4ddaef (Keep as separate books), 9b8ab23 (version bump);
- the delta 9b8ab23..b946ee7 (N1, N3–N6, N9), the delta b946ee7..01581a6 (N10, N11, N12, Futaba's chip blocker and M-1 to M-3, Delete book, the 403 body drain, the six-worker gate) and the final delta 01581a6..7490b39 (N13–N17, rulings 24, 24a, 25 and 26, Futaba's M-4, m-9 to m-13 and m-3, the scan-wait helpers, the seven-worker gate), each in its own section below.

Rulings checked against: `Team/Docs/BooksArranger_Rulings_2026-10-24.md` (2, 2b, 10, 14, 19, 19a, 19b, 23, 24, 24a, 25, 26) and `Team/Docs/BooksArranger_AuthorRulings_2026-10-24.md`.

**Artifact pin (final candidate 7490b39, replaces the 01581a6 pin).** Ender's manifest is `C:/Antigravity Projects/Worktrees/Books Arranger/cand-0220f/dist/release-artifacts.json`. I recomputed every value myself, read-only (a script in my session scratch, using the repo's own `release-contract.mjs` and `gitEntries`):
- Manifest SHA-256 `c8b910ce…f88b5b34fc`: the same over the file's bytes and over its UTF-8 string (no BOM). It equals Ender's value.
- `version` 0.22.0; `source_head` 7490b39524ec702ece35c3d5ca657d366c229786; `build_id` 8bbb0346-cc54-436c-b9e7-ae8feb32c941; `latest.yml` reads `version: 0.22.0`.
- `product_digest` `84c3b1a9…eb743f` equals `productTree(ls-tree 7490b39)`.
- The repo's own `artifactContract(manifest, {version: '0.22.0', productTree})` accepts it: three artifacts, payload verified, shell and backend 0.22.0, `installer_equivalent` true. `payload.manifest_sha256` matches its file map (279 files); the runtime lists 48 files.
- Each artifact's bytes match the manifest's size and SHA-256:
  - `Books-Arranger-Setup-0.22.0.exe`: 173,952,430 bytes, `74a1622dc7ed1ca69b6fff6893b40eda8d96edf29db6eb63b96d7cb76ccf024e` (Ender's value);
  - the `.blockmap` (181,502 bytes) and `latest.yml` (360 bytes).
- The `cand-0220f` worktree is at 7490b39 with a clean tree.
- The 01581a6 pin below (manifest `b1d3e975…f89037835`, installer `e70b90b5…20db63a`) and every earlier pin are superseded.

**Earlier pin (01581a6, superseded).** Ender's manifest was `cand-0220c/dist/release-artifacts.json`. I recomputed every value myself, read-only:
- Manifest SHA-256 `b1d3e975…f89037835`: the same over the file's bytes and over its UTF-8 string (no BOM). It equals Ender's value.
- `version` 0.22.0; `source_head` 01581a672adc5cd0d1fc45a641bce112a2a3d825; `build_id` 66e2795b-3b6c-462a-bff8-3843b109d7fc; `latest.yml` reads version 0.22.0.
- `product_digest` `2502fa98…6439dcc` equals `productTree(ls-tree 01581a6)`, computed with the repo's own `release-contract.mjs` and `gitEntries`.
- The repo's own `artifactContract(manifest, {version: '0.22.0', productTree})` accepts it: three artifacts, payload verified, shell and backend 0.22.0, `installer_equivalent` true; `payload.manifest_sha256` matches its file map.
- Each artifact's bytes match the manifest's size and SHA-256:
  - `Books-Arranger-Setup-0.22.0.exe`: 173,916,078 bytes, `e70b90b5019ee6c650e5dc14a34a9cb4dfea5d1ac7909f11a4af3b05c20db63a` (Ender's value);
  - the `.blockmap` (181,456 bytes) and `latest.yml` (360 bytes).
- The `cand-0220c` worktree is at 01581a6 with a clean tree.
- The b946ee7 pin below (manifest `7d52a894…a26dd21a`, installer `6e7fd420…b0fd5`) and the 9b8ab23 pin are superseded.

**Earlier pin (b946ee7, superseded).** Ender's manifest was `cand-0220b/dist/release-artifacts.json`. I recomputed every value myself, read-only:
- Manifest SHA-256 `7d52a894…a26dd21a`: the same over the file's bytes and over the UTF-8 string `release-flow.mjs` hashes (no BOM). It equals Ender's value and the one in his `logs/ender-pack.log`.
- `version` 0.22.0; `source_head` b946ee732be82acdbd56efa351bd1dce96d9880e; `build_id` 8747da8c-8d36-41c2-9fc3-8959ef6a3978.
- `product_digest` `cdbba6eb…a48dab` equals `productTree(ls-tree b946ee7)` computed with the repo's own `release-contract.mjs` and `gitEntries`.
- The repo's own `artifactContract(manifest, {version: '0.22.0', productTree})` accepts the manifest (three artifacts; payload verified, shell and backend 0.22.0, `installer_equivalent` true).
- Each artifact's bytes match the manifest's size and SHA-256:
  - `Books-Arranger-Setup-0.22.0.exe`: 173,883,415 bytes, `6e7fd42079a25a0d55e93e036ad787e1fe781585386df80bc8dcbbeb7ceb0fd5` (Ender's value);
  - the `.blockmap` (181,371 bytes) and `latest.yml` (360 bytes).
- `payload.manifest_sha256` matches its own file map.
- The `cand-0220b` worktree is at b946ee7 with a clean tree.
- The earlier pin (9b8ab23, manifest `4241fdae…8331e9`, installer `ee4ceba1…9c2525`) is superseded.

---

## Summary

**Update for the final candidate (7490b39).** Still no Critical finding, and the safety floor is intact. No Major finding is open. Details are in the section "Delta 01581a6..7490b39".
- **N13 to N17 are closed.** Delete and its preview refuse while a scan runs, at the route and again in `plan()`. A scan skips a file or folder that is gone, but only when a folder it can list shows the name gone. So a dropped share is still an error.
- **Remove this copy cannot delete a recording that is not a proven copy, and cannot touch Sorted.** The press proves everything again: each copy file's SHA-256 against the source the audiobook was made from, then the audiobook's full output check. It then holds the audiobook open while the copy goes. Junctions, hard links and case variants are refused.
- **Empty folders go only by a plain rmdir, after the listing shows nothing.** Never one directly in a source folder, never in Sorted. Every other path keeps the old refusal. The last working copy goes only through Delete book's own press.
- **M-4:** a double press or a page reload cannot approve twice. The server takes the second press after the first and refuses it.
- **Three new Minor findings:** N18 (two cases where "the folder holds no other book" is wrong), N19 (Remove this copy's proof runs under the app's locks, cannot be stopped, and has a 120 s page limit), N20 (no recorded answer on the copy's cover and text files).
- **The gate:** all 101 modules once each, across seven workers. The scan-wait helpers make no test pass without checking.
- **The artifact** for 7490b39 matches its manifest, and the QA entry script is a six-line copy.

**Update for the candidate 01581a6.** Still no Critical finding, and the safety floor is intact. Details are in the section "Delta b946ee7..01581a6".
- **Delete book cannot reach anything but the book's own audio.** I probed it on real files: a folder swapped for a junction into Sorted, and a real Need to reacquire marker. Both behaved safely, and Ender's tests cover the other cases. Files go first, one exact handle at a time. Records go only when every member is gone. Each row is offered by the server itself.
- **One new Major (N13, closed at 7490b39): Delete book runs during a library scan.** That includes the scan at the start of every automatic run. If the scan has already queued the book's files, the deleted book comes back as one book per deleted file, each with a raw "[Errno 2] No such file or directory" error. The scan ends "completed with errors", which stops an automatic run. Probe P1 shows it. Nothing is lost.
- **N10 is closed.** On the live catalog, read-only, «Пастушья корона» is one 77-file book again, and nothing else in the grouping changed.
- **N11 is narrowed** from 21 held albums to 17.
- **N8 and N12 are closed.**
- **New Minor findings:** N14 to N17 (all closed at 7490b39).
- **The gate:** it runs all 101 modules once across six workers, plus the side chain, and fails on any failure.
- **The checker change (a4783ba) is trustworthy.** The committed `entry-main.mjs` is byte-identical to the version I cleared for QuickLaunch (`eb8952ee…`). Its Git branch is inert for Books Arranger, whose context pins no Git.

**Update for the rebuilt candidate (b946ee7).** The six new commits close N1, N3, N4, N5, N6 and N9; my probes and in-memory mutants agree (section "Delta 9b8ab23..b946ee7" below). Keep can no longer answer "kept" without the split: every write is one transaction, and a refusal or an error leaves the catalog byte-for-byte as it was. **One new Major (N10): N4's fix stops the one live same-title set, «Пастушья корона» (77 chapter files), from joining.** Measured read-only on the live catalog: one book at 9b8ab23, 77 lone files at b946ee7. Nothing is converted wrongly and no file is touched; the files stay held, as they are under 0.21.2 today. N6's fix holds 21 live albums, and none of them is two books (N11, Minor). Still no Critical finding, and the safety floor is intact. The text below this paragraph is the review at 9b8ab23; its findings are marked where the delta closed them.

There is no Critical finding, and the safety floor is intact. Every delete in this range still happens only after a verified result is in Sorted, and that holds for joined M4B parts: a failed join leaves every part byte-for-byte untouched, and the joined book's chapters land exactly where each part's audio starts (measured in the decoded output, not taken from the plan).

**G1–G6 are closed.** I re-ran my own cases end to end on real private files, and each mutant that undoes a fix is caught by Ender's tests. Three narrow leftovers of the same family stay open as Minor findings (N4, N5, N6). None of them shows up on the live catalog today.

**One new Major finding (N1): Keep as separate books can report success and change nothing.** On a set whose group holds a saved review (Save in the details panel), Keep records the files, answers `{kept: 2}` and shows "Kept as 2 separate books", but the regroup leaves the protected set as it is. The next research asks the same set again, and every further Keep press "succeeds" the same way. No file is touched.

**The explicit-marker join skips every chapter caution, by ruling 19a (N2, Minor).** Two different books named "Часть 1. <Book A>" and "Часть 2. <Book B>" in one album are joined on their own and both originals are removed (probe J1, end to end). On the live catalog, all 69 explicit-marker sets join; read-only, I found none that is two books. Running `part_sets.decide()` on them would be worse: it would keep "Мерзость", "Сердце Пармы" and "Красные цепи" apart as separate volumes and ask about the 11 Wheel of Time books (each one book over 30 h). I log it for Sergei's attention rather than as a code defect.

**Answers to the four questions.**

1. **G1–G6.** Closed; details in the G-table below.
2. **Joining.**
   - *Can two different books be joined?* Through `decide()` (bare-numbered sets): only along the routes ruling 19b accepts (continuing chapter numbers; end matter only in the last file under one title tag), plus the three edge routes in N3. Through the explicit-marker route: yes (N2, J1). Through Sergei's Approve as one book or Convert what's there: yes, by his choice.
   - *30 h+, seasons, volume pattern?* In `decide()`: over 30 h is always asked (mutant M02 caught); "Сезон N" and "sNNeNN" are asked (M03 caught); every file restarting at chapter 1 or ending with its own afterword is never joined (my probes agree). The afterword rule and the "a file starting at chapter 1 never continues" guard have no test of their own (M22 and M18 survived, N9). Gaps (N3): "Эпизод N" numbering that continues joins; "Том 1 / Том 2" with continuing chapters joins while "Книга 1 / 2" is asked; a set holding three works where one spans two files joins. On the live catalog no `decide()` join has season or tome words, more than one work, or over 30 h (read-only measurement below). On the explicit route, all cautions are skipped (N2): 11 live explicit sets are over 30 h, all of them one Wheel of Time book each.
   - *Chapter offset math.* Correct. Probe J4 joined five explicit parts of 1.3 / 0.7 / 2.1 / 0.9 / 1.6 s (22,050 Hz, different tones). Each part boundary in the plan equals the sum of the decoded part durations, and in the decoded output the tone changes at every planned boundary (300 → 708 Hz at 1.300 s, 700 → 1092 Hz at 2.043 s, 1100 → 1492 Hz at 4.180 s, 1500 → 1883 Hz at 5.108 s). Every chapter start lands on its part's audio. A part without chapters became one chapter named after it. The plan is built from `decoded_duration` (counted PCM frames), and the encoder is fed exactly those frames (`stream_normalized`), so AAC priming in the parts does not drift the offsets.
   - *Source removed only after the joined output is verified in Sorted?* Yes. The joined job is an ordinary v4 job: output verification (duration, full decode, chapter titles and boundaries against the plan) and then the Sorted-only cleanup, which now reads the joined plan (`source_cleanup.py:233`). Mutant M06 (cleanup ignores the joined plan) is caught: the cleanup refuses and the originals stay.
   - *Failed join leaves the parts untouched?* Yes. J5a (failure while placing chapters) and J5b (failure at output verification): the job needs attention, both originals keep their SHA-256 and modification time, nothing is in Sorted, and no cleanup row exists. Encoding reads only the protected stage copies, and the in-place M4B path (ruling 2b) is offered for one source only (`inplace_m4b.py:195`).
3. **Keep as separate books.**
   - *Touches no file:* confirmed (Ender's test plus mine: sizes, times, no job, nothing in Sorted). It writes only `part_volumes` rows.
   - *Can't loop:* on an ordinary set, confirmed. After Keep, two full scans form no set again, each file researches with no reason, a second Keep on the old row is refused, and Keep on a non-set row is refused (K2, K3). The server-side "only an asked set" check has no test that fails without it (M07 survived, N9). On a set with a saved review it loops (N1).
   - *Remembered choice:* keyed by root, path, size and time. A changed file is judged alone (Ender's test). Only Sergei's Keep writes the "Kept separate by you" basis that skips the part-of-a-set rule at admission (M08 caught). Research-decided volumes still take that rule in the code, but no test notices if they are treated as kept (M21 survived, N9). A Keep has no undo and no confirmation (N7).
4. **The five-worker gate still runs everything.** The gate's own `pythonBatches` places all 100 declared patterns exactly once over five workers, the five reports of my real gate run match that partition exactly, and the gate's own `validatePythonReports` accepts them: 1,581 cases, 0 failures, 0 errors. The one skip is the opt-in private MP3 fixture (`ActualPrivateStagingTests`), which is absent on this machine, so my gate run exits 1 at the zero-skip check. That is environment, not code. Worker 0 took 509.9 s of the 540 s deadline under concurrent load (N8).

---

## Rubric

### 1. Security

- Status: Pass (at 01581a6 too: Delete book's file-delete guards hold under my probes, N14. At 7490b39 too: Remove this copy, the wider Delete book and the folder removal keep every guard; see the section "Delta 01581a6..7490b39")
- Findings: none.
  - The new route `/api/candidate/keep-separate` goes through `shape()` with exactly `{library, id, revision}`, the scan-active refusal and the closing check. `/api/candidate/approve` gains one bounded text field (`path`, 1000 characters).
  - The one new process call is `part_sets.read_chapters`: `ffprobe` with an argument list (no shell), `-protocol_whitelist file`, stdin closed, no window, a 60 s timeout, on absolute catalog paths.
  - Nothing under `desktop/` changed. No secrets in the diff (grep for key, secret, password, token and bearer patterns). No commit in the range carries a Claude attribution trailer.

### 2. Correctness & Logic

- Status: Concerns (at b946ee7: N1, N3, N4, N5, N6 closed; N10 and N11 new, see the Delta section. At 01581a6: N10 closed, N11 narrowed to 17 albums; N13 to N16 new. At 7490b39: N13 to N16 closed; N18 new; see the section "Delta 01581a6..7490b39")
- Findings:
  - **N1 [Major, closed at b946ee7]** `merge_service.py:2157-2177` (`keep_separate`), `groups.py:607` (`sync`: a group with a saved review is protected). **Keep as separate books on a set with a saved review reports success and changes nothing.**
    - What happens: `record_volumes` stores the files, then `groups.sync` regroups. The set's group is protected (`r['review']`), so its members are `assigned` and never re-scoped as volumes. The set stays one candidate.
    - Probe K1 (real private .m4b files, the seasons fixture): asked as `set_seasons` → panel Save (`reviews.save`) → still listed → Keep returned `{'kept': 2}` → the catalog still holds one 2-file group → research again: `['Source membership uncertain', 'One part of a bigger book']`, decision `ask`.
    - The UI shows "Kept as 2 separate books. Each is checked again." The row comes back after the next research, and every further Keep press "succeeds" the same way. Keep is inert only on *unsaved* panel edits (`web/app.js:2085`), so this path is open.
    - The Brief's Keep row says it "regroups at once"; that is not true here.
    - **Fix (Ender's choice):** refuse Keep on a protected group with a sentence that says why, or drop the saved review's protection for these members as part of Keep. Either way, return the number of new candidates the regroup actually made, not `len(members)`.
  - **N2 [Minor]** `split_books.py:72-84` (`EXPLICIT_PART`, `joinable_parts`), `public_research.py:654` (`_part_set` returns None for an explicit split book), `merge_service.py:2390-2393`. **An explicit-marker set is joined whatever its chapters say (ruling 19a).**
    - Probe J1: `Часть 1. Последнее желание.m4b` and `Часть 2. Меч предназначения.m4b`, album "Ведьмак", one artist, no title tags, each part restarting at "Глава 1". The split rules accept them, since a part marker may carry a name. Research gave no reason, and the job completed as `Сапковский Анджей\Ведьмак - Сапковский Анджей.m4b` with chapters Глава 1, Глава 2, Глава 1, Глава 2. **Both originals were removed.** `decide()` would have said `ask`.
    - Live catalog (read-only, chapters read with ffprobe): 69 explicit sets, all joined. Had `decide()` run on them, it would say join 29, ask 37 (11 over 30 h, 24 unclear, 2 authors) and volumes 3. Reading the names, all 69 are one book each: Harry Potter "Часть I / II", Wheel of Time "Часть 1-5", "Мерзость: Часть 1. Альпинисты / 2. Гора / 3. Мерзость". So the explicit route is right for today's library, and `decide()` is not the fix.
    - Why Minor: the code does what ruling 19a says, nothing is lost (both books are inside the one output, chapters kept), and no live set is affected. The only signal that would catch J1 is a later part restarting at chapter 1 under a distinct name; on the live catalog that would also ask about "Мерзость" and "Wolves of the Calla". **That trade-off is Sergei's call, through Jane.**
  - **N3 [Minor, closed at b946ee7]** `part_sets.py:139-196` (`decide`). **Three edge routes join where ruling 19b says to ask or never join.** Pure probes of `decide()`:
    - "Эпизод 1-10" then "Эпизод 11-20", same title tag: `join`. Ruling 19b asks on "season/episode markers"; the code treats episodes as chapters.
    - "Собрание сочинений. Том 1 / Том 2" with continuing chapters: `join`. The same files with "Книга 1 / 2" are asked (`book_words`). `TOME_WORDS` is used only on the restart branch.
    - Four files whose title tags name three works (Альфа 1, Альфа 2, Бета, Гамма) with track-like numbering that continues: `join`. Ruling 19b asks on joins "holding several works"; `works` only says volumes when every file names a different work.
    - Live: none of the 89 `decide()` joins has season or tome words, more than one named work, or more than 30 h (read-only measurement). **Fix:** treat "Эпизод" and "Том" like "Книга" (a caution), and ask when the files name two or more works.
  - **N4 [Minor, closed at b946ee7; the fix causes N10]** `groups.py:298` (`_same_title_sets`). **G2's fix is a word list; other generic title tags still join two books.**
    - Probe: `Кинг - Оно.mp3` and `Кинг - Мизери.mp3`, artist "Стивен Кинг", both tagged "Неизвестно" (or "Новая запись"). Result: one group, accepted with no reason, titled "Неизвестно" by King Stephen, so it converts on its own.
    - "Track 01" is held as a part, and "Аудиокнига", "Без имени", "Audiobook", "Unknown" and "Книга" stay separate.
    - At v0.21.2 the same files stayed six separate held candidates (same probe, run on a `git archive` of the tag).
    - Live: one same-title set (Пастушья корона, 77 real chapter files), so no hit today.
    - **Fix:** apply G1's works check to same-title sets: files whose file-name titles name two or more works are not joined.
  - **N5 [Minor, closed at b946ee7]** `local_identity.py:1818-1824`. **G4's split handles exactly two names.** An artist tag "Александр Варго - Иван Сидоров - Мария Петрова" is accepted whole as the author. Two names ("Варго Александр - Сидоров Иван" included) are asked as Author unclear, as fixed. **Fix:** split on the dash whenever two or more pieces look like people.
  - **N6 [Minor, closed at b946ee7; its cost is N11]** `groups.py:390-417` (`_same_album_parts`). **G3's works check covers only the new same-album join, not a plain album group.**
    - Probe: one folder, album "Ведьмак", one artist, no album artist, tracks 1-4, title tags "Последнее желание 1/2" and "Меч предназначения 1/2". It is one partition group (one album and one artist, as before this range), and v5 accepts it as "Ведьмак" with no reason, so it converts on its own. At v0.21.2 the offline research held it ("Book identity uncertain"); with the Internet it would most likely have matched a public "Ведьмак".
    - Live: 21 plain album groups repeat two or more title works; by name all are one book or one anthology.
    - **Fix:** run `_works` on plain album groups too.
  - **N7 [Minor]** `web/app.js:2188-2193`, `merge_service.py:2157`. **Keep as separate books has no undo and no confirmation.** After Keep, each file researches with no reason (K2), so a slip turns one book into separate books that convert and are filed on their own. Nothing in the UI removes a "Kept separate by you" row. Judy's spec chose no confirmation; Jane may want to ask whether an undo is needed before the first live sweep.
  - Carried from the early review: **m6 [Minor]** `author_rules.py:51-62`, no `retract` kind (not in 1e0cb03's list).

### 3. Crash / Stability Safety

- Status: Pass
- Findings: none new. m4 is fixed: drain and close set every press's stop event (`merge_service.py:705, 3318`), and an interrupted press answers "Books Arranger is closing. The book was not approved." (M17 caught). `read_chapters` turns an unreadable or timed-out probe into `None`, which `decide()` answers with `ask`.

### 4. Performance

- Status: Concerns (at 7490b39: N19, Remove this copy's proof under the app's locks; see the last Delta section)
- Findings: none up to 01581a6.
  - Live catalog, read-only: one regroup (`groups.build`) takes 3.0 s for Z:\Audiobooks (9,623 files, 1,391 groups) and 1.1 s for Z:\OLD_Audiobooks, so Keep's committed sync fits in the 15 s press.
  - Reading the chapters of every multi-part .m4b set in both roots, 223 sets, took about 4 minutes in total on the NAS. Research reads a set's chapters once per research, and held books are re-researched only on change (ruling 5).

### 5. State & Data Safety

- Status: Pass (safety floor intact; at 01581a6 Delete book removes only the confirmed book's own audio, by Sergei's ruling 23, and records go last. At 7490b39 it also removes the book's own other files, working files and the folders it leaves empty (rulings 24, 24a, 26), and Remove this copy removes only a proven copy (ruling 25); every path is one Sergei confirmed in the dialog)
- Findings: none beyond N1, N2 and N7, which are data-organization findings: no audio is lost and nothing is removed outside Sorted.
  - **Deletion rule (ruling 2) for joins:** a joined book's originals are removed only by the ordinary cleanup, after output verification and with the result in Sorted (J4: cleanup `completed`, sources gone only after `final_path` existed in Sorted). A failed join removes nothing (J5a, J5b).
  - **Frozen plan:** every part's chapters are frozen at manifest time and re-read from each protected snapshot before encoding; a change refuses (Ender's test; M05 caught).
  - **Keep** writes only `part_volumes` and runs one committed `groups.sync`; it approves and moves nothing.
  - **Research writes:** a `volumes` decision writes `part_volumes` from the research thread. That is a catalog write, not a file write, and it only splits a set into single-file candidates, which then pass the unchanged part-of-a-set rule at admission.
  - **Upgrade:** 0.22.0 ignores the 0.21 `part_chapters` facts and regroups those parts as sets. Read-only check of the live catalog: 180 facts in 61 folders, and no folder where some parts were already converted alone while others remain, so no half-converted set can be joined without its first part.

### 6. Input Handling

- Status: Pass
- Findings: none. Keep takes only identity fields. `path` on Approve is bounded, compared with `normcase(normpath(...))`, and a mismatch refuses with nothing queued (m1; M16 caught).

### 7. Maintainability (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **m7, second half [Minor]** `scripts/check-desktop.mjs`. The two modules I named are gated now (`test_split_books`, `test_collection_identity`). 23 test modules are still outside the gate (list in Tests run). The early review's "fix or retire the rotting suites" is not done.
    - Run in one process in my worktree, the 23 modules give 266 cases, 38 failures or errors, in 10 modules (test_start_over 11, test_app_launcher 9, test_fresh_stat 6, test_chapter_repair 4, and 6 more). That is not like-for-like with the early review's isolated fifth worker (339 cases, 28 in 8 modules), and some of it is environment (Tk), but the suites still rot outside the gate.
  - **N9 [Minor, closed at b946ee7]** Tests. **Five rules in the new join and Keep code have no test that fails without them.** Each mutant below passed every suite that covers its file:
    - M07 `merge_service.py:2167`: Keep accepts any split-book or part-set row, not only an asked set. The UI shows Keep only on set rows, so this server check is the only guard against a stale or hand-made request.
    - M18 `part_sets.py:189`: "continues" without `after[0] > 1`, so two files that each hold only "Глава 1" read as continuing.
    - M19 `groups.py:342`: part sets formed from mixed recordings. Admission re-checks audio profiles only for split books (`merge_service.py:2416`), not part sets, and the automatic policy resamples mixed rates and channels instead of refusing them, so this grouping filter is the only guard.
    - M21 `groups.py:104`: every research-decided volume counts as "kept by you" and skips the part-of-a-set rule at admission.
    - M22 `part_sets.py:165-166`: the "each file ends with its own afterword" rule. The Toradora test passes through the restart rule instead.
    - **Fix:** one test per rule, each a case only that rule decides.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **N1's Brief row:** "regroups at once" does not hold for a set with a saved review. *Fixed at b946ee7: the Keep row now describes the split, the dropped panel values and the refusal.*
  - **At b946ee7 (N10):** the Guard 2 row still names "77 chapters of «Пастушья корона»" as one book; at `same-title-v3` they are 77 lone files. *True again at 01581a6 (`same-title-v4`, measured on the live catalog).*
  - **At 01581a6 (N17):** `Handler.refuse` says its drain takes "2 s at most"; the timeout is per read, not in total. *Fixed at 7490b39: the 2 s are now a total.*
  - **At 7490b39 (N20, Minor):** the Brief and code take Judy's default that Remove this copy also deletes the copy's cover and text files; no ruling records Sergei's answer. See the last Delta section.
  - m8 is fixed: the Brief's guard 1, guard 2 and ruling 6b rows now match the code.

### 9. Build & Release Hygiene

- Status: Concerns
- Findings:
  - **N8 [Minor, closed at 01581a6]** `scripts/python-check-batches.mjs:24`, `tests/python-check-batches.test.mjs:36`. **The 70 % projection guard does not see worker 0's real time under load.** *Closed: the weights are now each module's time under concurrent load, and the gate uses six workers (projection 386-388 s, bound 432 s). Ender's entry run of 01581a6 took 364-400 s per worker against the 540 s deadline.*
    - My gate run, with other gate runs active on the machine: workers took 509.9 / 303.5 / 443.5 / 429.1 / 446.4 s, against projections of 347 / 348 / 346 / 346 / 346 s and a 540 s deadline. Ender's quieter run took 328 / 213 / 307 / 292 / 297 s. Jane reports his later worker 0 at about 490 s while my mutants ran.
    - Worker 0 holds every serial server suite (433 cases), so it grows most under contention. The deadline still fails closed; the risk is a flaky gate, not a false pass.
    - **Fix:** give worker 0's serial modules a contention margin in their weights, or split the serial set across two workers where the suites allow it.
  - Version bump present: package.json and package-lock.json both read 0.22.0, in one commit (9b8ab23). The CHANGELOG has a 0.22.0 entry that says 0.21.3 was never released and lists its changes under "Fixed (from the unreleased 0.21.3)".
  - The artifact manifest pins 7490b39 and 0.22.0 (Header). At 7490b39 the gate runs seven workers; all 101 modules are placed once.

---

## G1–G6 and m1–m9 (early 0.22.0 review), re-checked at 9b8ab23

| # | Status | Evidence (my probes on real private files, offline; mutants on copies of 9b8ab23) |
| --- | --- | --- |
| G1 | Closed | `01 Сапковский - Последнее желание` / `02 … Меч предназначения`: two books, each accepted as itself. Also separate with the folder named "Andrzej Sapkowski", "Sapkowski Andrzej - Witcher", "Pratchett Terry", "Terry Pratchett - Discworld" or "King Stephen". M10 and M11 caught. |
| G2 | Closed, residual N4 | "Аудиокнига": two books ("Оно", "Мизери") by King Stephen. "Без имени", "Audiobook", "Unknown", "Книга" also separate. M12 caught. |
| G3 | Closed, residual N6 | The Ведьмак disc case (a reader per book): held, "Source membership uncertain", works listed ("Последнее желание" 2, "Меч предназначения" 2); one file per book is held too. M09 caught. |
| G4 | Closed, residual N5 | "Александр Варго - Иван Сидоров": Author unclear. Surname-first spelling also asked. M13 caught. |
| G5 | Closed | A real automatic run with a 260-character title: Held, "Verified metadata exceeds the supported Windows output path length", `until_change` False, listed 1, still checking 0. M14 caught. |
| G6 | Closed | `Rules.changed_for` re-researches only books whose seen credits or folders a newer rule names; a cut list records `None` and is re-researched on any rule. M15 caught. |
| m1 | Fixed | Each press sends the Goes to line; a different destination refuses with nothing queued. M16 caught. |
| m2 | Fixed | Typed "Терри Пратчетт" goes to `Pratchett Terry\Мор - Pratchett Terry.m4b`. |
| m3 | Fixed | A Same author? answer is passed as `chosen`, recorded "Your Same author? answer". |
| m4 | Fixed | Drain and close set every press's stop event. M17 caught (Quit waited 20 s behind the press with the mutant). |
| m5 | Fixed | The gate prints each worker's real seconds and records them in its pass line (seen in my run). See N8. |
| m6 | Open | No `retract` kind. |
| m7 | Half fixed | The two modules are gated; 23 modules remain outside the gate. |
| m8 | Fixed | Brief rows corrected. |
| m9 | Fixed | A test reaches `approve_automatic`'s second safety filter. |

---

## Tests run

All runs were on the detached worktree of 9b8ab23 at `C:/Antigravity Projects/Worktrees/Books Arranger/review-0220f`, never in `WIP/`, `cand-0220` or `qa-run-0220`. Runtime: the gate's pinned Python 3.14.8 and FFmpeg, copied from `b0220/build-cache/qa-runtime` into my worktree and checked against `scripts/qa-runtime.json` (all three SHA-256 values match).

| Run | Result |
| --- | --- |
| The real gate, `node scripts/check-desktop.mjs` with `BOOKS_QA_RUNTIME_ROOT` | Node 64 pass. Python, five workers: 433 / 109 / 348 / 242 / 449 cases, 1,581 in total, 0 failures, 0 errors, 1 skipped (the opt-in private MP3 fixture). The gate exits 1 at its zero-skip rule; the gate's own `validatePythonReports` accepts the five reports with that one opt-in case counted as run. Workers 509.9 / 303.5 / 443.5 / 429.1 / 446.4 s (N8). |
| Partition check (`pythonBatches` on the gate's own declared list) | 100 patterns, 100 placed once each; the five run reports match it exactly. 23 test modules on disk are not declared: test_anthology, test_app_launcher, test_build_external_tools, test_chapter_preservation, test_chapter_repair, test_cleanup_catalog, test_encoding_policy, test_fresh_stat, test_merge_service, test_native_rename, test_native_thread_check, test_output_rename, test_recording_classification, test_refused_retry, test_replacement_media, test_replacement_plan_bytes, test_sort_title, test_staging_root_retry, test_standing_metadata, test_start_over, test_storage_busy, test_tk_review, test_working_clear. |
| `tests/test_*.js`, 20 frontend scripts | 20 pass |
| Identity probes (G1–G6, m2, variants) | Table above; N4, N5, N6. |
| Residual probes on a `git archive` of v0.21.2 | N4 files: six separate held candidates; N6 group: held offline. |
| `decide()` probes | N3. |
| Join probes J1, J1-control, J4, J5a, J5b | J1: two books joined, originals removed (N2). Control, the same files bare-numbered: `volumes`, nothing joined. J4: offsets measured in the audio (Summary). J5a, J5b: nothing touched. |
| Keep probes K1-K3 | K1: N1. K2: no set re-forms over two scans; each file researches with no reason; a second Keep on the old row is refused. K3: Keep on an Order unclear MP3 row is refused. |
| Live catalog, read-only (`mode=ro`, `query_only`; chapters read with ffprobe, read only) | 0.22.0 grouping of both roots: 69 explicit sets (all join; `decide()` would say join 29, ask 37, volumes 3), 154 other .m4b sets (`decide()`: join 89, ask 49, volumes 11 (one of them "no chapters"), missing 5, matching Ender's figures). No `decide()` join has season or tome words, more than one work, or over 30 h. One same-title set. 21 plain album groups with repeated title works, all one book or one anthology by name. 180 `part_chapters` facts, no half-converted set. Regroup time 3.0 s + 1.1 s. |

## Mutants

22 mutants, each applied to its own copy of 9b8ab23, with the named suites run on the pinned runtime, then the copy removed. The baseline copy (no change, all ten suites) ran 199 cases with 0 failures. **17 caught, 5 survived.**

A first batch I ran under my session-scratch folder errored in the end-to-end suites, because the paths there run past Windows' 260-character limit. I discarded it and re-ran every mutant under the worktree, at the gate's path depth.

| Mutant | Result |
| --- | --- |
| M01 admission joins chaptered parts whatever research decided | Caught: `test_split_books` (parts with their own chapters are held) |
| M02 `decide()` drops the 30 h caution | Caught: `test_part_sets` (cautions are asked) |
| M03 `decide()` drops the season caution | Caught: `test_part_sets` (6 failures) |
| M04 joined chapter offsets use half of each part | Caught: `test_m4b_join` (the job needs attention) |
| M05 part chapters are not re-read from the snapshot | Caught: `test_m4b_join` (a changed part completes) |
| M06 cleanup ignores the joined chapter plan | Caught: `test_m4b_join`, `test_part_sets` (cleanup refuses, originals stay) |
| M07 Keep accepts any split-book or part-set row | **Survived** (N9) |
| M08 a kept file still takes the part-of-a-set rule | Caught: `test_part_sets` |
| M09 G3: works never computed | Caught: `test_identity_v5`, `test_join_parts` |
| M10 G1: a bare surname is not checked against library credits | Caught: `test_identity_v5` |
| M11 G1: different works joined without an author folder | Caught: `test_identity_v5` (2) |
| M12 G2: junk titles key same-title sets | Caught: `test_identity_v5` |
| M13 G4: a dash credit is kept whole | Caught: `test_identity_v5` |
| M14 G5: only `until_change` rows are listed | Caught: `test_todo_holds` |
| M15 G6: any new rule unlists every row | Caught: `test_author_rules`, `test_todo_holds` |
| M16 m1: the shown destination is not compared | Caught: `test_approve_as_is` |
| M17 m4: close does not stop a press | Caught: `test_approve_as_is` (Quit waited 20 s) |
| M18 `continues` without `after[0] > 1` | **Survived** (N9) |
| M19 part sets formed from mixed recordings | **Survived** (N9) |
| M20 the snapshot accepts chaptered parts without a plan | Caught: `test_split_books` |
| M21 research-decided volumes count as kept by Sergei | **Survived** (N9) |
| M22 `decide()` drops the afterword volumes rule | **Survived** (N9) |

---

## Addendum: the 0.22.0 QA entry script (2026-10-25)

Jane asked me to check Ender's `C:/Antigravity Projects/Worktrees/Books Arranger/qa-run-0220/assemble-entry-0220.mjs` (SHA-256 `69a7275e…6df6167`) against the trusted reference, `WIP/Books Arranger/Docs/assemble-entry-0212.mjs`. That reference is the script I reviewed in the v0.21.2 addendum (`3b32855d…fd1a7`); it is still untracked. I only read files here and ran nothing in `qa-run-0220`.

- **The diff is the six lines Ender named, and nothing else.** `diff` shows the two header comments (0.22.0, 9b8ab23, `qa-run-0220`), `W` → `cand-0220`, `Q` → `qa-run-0220`, `HEAD` → `9b8ab23b2b122ea2b894e3b676308cd33f3df942`, and `FIXTURE_DIR` → `path.join(Q,'mp3-fixture')`. The walk, the refusals, the manifests and the context shape are byte-identical.
- **The fixture copy is the same file.** `qa-run-0220/mp3-fixture/fixture.mp3` is 35,053,612 bytes with SHA-256 `e2deceb3…f77047ed`. That equals the original in `WIP/Books Arranger/private-fixtures/ba-mp3-fixture/` and the hash `ActualPrivateStagingTests` asserts before it uses the file. The context pins it (`runtime-mp3-fixture.json` lists exactly that one file and hash).
- **The runtime matches what ships.** All 47 files of the context's `bundled-media` tree equal the candidate manifest's shipped `runtime.files`, and `python.exe`, `ffmpeg.exe` and `ffprobe.exe` match `scripts/qa-runtime.json`. I checked this by hand, because the script still trusts the tree on first use (E3).
- **The wrapper names the context it was built from.** `context.json` hashes to `e4dca1c1…765fac6`, the value `run-entry.sh` passes as `--context-sha` and the one in `logs/ender-assemble.log`. Ender's own entry receipt reads `check pass` at 9b8ab23, dirty N.
- **E1–E5 from the v0.21.2 addendum are unchanged, as expected for a six-line copy.** E1 (Major): the runtime root and fixture still come from the unpinned `run-entry.sh`. E2: the assembler's hash is still not recorded in `graph.json`. E3: the trees are still trusted on first use. E4: Git still runs with the caller's environment. E5: the paths are still literals. None of them changes this run's evidence, given the hand checks above. They are not counted in this report's totals and do not affect the verdict.

---

## Delta 9b8ab23..b946ee7 (2026-10-25)

Six commits: 790e99b (N1), 7104c29 (N3), 1a12380 (N4-N6), 5675512 (N9 tests), 1e08802 (Brief), b946ee7 (changelog). 8 files, +238 / -22. I reviewed them read-only on a detached worktree at b946ee7 (`review-0220c`).

Futaba's entry check and gate were running, so I kept the load light:
- one probe module (25 cases in 10.8 s, then 7 of them again to print the mutant failures);
- two read-only scripts on the live catalog, a few seconds each;
- no gate, no suite sweep, and no file changed for a mutant.

The probes used the system Python 3.14.9 and FFmpeg 8.1.1, not the pinned runtime. They test logic, not media bytes.

### 1. N1, Keep: can it report false success? No.

- **What the code does now** (`merge_service.py:2181-2193`). Under `group_lock`, in one `BEGIN IMMEDIATE` transaction, Keep:
  1. re-reads the row's revision (a stale or superseded row refuses);
  2. refuses a set that has any job;
  3. records the files;
  4. clears the set's saved review and approval;
  5. regroups;
  6. counts the files that are each their own "Volume of a series" book (`groups.separate_books`).
  If fewer than all members are counted, it raises `ValueError` and everything rolls back. `{'kept': n}` is returned only after the commit, with n the counted number.
- **The transaction holds.**
  - The connection is `scanner.ClosingConnection`: sqlite3's own exit commits on success, rolls back on any exception, then closes.
  - Nothing called inside commits on its own: `groups.record_volumes`, `sync`, `setup` and `separate_books` have no `commit()`, `executescript` or second connection (grep).
  - The code before this change already ran `sync` inside the same explicit transaction.
- **Probe P1.** A real .m4b set asked as `set_seasons`, then a panel Save with a typed title and author:
  - Keep with `groups.sync` stubbed is refused with "Keep as separate books was not accepted. Nothing was changed." Afterwards these are identical to before: the group row (review, approval, revision, fingerprint, superseded), the `part_volumes` count, the catalog revision, the current group ids and the "Entered by you" records.
  - Keep with an exception raised after the regroup leaves everything identical too.
  - A real Keep returns `{'kept': 2}` and makes two one-file books. Each is `volume_of_set {'kept': True}` and researches with no reason. A second press with the old row is refused.
- **`separate_books` cannot count a file that is still in a set.** It needs exactly one current group holding the path, scoped "Volume of a series", whose only member is that path. Each of these leaves the count short, so Keep refuses:
  - a file another protected group still holds;
  - a file that changed since the row was read (its size or time no longer matches the recorded volume);
  - a frozen re-acquire path.
- **The UI** (`web/app.js:2190-2193`, unchanged) shows the server's `kept`. Every refusal goes to its error path.

**Sergei's "Entered by you" record is not deleted, not changed and not used.**
- A panel Save writes two things: the draft on the set's group row (`book_groups.review`), and an append-only `manual_metadata_sources` record keyed by the set's candidate id.
- Keep clears the draft: the old row ends with `review=''` and is superseded. The record stays byte-for-byte as it was (P1).
- The new books have new candidate ids, so the record is not shown on them (0 records each). Their titles and authors come from their own tags.
- Nothing in the UI reaches a superseded id. The record shows again only if the same set forms again (both files change), because the same scope brings back the same id.
- The Brief's Keep row and the docstring say exactly this. Whether Keep should warn that it drops saved values is a UX question for Jane and Judy, together with N7 (no confirmation, no undo).

### 2. N3-N6: more holds than intended, or a new join path?

**No new join path.** Every change can only remove a join:
- **N3** (`part_sets.py:110-117, 143-144`): the episode and tome cautions and the new `works` ask return `ask` where `join` or `volumes` came back before. Nothing reaches `join` that did not before.
  - Tome-named sets whose files start again stay `volumes` (that branch did not change).
  - A set whose files each start again at "Эпизод 1" is now asked instead of `volumes`, as ruling 19b's episode wording says.
- **N4** (`groups.py:319-322`): one more `continue` before a same-title set is formed. The longer generic-title list only blanks titles.
- **N5** (`local_identity.py:1828-1835`): a dash credit with three or more pieces, two or more of them people, is offered piece by piece. It is asked unless a file or folder name decides it. Two-piece credits work as before. `ignored` is the list of the enclosing function (line 1687).
- **N6** (`groups.py:592-605`): it only adds a hold. It skips reviewed, approved, queued, split, joined and part-set groups.

**More holds than intended: yes, in two places.**

Measured read-only on the live catalog: `WIP/Books Arranger/data/inventory.sqlite3`, opened `mode=ro` and `query_only`; 13,747 files in both roots; 0.22.0 grouping with the stored protections.

- **N10 [Major] `groups.py:319-322` (N4's file-name works check). The one live same-title set no longer joins.**
  - «Пастушья корона» (Terry Pratchett) is 77 MP3 files in one folder, with one title tag and no album. The file names carry chapter names: "Пастушья корона 0. Пролог. Корона Холмов", "Пастушья корона 00. Словарь Нак-мак-фиглов", "Пастушья корона 01. Глава 1. Там где ветер", "Пастушья корона 02".
  - `work_name` strips only a trailing number. So every named chapter reads as a work of its own, and the set is dropped.
  - Measured: with N4's two lines taken out in memory, the folder is one group, "Same title пастушьякорона", 77 files. At b946ee7 it is 77 "Standalone source" groups. Same-title sets in the whole live catalog: 0 (there was 1).
  - By the code (`local_identity.py:1273`, piece `siblings`), each lone file beside 76 files with the same title is held as one part of a bigger book.
  - No file is touched and nothing converts wrongly. The stored groups today (0.21.2) are the same 77 standalones, so Sergei loses the join 0.22.0 promised, not anything he has now.
  - Ender's positive control ("Оно 01.mp3", `test_identity_v5.py`) does not use the real naming. The Brief's Guard 2 row still names this set as one book.
  - My N4 fix ("apply G1's works check to same-title sets") did not say which file-name titles count as works; this is the result.
  - **Fix (Ender's choice):** either a file-name title that starts with the tag's own title, or carries a chapter or part label, names no other work; or the check runs only on "Author - Title" file names, the shape G1 and the King probe have. Add the real naming as a positive control.
- **N11 [Minor] `groups.py:592-605` (N6). The album works check holds 21 live albums. By their names, none of them is two books.**
  - None of the 21 is converted yet, so all 21 become Files unclear rows on the first sweep. Each says "The title tags name more than one book" and lists chapter or story titles as books.
  - They include Schismatrix ("Часть 1. Бродяжья зона" …), the three Конан scrolls (stories), Таксидермист, Кольцо Тьмы 1-3, Мистер Вечный Канун ("Глава 1. Дом, милый дом" …), Война миров ("Часть первая. Фрагмент"), and 11 more of the same kind.
  - This is the count I gave in N6, now confirmed as 21 false holds. The Brief records it ("asked once").
  - Ignoring titles that start with a chapter or part label would clear 4 of the 21. The rest have the same tag shape as the Ведьмак probe.
  - **For Sergei, through Jane:** either accept 21 one-time asks as the price of never joining two books in one album, or narrow the check. The wording of this row's cause is Judy's.
- **N5:** no live credit has three or more dash pieces with two or more people, so nothing changes live.
- **N3:** I did not read chapters from the NAS again for this delta, to keep the load light. My earlier read-only measurement found no `decide()` join with season or tome words, more than one work, or over 30 h. "Эпизод" numbering was not measured on its own. Every N3 change can only turn a join or volumes into an ask.

### 3. N9: the five mutants

Each mutant was applied in memory only (`mock.patch` or a recompiled copy of one function; no file changed). For each, I ran only the new test that should catch it.

| Mutant | Result | Failing assertion |
| --- | --- | --- |
| M07 Keep accepts any set row | Caught | `test_review_n9_keep_refuses_a_set_the_app_did_not_ask_about`: "ValueError not raised" |
| M18 `continues` without `after[0] > 1` | Caught | `('join', …) != ('ask', 'unclear')` |
| M19 part sets from mixed recordings | Caught | `1 != 2` (one "Part set перн") |
| M21 research volumes count as kept | Caught | `test_volumes_become_books_of_their_own`: `[{'kept': True}]*2 != [{'kept': False}]*2` |
| M22 no afterword volumes rule | Caught | `('join', …) != ('volumes', 'each file ends with its own afterword')` |

Without the mutants, the same tests pass. So do `DecideTests`, `GroupingTests` and Ender's three Keep tests: 25 cases, 0 failures.

- **N12 [Minor] Tests. No test checks that a refused Keep keeps a saved review.** Ender's refusal test runs without a Save. Reading the tests, a change that cleared the review in its own committed write would still pass them. My probe P1 checks this; one such case in `test_part_sets.py` would close it.

### 4. Rebuilt artifact and the QA entry script

- The manifest, installer, `.blockmap` and `latest.yml` all match (Header and Artifact pin): version 0.22.0, source b946ee7, product digest equal to b946ee7's tree.
- **The entry script diff is six lines.** I compared `qa-run-0220b/assemble-entry-0220b.mjs` (SHA-256 `3b2f6437…3eb0e9`) with the trusted reference `Docs/assemble-entry-0212.mjs` (`3b32855d…fd1a7`). `diff` shows exactly these changes, and nothing else:
  - the two header comments (0.22.0, b946ee7, `qa-run-0220b`);
  - `W` → `cand-0220b` and `Q` → `qa-run-0220b`;
  - `HEAD` → `b946ee732be82acdbd56efa351bd1dce96d9880e`;
  - `FIXTURE_DIR` → `path.join(Q,'mp3-fixture')`.
- **The inputs match.**
  - The fixture copy (`mp3-fixture/fixture.mp3`, `e2deceb3…f77047ed`) equals the original and the context's pin.
  - `context.json` hashes to `a6a111e8…fee45b1a7`, the value `run-entry.sh` passes and `logs/ender-assemble.log` records.
  - The QA runtime's `python.exe`, `ffmpeg.exe` and `ffprobe.exe` match `scripts/qa-runtime.json`.
  - The 47 bundled-media files equal the shipped runtime. The shipped runtime has one more entry, `ffmpeg/BUILD.txt` (a text note), which is not in the context's media list.
- Ender's receipt reads `check pass` at b946ee7, dirty N.
- E1-E5 are unchanged, as expected for a six-line copy, and stay outside the totals.
- I only read and hashed files. Nothing ran in `cand-0220b` or `qa-run-0220b`.

### Other dimensions for the delta

- **Security:** Pass. No new process call, path, route or Electron change; no secrets; no attribution trailer in the six commits.
- **Crash safety:** Pass. An exception inside Keep rolls back (P1).
- **Performance:** Pass. Both live roots regroup in a few seconds, including N6's extra pass.
- **State and data safety:** Pass; the safety floor is intact. Keep writes only catalog rows, in one transaction, and moves or deletes nothing. N10 and N11 hold files; they never convert or remove one.
- **Build hygiene:** Pass. The CHANGELOG line matches the code, and the version stays 0.22.0.

---

## Delta b946ee7..01581a6 (2026-10-25)

17 commits, 31 files, +1938 / -123:
- N10 and N11: 08ee8b8, 615a05b;
- N12: db4bc6b;
- Futaba's chip blocker: cd533fe;
- Futaba's M-1 to M-3 and Minors: feb21f7, 60a66c6;
- Delete book: b85e7d1, b80b07c, 99e9dab;
- the gate: 5073d4f, ed866a3;
- the 403 body drain: 17abe60, 7158f26;
- docs and changelog: d5276f0, 55d664b, e579517, 01581a6.

I reviewed them on a detached worktree at 01581a6 (`rv0220d`). Futaba's entry check and gate were running, so I kept the load light:
- one probe module of 3 cases, run once (4.4 s);
- two read-only groupings of the live catalog (6 s each) and one read-only query;
- hashes.

I ran no gate, no suite and no mutant. In `cand-0220c` and `qa-run-0220c` I only read and hashed files. The probes used the system Python 3.14.9 and FFmpeg 8.1.1.

### 1. Delete book (ruling 23), red team

**What it does** (`book_delete.py`). Preview and Delete both run `plan()` again: the server's own offer, then every refusal, then the list built from the disk now. Delete re-plans under `operation_lock` and `group_lock`. It refuses unless that fresh list equals the list Sergei confirmed, compared case-insensitively, with no duplicates. Then:
1. It removes the server's own fresh paths, never the client's strings, one at a time.
2. It clears the leftover working files of the book's failed jobs.
3. It checks that every member path is absent.
4. Only then does it delete the records, in one transaction.

**Can it delete anything outside this book's own files? No, in every case I could build.**
- **Other books' files in the same folder.** Only the group's members are listed. Ender's test shows the sibling book, the cover and the text file stay.
- **Files another book also holds.** A file that another current group, any other book's job or any other reacquire record holds is refused as `shared` before anything is touched.
- **Sorted and other roots.** Every path must be audio, inside a configured Audiobooks source root and not inside the configured Sorted folder (`scanner.inside`, case-folded). Ender's tests cover a path outside the roots and Sorted placed over the book's folder.
- **Links.** At removal, `DirectoryBoundary` holds every folder from the drive root down, and refuses any junction or symlink among them. `VerifiedFile` opens the exact file without following a reparse point, checks a single link and the listed size, and deletes through that handle. A symlinked file is refused in `plan()` (`lstat`).
- **Probe P6, a junction.** I replaced the book's folder with a junction into `Audiobooks Sorted\Петров Иван\Новая плоть`, which holds same-named copies. The preview listed both files, because `lstat` follows a folder junction. Delete then removed nothing: both failed with "Destination ancestor is a symlink or junction", Sorted was byte-for-byte unchanged, and every record stayed. Safe, but the dialog first said those files would be deleted (N14).
- **Case and Unicode.** Every comparison is case-folded. Unicode forms are not normalized, so a different spelling can only make the lists differ, which refuses (`files_changed`). On NTFS and SMB a different Unicode form is a different file.
- **Stale revision.** The route requires an integer revision. `_row` compares it, and Delete re-reads it under the locks (Ender's test: `changed`).
- **Limit, not a finding.** A symlink made on the NAS side (Samba "wide links") looks like an ordinary folder to Windows. Source cleanup has the same limit.

**Half-forgotten?**
- **Files deleted, records kept:** possible, by design. A failed file, a working folder the app cannot clear, or a crash between the steps keeps every record. The book stays listed with what remains, and the next press finishes. Ender's partial and crash tests show this.
- **Records forgotten while files exist:** only if an existing path reads as absent, for example a reachable root whose subfolder is unreachable. I did not measure this.
- **The reverse does happen.** The forgotten book comes back during a scan (N13).

**Can it run for a row the server did not offer it on? No.** `plan()` calls `offer()` itself: a Missing files row from `needs_you()`, or the newest stopped job with the reacquire group or the `replace_source` remedy. Ender's tests refuse a book the app can still fix, including the MP3 that "Retry checks again". P3 shows the page and the server agree on Need to reacquire.

**Ender's narrow window, "being researched" versus research starting: harmless.** Before it records "Researching", the research loop reads the row and may refresh its sources. Neither step shares a lock with Delete. What can happen:
- The source refresh takes `group_lock`, so it waits for Delete to finish. It then finds no book and returns "held"; its error is caught. Research writes a Held record for an id no group has. That record has no effect: every count joins current groups, and ids are random UUIDs that never come back.
- If research reads a file while Delete removes it, Windows sharing makes one of them fail. Either Delete reports "In use by another program." and keeps every record, or research holds the book.
- `approve_automatic` takes `group_lock` and re-reads the row at its revision. It cannot run during a Delete, and it refuses afterwards.

**The Need to reacquire offer (probe P3, backend).** I built a real `required` marker with `reacquire_sources._current` on a stopped job.
- The page offer (`attention.delete`) and the server offer (`offer()`) both read `{kind: audio_damaged, present: 1}`.
- The preview listed the one file. Delete removed the file, its marker, group, job and file row.
- A copy put back at the same path was a new book: new id, no marker, no research record, and no Delete offer.

**Can a reacquired copy be blocked by leftover markers?**
- Its own marker: no (P3, and Ender's reacquire test).
- Another book's history: yes, but only Delete is blocked. An *archived* marker, or another book's job, that names the same paths makes Delete refuse that copy as `shared`, naming a book that is not listed. Ender's own test treats an archived marker that way (N16).

**Findings**

- **N13 [Major, closed at 7490b39] `web_server.py:799` (the scan-active refusal list), `book_delete.py:94` (`plan`). Delete book runs during a library scan, and the scan brings the forgotten book back.**
  - Keep, Approve, Scan again and Convert are refused while a scan runs. Delete and its preview are not, and `plan()` does not check the scanner. The page's Delete button is live during a scan too: `deleteMode` checks presses, not scans.
  - Every automatic run starts with a full scan of 13,747 files on the NAS.
  - **Probe P1.** The scan enumerated the book's folder and queued its files. I paused it there, pressed Delete (2 deleted, forgotten), then let it continue. The scanner's queued file tasks found no file and no catalog row, so its error branch inserted a fresh row for each: `missing=0`, error "[Errno 2] No such file or directory".
  - **Result.** The scan ended "completed with errors" (2). The list showed two new one-file books, "Новая плоть 1" and "Новая плоть 2", for the deleted files.
  - **Automatic run.** A run in its discovery phase stops at that status: "Discovery incomplete or has read errors" (`automatic_processing.py:563`).
  - **Impact.** No file is touched and nothing is lost. The next scan marks the two rows missing, and Remove from list or Delete clears them.
  - **Fix:** add `/api/candidate/delete` and `/api/candidate/delete-preview` to the scan-active refusal set, and refuse in `plan()` with `busy` while `inventory.worker` is alive.
- **N14 [Minor, closed at 7490b39] `book_delete.py:163-183` (`plan`). The preview lists files reached through a folder junction** (P6). Removal refuses them safely. But the dialog first says "These 2 files will be deleted", then "Couldn't delete it." for each, and the book stays listed.
  - **Fix:** in `plan()`, refuse (`refused`) when any folder between the root and the file is a junction or symlink, the check `DirectoryBoundary` makes at removal.
- **N15 [Minor, closed at 7490b39] `book_delete.py:262-279` (`_clear_working`). Delete clears working files by Retry's rule, not by "everything".**
  - For an M4B job, `_working_state` counts only `.m4b` and `.wav` leftovers (`audio_only`, `merge_service.py:2750`). An error while reading the working state reads as "nothing left".
  - In both cases the job's `working_*` records are deleted with the book, and any other leftover files stay on the app's drive with no record.
  - **Fix:** read the state with `audio_only=False` and clear with it. If the state cannot be read, keep the records, as a failed clear already does.
- **N16 [Minor, closed at 7490b39] `book_delete.py:144-156`. `shared` counts old history: archived reacquire markers and other books' jobs in any state.**
  - An archived marker's originals are confirmed gone, and the paths now hold the replacement. That replacement can never be deleted, and the refusal names a book that is not listed.
  - On the live catalog (read-only), none of 1,938 current books shares a path with another book's job. There is no reacquire marker table yet.
  - **Fix:** skip markers in the `archived` state. For a job that is not current, say "an earlier attempt" instead of a book title.

### 2. N10, N11 and N12

- **What changed.** `local_identity.chapter_works` treats two kinds of title as no work of their own:
  - a title that opens with a chapter or part label;
  - in a set that visibly holds chapters, a title that is the book's own title and a number.
  Both grouping checks use it.
- **Measured read-only on the live catalog.** I grouped both roots, with the stored protections, at b946ee7 and at 01581a6:
  - **One partition change only:** the 77 files of «Терри Пратчетт - Пастушья корона (Макс Потёмкин)» form one same-title set (1,648 groups become 1,572). No other group changed, so there is no other new join. **N10 is closed.**
  - **Album holds: 21 become 17.** Cleared: Schismatrix, Война миров, Мистер Вечный Канун, Книга осенних демонов. **N11 is narrowed;** the 17 left still need Sergei's answer, as before.
- **Tests.** Ender's test uses the 77 real file names as the positive control, which was my N10 fix. "Ведьмак 1. Последнее желание" and "Ведьмак 2. Меч предназначения" under one tag still read as two works.
- **N12 is closed.** A refused Keep after a panel Save leaves the review, approval, revision and "Entered by you" record as they were (`test_part_sets.py:312`).
- **Note for N2.** A title tag that opens with a part label now names no work. So an MP3 album tagged "Часть 1. <book A>" / "Часть 2. <book B>" is no longer held. It joined at 9b8ab23 as well. This is N2's shape on the album route, and Sergei's call together with N2.

### 3. The chip blocker and Futaba's fixes

- **The chip blocker.** One list, `review_backend.NEEDS_GROUPS`, `JOB_GROUPS` and `ATTENTION_GROUPS`, now serves the HTTP route, `page()` and the counts. `test_web` sends every chip the page has through the real route, with an unknown chip as the control. The count keys are the same as before.
- **Futaba's fixes: no finding.**
  - M-1, `_continue_after_rule`: puts back the books a new rule answers.
  - M-2, Scan again on a missing part: `_new_audio_beside` is read-only, at most 5,000 entries per folder; a scan starts only when new audio is found.
  - m-7: Sergei's own track review needs no note; an assistant review still does.
  - m-8 and the copy changes.

### 4. The 403 body drain (`web_server.py:294-311`)

- **Bounded, and cannot leak anything.** It drains only:
  - a POST with exactly one Content-Length;
  - of ASCII digits, at most 6 of them and at most 256 KiB;
  - with no Transfer-Encoding.
  The bytes are dropped, and the 403 follows on an HTTP/1.0 connection that then closes. So nothing in the body is read or used, and no second request can ride on it.
- **N17 [Minor, closed at 7490b39] `web_server.py:295`.** The docstring says "2 s at most", but `settimeout(2)` applies to each read. A slow sender holds one handler thread for longer, bounded by 256 KiB. The trusted body read already allows the same, at 5 s per read. Handler threads are daemon threads, and only a local process can do this. **Fix:** a total deadline, or correct the comment.

### 5. The gate: six workers, with side checks alongside

- **All 101 modules run.** I counted with the gate's own `pythonBatches` on the list `check-desktop.mjs` declares: 101 modules, each placed once across six workers. Projected 386-388 s per worker, under the test's bound of 432 s.
- **The side chain runs alongside:** 8 syntax checks, 10 node test files and the 21 page scripts, including `test_delete_frontend.js`.
- **Any failure still fails the gate.**
  - A failed, timed-out or unstartable step stops the chain and records the failure. The gate throws on it after every Python worker has finished.
  - The node TAP counts are checked as before: tests above 0, fail 0, skipped 0, cancelled 0.
  - The source inventory is checked again after the chain, because the chain runs in the source folder.
- **Ender's entry run of 01581a6:** 1,610 Python cases, 65 node cases, 21 page scripts. Workers took 391.6 / 386.5 / 396.4 / 364.4 / 399.8 / 390.9 s against 540 s.
- **Still open:** the 23 modules outside the gate (m7).

### 6. The checker change, studio commit a4783ba

- **Only one checker file changed.** Of the five checker files, only `entry-main.mjs` changed. I recomputed the checker digest from the files: `8af6c258…` at the parent, `a448c08c…` at a4783ba. The latter equals the BA context's tooling pin and Ender's receipt.
- **I cleared these exact bytes before.** The committed `entry-main.mjs` is `eb8952ee…` and `entry-git.test.mjs` is `28d44268…`: the bytes I cleared in `Team/Docs/QuickLaunch_QAHandoff_GitRuntime_Review_2026-10-25.md`. The working tree is clean.
- **What it adds:** an optional `runtime.git`. It must be:
  - an absolute, canonical `git` or `git.exe`;
  - inside a pinned Git manifest whose whole tree verifies;
  - matched by its hash.
  It joins the runtime digest. PATH gains only its folder, and a scan refuses any other `git` command that could shadow it.
- **Without it, nothing changes.** PATH is the Node folder and the shell folder. The Node path is checked to be the running Node, so this equals the old PATH.
- **Books Arranger's context has no `runtime.git`,** so the new branch does not run for this tool.
- **The checker is still trustworthy.**

### 7. Final artifact and the QA entry script

- **Artifact.** The manifest and the installer match: Header and Artifact pin.
- **The entry script diff is six lines.** `qa-run-0220c/assemble-entry-0220c.mjs` (`b9d50bb2…`) against the trusted reference `Docs/assemble-entry-0212.mjs` (`3b32855d…`) differs only in:
  - the two header comments (0.22.0, 01581a6, `qa-run-0220c`);
  - `W` → `cand-0220c` and `Q` → `qa-run-0220c`;
  - `HEAD` → `01581a672adc5cd0d1fc45a641bce112a2a3d825`;
  - `FIXTURE_DIR` → `path.join(Q,'mp3-fixture')`.
- **Inputs.**
  - The fixture copy is `e2deceb3…f77047ed`, which equals the context's pin.
  - `python.exe`, `ffmpeg.exe` and `ffprobe.exe` match `scripts/qa-runtime.json`.
  - `context.json` hashes to `063cde6d…dc52a4c`, the value `run-entry.sh` passes and `logs/ender-assemble.log` records.
- **Ender's receipt** reads `check pass` at 01581a6, dirty N, checker `a448c08c…`.
- **E1-E5** are unchanged and stay outside the totals.

### Other dimensions for this delta

- **Security:** Pass.
  - Both new routes go through the token, `shape()` and `candidate_identity()`, and are refused while the server closes.
  - `paths` is bounded: a list of at most 10,000 strings of 1-1,000 characters.
  - No shell, no Electron change, no secrets.
  - No attribution trailer in the 17 commits.
- **Crash safety:** Pass. A failure in the records step rolls the transaction back. P1 does not crash the app.
- **Performance:** Pass. Delete holds `operation_lock` and `group_lock` through its whole file loop, so for a large book on the NAS the list waits seconds. Not a finding.
- **Build hygiene:** Pass. Version 0.22.0; the changelog lists Delete book and the six-worker gate.

---

## Delta 01581a6..7490b39 (2026-10-25)

19 commits, 50 files, +2433 / -354. Product code and scripts: 11 files, +1018 / -255 (`book_delete.py` +565 / -132, `working_lifecycle.py` +90, `web/app.js`, `scanner.py`, `web_server.py`, `chapter_plan.py`, `merge_service.py`, `review_backend.py`, the batching script).
- N13 to N17: 053c37d, 0892cc6, 9e1a7bc, d2fd06b, abf5d8a, 4d9e687, ce6ebc9;
- rulings 24 to 26 (Delete book's wider removal, Remove this copy): 2bad0e4, ab6c5ed, 3352d39; ruling 24a: 051edad, 95048a3;
- Futaba's QA report and fixes (M-4, m-9 to m-13, m-3's Goes to line): 44d7dd2, 461506c, dad6394;
- tests and gate: ee2e9d5 (scan-wait helpers), 4f6643a (seventh worker);
- docs and changelog: c0052d2, 7490b39.

I reviewed them on a detached worktree at 7490b39 (`rv0220f`). Futaba's entry check and delta pass were running, so I kept the load light:
- one probe script on plain local folders inside my worktree (`book_delete._others`, `_folders`, `_remove_folder`, `scanner.gone`), a few seconds;
- the gate's own batching test (18 node cases, 0.1 s) and its partition of the declared list;
- hashes.

I ran no gate, no Python suite and no mutant. In `cand-0220f` and `qa-run-0220f` I only read and hashed files. The probe used the system Python 3.14.9.

### 1. Remove this copy (ruling 25), red team

**What it does** (`book_delete` mode `copy`, the same two routes). Preview and press both run `plan()` again.
- **The offer** (`copy_source`) needs all of these:
  - a "Needs you" row whose reasons say "Identical verified recording already arranged";
  - a stored recording review that is `verified_identical` and not blocking;
  - no missing file;
  - a related job that is completed and passed its output check, with as many sources as the copy has files, size for size, in order.
- **The proof** (`_copy_proof`) runs on every preview and again on the press, under `operation_lock` and `group_lock`:
  1. every copy file, in order, has the size and SHA-256 the job recorded for its source;
  2. the audiobook passes the full output check (`_output_valid`: file identity, parent folder identities, size and SHA-256 of the whole file);
  3. no listed file has the audiobook's device and file id.
- **The hold** (`_hold`): before the first file goes, the audiobook is opened with read sharing only, its size and identity are checked again, and it stays open while the copy's files go.

**Can it delete a non-duplicate? Not a recording that is not a proven copy.**
- The offer only shows the button. The hashes decide. A wrong or stale verdict still has to pass the hash proof on the press. Ender's tests:
  - one byte flipped in a copy file, size kept: `not_identical`;
  - a "Possible duplicate" row is refused, even with its stored verdict changed to identical.
- A copy with more or fewer files than the job's sources is refused. An extra recording in the copy's folder makes the folder another book's, so only the members go.
- **The copy cannot be the job's own originals.** A completed job always counts as holding its source paths (`_history` exempts only stopped jobs that made nothing). So those paths are refused as `shared`. A copy with a job of its own is refused too.
- **Its non-audio files are not proven copies of anything (N20).** The copy's cover, text or booklet go with it, by Judy's default. Each is listed in the dialog.

**Audiobook missing or changed: refused.** Ender's tests, preview and press both:
- moved away: `sorted_missing`;
- one byte flipped with size and time kept: `sorted_changed`.

The press proves everything again; it never reuses the preview's proof.

**Race between the proof and the delete: as closed as the app can make it.**
- Proof and removal run in one press, under both locks. Between the full hash and the first removal only the list comparison runs. Then `_hold` keeps the audiobook from being written or deleted, and checks its size and identity again.
- The copy files are not hashed a second time. `remove()` checks each file's size and single link at its handle. Only another program rewriting a copy file in that window, same size, could get past. The file deleted would still be the path Sergei confirmed.

**Can it touch Sorted? No.**
- Every member and every other file must be inside a source root and not inside the configured Sorted folder (case-folded). `_others` skips folders in Sorted, and the folder walk stops there.
- The audiobook is only read (`VerifiedFile` without delete, `_output_valid`).
- **Junctions:** every folder from the drive root down is held by `DirectoryBoundary`, in the preview (N14's check) and again at removal. Ender's test swaps the copy's folder for a junction: `refused`, nothing deleted.
- **Case variants** are folded. **Unicode forms** are not normalized. A different form is a different name on NTFS and on the NAS's Samba share, so it can only make a path miss, which refuses.
- **Hard links:** a member or other file with a second name is refused three times over:
  - in `plan()` (`st_nlink != 1`);
  - at removal (`VerifiedFile`'s link count);
  - by the device-and-file-id check against the audiobook.
  On the NAS, Samba reports the real link count and file id.

### 2. Delete book's cover and text files (ruling 24)

**How it decides** (`_others`). It reads each folder that holds a member. A source root itself and a folder in Sorted are never read. A folder counts as another book's when either is true:
- any book, job or reacquire record holds a path in it;
- it lists an audio file (by `metadata.AUDIO`) that is not a member.

Then every other file in it stays. Otherwise each other entry goes if it is an ordinary, single-link file that nothing holds. A subfolder, link or reparse point stays.

**Shared folder: safe.** Another book's audio in the folder, on disk or only in the catalog, keeps every other file there (Ender's test "a folder with two books keeps its cover and text files"). A cover another book's job used stays by itself (Ender's test).

**CD1/CD2 parent: safe.** Only the members' own folders are read. Probe C: a book in `Книга2\CD1` and `Книга2\CD2`, with `cover.jpg` in `Книга2`:
- no other file is listed;
- CD1 and CD2 are listed as folders left empty;
- `Книга2` stays, with its cover.

**But two kinds of "another book" are missed (N18, below):** a subfolder holding another book, and audio in a format the app does not know.

### 3. Empty folders (ruling 24a)

**Which folders are listed** (`_folders`, at plan time). First a member's folder whose entries are all listed files. Then each parent whose entries are all listed files or folders already listed. The walk stops at:
- a folder directly inside the source root, or the root itself;
- a folder inside Sorted;
- a folder it cannot list, or one already empty;
- a folder `DirectoryBoundary` refuses (a junction or link anywhere from the drive root down).

The dialog lists the folders, and the press refuses if its own list differs (`files_changed`).

**How each is removed** (`_remove_folder`). Only after every file is gone and none failed. With the parent's folders held, the folder must be an ordinary directory (no reparse attribute, no junction, no link). Its listing must show nothing. Then a plain `os.rmdir`, which fails on a folder that is not empty. A folder that stays is reported, and never keeps the book listed.

**Can rmdir remove something not empty, or not this book's? Not that its listing shows.**
- **Probe E:** a hidden, system file put into a listed folder after the plan keeps the folder (removal answers False; the file is still there). Once emptied, the folder and its emptied parent go. `Автор`, directly in the root, stays.
- **Probe D:** a hidden file in the book's folder is listed as one of its other files, so the dialog shows it.
- **Ender's tests:** a file arriving before the folder goes; a folder swapped for a junction during the press; a subfolder or link inside it; and the emptiness check forced to pass while a file arrives, where `rmdir` itself still refuses, so nothing recursive runs.
- **Within ruling 24a, not a finding:** the listing is all the check can see.
  - On NTFS, a folder's named streams go with it.
  - On the NAS, a share can hide some names (Samba `veto files`). If it is also set to delete hidden names, they go with the folder. QNAP shares often hide `.@__thumb` thumbnail folders this way.
  - I did not read the NAS's share settings. Judy's offer 5 assumes such a folder stays; on a share that hides them, it goes.
  - This is the case Sergei's "Allow" accepts.

**"Never directly under a source root" and "never in Sorted": both hold.**
- Depth is counted from the member's own source root. The roots cannot overlap (`source_config` refuses it), so `root\A` is never removed and `root\A\B` can be. Ender's test and probe D agree.
- Sorted: `_others` skips folders in it, and the walk stops at it.

**The other paths keep the old refusal.**
- `native_io` and `source_cleanup` do not change in this delta.
- `book_delete._remove_folder` is called only from `delete()`.
- Source folder cleanup, Clear working files and the other `rmdir` callers (recovery retention, replacement retirement, series backfill) are in files this delta does not touch.

### 4. The last working copy (ruling 26)

- **Only Delete book's own press removes it.**
  - `WorkingLifecycle.discard` (`working_lifecycle.py:441`) is new. Its only two callers are in `book_delete`: the dry run in `_working` and the removal in `delete()`. Both run only in mode `delete`.
  - Copy mode lists no working files, and a copy with any job is refused.
  - retire(), Retry and Clear working files are unchanged, so they keep the "never remove the last copy" refusal.
- **Only a stopped job's files.** Only jobs that need attention and have no output are read. A book with a completed job, an output, a source cleanup or a replacement lineage is refused (`sorted`) before that.
- **`discard` keeps retire()'s proofs, except the one about the originals:**
  - the private ownership record names this job and its frozen manifest;
  - every file sits directly in its attempt folder under its recorded name;
  - no folder from the staging root down is a link or junction;
  - no other job, attempt, publication or recovery record references it;
  - each file has the exact identity and size the producer closed.
  A published or isolated attempt, a producer that did not close, or an unknown file refuses before anything goes.
- **The dialog** lists every working file by path. It says when they are the last copy (`last_copy`: some or all).
- **N15 is closed.** Every recorded working file is listed, not only audio. A state the app cannot read refuses before anything goes.

### 5. The scanner's quiet skip (N13)

**What changed.** A file, or a queued folder, that raises "not found" is skipped quietly only when `scanner.gone` proves it is gone. The proof: the nearest folder at or below the source root that can be listed lists without the next name toward the path. The skipped file gets no error and no row. Its folder is listed once more in the same scan, so a renamed file is catalogued. Without the proof, the error stands.

**Can it hide a real read error or a dropped share? No.**
- **A dropped share.** This matters, because Windows reports "network path not found" (errors 53 and 67) as "not found" too. `gone` walks up past folders it cannot list. When it reaches the source root and cannot list that either, it returns None, and the error stands.
  - Ender's two negative controls move the root away mid-scan: "completed with errors", the reads are errors, nothing is marked missing.
  - Probe G4 agrees.
- **A file that exists but cannot be read.** Its name is still in its folder's listing, so it is not gone. Probe G2: a queue path that differs only in case from an existing file is not gone.
- **Any other error** (access denied, a network error that is not "not found") is not touched.
- **No new way to mark files missing.** Only a folder that lists without the name counts. A NAS sub-volume that unmounts inside a share lists as empty, so its files go missing. But a scan that lists that folder after the unmount marked them missing in exactly the same way before this change.

**N13 is closed.**
- Both routes refuse while a scan runs, typed `busy`, before the service is asked (`web_server.py:817`; Ender's route test with the service mocked). `plan()` refuses again (`book_delete.py:465`).
- My P1 order (the scan queued the files, then Delete ran) now ends "completed" with 0 errors and no new book (Ender's test of my probe).
- **Residual, not a finding.** A scan *started* during a Delete is not refused: `_launch_sources` and the automatic start take neither lock Delete holds. The quiet skip covers a read that comes after the removal. Only a read that finished just before the removal and is written after the records are forgotten could bring back one row, until the next scan. The Delete dialog is modal, so Sergei cannot start a scan from the page meanwhile.

### 6. M-4 and the other QA fixes

**Double Approve: no.**
- **On the page:** Approve, Convert what's there and bulk Approve now wait up to 600 s for the answer. The pending face and `askPending` stay until then. Meanwhile every Approve, Delete and Remove button reads busy.
- **After a page reload during the wait:** the row shows ready again, because the first press has not committed. A second press then waits on `operation_lock`, which `approve_automatic` holds for its whole check. Under `group_lock` it then finds the first job ("Audiobook job already exists") or a changed revision, and refuses with nothing written.
  - The part of `approve_book` before that lock only reads. The one exception: a Same author? choice records the same rule again.
  - Wording only, not counted: that refusal contains "already exists", so the route types it `name_taken`, and the page says the name is taken.

**m-9:** the destination is now checked before anything is written. The late check in `build_manifest` and the never-overwrite publication stay. A name taken between the two checks still refuses late, as before. Ender's test shows the stored book unchanged after a refusal.

**m-12** (`chapter_plan.prepare`) changes only the chapter names and numbers of new plans; frozen plans keep theirs. The shared-prefix rule needs one title on every file, and every file name starting with it.

**m-10, m-11, m-13 and m-3's Goes to line** change the page, or only read (`job_destination` reads the manifest).

### 7. N14, N16 and N17

- **N14 closed.** Before it lists a file, `plan()` now makes removal's own checks: a single-link ordinary file, and `DirectoryBoundary` from the drive root down. Ender's test is my probe P6 (a junction into Sorted): the preview refuses before listing anything.
- **N16 closed.** These no longer count as sharing: an archived marker of a book that is gone, and a stopped job of a gone book that made nothing. These still do: a queued, running or finished job; a job with a replacement lineage; any job of a listed book. Ender's test walks all five.
- **N17 closed.** The drain has a 2 s total now: one `read1` per loop, with the time left as its timeout. Ender's test trickles a 200,000-byte body and gets the 403 while bytes still arrive.

### 8. Scan-wait helpers: no test now passes without checking

- 28 modules swap `worker.join(N)` for `finish_scan` or `finish_thread`. Each joins with a 120 s bound and raises if the thread still runs. `finish_scan` also fails when no scan was started. The old join returned silently when its time ran out.
- The lines removed beside them are of two kinds:
  - `assertFalse(worker.is_alive())`, which the helper now does itself;
  - `tearDown` cleanups, moved into `addCleanup` with `close_scan` running first.
- No other assertion was removed, except in `test_book_delete`, where the removed lines were reshaped into the N16 test.
- Neither the old wait nor the new one checks that a scan *succeeded*. Tests that care read the catalog afterwards, as before.
- Five of the 28 are among the 23 modules still outside the gate (m7).

### 9. The gate: seven workers

- **All 101 modules run, each once.** Counted with the gate's own `pythonBatches` on the list `check-desktop.mjs` declares: 101 placed once across seven workers. Projected 401 to 403 s per worker, under the test's 432 s bound. The gate's batching test passes (18 node cases).
- The weights are now each module's time while seven workers ran together.
- **Ender's entry run of 7490b39:** 1,642 Python cases and 65 node cases. Workers took 350.9 to 381.0 s against 540 s.
- **Futaba's entry receipt** in `qa-run-0220f/logs/futaba-entry.log` is the same line: check pass at 7490b39, dirty N.
- **Still open:** the 23 modules outside the gate (m7).

### 10. Final artifact and the QA entry script

- **Artifact.** The manifest and the installer match: Header and Artifact pin.
- **The entry script diff is six lines.** `qa-run-0220f/assemble-entry-0220f.mjs` (`82e73db7…b4c30a`) against the trusted reference `Docs/assemble-entry-0212.mjs` (`3b32855d…fd1a7`) differs only in:
  - the two header comments (0.22.0, 7490b39, `qa-run-0220f`);
  - `W` → `cand-0220f` and `Q` → `qa-run-0220f`;
  - `HEAD` → `7490b39524ec702ece35c3d5ca657d366c229786`;
  - `FIXTURE_DIR` → `path.join(Q,'mp3-fixture')`.
- **Inputs.**
  - The fixture copy is `e2deceb3…f77047ed`, which equals the context's pin.
  - `context.json` hashes to `a441ffcb…49dc52`, the value `run-entry.sh` passes and `logs/ender-assemble.log` records.
  - `python.exe`, `ffmpeg.exe` and `ffprobe.exe` match `scripts/qa-runtime.json`.
- **Ender's receipt** reads `check pass` at 7490b39, dirty N, checker `a448c08c…`.
- **E1-E5** are unchanged and stay outside the totals.

### Findings in this delta

- **N18 [Minor] `book_delete.py:298` (`_others`). "The folder holds no other book" misses two cases, so their files are listed to go.**
  - **A folder whose subfolder holds another book.** Probe A: `Кинг\Оно.mp3` (the book), `Кинг\folder.jpg`, `Кинг\notes.txt`, and `Кинг\Мизери\01.mp3`, held by another book. `folder.jpg` and `notes.txt` are listed to go; only the subfolder stays. Nothing tells whose cover that is.
  - **Audio in a format outside `metadata.AUDIO`** (for example `.ape`, `.mka`, `.mp4`, `.wv`). Probe B: `Книга\Другая запись.ape` beside the book is listed as one of its other files.
  - **Why Minor:** each file is listed by path in the dialog Sergei confirms. Nothing outside the book's own folders goes, and nothing in Sorted. But ruling 24 says shared or ambiguous files stay, and these two are ambiguous.
  - **Fix:** count a folder as another book's when a folder another book holds is below it, or when it has a subfolder that holds audio. For this test, also treat a wider list of audio and container extensions as audio.
- **N19 [Minor] `book_delete.py:419-455` (`_copy_proof`), `book_delete.py:642` (`delete`), `web/app.js:2402`. Remove this copy's press reads the book twice over the network while it holds the app's locks, and it cannot be stopped.**
  - The press hashes every copy file and the whole audiobook in Sorted, holding `operation_lock` and `group_lock`. `merge.state()` takes `group_lock`, so the status poll waits for the whole proof. So do Approve, Keep and the list's regroup.
  - The stop event in `_copy_proof` is never set, and `_output_valid` is given none. So Quit waits for the hashes. Approve's m4 fix made its own presses stoppable.
  - The page gives the press 120 s. A large book read twice over a slow link can take longer. The page then says the connection was lost while the server goes on and removes the copy: the M-4 pattern, on a new action. What it removes is still exactly what was proven and confirmed.
  - **Fix:** pass a stop event that drain and close set. Prove outside `group_lock` (keeping `operation_lock`), then check size and identity again under it, as `_hold` already does. Give the press Approve's long bound.
- **N20 [Minor, doc] No recorded answer for the copy's cover and text files.**
  - Judy asked Sergei: "Should Remove this copy also delete the copy's cover and text files and empty folders, by the same rule as ruling 24? (yes / audio only)".
  - Ruling 24a answers the folder half ("Allow"), which implies the files go. But no ruling says so. The code and the Brief take Judy's default, yes.
  - Those files are not copies of anything in Sorted: a booklet PDF may exist nowhere else. Each is listed in the dialog.
  - **For Sergei, through Jane:** yes, or audio only.

### Other dimensions for this delta

- **Security:** Pass.
  - The two routes take one more optional field each: `mode`, one of two values; `folders`, with the same bounds as `paths`.
  - No shell, no new process call, no Electron change (nothing under `desktop/`), no secrets.
  - No attribution trailer in the 19 commits.
- **Crash safety:** Pass. A failed working-file discard or folder removal is reported, never raised past the press. The records transaction rolls back on any failure.
- **Performance:** N19.
- **State and data safety:** Pass; the safety floor is intact. Every file removed is a path Sergei confirmed in the dialog, inside a source root, through an exact handle, never in Sorted. A folder is removed only by a plain rmdir after its listing shows nothing.
- **Build hygiene:** Pass. Version 0.22.0; `package.json` and the lockfile do not change in this delta. The changelog lists the new actions, the quiet skip, the seven workers and the QA fixes.

---

## Patterns

Grouping is still where the risk lives, as in the early review. Each fix closed the exact case I probed, and a sibling case of the same shape stays open: a word list in place of a works check (N4), two names in place of a dash split (N5), the new join path in place of every album group (N6). The joins themselves are sound: offsets, verification, cleanup order and failure handling all held under my probes, and their core mutants are caught. Five guards around them still have no test of their own (N9). The next gains are one shared "these files name more than one work" check used by every grouping route, and a decision from Sergei on whether chapter restarts may ever overrule an explicit part marker (N2).

The delta shows the other side of that shared check. Reading every file-name or track title as a work is too broad: named chapters look like works, so one real book stops joining (N10) and 21 real books are held (N11). The shared check has to know chapter names before it is applied to every route. Each fix should be measured on the live catalog before it ships, not only on a synthetic positive control.

The final delta did exactly that for N10: one partition change on the live catalog, and it is the intended one. Delete book's file guards are the strongest part of this release. They are the same exact-handle code source cleanup uses, and the server alone decides each offer. Its gap is the same kind as the grouping gaps: it is guarded against everything that acts on a book except the app's own scanner (N13). Any new action that writes the catalog should join the scan-active refusal list by default.

The last delta widened Delete book on purpose (rulings 24 to 26) and added Remove this copy, and it kept the same shape: the server lists every path, Sergei confirms that exact list, and the press removes exactly it through exact handles, records last. What is left are judgment calls about whose a file is (N18, N20), not missing guards. Remove this copy's proof is sound; its cost is where it runs, under the app's locks (N19).

---

## Verdict

Counted at 7490b39 (whole range v0.21.2..7490b39):
- Total Critical: 0
- Total Major: 0
- Total Minor: 8 (N2, N7, N11, N18, N19, N20, m6, m7 second half)
- Closed by the final delta 01581a6..7490b39: N13 (Major), N14, N15, N16, N17. Earlier: N10 (Major), N8, N12; N1 (Major), N3, N4, N5, N6, N9.

No Critical finding is open, and the safety floor is intact:
- no machine harm, no secret, no source of truth touched;
- every original is removed only after its verified result is in Sorted, with two exceptions, each Sergei's own ruling on his own press:
  - Delete book (rulings 23, 24, 26) removes only the confirmed book's own files, its own working files (the last copy included) and the folders the press leaves empty;
  - Remove this copy (ruling 25) removes only a copy whose every file has the SHA-256 of a source of a verified audiobook in Sorted;
  - neither touches Sorted or goes through a junction, and a folder goes only by a plain rmdir after its listing shows nothing (ruling 24a);
- Keep writes catalog rows only, in one transaction that cannot report success without the split.

N18 to N20 are logged for Ender and do not block. N20 and N11 (17 albums) need Sergei's answer through Jane.

The checker change in studio commit a4783ba is trustworthy, and its Git support does not run for Books Arranger.

**Verdict:** RELEASE CLEAR
