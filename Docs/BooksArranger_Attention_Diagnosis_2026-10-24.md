# Books Arranger: attention diagnosis, 2026-10-24 (v0.21.1 live)

Ender, read-only diagnosis of the live app (pid 25864, started 2026-10-23 20:40 UTC). Times are UTC; Sergei's local time is UTC+3.

## How this was measured

- **Catalog.** The live catalog `data/inventory.sqlite3` was opened with `file:…?mode=ro` plus `PRAGMA query_only=ON`. Nothing was written to it. One consistent copy, made with the SQLite backup API from the read-only connection, was used for one timing (group rebuild) in session scratch.
- **Library.** Z: was only listed, stat-ed and read. Iron Inferno's MP3 was copied from the NAS recycle bin into session scratch and examined there. The app's own bundled `ffmpeg.exe` and its `mp3_tag_repair.plan()` were used.
- **Process.** CPU and I/O were read from Win32_Process counters. Stacks were sampled 150 times at 1 s intervals with Python 3.14's stdlib `_remote_debugging.RemoteUnwinder`, which reads process memory only, injects no code and pauses nothing.
- **App.** Nothing was pressed, stopped or restarted.

## Verdicts

| Item | Verdict | Evidence |
| --- | --- | --- |
| A. Iron Inferno | The MP3 is **not damaged mid-stream**. It did not convert because its file **was deleted from the library on 23 Oct 07:29 UTC (10:29 local), outside the app**. | See A below. |
| B. Max Frei 01 and 04 | Both M4Bs carry one box shape the preservation proof has never admitted: **a 4-byte all-zero box type with an all-zero payload inside `moov/udta`** (70,903 B and 100,381 B). The in-place path declines it ("fallback: Unsupported structural box"), and so does the copy flow. | See B below. |
| C. Read errors · 1 | `Z:\Audiobooks\Сборники\Новая плоть (2016)\03 - Павлов Михаил - Засор.m4b`, 0 bytes, "moov atom not found" since 9 Oct. The file is **no longer on disk**, but the counter still counts it. | See C below. |
| D. Сказка | **Converted and verified.** | Child job `dc45a792` was admitted 20:50:25 and verified 21:02:21 as `Z:\Audiobooks Sorted\King Stephen\Сказка - King Stephen.m4b`. Its source cleanup completed 21:04:48 (original removed). Its recovery copy is gone, and the interrupted attempt's 2.4 GB leftovers are gone from disk (only a 9 KB `ownership.json` and an empty folder remain). |
| E. Automatic processing | **It is working, but slowly.** Each approved book costs about 10–12 minutes, and during that time the status poll and the book list are blocked. Approved books convert on their own. | See E below. Two bugs found and fixed. |

## A. Iron Inferno

**The file is sound.** The recycled copy's SHA-256 is `e2deceb3…7047ed`, the exact reviewed bytes.
- With its trailing 128 bytes, strict decoding reproduces Sergei's error exactly ("Header missing … -1094995529"), but only after all audio has been decoded: 384,763,392 PCM bytes, which is 96,190,848 frames (36:21.2).
- With the trailing 128 bytes removed, the same decode returns rc 0 and identical PCM.
- `mp3_tag_repair.plan()` accepts the file: 83,499 frames, one terminal ID3v1 tag removed.

So the 0.21.1 repair is the right remedy.

**Why it did not run:**
1. **The file was deleted.** At 07:29:08–07:29:10 on 23 Oct, nine folders under `Z:\Audiobooks\Unsorted` were deleted within 2 seconds and went to `Z:\@Recycle\Audiobooks\Unsorted\…`.
   - Eight of them held only leftover covers or `info.txt`.
   - The ninth was `WH40K\…Бойся Чужого [Casper Valter]`, which held Iron's MP3 plus `Cover.jpg`.
   - The app has no record of touching it. `cleanup_members` lists only the nine other tracks of that anthology, removed on 19 Oct. `source_folder_cleanup_directories` shows the folder as `retained_nonempty` every time. Around 07:29 the app's own activity was on other books.
   - Of everything in that recycle path, Iron's MP3 is the only audio file the app did not remove itself.
2. **The Retry was refused.** It was requested at 20:28:11 and refused at 20:47:29 with "Source changed — review required; Review the exact source files and playback order". The opener hit FileNotFoundError, and the admission records any OSError as `source_changed`.
3. **The catalog does not know the file is gone.** It was last scanned 22 Oct 17:09 (`files.missing=0`, seen=6), and no discovery pass has run since.
4. **Start over did not help.** It was pressed at 21:14:12, re-researched the book and **held it for 24 h** with "An inspected destination ancestor is unavailable". That is the source-folder boundary failing on the missing folder.

The refusal was correct; only its wording misleads. The wording is copy for Judy, not a code fix.

## B. Max Frei 01 and 04

Box walk of the sources, read-only:

```
moov/udta: [00 00 00 00] size 70903 (payload: all zero), then meta size 70906 (hdlr, ilst, free)   # 01 Дебют в Ехо
moov/udta: [00 00 00 00] size 100381 (payload: all zero), then meta size 100384                   # 04 Путешествие в Кеттари
```

- **What the box is.** It is zero padding, about the size of the `meta` box, which looks like a tagger blanking an old `meta` in place. It carries no data.
- **Other books with this refusal.** All 15 other jobs refused with "Unsupported structural box" are superseded. Their sources are gone and the books were converted by later work.
- **Why this needs a decision.** The preservation profile admits only exact writer shapes, and the brief records that new shapes are Sergei's decision ("Four exact M4B shapes are accepted (Sergei, 2026-10-19) … Revisit when another writer shape shows up"). So this is a question, not a fix.
- **If yes,** the change is narrow: inside `moov/udta` only, treat a box whose type and payload are all zero bytes as padding. Drop it from the new `moov`, list it in `metadata_dropped`, and leave every other shape refused.

## C. Read errors · 1

- The file was read twice on 9 Oct (generations 3 and 4); both failed with "moov atom not found" on a 0-byte file. It is gone from the folder now (`missing=1`). The other eight stories of that collection are present.
- `scanner.source_status()` counts `files WHERE error<>''`, which includes missing records, and the Files "Read errors" filter shows it too.
- Nothing can resolve this error, because there is no file left to re-read.
- Counting it, or not, is visible behaviour, so it goes back as a question.

## D. Сказка

| Step | Record |
| --- | --- |
| Confirm and convert | `m4b_readmissions` seq 276 for parent `8a8a23d1`, requested 20:43:25, admitted 20:47:29 |
| Child job | `dc45a792`: created 20:50:25, completed 21:02:21 |
| Verified output | `verified_outputs`: `z:\audiobooks sorted\king stephen\сказка - king stephen.m4b`, sha256 `82e0d7bf…09c8`, file present on Z: |
| Source cleanup | `source_cleanup 9ff3530b` completed 21:04:48; member `Z:\Audiobooks\Stephen King\Сказка.m4b` state removed; the recovery copy folder is gone |
| Storage and folder cleanup | Both completed, 21:05:01 and 21:05:03 |
| Old attempt's working files | Gone from disk (the folder is empty except `ownership.json`, 9 KB). The old `working_files` rows still read `creation_intended`; this is cosmetic and recorded only |

Observation, not acted on: the output is titled `Сказка`. The naming rule gives Russian translations their English canonical title, which here would be Fairy Tale. The book went through Confirm and convert on its embedded tags.

## E. Is automatic processing working?

**Throughput, measured.**
- **Methods.** Four DB samples were taken 2 min apart (21:25–21:31) plus spot checks to 21:52. History timestamps from `automatic_candidates.result.research_history` were matched against `audio_jobs.created`.
- **Ordinary research:** about 3 min per book. Public hosts are paced at about 6 s per request, and `public_research_requests` shows wikidata, ru.wikipedia and fantlab interleaved.
- **Approvals:** about 10–12 min each. Approvals measured on 23 Oct took 4.4–8.5 min before the queue insert and 3.2–7.0 min after it.
  - Book 08a6c713 (Макс Фрай 07): research started 21:21:46, enqueued 21:29:04, converter started 21:34:54, Queued 21:36:22, converted 21:42:24.
- **Approved books convert on their own:** job `e273b56f` started by itself 6 min after its approval.
- **Backlog:** 1,297 "Waiting for source", all due now. 1,151 of them say "Book identity uncertain" and 45 are gap deferrals. There are also 148 held.
  - At about 3 min each, this sweep (pending 1,445) needs roughly 3 days, and most of those books will probably stay uncertain.

**Why each approval stalls, and why the screen looks frozen.** Stack samples, 150 at 1 s, 21:49:31–21:52:01:
- **The worker.** It spent 121 of 150 s in `MergeService.progress_books()`, called from `CandidateReviewService.enrich()` inside `approve_automatic`.
  - `progress_books()` recomputes the whole catalog's converted set every time: every job, cleanup and publication record, a `PublicationBindings.lookup` per converted book, and one NAS `stat` per converted book.
  - One approval enriches its book about seven times (`save`, `_write` ×3, `tracks`, `build_manifest`, post-queue), all while holding `group_lock`.
- **The UI.** The status poll (`progress_books` in `SharedSnapshot`) and the book-list page (`Inventory.candidates`) were blocked acquiring `group_lock` in 136 of 150 samples. That is why the counters stop moving ("0 researching") during an approval.
- **Load.** The backend read about 100–550 MB/s (small 4 KB reads, which is SQLite pages) at 0.1–1.5 cores.
- **"0 researching" while a book is being approved.** The approval's `save` and `tracks` bump the book's revision. The status count joins `automatic_candidates` on the current revision, so the book in progress drops out of the count.
  - Live, 22:04: `b0c127a0` reads Researching at revision 1 while its group is at revision 4. The count read 0, and its job `e56951fd` was queued at 22:06:02.
  - Not changed; this is display semantics.

**Final samples (22:00:44, 22:02:45, 22:04:46).**
- A different book was researching at 22:00 and at 22:02.
- Saved pending went from 1,437 to 1,436, and 5 books were recorded in the last 15 min.
- Over the session (21:21 to 22:04), 3 books converted by themselves (488 → 490 completed jobs here, 487 → 489 verified outputs) and a 4th was queued.

**The earlier "can't start, something needs attention".**
- `automatic_errors` 7f3ca0c0 (20:30:53) is a `StartRefused` raised from `merge_service._capture_start_generation` via `AutomaticProcessing._work` line 531. Its redacted message hash matches "Books is closing; saved retry requests are retained.".
- A Start raced Quit: the worker's first queue resume was refused because the app was closing, and the worker recorded that as a failure. The run then read Needs attention, "Automatic pass could not continue", until Sergei pressed Start.

**Unexplained.** Under 0.21.0, nothing ran from 17:39 (job d3947c0d queued) to the 0.21.1 start. The DB alone cannot tell an app that was quit for the install from one that was stuck.

## Fixes (committed on `main` in `WIP/Books Arranger`, not pushed)

1. **One converted set per automatic approval** (`585cbb3`).
   - Change: `review_backend.ready_snapshot()` gives `approve_automatic` one converted set; the first `enrich()` computes it and the rest reuse it. The book-list page keeps its own set, and nothing changes outside an approval.
   - Test: `tests/test_automatic_media.py::test_one_approval_reads_the_converted_set_once`.
   - Control: on the unfixed code the same test counts 7 recomputations per approval.
2. **A Start racing Quit pauses instead of failing** (`656f402`).
   - Change: in `_work`, a `StartRefused` of kind `closing`/`stale` from the queue resume (or any refusal once stop is set) becomes the pause path. Other refusals are still recorded failures.
   - Tests: `tests/test_automatic_processing.py::test_quit_racing_a_start_pauses_the_run_without_a_failure` and `::test_other_queue_start_refusal_is_still_a_recorded_failure`.
   - Control: on the unfixed code the run reads Needs attention.

**Other tests run** (single modules via `unittest discover -p`, not the gate):
- Passed: `test_automatic_processing` (65), `test_automatic_media` (10), `test_automatic_record_retry`, `test_iron_skazka`, `test_refused_retry`, `test_start_over`, `test_quiet_status`, `test_status_read_contention`, `test_inplace_m4b`, `test_split_books`, `test_working_lifecycle`, `test_merge_service`.
- Failed identically on the unchanged code (7ecfeca, in a throwaway worktree), so they predate this work: `test_local_admission` (1 failure, an unexpected DuckDuckGo URL), `test_standing_admission` (3 errors, the fixture folder `scratch/source-fallback-2026-10-11` is missing outside the gate) and `test_catalog_paging` (1 error).
- The full gate was not run here, because it copies the live `data/`.

**Not changed**, needing product or UX calls: B (new writer shape), C (read-error count), Iron wording ("Source changed", "destination ancestor"), and re-research cadence for uncertain books.

**Not measured:** the remaining ~4 min of an approval's pre-queue time (hashing, probes, covers, recording review), and the status poll's own `progress_books` cost when its cache is invalidated by every commit.
