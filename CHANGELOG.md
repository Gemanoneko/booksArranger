# Changelog

## [v0.22.2] - 2026-10-26

### Added

- Edit names on every row. Fix a title, author or series yourself. A correction is kept for later scans, and the app says how many books it applies to before you save.
- Collections that belong to a series are filed under Сборники, in a folder for the series, with the series number in the file name.
- Вселенная Дозоров is a universe with one numbered series. «11/22/63» files as «11.22.63».
- Save shows Saving… and then Saved.

### Changed

- Nothing refuses for being busy any more. A press made while something else runs is queued and shows Cancel. When a press is refused, the row says why and what to do next.
- Translated books wait for their English title. If none can be found, they convert under the Russian title (ruling 29).
- Latin names are filed surname first. Authors who write in Russian are filed in Cyrillic. Ж is matched with Z.
- Co-authors and readers are sorted out before the title is read.
- Start works while audiobooks convert. The scan waits for the conversion to finish.
- The "evidence" field is gone. Nothing asks for it and nothing requires it.
- The "pause audiobook jobs before automatic processing" refusal is gone.

### Fixed

- Updater: a failed install keeps the app open. Restart to update and Cancel answer at once, and an approval in progress stops for the update.
- The first-run window stays hidden when the app starts hidden.
- Research no longer stops when the catalog is busy.
- The empty Xtra box and the Explorer rating are accepted in M4B files, so those books convert.
- A slow media check waits and is tried again by itself. It no longer lands in "Needs you".
- A deleted book's row leaves at once, and a stale list cannot bring it back.
- Odd titles from the live catalog now file correctly («1408», «11.22.63», «Голиаф»).

## [v0.22.1] - 2026-10-26

Updating from 0.22.0 is manual: right-click the tray icon and choose Quit, then run the installer. From 0.22.1 on, the app updates itself with Restart to update.

### Added

- Retry, Repair and Delete book can be queued: pressed while the engine is busy, they wait in a queue instead of failing. Each row shows its queued state, the details panel has Cancel retry and Cancel repair, and the outcome is shown on the row. One queued action per book.
- Delete book is offered on rows whose files are all missing.
- Odd names are asked instead of filed by themselves (a bitrate in a title, two people in one author folder, a folder name as author).
- The folder structure Author\Series\N. Title is read, and clean numbering in the file names decides the order. On a copy of the live catalog, Order unclear rows fell from 134 to 19.
- An author rule, a seed included, can be taken back.
- The window opens at once and fills in. One loading strip shows Working, Waiting, Stuck or Stopped.
- An App updates panel with a confirmation dialog and phase lines.

### Changed

- Presses and the book list no longer wait behind background work. On a copy of the live catalog, Remove from list during research went from 46 s at most to 0.4 s.
- Books are approved at once on their local title and author. Optional details are filled in later, in the background. Approvals per hour during a research run rose from about 58 to about 590.
- A reader is never taken for the author.
- A slow answer shows "busy" instead of "Connection interrupted".
- The update check no longer depends on the engine. Restart to update answers at once and stops the engine in safe steps. It can be cancelled, installs silently, and puts the old engine back if the install fails.
- The to-do list reuses each row's "Goes to" answer while nothing it reads has changed.
- The test gate runs the new suites (lock timing, gap fill, folder structure, updater, startup, action queue).

### Fixed

- A copy offer withheld while the audiobook was away comes back without a scan.
- A conversion that lost its drive offers Retry once the drive is back.
- A task whose catalog evidence changed during its read is read again; it no longer fails the scan.
- Remove this copy proves the copy before it takes the app's locks, and Quit stops it.
- A folder with another book below it, or with other audio, keeps its files when a book is deleted.
- A series folder names its series only; "Author (year) - Title" folders name the book.
- The busy notice no longer flickers while a slow press waits, and the status keeps answering.
- Focus returns to a row's queued face after the list is rebuilt; focus survives re-renders on Stopped rows.
- The updater panel no longer breaks on a shell status without busy flags.
- Test probe folders are removed when their test ends.


## [v0.22.0] - 2026-10-25

0.21.3 was never released; its changes ship here.

### Added

- Sergei's typed values are authoritative: what you type for a book's title, author or series is used as it is. A book on the to-do list can be accepted with Approve as is.
- Lasting author rules: Sergei's answers about authors, such as which name is the author and which is a reader, are kept as rules and applied to later books.
- One to-do list in "Output needs attention". It holds only books that need Sergei, sorted by reason, folder and title, with a typed reason and its actions on each row, including Keep as separate books for a set that looks like parts of one book.
- The parts of one book in one folder are joined into one book. M4B parts are joined by re-encoding once, with their chapters kept; chapters also decide sets whose files are only numbered.
- Two common Order unclear causes are named on the row.
- A new "Delete book" action for books with missing parts or broken audio. After a confirmation it removes that book's own files and records; nothing in Audiobooks Sorted is touched. It waits while a library scan runs. It also removes the book's own cover and text files, the app's working copy, and folders left empty (including on network drives; never one directly in a source folder or in Sorted).
- A new "Remove this copy" action for verified duplicates. It checks the copy in Audiobooks Sorted byte for byte before deleting.

### Changed

- Title and author from one local source are enough to identify a book.
- A held book is researched again only when it changes.
- The book list is faster: on a 200-book test with 50-99 books converted, the median wait fell from 13.3 s to 3.4 s. It no longer waits behind automatic approvals.
- The test gate now runs on seven workers, with the page and syntax checks running alongside them, and its tests wait for each fixture scan to finish instead of a fixed time.
- Scanning: files and folders deleted outside the app are skipped quietly during a scan.

### Fixed

- Senua's review findings: the 0.21.3 findings F1-F4, F6 and F8, the early 0.22.0 review findings (G1-G6, m1-m5, m7-m9), and series backfill now names books relative to the folder they were published in.
- "Keep as separate books" now really splits a set even when its details were saved. More doubtful part sets are asked about instead of joined: Эпизод/Том numbering, sets that name several works, generic titles like «Неизвестно», and credits naming three or more people.
- A status computed without a catalog no longer fails on the to-do list.
- The to-do list filter chips work.
- Chapter-named files and title tags no longer split a single book.
- After a "Same author?" answer, both books continue.
- Approve on books with many files no longer reports a false "Connection interrupted".
- Joined chapter files get proper chapter names.
- Small fixes: a refused Approve keeps the book listed; "Not found" is shown for missing files; focus returns sensibly after Delete; the "Goes to" line is shown on stopped rows.
- "Scan again" reports honestly.
- "Approve this order" works right after the track review is saved.
- No typed note is needed to save a track review.
- Missing or unreadable files are described in plain words.
- The to-do row never proposes a suspected reader as the author.
- Tests: a borrowed fixture no longer leaks its research patch, and the local-identity switch is restored after each test.

### Fixed (from the unreleased 0.21.3)

- Two Макс Фрай M4B books with an empty padding box now convert; the audio is proven identical.
- The converter no longer re-reads the whole library for every book. On a 200-book test, 194 books converted in 50 minutes instead of 138, and the longest list wait during approvals fell from 34 s to 11 s. The book list itself can still take several seconds on a large library.
- Files gone from disk no longer count as read errors; they show as "No longer found".

### Safety

- Originals are removed only when the verified result is in the configured Audiobooks Sorted folder; automatic processing refuses to start without one.
- Further hardening of the delete paths: the output is re-read right before each original is removed, a folder that is a direct child of a source root is never removed, a removed download marker is put back when cleanup stops, series backfill never changes a book outside the Sorted folder (it renames nothing at all in this version; renaming in Sorted comes later), and a recovery child's output is re-verified before the old attempt's files go. The source-removal suites now run in the gate.

## [v0.21.2] - 2026-10-24

### Fixed

- An automatic approval reads the list of converted books once instead of seven times. On a 200-book test catalog approvals took about 40% less time and the book list waited about half as long during them. The book list still pauses for seconds while a book converts; that is not changed in this version.
- Pressing Start at the same moment as Quit or Pause now pauses the automatic run, instead of failing it.
- The build guard is re-pinned to Git for Windows 2.56.0.3, so `npm run pack` starts again. A Git core pin mismatch now names the core, not the wrapper.

### Changed

- The QA gate now refuses a checkout that holds a live `data/` folder, so it can never run against the real catalog.
- Test fixes: the gate runs the local-admission and catalog-paging tests and finds its pinned QA runtime through `BOOKS_QA_RUNTIME_ROOT`; the standing-admission retry fixtures make their own scratch folder; the local-admission host check allows the v0.18.0 series publisher query; the catalog-paging invalidation case changes a track title, not the album; the one-approval case counts only the approving thread's reads.

## [v0.21.1] - 2026-10-23

### Fixed

- A damaged in-place edit record can no longer keep the app from starting, whichever of its fields is missing or wrong. Its book needs attention with a reason that says the record is damaged, nothing is written to its file, and other books carry on. A record with an empty key now affects only its own book, instead of giving every interrupted book a false reason at every start.
- A book folder renamed or deleted after an interrupted in-place edit is reported on its book again as a missing original. Only a library that cannot be reached at all, such as a share that is not reconnected yet, leaves the edit open until the library is back.
- Undoing an in-place edit, after a failed check or an interrupted run, now puts back the Windows download marker the edit removed, so the original is restored exactly. Edits recorded by 0.21.0 get their marker back too.
- An undo checks the recorded modification time and attributes before it changes any byte. A record with values it could not restore is left as it is and needs attention, instead of being half undone.
- An MP3 book whose full audio check failed in an earlier app version, such as Железная преисподняя, can be retried. Retry, Retry all and Retry selected accept it, and automatic processing queues it once by itself. The new job checks the MP3 again with the existing trailing-tag repair. If the check fails again, the book asks for a replacement source as before. Its original is cleaned up like any converted book.
- A book blocked because its interrupted conversion may still be running, such as Сказка, now offers Convert…. In its dialog you confirm that the conversion ran on this PC and that Windows and its files were not moved, copied, cloned or restored from a backup since. One press then saves the confirmation and starts the new conversion. The app confirms the old conversion ended from a Windows startup after it, so no restart is needed when one has already happened; otherwise the book asks for one and keeps the confirmation. Once the new conversion is verified, the old working files are deleted, and the original goes through the normal source cleanup, like any converted book.

## [v0.21.0] - 2026-10-23

### Added

- A single M4B whose audio is already kept as it is now has its new tags, cover and chapters written into the file itself, and is then moved into the sorted library by a same-volume rename, without copying the book. The result is the same file the existing flow publishes; the audio bytes never move.
- Every in-place edit is journaled before its first write. Any failed check, a pause, or an interrupted run restores the original's exact bytes, size and modification time before the book continues, and the existing flow then runs with all of its checks. A Windows download marker removed just before the move is not put back. A file that can no longer be proven to be the edited original is left as found, and its book needs attention. Books that need a repair or a re-encode, ALAC files, or a destination on another drive keep the existing flow.

### Changed

- The in-place path checks tags, cover, chapters, packets and the exact original bytes, but does not decode the audio (Sergei, 2026-10-22). Its source cleanup records the move as the original's retirement; no recovery copy is made.
- Within one conversion, sources are hashed in full once at the first check; later checks in the same conversion compare size, modification time and file identity, and hash in full again only when one differs. Removing or retiring an original still hashes it in full first.

## [v0.20.3] - 2026-10-22

### Fixed

- Automatic discovery resumes safely when a previous scan is interrupted and an additional source is configured, preventing the mixed resume/new-source path from aborting the scan.
- Bulk Retry accepts eligible books in the Other reason group instead of refusing them because of the displayed group label.
- Processing status clears stale Starting messages and keeps Pause, Continue and retry refusal feedback aligned with the current operation.

### Changed

- The build bootstrap Python pin is updated to the installed 3.14.9 so packaging starts again; the bundled runtime in the installer remains 3.14.8.

## [v0.20.2] - 2026-10-21

### Fixed

- Same-volume output migration uses a journaled Windows move without copying files, with recovery after interrupted moves and explicit cleanup of a previously verified duplicate.
- Scanning and conversion wait for unfinished moves, and completed books remain valid under the configured output root.

## [v0.20.1] - 2026-10-21

### Fixed

- Output migration recognizes completed series retagging through its recorded publication history, while refusing changed or incomplete records.
- A book whose publication cannot be verified is reported as held without aborting planning for the remaining books.

## [v0.20.0] - 2026-10-21

### Added

- Author, shared-cycle and universe organization, with short-story collections placed under their applicable cycle or universe and unassigned collections retained in Сборники.
- Additional audiobook source configuration and verified output-migration tooling that preserves publication, job and recovery bindings while checking destination copies before removing originals.
- Preserved manual metadata evidence and explicit choices when metadata sources disagree.
- Producer-recovery preparation and source-incarnation handling for replacement discovery. General serious-audio-damage classification remains inactive; recovery holds still require their recorded proofs.

### Fixed

- Bulk Retry distinguishes saved requests from created conversion jobs, reports waiting or blocked starts, and prevents superseded starts or cleanup work from continuing after Pause completes.
- Catalog progress and scan writes use bounded database-only contention handling without replaying external media or metadata operations.
- Narrow M4B admission barriers and a verified zero-audio-loss trailing ID3v1 repair are handled without changing original-source bindings.
- Direct metadata resolution opens Manual review at the questions, and lifecycle counts remain accessible.

These changes do not activate additional sources, migrate the existing library or clear recovery holds automatically.

## [v0.19.0] - 2026-10-19

### Added

- Refused Retry follow-ups. Start over replaces Retry on a book whose saved review changed, and "Let the app handle it" (a single held M4B, with a Cancel-first confirmation) hands the book back to the automatic pass. The book keeps a "Started over" state with the live pass state, and the book list now fits a narrow window.
- Leftover working files can be cleared or are reported as blocked, with a Clear working files action; Retry and Repair clear them first.
- A pass started by Start over, a release or a pending start now shows its library scan.

### Fixed

- M4B Retry says "ready to retry" only after a passing dry run, shows "checking" or "can't open" otherwise, stops offering Retry on a book whose Retry was refused, accepts four exact M4B writer shapes that refused nine books, and is admitted on a catalog that never had an audio-staging folder.
- A pending start now ends on Stop, Quit and the safety stops, and nothing starts once Quit has begun (previously a pass could start during Quit or past a disk-full hold).
- A working file held open by another program reads "try again in a moment" and its row recovers once released, with no restart.
- A refused Retry or Repair clear-first answers with the refreshed row, so the details panel no longer offers actions from before the press.
- The Start over note promises "Let the app handle it" only when the button will appear.

## [v0.18.0] - 2026-10-18

### Added

- Independent series fallbacks after Goodreads and FantLab: strict referenced Wikidata narrative-series statements, Wikipedia revision/reference discovery, and a supported Penguin Random House primary-book schema. Exact title, all authors, work identity and explicit order remain required; provider quotas, cache and holds stay shared and unchanged.
- Bounded local Open Library indexing for authenticated downloaded authors/works and, once complete, editions. Imports verify whole inputs through gzip EOF/CRC, preserve reference integrity and checkpoints, and activate a validated SQLite generation atomically. Partial Editions downloads remain unavailable; edition series strings are discovery, never automatic reading-order proof.

### Fixed

- Previously negative series results can be researched again when the accepted local-index generation changes, while completed, held and recovery records retain their safeguards and preferred Goodreads evidence.

## [v0.17.0] - 2026-10-18

### Added

- Goodreads series-page evidence: an explicit numbered entry can supply series order when an independently fetched search result matches the exact title, every credited author and immutable book id. Citation-only source leads preserve the original «Нормальное аномальное» sequence for «Призраки белых ночей» #10. Normal provider pacing, quotas, cache and human-check holds remain unchanged.

### Fixed

- A provider wait now defers only its book, with a saved reason and next-attempt time, so other eligible books continue fairly. Verified findings can wait for genuine conversion/cleanup/scan idle without renewing their original evidence age; stale or invalid proofs require fresh research. Existing exact-file recovery and disposal checks remain required.

## [v0.16.12] - 2026-10-18

### Added

- Series for books already published (Sergei, 2026-10-18). A background pass looks up the series of each finished book that has none: Goodreads first, then FantLab, with the same pacing and cache as research. It starts two minutes after the app opens, never holds up a conversion, and picks up where it stopped after a restart. When a series is found, the album, grouping, sort-album and track-number tags are rewritten. Every other byte, including all audio and chapters, is copied exactly, and that is proven before anything is replaced: the media and sample tables are byte-identical, the compressed audio and its decoder settings match, the chapters, cover and other tags are unchanged, and the new tags read back correctly. The book is then renamed on the same drive to the name a newly converted book in that series gets ("Series - NN - Title - Author.m4b"), never over an existing file. The catalog records the new file at once, so the book still reads as verified, and the old file is removed; no copy is kept. If anything is in doubt, the book is left exactly as it was and the reason is recorded. While it works, a progress row reads "Updating series: <title>" with "N of M books".

### Fixed

- Retry in Output needs attention (Sergei, live on v0.16.11). A pressed Retry briefly came back as an enabled "Retry". The press could wait behind a slow book-list read, and when the book left the list, focus jumped to the next book's Retry. Now:
  - the button shows "Checking…" while the request is in flight, then a disabled "Queued", and only an explicit refusal from the server, with its reason, brings back Retry;
  - an older list never repaints it, and the book stays in place with a note "<title> queued — runs after the current book";
  - focus stays on that book;
  - a repeated press changes nothing on the server;
  - a press no longer waits for the review lock;
  - a book-list read no longer holds the catalog's write lock while it builds the page.
- "Retry selected (N)" replaces "Queue selected books" in Output needs attention. It queues the selected books that can be retried or repaired, after one confirmation, one at a time right after the current book. The selection count there reads "N can be retried or repaired" instead of "need review".

## [v0.16.11] - 2026-10-18

### Added

- Series research (Sergei, 2026-10-18). When a book has no series in its own tags, research reads its Goodreads book page for the series name and number. Requests are slow on purpose: at most one every 5 seconds and 120 an hour, each page cached for 7 days, and an unavailable Goodreads never holds a book. When Goodreads lists no series, FantLab's cycle is used instead; its number is counted from the cycle's order, and books with two authors are accepted. When both have a number, Goodreads wins. The source is recorded with the book's metadata.

### Fixed

- "Storm of the Century": its temporary working files showed cleanup "pending" with no reason. The step after its source cleanup ended without leaving any record, and nothing tried again while the queue kept running. Now such an error is recorded with its reason, and the background cleanup finishes any finished book whose temporary-file cleanup has no record, once per run.

## [v0.16.10] - 2026-10-18

### Fixed

- Every book started by Retry or Repair stopped at once with "Source changed — review required", so none of them ever finished. Five books were affected: "Cabal", "Storm of the Century", "Призраки белых ночей", "Пасынки Вселенной" and "Темные воды". Before a book starts, the app compares the job with the reviewed book. Retry and Repair add their own repair details to the job, and that comparison treated those details as a change. Now only what the review decides is compared. Every source file's content is still checked in full, and the repair details are checked when the book runs.
- A book stopped this way shows Retry, or Repair for a repaired book, and runs again as the same job, with the same approved repair.
- The 0.16.9 file-number change stays, but it was not what stopped "Cabal".

## [v0.16.9] - 2026-10-18

### Fixed

- A book could stop under "Other" with "Source changed — review required" even though its files had not changed ("Cabal"). The library share sometimes reports a different internal file number for the same file, and the check compared that number. Now the file size, modification time and full content decide, and the file number no longer counts. A book stopped this way shows under "Can retry", and the files are checked again before it runs.
- An M4B whose chapter pictures point to the file itself ("Orphans of the Sky") is no longer refused. It shows under "Can retry".
- An M4B whose audio container declares a slightly smaller size than the audio it holds ("Темные воды") shows under "Can repair". Repair corrects only that size field; every audio byte stays in place.

## [v0.16.8] - 2026-10-18

### Changed

- Backups end when the audiobook is verified (Sergei, 2026-10-18). As soon as a converted book is verified, its recovery copies are deleted, and so are the recovery copies of former outputs a replacement retired. The 24-hour window is gone, and books waiting in the queue or converting no longer hold the deletion back. On the first start, every existing set whose book is verified is deleted the same way. Each deletion verifies the audiobook in full first, and a copy that is already gone is recorded rather than reported as an error. Only a missing or unverified audiobook, or a copy that changed, keeps the files; those are flagged with the reason.
- Retry and Repair now answer at once, even while a book converts, and every retried or repaired book runs right after the current one, including a book that stopped because the catalog was busy. The row and the panel show a disabled "Queued" button with "Queued — runs after the current book" (or how many books first). If the press gets no answer in time, the page checks the book on the server and shows "Queued" when the press went through, instead of an error.

### Fixed

- Status and the book list stay fast while a book converts. Before, every poll re-read every recovery set and checked every source folder on the library share, which took 5 to 7 seconds per poll and led to "Status is still updating" and "Local server unavailable". Measured on a copy of the real catalog with a one-hour book converting: status 5.8 s to 0.5 s, the Ready list 5.6 s to 0.3 s, and switching attention groups 5.4 s to 0.4 s (median). A busy status reply is no longer treated as a lost connection.
- Quit: once the engine has finished its work and closed, the app now always exits, and a second Quit ends the app when the engine no longer answers. Before, the app could stay running with no window.
- A cleanup held by "Download marker native identity differs" finishes on its own. The library share reports its own file number for a file's download marker, so the check now compares only what is reliable; each original is still proven by its full content hash.
- A cleanup that needs attention shows "On hold — reason" with no progress bar or elapsed clock, instead of a bar that looked like it was moving.
- Books whose backups are kept now appear in "Output needs attention" under "Original changed" or "Audiobook problem", with a "Keep files" button that stops flagging the book and deletes nothing. Keeping is permanent: no later automatic deletion touches that book's files, even once its audiobook verifies again; "Delete recovery copies" still removes them on request. Empty reason groups are hidden, except All and Can retry. The Jobs panel's "need attention" count now matches the All count.
- A download marker with unexpected contents no longer holds a cleanup: its exact bytes are saved in the cleanup receipt. Empty source folders the app cannot remove safely on this drive stay in place and no longer show a note or hold anything. A folder job that stopped on a busy catalog runs again, and one whose folder is already gone is marked done.
## [v0.16.7] - 2026-10-17

### Changed

- A book no longer needs tens of GB of free space to convert. Before, every track was turned into a full uncompressed WAV copy of the audio and all of them were kept until encoding, so a 1.3 GB, 22-hour book ("The Lost Symbol") asked for 62.7 GB. The audio is now decoded straight into the encoder, so the working space needed is about twice the size of the book's source files. Every byte given to the encoder is still checked against an independent full decode of the sources, and the finished audiobook is still verified before any original is touched. Measured on a 1-hour, 20-track book: peak working space went from 1.39 GB to 116 MB, and conversion time from 146 s to 74 s.
- The book list loads much faster on a large library. On a 4,000-book test catalog: "Output needs attention" took 1.1 s instead of 7.4 s, "All candidates" 1.5 s instead of 6.5 s, and Held, Queued, Ready and Approved about 0.1 s instead of 2 to 10 s. While a different list is loading, the table says "Loading …" instead of showing the old list under the new filter.
- Idle app no longer re-scans the catalog: indexed recovery lookups, page-scoped lists and quiet status; filter changes show Loading at once.

### Added

- Books that need attention now say what to do. Each row shows a short status ("Stopped — ready to retry", "Stopped — not enough disk space", "Damaged — can repair", "Can't convert — M4B not supported" or "Stopped — see details") and a one-line hint. The technical reason is shown when you point at the status and in the book's details.
- Retry is now in the list row too, and also works for a book that stopped because the catalog was busy or the disk was full (once enough space is free). Every Retry checks the book again before queueing it.
- Existing M4B books that stopped for a reason this version now handles can be retried. Retry first proves the book can be kept byte-for-byte, then queues it as new work; the stopped attempt is kept as history.
- Retry and Repair of these M4B books work even while another audiobook is being created. The book runs right after the current one, ahead of the normal queue, in the order you pressed, and its row says so ("Queued — runs after the current book", or after how many books). If the check before it runs refuses it, the row shows why and Retry or Repair can be pressed again. "Retry all" queues them the same way.
- Repair for M4B files with a broken chapter pointer, an audio container that claims a few bytes past the end of the file, or a cut-off end (at most the last second of audio, replaced with silence of the same length; every other audio frame is unchanged and checked). It runs only when you press Repair, never on its own. The row says what is wrong and what Repair does, and afterwards the row and the details panel record exactly what was patched. Repair only reads the original files.
- While "Output needs attention" is selected, buttons above the list group the books by reason (Can retry, Can repair, Other, M4B not supported), with live counts. "Retry all" asks you to confirm, then retries every book in the "Can retry" group (the whole group, not just the page shown), one at a time, and reports how many were queued.

### Fixed

- Existing M4B books written by Audiobook Builder/QuickTime 7, Chapter and Verse, fre:ac (Nero tags) and iTunes-style taggers are now kept byte-for-byte instead of stopping for review.
- A book without its own cover no longer fails "Preservation changed decoder, packets or presentation" when the approved cover is added.
- Very long existing M4B books with large chunk tables (up to 524,288 chunks) are now kept byte-for-byte instead of stopping with "Table count/extent".
- The research progress row moves again. Before, it could stay at the same count while the book being researched changed many times, because it read a progress record that was saved only now and then.
- A cleanup that stopped and needs attention is shown as a needs-attention row, instead of appearing as running work between two books.
- Copying source files now shows whole files ("2 of 17 files") instead of fractions.
- The estimate of time left appears once it is reliable. The research row's timer no longer restarts with every book, and the list no longer delays the progress updates.

## [v0.16.6] - 2026-10-17

### Added

- The Audiobook jobs panel now shows one progress row for each running activity: converting a book, removing originals or temporary files, checking finished books, and scanning or researching. Each row says what is happening now, shows real progress where it can be measured (files, MB or GB, audio time, or books), and counts the elapsed time, with an estimate of the time left once it is reliable.
- Conversion is shown as four steps, each with its own bar and step text: checking and copying the source files, normalizing the audio, encoding, and verifying and copying the audiobook to the library. Before, everything before encoding showed as "Checking source files" with a bar that never moved, sometimes for 20 minutes or more.
- Steps whose amount cannot be known show a moving bar instead of an empty one. Paused rows freeze and say "Paused"; a row that needs attention shows the reason. Pause and Resume now sit above the rows, so they never move.

### Fixed

- After Retry was accepted, the book could keep showing "Needs attention" with Retry still available, and a second press said "This book changed. Refresh and try again." The book now shows as queued at once, and a book list requested before Retry was answered can no longer bring back the old state.
- The message for a Retry pressed on an out-of-date view no longer names a Refresh action that does not exist. It now reads "This book's status changed. Check the updated status above."
- Progress updates can no longer stall or fail a conversion. While the catalog was busy, a progress update could wait for the job queue long enough to fail the book.
- The version badge now shows the engine version only. It no longer switches between "Engine v…" and "v… · local prototype".

## [v0.16.5] - 2026-10-17

### Added

- Retry for an audiobook job that was stopped before it started. Leftover working files from an earlier attempt could block a book: it showed "Output needs attention" and nothing could run it again. The selected book's details now show a **Retry** button under Automatic result. While the files are still there, Retry is unavailable and says why; once they are gone, it turns on within a moment. Retry checks the book again and puts the same job back in the queue, and its saved review and source files are checked again before any work starts. Like every queued book, a retried book removes its included originals after a verified audiobook, keeping 24-hour recovery copies.

### Fixed

- A source cleanup that stopped because the catalog was busy no longer stays stuck in "needs attention". At startup it becomes "paused", and the next **Start automatic processing** or **Resume audiobook jobs** finishes it. The recovery copies, the remaining originals and the finished audiobook are all checked again in full before anything more is removed, and the 24-hour recovery period starts when the cleanup finishes. This also finishes the two cleanups stuck on 2026-10-15 and 2026-10-17. The same Start or Resume also re-checks the books held for extra download markers. After updating, press Start or Resume once: while a cleanup is paused, the next app update cannot install and expired recovery copies are kept.
- A busy catalog during source cleanup now retries automatically after 5 seconds and again after 15 seconds, then pauses the cleanup instead of marking it "needs attention". Pause, Stop and Quit cut the wait short.
- A book whose audiobook job needs attention now shows the job's own reason instead of "Audiobook job already exists; inspect its current status".

### Changed

- "Retry available after …" on a held book now reads "Automatic retry after …", so it is not confused with the new Retry button.

## [v0.16.4] - 2026-10-17

### Fixed

- Quit now works at any time, including in the first minutes after launch. The background check of finished books in v0.16.3 could keep the engine too busy to answer the window's Quit, which then failed with "The engine did not confirm a safe Quit". The window's status request now always answers within a few seconds, a Quit request does no slow work before it is accepted, and the check stops within moments when the app quits.
- Finished books are no longer re-read from the library share in full at every launch and every Start. Each book's file identity (volume, file id, size, modification time) is recorded when the book is fully checked; later routine checks compare that identity instead of hashing the whole book again. A book whose identity changed is still hashed in full, and removing originals, recovery copies or working files still checks the book in full first. On the first launch after updating, the one-time full check runs in the background at a limited read speed so the window stays responsive.
- Start no longer holds the queue while it re-checks finished books. Pause and Quit answer at once during that check, and either one stops it before any new book begins.
- The "Audiobook Ready" count no longer reads 0 after launch: it uses each book's last full check from the start.

## [v0.16.3] - 2026-10-17

### Fixed

- Books Arranger starts again on a catalog with many finished books. At startup the engine re-read and hashed every finished audiobook from the library share before it answered the window, which took about 2.3 minutes with 30 books and more than 4 minutes with 60. The window gives the engine 3 minutes, so it showed "Books Arranger could not start". The engine now answers right away and runs the same check in the background; a changed or missing book is still marked "needs attention", and Start still re-checks every finished book before any new work begins.

## [v0.16.2] - 2026-10-17

### Fixed

- Automatic processing no longer pauses itself between two books. When research had run out of new matches and the run was waiting for queued books, a status check made just as one book's originals finished moving to recovery could briefly read "Paused". The run then paused everything, stopped the book that had just started, and recorded "Paused — pending work saved" with no one asking. Overnight conversion stopped this way after 21 books. The queue now reads "Paused" only when no conversion or cleanup work is still running. Stop, Pause, Quit, a full disk and a working-file problem still pause the run as before.

## [v0.16.1] - 2026-10-17

v0.16.0 was never released; its changes ship in this version.

### Fixed

- The desktop window no longer piles up status requests on a large catalog. Previously the shell asked for status every second, each request did the same slow work twice, and abandoned requests kept running until the app ran out of threads and memory and could not quit. Status is now requested one at a time, computed once per call from a shared snapshot that is refreshed after every control, and reports "unavailable" instead of waiting more than 4 seconds. Cleanup checks and replacement lookups no longer reload the whole job table repeatedly.
- Fixed three intermittent test races (automatic processing and web server teardown).

## [v0.16.0] - 2026-10-15

### Added

- Standalone Windows Electron installer with bundled Python and FFmpeg, an explicit data-folder selector and a tray window. Closing the window keeps processing alive; Quit waits for the current book and preserves pending work.
- Manual update checks, downloads and explicit idle-only restart to update. Startup and update relaunch keep automatic processing paused.

### Fixed

- Preserve supported AAC M4B media, chapters and presentation timing when replacing metadata, avoiding a remux that changed otherwise valid books.
- Retire verified attempt-owned temporary files and published input snapshots at their terminal boundaries. Preserve originals, unfinished work and required recovery; repaired historical jobs cannot create another source snapshot while their old working files remain.
- Allow verified original-file cleanup when the only extra stream is the exact recognized Zone.Identifier download marker. Unknown streams still hold cleanup, and normal original and recovery checks remain required.
- Retry bounded automatic-processing SQLite contention and keep status reads from taking an unnecessary database write lock. Start availability follows the same state rules in the server and interface.
- Native engine and catalog ownership remain held when safe checkpoint shutdown fails; stale ownership records cannot authorize an unguarded launch or PID-only forced termination.
- Installer staging and publication use owned bounded workers, exact artifact/source proofs and a single documented release path.

## [v0.15.0] - 2026-10-13

### Added

- Split books: files that provably form one book become one candidate whose ordered parts become one M4B, one chapter per part (for example the 155 chapter files of one Dan Brown novel, "Чужак 1.m4b" / "Чужак 2.m4b", CD1/CD2 folders). Grouped only when every part has the same book title (album), the same author, reader and recording tags, the same audio format, and gap-free numbering with no duplicates (embedded track numbers, part numbers in the file names, or disc folders). Gaps, duplicates, mixed readers or recordings, volume numbers ("Том 3", "Книга 2") and parts with their own story or book titles hold the files as before.
- Split-book safeguards (review of the first candidate): the numbers in the file names must equal the track numbers, so numbered titles such as "Метро 2033" / "Метро 2034" or "Fallout 3" / "Fallout 4" are never one book; a year in a name is part of the title; a title tag on any single part, the exact album (brackets included) and an episode, CD or track number followed by a name each keep separate works apart; a zero-padded part ("0001") is a part, not a year.
- One author, one folder: a spelling confirmed by fetched, verified catalog or publisher evidence (books admitted for conversion, approved reviews, conversion jobs) anywhere in the library wins over a more common local spelling; a one-letter slip is replaced only when the confirming book itself carried that slip. Unverified research never confirms. Without a confirmation the most common local spelling is kept (Pratchett and Zahn have no verified confirmation today).

### Changed

- M4B parts are joined by the existing v4 normalizer: decoded and re-encoded once at the parts' own bitrate, sample rate and channels. Joining AAC by stream copy is not supported (each part carries its own encoder delay), so it is not attempted. Parts whose audio profiles differ at conversion are held.
- M4B parts that carry their own chapters are never joined (Sergei 2026-10-13): each part is its own book with its chapters kept (single-M4B copy, no re-encode). Example: Clive Barker's Imajica folder becomes "Имаджика - 1 - Пятый Доминион. Главы 1-20" … "Имаджика - 4 - …". Every part keeps its parent work: the set's album is its series (only when a folder or the shared file name repeats it), its track number is its number, and its own title (where tag and file name agree) is its title. A set is filed part by part only when every part qualifies and every part carries its own chapters; otherwise the whole set stays held, so a book is never published piecemeal. Only whole .m4b files become part books or are re-filed; a multi-file .m4a group with a chaptered file is held together. Parts of a joined book found with their own chapters at conversion are re-filed as separate books.
- "Philip K. Dick" and "Дик Филип Киндред" are one person: a middle initial may stand for a middle name when the first name and surname are written in full on both sides and the library has no other middle name for that person. An initial written before the first name is never read as a middle name; the word order of the two spellings is not compared (known limit; the only live merge is Dick).
- Under a collection folder, a plain credit of Олег Булдаков (named in Sergei's ruling 1 and credited as a reader in the library) is the narrator: such books are filed under Сборники as before for his comment-credited collections.
- A trailing four-digit number is part of a title, not a part number ("Метро 2033" beside "Метро 2034" is not a split part).
- A running automatic pass adds candidates created by the new grouping instead of waiting for a new discovery pass. Every waiting or held book gets one fresh pass. Media verification, publication, source retirement and 24-hour recovery are unchanged.

### Fixed

- Verified published jobs dispose of their exact producer-receipted working files independently of original retirement. Source snapshots, recovery, unknown files and full Ready/retirement obligations stay protected.
- Normalization chooses one smallest sample-exact PCM format for the whole job and proves the actual ordered concatenated PCM before AAC encoding. Rejected format comparisons create no WAV files.
- Space estimates and staging rechecks hold a job when space is short; ENOSPC parks the remaining queue at its saved checkpoint instead of accumulating failed working directories. Restart stays inactive until explicit Start.

## [v0.14.0] - 2026-10-13

### Added

- Local-agreement identity (Sergei decision 2026-10-12): when embedded tags and the file and folder names agree on title and author, that is the book's identity and no Internet confirmation is needed. Names match across scripts and word order ("Rollins James" = "Джеймс Роллинс"); every decision records which local fields agreed and how, and is re-checked against the current files before admission.
- Gap-only search: the Internet is asked only for fields missing locally (original title and language, series position, full author name), from the source that can answer them: FantLab, Wikidata, Open Library, Google Books (no key) and iTunes Search. A catalog answer is used only when it matches the locally agreed title and author.

### Changed

- Local conflicts still hold a book for the existing research path: different titles or authors between tags and names, two different people in author/artist tags (unless an author folder names exactly one), and a file sitting beside other files with the same title (one part of a split book).
- Readers and compilers are never authors: credits with a reader marker (читает, исп., read by …), a credit equal to the named reader, an author credited as a reader on other books in the library, and collection credits (Сборник, Разные авторы) all hold the book; collection folders and titles go to research.
- Names match across scripts only as a real transliteration, vowels included (Хокинг is not King); -ович/-евич/-ич surnames are never dropped as patronymics; a first name alone never matches a full name.
- A series name, a lone numbered part or chapter, or a disc/part folder whose sibling parts exist is never accepted as a whole book; the split-part check reads every file beside the book and fails closed.
- Sergei rulings (2026-10-13): collections compiled or read by a narrator are filed under Сборники with the narrator recorded only as narrator; a title spelling slip agrees and the tag spelling wins; one canonical author spelling per person (Russian name for Russian originals, English otherwise, most common local spelling, surname first, recorded); generic titles such as "Сборник рассказов" are accepted when the author agrees.
- Optional missing fields never block a book; a book waits for them only while the converter is busy, at most three queue drains.
- Retry timing waits for the sources a book actually needs instead of the first source that reopens.
- Host pacing is raised only where the vendor publishes a limit (Open Library, iTunes); Google Books has a courtesy cap below the default (no published anonymous number); other hosts unchanged. Requests identify the app with the public repository URL. A DuckDuckGo human check is respected as a one-hour pause. The research cache keeps up to 5,000 responses / 64 MB, with expiry and eviction through a small index so the shared catalog is not locked while raw responses are scanned.
- Every waiting or held book gets one fresh pass under the new rule. Media verification, publication, source retirement and 24-hour recovery are unchanged.

## [v0.13.1] - 2026-10-12

### Fixed

- Preserve the approved replacement recipe as exact LF bytes on Windows Git checkouts, preventing line-ending conversion from triggering the unchanged-plan admission guard. Genuine recipe edits remain rejected.
- Add regression test `tests/test_replacement_plan_bytes.py`: the checked-out recipe must pass the real admission guard (a CRLF checkout fails the suite), a CRLF copy must be rejected, and `.gitattributes` must keep its `eol=lf` rule.

## [v0.13.0] - 2026-10-12

### Added

- Durable, idempotent admission and publication of the authorized Eye of God replacement, using its protected original tracks, source-matched 128 kbps mono settings and one distinct Final output. Originals remain protected; lossy re-encoding is not claimed lossless.
- Verified current-publication relations and app-owned retirement of only the three authorized older conversions after new-output publication, registration and required cleanup, with verified 24-hour recovery and retained historical records.

### Changed

- Resolve current audiobook metadata, tags, artwork, folder action and Ready eligibility through the same verified publication; preserve reviewed destination previews and explicit unavailable states.
- Refresh changed publication facts while preserving inspector focus and manual drafts. Completed-book counts remain distinct by candidate during replacement.
- Publish source separately from its guarded application and actual replacement admission. No old conversion is retired merely by release or source update; unrelated audiobooks and the Google/Yandex prototype remain untouched.


## [v0.12.3] - 2026-10-12

### Fixed

- Retry only short native SQLITE_BUSY storage receipt transactions within existing bounds; full-row comparisons preserve output/file provenance and monotonic cleanup state without repeating native disposal.
- Retain bounded typed database diagnostics and logical disposition phase while preserving the primary exception if diagnostic persistence also fails.
- Correct a private recovery-retention fake's missing initialization field; no production recovery or Ready semantics change.

### Changed

- Leave actual fifth-book temporary cleanup for separately guarded stable application. UI, provider behavior, verified output/source protection and 24-hour recovery remain unchanged.


## [v0.12.2] - 2026-10-12

### Fixed

- Bind one module-level Windows ThreadEntry ctypes structure and thread enumeration signatures so concurrent owned-process launches cannot replace each other's pointer type.
- Preserve exact suspended-process ownership, one-thread identity, resume-count and handle-closure checks; no retry loop or ownership bypass is added.

### Changed

- Retain existing failed-job evidence; the separate guarded recovery proposal and Google/Yandex browser prototype are excluded from this release. UI, media verification and 24-hour recovery are unchanged.


## [v0.12.1] - 2026-10-12

### Fixed

- Retry native SQLite BUSY within bounded replay-safe checkpoint, fetched-cache, failure-diagnostic and atomic Paused saves; roll back and close each failed transaction without repeating requests, approvals or media operations.
- Preserve a committed Paused checkpoint when a stale Stop snapshot arrives, and close a connection if its initialization fails.
- Persistent contention at unchanged Stop-entry and other database boundaries may still fail closed. This patch does not guarantee uninterrupted processing; verification-before-deletion and 24-hour recovery remain unchanged.

### Changed

- Publish the reviewed patch separately from live application. The running v0.12.0 app remains unchanged until a later coordinated normal Windows restart.


## [v0.12.0] - 2026-10-12

### Added

- Independent public work/author evidence and approved standing metadata rules, including verified fan compilation contents, recording identity and source-bound duplicate review. Uncertain identity remains held.
- Guarded existing-M4B arrangement and supported media normalization, with native source holds, validated publication, ordered chapter evidence and exact working-file cleanup.

### Changed

- Default Book candidates to Audiobook Ready, hide intermediate stage filters, and refresh filters immediately while preserving manual drafts and stale-response protection.
- Continue eligible research across deferred sources with durable uncertainty backoff and guarded prepublication I/O retries. Manual Stop and restart remain Paused; confidence, source verification and 24-hour recovery retention remain enforced.
- Publish this coherent source release separately from the pending canonical application. Publication alone does not update the running server or its dependent browser assets.

## [v0.11.3] - 2026-10-11

### Changed

- Open the browser in Book candidates by default instead of Files. Switching views and their filters remain unchanged.

## [v0.11.2] - 2026-10-11

### Changed

- Rename the candidate filter label to “Converted by this app” to clarify its scope. The internal filter value and completion predicate are unchanged.

## [v0.11.1] - 2026-10-11

### Fixed

- Remove the blanket Windows Job-membership rejection that blocked normal Start-menu launch and restart. Exact-owner, idle, exclusive port/catalog, completed-record and readiness guards remain intact. No Job manipulation or tool-host launch bypass is introduced.
- Correct the startup admission documentation. Targeted producer and independent receiver launcher checks pass; actual normal-user launch/restart acceptance remains pending.

## [v0.11.0] - 2026-10-11

### Added

- Windowless Pythonw launch and guarded idle restart entrypoints, plus a bounded installer for the current user’s Books Arranger and Restart Books Arranger Start-menu entries. Installation does not launch the app.
- Verified-owner reuse and cause-specific native startup feedback. Restart refuses active work or unverified ownership; ordinary launch/restart leaves saved automatic work paused until Start.

### Fixed

- Health reports the loaded server version, and the server supports absent Pythonw standard streams. Existing metadata, retry, conversion and recovery safeguards remain unchanged.

## [v0.10.0] - 2026-10-11

### Added

- Active automatic runs retry eligible saved metadata research after interruptible waits, with the earliest retry check and distinct wait reasons shown in the browser. Explicit Stop and server restart keep work paused until Start.

### Changed

- Replace the app-imposed 100-request daily limit with 100 uncached requests per rolling hour per allowlisted host. Genuine source pauses and Retry-After remain respected; blocked hosts and cache hits do not spend the candidate request budget.
- Preserve confidence/admission gates, bounded public transport and evidence storage, existing conversions and 24-hour recovery retention. No new provider or paid connector is added.

## [v0.9.2] - 2026-10-11

### Fixed

- Closed, reset or aborted browser connections during response headers or body now end only that request, without a second response through the disconnected socket. Connected backend failures and unrelated I/O errors retain their existing behavior.
- This handles the observed disconnect symptom; WinError 10053 alone does not establish why the connection closed. Automatic-processing, conversion and recovery safeguards remain unchanged.

## [v0.9.1] - 2026-10-11

### Fixed

- Unexpected metadata-research failures now retain bounded sanitized diagnostics and atomically mark the run and affected candidate inactive. Previously stranded research states report missing historical details without inventing an exception cause.
- Explicit Start retries an eligible saved research checkpoint while preserving pending, completed and deferred work. Failure to save the checkpoint blocks retry rather than claiming it was saved.
- The original overnight exception remains unknown; this patch repairs lost diagnostics and misleading state, without changing approval gates, existing jobs or 24-hour recovery retention.

## [v0.9.0] - 2026-10-10

### Added

- Automatic audiobook discovery, bounded public metadata research, conservative approval and queueing through the existing converter. Explicit Start resumes saved work; Stop and server restart preserve pending work without an unattended retry scheduler.
- Evidence and held reasons in the browser, with protected manual drafts and safer separation of unrelated recordings sharing a folder.

### Changed

- Public-source requests and cached responses have bounded budgets, deadlines and retention. Missing or contradictory identity, source order, translation, name ordering or verified cover evidence keeps a book held; public search leads alone never approve it. The evidence-only Kabir/Shimada pilot did not enroll either recording.
- Existing approved/completed identities, validated conversion, Converted counts, source cleanup and 24-hour recovery retention remain unchanged. Empty-folder removal remains safely unavailable on the actual Z: drive. No paid connector, audio upload or dump importer is added.
