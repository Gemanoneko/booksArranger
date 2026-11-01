# Books Arranger 0.24.1: missing series previews and Tolkien chapter refusal — 2026-11-01

Status: diagnosis only, Ender; no implementation, build, app operation or release. Proposed additions to 0.24.2 require Sergei's scope approval. All timestamps are UTC. Source HEAD c0aa24f, installed version 0.24.1. Existing running app and queued approvals were not touched. Sergei later supplied a screenshot showing both Tolkien approvals cancelled.

## Evidence boundary

Used the retained ordinary byte copy of the catalog captured 2026-11-01 06:40:33.304–06:40:35.422, opened mode=ro with query_only=ON. No new live copy or live SQLite connection was made. Main file 814,809,088 bytes, SHA-256 7f695a22c4bff5e16bbc2fc849ca13ee1e123d11acb9e8fada59f000366d0222; WAL 4,911,072 bytes, SHA-256 95c63ebb7f14fc12d47dc4b84f10b479047f2d8011963b69b2481fd4c59ee6c1; SHM 32,768 bytes, SHA-256 20b2f405d5a9aef67cab26623d81565941c5568838c9525ff1e62083a2d981f9. Per-file copies matched their immediately read sources and quick_check was ok. Ordinary main/WAL/SHM copying is not an atomic snapshot; this is a readable morning observation, not proof of the later approval state.

Screenshots inspected, supplied in the host Temp folder:
- codex-clipboard-39838c64-29f0-4776-a1ec-fe566e4bd76b.png — McCammon.
- codex-clipboard-99820ea3-fb28-48d9-ba40-99993f013263.png — Tolkien, both approvals queued.
- codex-clipboard-1428ac3a-6b16-48a4-9edf-2a60ea05eb8c.png — both Tolkien approvals cancelled with the chapter-boundary error.

The initial pass used only catalog metadata and source. Sergei then explicitly approved read-only chapter timing inspection of the four Tolkien M4Bs; those four container probes are recorded below. No audio decode, app endpoints/control/debugger/snapshot, source writes or live-data writes occurred. No final output for these approvals was inspected. The earlier pause incident recovered by itself after about five hours according to Sergei; its proposed thread snapshot was never executed and is no longer needed.

## 1. Matthew Corbett: folder recognition rejects a character-named series

Sergei confirms these books belong to Matthew Corbett and provides https://www.goodreads.com/series/49541-matthew-corbett (parent inspected: Speaks the Nightbird #1; The Queen of Bedlam #2). Source paths in the catalog explicitly contain Robert R. McCammon / МЭТЬЮ КОРБЕТТ / 1. Голос ночной птицы and 2. Королева Бедлама.

The rejection is concrete: local_identity.py:2047–2062 recognizes Author / Series / Numbered book, but returns None whenever the second folder looks like a person. looks_like_person (:1726–1742) treats a known given name as sufficient, and Мэтью is in GIVEN_NAMES. A bounded pure-function probe using only the two copied rows returned author_is_person=true, series_is_person=true and folder_structure=null for both. No database, network or audio operation was used by that probe. Without that structure, local_identity.py:2717–2724 does not promote the folder's series and book position; the source files' dedicated series/number tags are empty. The retained folder text is only a local clue. This is a missed legitimate eponymous series, not a missing folder clue.

Nightbird current group 6ffd83a7-8a23-4d24-acad-9a113c69b1ba, revision 1, approved=0, has four M4Bs, track tags 1/4–4/4, and part_set m4b-parts-v2. Its Held result at 2026-10-29 02:23:23 has title Голос ночной птицы, blank series/number, unresolved original_title/series gaps, and part_set decision ask, basis book_words. Internal «Книга первая/вторая» are the two internal sections across four files; they are not Matthew Corbett positions 1 and 2. The grouping question is separate from the series omission.

Queen's current first-part group b78033bc-7a04-42d1-8a26-c0d2a3cea723 has one file; three sibling groups hold the other parts. Its older four-file group ec74b990-8f80-41e2-a8f4-502bc7803aaf was superseded after a volumes decision, basis “each file names its own work.” Four part_volumes receipts dated 2026-10-29 02:23:26.369835 carry that basis, with kept=false in current evidence: this was an automatic heuristic, not a recorded Keep as separate books answer. The section titles are Маскер, Безумие, Послание and Методы убийства. part_sets.py:166,191–195 treats distinct reduced titles as separate works unless its caution conditions apply. This needs a narrowly bounded regression for this edition; the evidence does not authorize generic folder merging.

“Still checking which other files belong to this book” is emitted when sibling groups exist or coverage is incomplete (merge_service.py:2535–2555; web/app.js:3206–3211). It does not prove a check is actively running. The morning first-part group has no automatic result; the later screenshot already says The Queen of Bedlam. Its later research outcome cannot be reconstructed from this old copy.

## 2. Tolkien: successful research is lost from the preview/approval path

This is a different failure from McCammon. In the morning copy the successful work and cycle facts already exist:

| Group | Research saved | Original title | Cycle / position |
| --- | --- | --- | --- |
| 832c9d26-c332-44b1-a583-29e9ce622e21 | 2026-10-31 14:03:27.222294 | The Return of the King | Властелин колец / 3 |
| a65f1061-4eb3-4655-b63e-fef2aa6acf52 | 2026-10-31 14:03:33.661567 | The Two Towers | Властелин колец / 2 |

Both are revision 1, approved=0, Held for part_set decision ask / basis book_words. Their saved work aliases bind the exact Russian edition titles to the English originals. metadata_facts says original language en verified, original title found, series_state verified, and original_title/series gaps fully filled. Return work is fantlab:1669; Towers work is fantlab:1668; their cycle source is https://fantlab.ru/work1693. Receipts identify API URLs https://api.fantlab.ru/work/1669/extended and /1668/extended, SHA-256 3798d9cf0020e168c82d53c5b616125f409f5b3bb2175b79c2a5af94b7ade74e and 41ca7f77157b462db8cad60d7f5b38bb8459d17d9eab35f0a6170a7c6cfc4172. Cycle /1693/extended receipt SHA-256 cf0d7ece973c30c5c2d68148efbfbbcefa5ddf93b573048ffc12507d6aec3452. All three responses were retrieved at about 14:03 on October 31.

None of those three API cache rows remains in the morning copy. Its public_research_cache holds 1,279 responses, 61,925,396 encoded bytes; the oldest remaining fetched time is October 31 16:04:17.987, later than the Tolkien responses. public_research.py:58–59,329–345 imposes 5,000 entries / 64 MiB and evicts oldest responses down to 90%. Capacity eviction fits this observed cutoff; no eviction event receipt proves the exact deletion cause. Seven-day expiry alone does not explain yesterday's missing rows.

The source explains why loss of an expendable HTTP response can erase an already-known result from these rows. ask_payload calls approval_preview, which calls _approval_result (merge_service.py:2418,2743–2777,2845–2858). _approval_result calls research.approved; that rebuilds local identity, then _english_original and _local_lookup using a zero-request cache budget (public_research.py:635–666,675–695). It does not reuse the successful persisted automatic result. A missing response raises ResearchWait in the cache-only client (:403–411), and the gap-fill path falls back to local values. Thus the original Russian title and blank cycle can be shown again even while the successful verified result remains in automatic_candidates.

This is not an intentionally provisional pre-research destination: approval_preview explicitly promises the path Approve uses, and _approve_once calls the same _approval_result (merge_service.py:3533). The screenshot agrees with this failure mechanism. The exact later runtime cache/reconstruction was not observed, so do not claim an instrumented reproduction of that particular request. No incorrect final filing is established; the subsequent screenshots show both approvals cancelled before admission.

The source folders here are an English author folder followed by a Russian author alias; rejecting the second folder as a series is appropriate. Raw tags already carry grouping=Властелин колец, but dedicated series/number fields are blank. Do not promote disc or internal book numbers without identity evidence: Return's disc 3/3 agrees with trilogy position 3, while its files are internal Books 5 and 6; Towers' disc 2/3 agrees with trilogy position 2, while its files are Books 3 and 4. The saved public-work binding already provides the correct distinction.

Universe is a separate omission. No universe is present in these saved results. The local path detects an explicit «Вселенная …» folder (local_identity.py:2017–2032), and this public gap-fill route asks original_title/series/author_full, not a parent universe (public_research.py:1594–1635). A saved user universe or local universe is passed through (:1547–1549), but successful LOTR series research does not itself populate Middle-earth. Sergei has now confirmed that relationship. Preserve ruling 30 Universe > Series > Book and ruling 72b exact cycle spelling «Властелин колец». His “Middlearth” wording is relationship confirmation, not a newly chosen exact UI spelling.

## 3. Tolkien chapter refusal: three last-chapter endpoints exceed audio by hours or days

The new screenshot says “Approve cancelled: existing M4B chapters overlap or exceed complete source audio. Nothing was changed.” It identifies a protective chapter-boundary validation failure, not proof that the audiobook is corrupt or incomplete.

audio_pipeline.py:694–705 parses ffprobe chapter start/end seconds and rejects if any value is non-finite, start < 0, end <= start, start < previous end - 0.05 seconds, or end > supplied duration + 0.25 seconds. This single message combines all five conditions and omits file, chapter, numbers and which predicate failed. The recording check calls it with the catalog member duration (merge_service.py:4414–4424) before accepting the conversion. Other admission/chapter-planning uses retain the same preservation safeguard. A refusal establishes that approval was not accepted for conversion; source review may still have refreshed cover/cache metadata, so the message should not be interpreted as proof of zero incidental catalog/cache activity.

The copied probes contain streams and format, but no chapter list. There are no part_chapters rows for these four paths (that table stores counts, not timing boundaries, in any event). Stored audio/format durations are:

| Exact filename, under its pictured Tolkien book folder | Duration, seconds |
| --- | ---: |
| 3-01 Возвращение государя. Книга пятая.m4b | 28352.563084 |
| 3-02 Возвращение государя. Книга шестая.m4b | 30618.389478 |
| 2-01 Две твердыни. Книга третья.m4b | 37928.843900 |
| 2-02 Две твердыни. Книга четвёртая.m4b | 27709.416780 |

All four stored audio streams start at +0.047891 seconds (time base 1/44100); chapter-data streams start at 0.048 seconds (time base 1/1000). This small offset alone does not establish a false refusal: it is below the 250 ms duration tolerance. At that initial stage, the catalog alone could not distinguish invalid spans, a terminal out-of-duration timestamp, stale duration or a guard defect. The subsequently approved read below resolves the failing predicate. No chapter stripping, tolerance widening, source rewrite or forced join was performed.

### Approved timing inspection: completed 11:31:56–11:32:19 UTC

Sergei approved “Yes, inspect those four files read-only.” Exactly four sequential installed-ffprobe processes read the exact paths already listed in the copied catalog, one invocation per file. All exited successfully with empty stderr in 0.19–0.42 seconds; none reached the 60-second owned-process deadline. There was no decode, playback, conversion, packet/frame dump, source write, app operation or further probe. Before/after source size and mtime were unchanged; sizes and reported durations agree with the morning catalog. This is not a content hash or proof of decoded audio.

The installed build is n8.1.3-9-g29e619e767 (BtbN 2026-09-30); ffprobe.exe SHA-256 fe818a56825e31f39791216977c729ccf1223051e3abfb13acbf8ea16e0e94bd. The probe returned 47 chapter entries. Their starts and ends use time_base 1/1000. All chapter starts are nonnegative and inside their file's current duration, all spans are positive, and all earlier chapter ends equal the following start. There are no overlap failures. Three final endpoints alone fail end > duration + 0.25 seconds:

| Source file | Final chapter ID / title | Start (s) | Reported end (s) | Current audio/format duration (s) | Excess (s) |
| --- | --- | ---: | ---: | ---: | ---: |
| 3-01 Возвращение государя. Книга пятая.m4b | 9 / Глава X. Ворота отворяются | 26315.624 | 1919501.372 | 28352.563084 | 1891148.808916 |
| 3-02 Возвращение государя. Книга шестая.m4b | 15 / Одна из последних записей красной книги | 30476.121 | 551938.285 | 30618.389478 | 521319.895522 |
| 2-01 Две твердыни. Книга третья.m4b | 10 / Глава XI. Палантир | 35483.272 | 37928.892 | 37928.843900 | 0.048100 — passes |
| 2-02 Две твердыни. Книга четвёртая.m4b | 9 / Глава X. Выбор Сэммиума Скромби | 24718.054 | 134744.072 | 27709.416780 | 107034.655220 |

The failing excesses are roughly 21.89 days, 6.03 days and 29.73 hours, respectively. This rules out a tiny rounding adjustment or the 48 ms start offset as an explanation of these three refusals. Towers part 1 demonstrates that the existing 250 ms end tolerance already accepts the small offset. The current format/audio durations exactly match the catalog durations supplied to the guard, so stale duration does not explain this observed failure.

**Conclusion:** the app correctly refuses the three invalid final endpoints that its installed ffprobe reports. This establishes a chapter-timing inconsistency, not damaged or missing audio. This read does not distinguish malformed on-disk chapter data from a demuxer interpretation defect, and it does not prove decoded sample duration or full audio integrity. No repair was performed. The generic error combines distinct cases and should identify the file, chapter, reported endpoint, duration and failed condition.

**Bounded remedy proposal:** support correction of only an impossible final-chapter endpoint after the complete audio endpoint has been independently proven by the existing full-audio/preservation path. Require every earlier boundary to be sane and ordered, final start strictly inside the proven duration, and no missing or ambiguous chapter. Preserve all chapter titles, starts and order and the source audio bytes; do not rewrite the originals in place, trim audio, drop chapters or widen the general tolerance. Any prepared copy/output must pass the existing whole-M4B preservation checks before it can be used. The existing join planner already derives final ends from full part duration (audio_pipeline.py:722–735), but the source chapter gate rejects earlier; that observation does not authorize bypassing it. Implement a narrowly evidenced repair case only after 0.24.2 scope approval, with input-versus-parser attribution still treated as an uncertainty where relevant.

The exact raw values, process receipts and all 47 chapter entries are retained in BooksArranger_DiagnosisEvidence_2026-11-01.json. Four raw probe envelopes were condensed into that artifact; incidental container tags are omitted there. It also retains SHA-256 pins of the raw probe stdout. No further source read is needed to establish which predicate failed.

## Proposed 0.24.2 scope addition — for approval

1. Preserve successful original-title/cycle/position evidence for the current revision/fingerprint through grouping holds and the shared preview/Approve path; HTTP cache eviction must not silently downgrade it. Revalidate source binding, user overrides, rules/policy changes and number-conflict safeguards; no blind reuse of stale research. Test the exact Tolkien aliases, eviction, current versus stale fingerprints, user-entered names and internal books versus trilogy positions. Preview and approval must agree.
2. Correct the eponymous-series folder veto using bounded structural and identity evidence. Cover the confirmed Matthew Corbett folder and ordinal 1/2 while preserving rejection of a second author alias, numbered book folders, container/disc folders and unrelated sibling books. Do not simply remove the person check or merge arbitrary folders.
3. Review Queen's named internal sections being classified as independent works; retain user choice and whole-M4B chapter-preservation requirements. Any grouping-rule adjustment is limited by evidence from this exact edition and regression cases. Correct “Still checking” copy/state if no active check exists; Judy owns visible behavior/copy.
4. Carry the user-confirmed Middle-earth > Властелин колец > book relationship through the established universe naming rules. This is a separate mapping/research requirement, not solved by preserving already-found series facts. No unapproved generic universe-inference feature or exact spelling is added.
5. Add actionable file/chapter/timing diagnostics and a narrowly validated final-endpoint repair path for the three demonstrated cases, subject to the full-audio proof and preservation conditions above. Preserve source bytes and chapter titles/starts/order; do not treat huge terminal endpoints as normal tolerance or drop chapters. The read-only diagnosis is complete; implementation and repair are not approved.

These are proposed additions, not scope approval or permission to build. Existing paused-cleanup/ruling-78/backlog dispositions remain in BooksArranger_PausedCleanup_Diagnosis_2026-11-01.md. No production tests, QA installs, version bump, commit or push has occurred.

## Retained evidence and hygiene

Named scratch: C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-pause/shared/. The compact durable evidence bundle BooksArranger_DiagnosisEvidence_2026-11-01.json retains the needed catalog rows, source pins, comparison/delta, grouping evidence and chapter timings. The obsolete thread-snapshot/debug helpers and one-use pure folder probe were removed (2,976 bytes). The remaining catalog copy and superseded scratch extracts were removed after validating the durable bundle: 22 files / 820,153,473 bytes, including 819,752,928 catalog bytes. The named shared directory is empty. No supplied screenshots, live data, root dirty work or unrelated scratch are removed.
