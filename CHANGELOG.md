# Changelog

## [v0.15.0] - 2026-10-13

### Added

- Split books: files that provably form one book become one candidate whose ordered parts become one M4B, one chapter per part (for example the 155 chapter files of one Dan Brown novel, "Чужак 1.m4b" / "Чужак 2.m4b", CD1/CD2 folders). Grouped only when every part has the same book title (album), the same author, reader and recording tags, the same audio format, and gap-free numbering with no duplicates (embedded track numbers, part numbers in the file names, or disc folders). Gaps, duplicates, mixed readers or recordings, volume numbers ("Том 3", "Книга 2") and parts with their own story or book titles hold the files as before.
- One author, one folder: a spelling confirmed by fetched catalog evidence anywhere in the library wins over a more common local typo ("Pratchet" becomes "Pratchett Terry" for every book). Without a confirmation the most common local spelling is kept.

### Changed

- M4B parts are joined by the existing v4 normalizer: decoded and re-encoded once at the parts' own bitrate, sample rate and channels. Joining AAC by stream copy is not supported (each part carries its own encoder delay), so it is not attempted. A part that already has its own chapters is held, so no chapter marks are lost; parts whose audio profiles differ at conversion are held.
- "Philip K. Dick" and "Дик Филип Киндред" are one person: a middle initial may stand for a middle name when the first name and surname are written in full on both sides and the library has no other middle name for that person. An initial still never stands for a first name.
- Under a collection folder, a plain credit of Олег Булдаков (named in Sergei's ruling 1 and credited as a reader in the library) is the narrator: such books are filed under Сборники as before for his comment-credited collections.
- A trailing four-digit number is part of a title, not a part number ("Метро 2033" beside "Метро 2034" is not a split part).
- A running automatic pass adds candidates created by the new grouping instead of waiting for a new discovery pass. Every waiting or held book gets one fresh pass. Media verification, publication, source retirement and 24-hour recovery are unchanged.

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
