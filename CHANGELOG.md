# Changelog

## [v0.16.6] - 2026-10-17

### Added

- The Audiobook jobs panel now shows one progress row for each running activity: converting a book, removing originals or temporary files, checking finished books, and scanning or researching. Each row says what is happening now, shows real progress where it can be measured (files, MB or GB, audio time, or books), and counts the elapsed time, with an estimate of the time left once it is reliable.
- Conversion is shown as four steps, each with its own bar and step text: checking and copying the source files, normalizing the audio, encoding, and verifying and copying the audiobook to the library. Before, everything before encoding showed as "Checking source files" with a bar that never moved, sometimes for 20 minutes or more.
- Steps whose amount cannot be known show a moving bar instead of an empty one. Paused rows freeze and say "Paused"; a row that needs attention shows the reason. Pause and Resume now sit above the rows, so they never move.

### Fixed

- After Retry was accepted, the book could keep showing "Needs attention" with Retry still available, and a second press said "This book changed. Refresh and try again." The book now shows as queued at once, and a book list requested before Retry was answered can no longer bring back the old state.
- The message for a Retry pressed on an out-of-date view no longer names a Refresh action that does not exist. It now reads "This book's status changed. Check the updated status above."

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
