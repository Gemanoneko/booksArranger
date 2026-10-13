# Books Arranger v0.15.0 QA — 2026-10-13

Author: Futaba. Candidate: branch `codex/books-split-books-0.15.0`, exact commit `3346da12ccb512acd44bd120afea5af28b603da7` (3346da1). The worktree HEAD and the local remote-tracking ref `origin/codex/books-split-books-0.15.0` both read this hash (I made no network call, so "pushed" is read from that ref). Base: `2072cf1` (v0.14.0).

Offline only, as briefed: no app, no port 5210, no live database, no Z:/Y:, no network, no real-desktop or real-input check (no away window confirmed). Everything below ran from `git archive` exports of 3346da1 and 2072cf1 (never a clone, never the live worktree) and from my own copy of Ender's catalog copy (sha256 `b16c048a…7256301`, identical to his file and unchanged at the end; his file was never touched). I committed nothing, fixed nothing, stashed nothing. Environment: Windows 11, Python 3.14.8.

Note on the live worktree: when I started it was clean at 3346da1. By the end it showed uncommitted edits to `groups.py`, `local_identity.py`, `merge_service.py`, `public_research.py`, `source_identity.py`, `split_books.py`, `tests/test_split_books.py` and several docs (someone is working on it). **None of that is covered by this report.** This verdict is for the committed 3346da1 only.

**Summary: NO-GO for 3346da1, on one failing control, not on anything found in the real library.** Zero wrong groupings exist among the 173 real grouped books (independent scan plus hand review), the suite shows zero new failures, the headline numbers reproduce exactly (445 → 528), order, spelling and protection checks all pass. But a control I built from the brief's own "year-like numbers" hazard groups separate books into one candidate that then reaches *approvable* with no Internet: titles that carry a number ("Метро 2033" / "Метро 2034", "Fallout 3" / "Fallout 4", "Area 51" / "Area 52") filed under one album with track tags 1..N. Under the dispatch rule (any wrong grouping that could retire the wrong originals is a NO-GO) that decides it. The fix looks small (section 8) and the real library is not affected today.

## Result per check

| # | Check | Result |
|---|---|---|
| 1 | Full suite from `git archive` 3346da1 at a short path vs the 9-error baseline | PASS. Run 2: 587 tests, 9 errors, name-for-name identical to the baseline 9. Run 1 had one extra error, a file-lock flake that passes 3 of 3 isolated. 38 of 38 `test_split_books` tests pass |
| 2 | Own scan over all 173 grouped books (940 files) | PASS on the real library: 0 wrong groupings. 14 groups raised a hard flag, all judged correct by hand (named or Roman-numeral parts of one novel). The scan also fires on the synthetic wrong groups (36 of 40 caught, 4 known blind spots listed in 5.2) |
| 3 | 25 random groups by hand plus the 10 riskiest | PASS: 25 of 25 correct, 10 of 10 riskiest correct as one book each |
| 4 | Synthetic wrong-group controls | **FAIL on one family.** 52 scenarios: 44 as expected, 3 failed, 5 are probes of inherent limits. The named three (series of separate novels, two recordings of one book, missing part) all hold. Numbered-title / year-like names do not (F1) |
| 5 | Spelling: Pratchett, Dick, Zahn, no wrong merge | PASS. 7 Pratchett books to one spelling, all 7 Dick books one spelling, Zahn unchanged, all 24 spelling pairs the new rules can unify across the library (22 confirmed-spelling pairs, 2 middle-initial pairs) judged by hand: no two different people merged |
| 6 | The 81 approvable grouped books carry the right order | PASS. 81 books, 707 files: recorded positions equal my own reading of the numbers in every one (80 from track tags, 1 from file names) |

Also reproduced and checked (not separate briefed checks): 445 → 528 approvable exactly; 14 of 14 already approved/reviewed/job groups unchanged by the regroup; 0 regressions.

## 1. Full suite

`python -m unittest discover -s tests -p "test_*.py"` (timeout 600000), from `git archive` exports at `C:\Users\AnGeLZzZ\AppData\Local\Temp\fq\c` (candidate) and `...\fq\b` (2072cf1), 38-character paths (the long-path cause of the known errors is irrelevant at this depth).

| Run | Tests | Errors | Failure set |
|---|---|---|---|
| Baseline 2072cf1 | 549 | 9 | The known 9, identical name-for-name to Ender's recorded baseline |
| Candidate run 1 | 587 | 10 | The same 9 plus `test_partial_base_intent_absence_preserves_history_before_overall_completion` (`WinError 32`, file in use, in `DirectoryBoundary`). Passes 3 of 3 in isolation |
| **Candidate run 2** | **587** | **9** | **Identical name-for-name to the baseline 9. Zero new failures** |
| Focused `test_split_books.py` | 38 | 0 | OK (15.9 s) |

The 9: `test_sort_title` actual review export, `test_native_thread_check` baseline race, `test_standing_admission` x3 (changed frozen source review, classified io failure, publication or unclassified failure), `test_collection_identity` lookup fetches components, `test_merge_http` protected cover enrichment, `test_chapter_repair` stream copy full presentation, `test_catalog_paging` grouping reused.

## 2. Reproduction of the measurement (my own driver, not Ender's)

My `futaba_measure.py`: copy of the catalog copy, `groups.sync` of the code under test, then `PublicResearch.lookup` with every public source closed on every waiting/held candidate (and every new split book).

| | v0.14.0 | 3346da1 |
|---|---|---|
| Candidates checked | 2,416 | 1,649 (1,476 + 173 new split books) |
| Approvable without the Internet | **445** | **528** |
| Split books | 0 | 173 groups, 940 files; 81 approvable (707 files), 92 research path (233 files) |

Comparison by member path set, v0.14.0 against the candidate:
- 1,476 candidates unchanged in membership. **0** approvable in v0.14.0 that stopped being approvable.
- **2** newly approvable with the same members: `Фантастика 2021 (без муз. сопр.)` and `Олег Булдаков - Тёмные Аллеи в Кино` (both "Разные авторы").
- **9** approvable books whose author spelling changed, and no others: 7 Pratchett, 2 Dick.
- 940 v0.14.0 candidates were absorbed into the 173 split books. All 940 were "Book identity uncertain" in v0.14.0, so no approvable book was absorbed. No candidate with non-split changed membership exists.
- 14 protected groups (approved, reviewed or with an audio job): none overlaps the 940 files, and after the candidate's sync all 14 have the same revision, fingerprint and approved state.

Discrepancy with the handoff doc (F2, Minor, doc only): the doc says 935 files in 173 books and 228 files in the 92 research books. The data, including Ender's own `m-after-final.log` (`split_files: 940`) and mine, says **940 and 233** (707 + 233). The 1,299-file accounting line should read 1,304 or the 363 should read 358.

## 3. Independent scan over the 173 grouped books

Own script `futaba_scan.py`, importing nothing from the candidate. It reads the RAW ffprobe format and stream tags from the catalog (not the app's derived tags) and checks per group: every author-like tag (artist, album_artist, author, composer, narrator, reader, performer, copyright, publisher), album, series, language, genre and date tags; readers named in comments; audio profile (codec, rate, channels, profile) and bitrate spread; duplicates by size plus duration; missing durations; embedded track numbers (gaps, duplicates, start, declared totals); the number that varies in the file names (gaps, duplicates, start, year-like >= 1000, track-versus-name order); words that differ between parts beyond the shared name; volume and season markers; year-like numbers differing between parts; abridged / adaptation markers on some parts only; parts spread over folders; and files in the same folder that share the album but are not in the group. A separate script checks that, wherever a group has both track tags and varying file-name numbers, the two are equal per file.

Results over all 173:
- Mixed authors, artists, composers, narrators or recordings (profile, rate, channels, language): **0**.
- Numbering gaps, duplicates, wrong start, or declared totals not equal to the files found: **0**.
- Same-album files left outside a group (an incomplete group): **0**. Parts in several folders: **0**.
- Volume or season markers that differ between parts: **0**. Abridged / adaptation marker on some parts only: **0**. Duplicate files inside a group: **0**.
- Year-like numbers that vary between parts: 1 hit, `Оно` (parts titled "Июнь 1958 года" and "Июль 1958 года" are the novel's own part titles, tracks 1/7..7/7, total matches). Correct.
- Wherever a group has both track tags and varying name numbers (160 groups), the file-name number **equals** the track number for every file; 0 differ. 8 groups have no usable name numbers, 5 have no track tag (their order comes from file names).
- Hard flags: 14 groups, all because parts carry their own names: Roman-numeral parts ("Часть I/II": 4 Гиперион/Эндимион books and 5 Harry Potter books), "Вступление" in Точка обмана, Мерзость ("Альпинисты / Гора / Мерзость"), Красные цепи ("Ртуть / Свинец / Сера"), Волки Кальи (Todash / Рассказывая истории / Волки), Оно. In each case the files carry a "Часть N" marker, the tracks run 1..N with the declared total equal to N, and the parts are the named parts of one novel. Judged correct.
- Declared totals ("1/2") are absent in 11 groups (the four Dan Brown chapter sets of 108-155 files, Origin with 5, and six small ones). For those, a missing last part cannot be detected (inherent, 5.2).

## 4. Hand judgement

**25 random groups** (seed 13102026, indices into the 173-group list): 4, 22, 34, 36, 39, 40, 54, 55, 63, 68, 86, 88, 102, 109, 110, 111, 114, 117, 132, 155, 161, 162, 167, 168, 169. Each judged on file names, album, artist, composer/reader, track and total, durations. **25 of 25 are one book each:** Элементарно Ватсон, Аспект дьявола ("Черные холмы" Part 1/2), Harry Potter and the Goblet of Fire and Deathly Hallows (Часть I/II), Бог-император Дюны (1/3..3/3), Честь Королевы, Продажное королевство, Шестёрка воронов, Кости Авалона, Ученик монстролога, Ночная смена, Четыре сезона, Дьюма-Ки, Бессонница, Кристина, Кто нашёл берёт себе, Салимов удел, Чёрный дом (1/4..4/4), Сердце зимы (Wheel of Time 9), Splatterpunk stories 2 (an anthology in two files), Каменный город and Мастер снов (Сборник albums), Созвездие Льва 3 том 2 / 4 / 5. All have one album, one artist, one reader, one profile, and track n/N with N equal to the files found.

**10 riskiest I found**, each looked at in full:

| # | Group | Why risky | Judgement |
|---|---|---|---|
| 1 | Насекомые с Шаггаи, 5 mp3 (no tags, order from file names "Глава 1..5") | No tags at all | One short story in 5 chapters, 80 min, one folder named after it. Correct. Held for research (no author source) |
| 2 | Глубина 01/02 and Светлана 01/02 in the story-per-file collection folder `Ужасы и трэшатинка`, no tags | Separate works numbered like parts, in a folder tree of 49 other single stories | Each is one story in two files (20 + 27 min, 31 + 36 min); the 11 other stories in the same folder (and 38 more in `Сборник 2-4`) are separate files with their own names and stay single. Correct. Held for research |
| 3 | Лавка дурных снов 1-3 (King, no track tags, the only approvable group ordered by file names) | A collection of stories, order from names | Same album, title, artist, profile, bitrate 120 kbps; 26601 + 31523 + 26528 s; names 1,2,3 contiguous. Correct |
| 4 | Странная погода 1, 2 (Joe Hill, four novellas) | A collection | Same album, composer, comment; names 1,2; bitrate 60 kbps both. Correct. Held for research |
| 5 | Оно, 7 files (parts with sub-parts, "Июнь 1958 года 1/2") | Names carry duplicate part numbers, so track tags decide | Tracks 1/7..7/7, total 7, all parts of one novel. Correct and approvable, order checked in 6 |
| 6 | Волки Кальи, 4 files with named parts | Distinct part titles | "Часть 1 / 2 (1) / 2 (2) / 3", tracks 1/4..4/4. Correct. Held for research |
| 7 | Мерзость, 3 files "Часть N. Альпинисты / Гора / Мерзость" | Distinct part titles, approvable | Tracks 1/3..3/3, Часть 1,2,3. Correct |
| 8 | Метро 2033 / 2034 / 2035 (three groups in one folder) | Year-like numbers | Each has its own album ("Метро 2033", ...) and stays its own 2-file group; no cross-grouping. Correct |
| 9 | Иная and Иная 2001 (two groups in one folder, near-equal total length 55317 and 55319 s) | Two groups that could be one recording filed twice | Different albums, different artist spelling, each internally consistent; "Another" and "Another 2001" are two novels. Correct as two groups. See O1 |
| 10 | Dan Brown chapter sets (155, 135, 129, 108 files) | The biggest sets, 527 of the 940 files | One album each, tracks 1..N complete, name numbers equal tracks, profile identical. Correct. Approvable, order checked |

## 5. Controls

### 5.1 Method

Synthetic rows shaped like catalog `files` rows, run through the candidate's real `groups.build()` (in memory), so the integration code is exercised, not just `split_books.check`. Positive controls prove the harness can see a grouping. For the end-to-end shape, the same rows go through `groups.sync` on a disposable database and `PublicResearch.lookup` with every source closed ("E-series", author in folder and tags so a good book is approvable).

Positive and structural controls, all as expected: P1 two-part book grouped; P2 12 chapter files grouped; P3 CD1/CD2 one m4b per disc grouped; P3b two m4b tracks per disc grouped; P3c three mp3 per disc stays a legacy multi-file group (not a split book); H8a one book from chapter files; H8b two books with chapter files in one folder come out as two groups of three, never one; E1 genuine two-part book is approvable end to end.

Held as required (37 scenarios, all PASS):
- Series of separate novels in one folder numbered 1..N: "1. X / 2. Y / 3. Z" under one series album with tracks 1..3 (H1a); title tags naming each novel, no tracks (H1b); bare 1/2/3 with distinct title tags (H1c); "Хоббит / Властелин колец" under the author as album (H1d); the English form (H1e).
- Volumes and seasons: "Том 1/2" (H2a), "Книга 1/2" (H2b, and H2f under the author as album), "Season 1/2" (H2g).
- Year-like with no track tags (H2d, H2e) hold, because numbering does not start at 1.
- Two recordings of one book: readers differing in composer (H3a), only in file names with tracks continuing (H3b), differing sample rate (H3c), differing readers named in comments (H3d), duplicate track numbers across part folders (H3e), two recordings with tracks restarting (H12).
- Missing part: middle (H4a, d), first (H4b), last with declared totals (H4c), missing disc folder (H4e), declared disc total not met (H4f), duplicate position (H4g).
- Mixed authors under one album, mixed container, mixed channels, mixed language tag, mixed series tag (H5a-e); the same file twice (H6a); a part with its own title (H6b); full versus abridged named parts (H6c); tag order against name order (H7a); unreadable part (H7b); part without duration (H7c); a whole-book file beside numbered parts (H9); series number misused as a disc tag (H11).

### 5.2 Failures and probes

**Failed controls (3):**

| ID | Files | Result |
|---|---|---|
| H2c | `Метро 2033.m4b`, `Метро 2034.m4b`, album "Метро", tracks 1 and 2 | grouped into one split book |
| H2h | `Fallout 3.m4b`, `Fallout 4.m4b`, album "Fallout", tracks 1 and 2 | grouped |
| H2i | `Area 51.m4b`, `Area 52.m4b`, no album, title tags "Area 51/52", tracks 1 and 2 | grouped |

End to end, with the author in the folder and the tags (E-series): E2 (Метро 2033/2034 under album "Метро"), E5 ("Фантастика 2021" / "Фантастика 2022" under album "Фантастика", artist Сборник) and E9 (Fallout 3 / 4) all become **approvable without the Internet**, basis `local_agreement`: two separate books become one M4B titled "Метро" (or "Fallout", "Фантастика") and the originals of both are retired. See F1.

**Probes of inherent limits (reported, not asserted; none occurs in the real library):**
- X1 / E8: bare-numbered files `1.m4b, 2.m4b, 3.m4b` under one album that equals the folder name, tracks 1..3. Grouped, and approvable when the folder name agrees with the album (E8); held by identity when only the album names the book (E3). Indistinguishable from a three-part book by tags and names.
- X2 / E6: the missing LAST part with no declared totals (tracks 1, 2 of a three-part book). Grouped, approvable. A missing last part cannot be known without a total.
- X3 / E7: "полная версия" on part 1 and "сокращённая версия" on part 2, in comments only. Grouped, approvable; only reader names in comments are compared. Names carrying the marker (H6c) hold.
- X5: parts of 2 h and 40 h at 64 and 192 kbps. Grouped; no duration or bitrate sanity check.
- X4: a reader named in the comment of one part only: held.

**Blind spots of my own scan** (known, none hits the real library): it does not hard-flag a differing `language` tag (soft only), a series number used as a disc tag, an unreadable part (the scan input carries no error flag), and bare names with distinct title tags (soft only). The 173 real groups carry no `language` tag, two have `disc 1/1` on every part, none has an error.

## 6. Spelling

Source of confirmed spellings (read from my copy of the catalog): 12 spellings with a fetched source URL (Van Vogt, Anatole France, Sanderson, Dan Brown, Hardinge, Rollins, Gaiman, Shimada Masahiko, Pratchett, Tremblay, Парфёнов, Обухова). I enumerated every library author spelling (837) against them with the candidate's own predicates to list what each confirmed spelling can absorb, then judged each pair myself:

- 22 absorbed spellings, all the same person: Sanderson (Sanderson Brandon, Брендон Сандерсон, Сандерсон Брендон), Dan Brown (Дэн Браун), Hardinge (ФРЭНСИС ХАРДИНГ, Фрэнсис Хардинг), Rollins (Rollins James, Джеймс Роллинс, Роллинс Джеймс), Gaiman (Gaiman Neil, **"Neil Gayman" by the one-letter slip rule**, Гейман Нил, Нил Гейман), **Pratchett ("Terry Pratchet", 20 books, by the slip rule; Пратчетт Терри; Терри Пратчетт)**, Парфёнов (four е/ё and initials variants), Van Vogt (case), Обухова (Лена Обухова). The slip rule produced exactly two pairs in the whole library, both genuine typos of the same person.
- Middle-initial rule: exactly two pairs library-wide, both the same person (Philip K. Dick ~ Дик Филип Киндред; Robert E. Howard ~ Роберт Ирвин Говард).
- **Pratchett**: 7 approvable books `Pratchet Terry` → `Pratchett Terry`, no other Pratchett book changes. The co-authored credit "Neil Gaiman & Terry Pratchett" is left alone (correct). 114 other Pratchett-path candidates remain "Book identity uncertain" and are untouched.
- **Dick**: v0.14.0 approvable Dick authors were `Dick Philip K.` (5) and `Дик Филип Киндред` (2); the candidate gives `Dick Philip K.` for all 7. One folder.
- **Zahn**: `Zahn Thimoty` x3 before and after. No confirmed spelling exists, so unchanged as briefed. (The library holds "Thimoty Zahn" 2, "Timothy Zahn" 1, "Тимоти Зан" 1.)
- No catalog-adopted spelling merged two different people. The `Булдаков` ruling fires on one book only (Тёмные Аллеи в Кино, "Разные авторы").

## 7. Order of the 81 approvable grouped books

For each of the 81 approvable split books (707 files) I took the order the candidate will use (the row's member order and recorded disc/track) and compared it with my own reading of the raw numbers: embedded track tag when every part has one (80 books), else the varying number in the file name (1 book, Лавка дурных снов). In all 81 the recorded track equals my number for every file, the numbers run 1..N with no gap or duplicate, the order is ascending, and the member list is already in that order. No multi-disc book is among the 81. The largest: The Lost Symbol 155 chapters 1..155, Точка обмана 135, Digital Fortress 129, Inferno 108, Оно 7 (tracks 1/7..7/7; its file names repeat part numbers, so the tags decide, which is right).

Limit of this check: I verified the order in the candidate row, which is what `build_manifest` consumes through `track_order`. Whether the packaged conversion preserves it was only exercised by Ender's real-ffmpeg two-part test, not by me (NOT RUN, no app and no real conversion allowed).

## 8. Findings

**F1 — Major (release-gating under the dispatch rule). Titles that carry a number are grouped into one book when tracks run 1..N under one album.**
- Repro: three files or two, same `album` (or no album and title tags "Area 51"/"Area 52"), embedded `track` 1, 2 (or 1..N), file names "`<Title> <n>`" where `<n>` is part of each title ("Метро 2033" / "Метро 2034", "Fallout 3" / "Fallout 4", "Area 51" / "Area 52"). Run `groups.build`: one `split_book` candidate. With the author in the folder and tags, `PublicResearch.lookup` returns it approvable (E2, E5, E9). Approval would convert both books into one M4B and retire both sets of originals.
- Cause (read-only reasoning, confirmed by the failing controls): `split_books.check` accepts any one-to-four-digit number after the shared name as a part number (`LEADING_NUMBER` `\d{1,4}`), then compares only the ORDER of the embedded track numbers and the file-name numbers, never their values. Tracks 1,2 and names 2033,2034 (or 3,4, or 51,52) agree in order, so the group passes. The year-like guard Ender added lives only in the local-identity sibling check, not here, which is why the doc's "Year numbers" claim holds for identity but not for grouping.
- Real library exposure today: none. All 160 testable real groups have file-name number equal to track number; none has a varying year-like number; none of the 173 is a numbered-title series.
- Likelihood: needs a shared album tag over separate novels with numbered titles. The library's convention (one album per book) makes it rare, but the app's automatic run approves "approvable" books without a human, and the retirement is the destructive step (24-hour recovery only).
- Suggested direction for Ender (not mine to fix): require the file-name number to equal the embedded track number per file when both exist (160 of 160 real groups satisfy that, so nothing real is lost), and read a 4-digit year-like number in a part name as a separate work (hold) rather than a part number; add the three held cases (H2c, H2h, H2i) as tests. Re-check with this control set; it re-runs in seconds.

**F2 — Minor (doc).** The handoff and sample docs say 935 grouped files and 228 research-path files; the measurement is 940 and 233 (section 2).

**Observations (no action required for this build; each has a disposition):**
- O1: `Иная` and `Иная 2001`, `Метро 2033/2034/2035`, `DDD / DDD 2` sit in one folder as separate correct groups. The near-equal total length of `Иная` (55317 s) and `Иная 2001` (55319 s) with the same reader suggests a possible duplicate recording; the duplicate gate, not grouping, decides. Disposition: accept.
- O2: the inherent limits X1, X2, X3, X5 (section 5.2): a missing last part without a declared total, an abridgement noted only in comments, bare-numbered files, absurd length or bitrate differences cannot be detected from tags. None occurs in the 173 real groups. Disposition: accept for this build; the 24-hour recovery and the research path are the backstops.

## 9. Not run

- NOT RUN: whether M4B parts carry their own chapters (the pipeline and admission hold those). The catalog probe stores no chapter list (`chapters` is absent for all 940 files), so this cannot be measured offline. Covered only by Ender's real-ffmpeg tests.
- NOT RUN: a real conversion of a split book, retirement and recovery on real files (no app, no Z:/Y:).
- NOT RUN: any real-desktop or real-input check (no away window confirmed), the packaged build, Sergei's Restart + Start sequence.
- NOT RUN: manifest-level order for three or more parts in a real conversion (section 7 limit).

## 10. Pattern alerts

Pattern alert 1: the full suite shows one more `WinError 32` "file in use" error in a different test on each full run (seen in the v0.14.0 report and in Ender's own candidate run 1, and now `test_partial_base_intent_absence_preserves_history_before_overall_completion` here), always passing in isolation and on rerun. It is test-teardown locking, not a product defect. Disposition: defer (does not gate release; Ender can look at teardown locking when convenient).

## Method record

Scripts and raw outputs are in the session scratchpad `futaba-0150` (not in git): `futaba_scan.py` (independent scan), `futaba_measure.py` and `diff_measure.py` (reproduction), `controls.py` and `e2e_controls.py` (synthetic controls, in-memory and through sync plus lookup), `scan_control.py` (positive control of my scan: 36 of 40 forced-wrong groups caught), `order_check.py`, `spelling_pairs.py`, `spelling_pairs2.py`, `protected_check.py`, `compact.py` and the suite logs. My catalog copy (hash re-checked equal before removal) and the database scratch were removed through the studio hygiene planner (about 377 MB each, both complete). The two `git archive` exports (`Temp/fq/c` and `Temp/fq/b` under `C:/Users/AnGeLZzZ/AppData/Local`, 50 MB) are still on disk: they contain a `.claude` folder, which the planner refuses by name, so they need an owner's decision.

Round 1 verdict (superseded by Round 2 below): NO-GO at 3346da1 — control failure F1 (numbered-title books grouped and approvable); zero wrong groupings found in the real library.


## Round 2 — b756301

Candidate: branch `codex/books-split-books-0.15.0`, exact commit `b756301cf8364f0a307a9547b104c52255833dca` (b756301), parent 3346da1. The worktree HEAD and the local remote-tracking ref `origin/codex/books-split-books-0.15.0` both read this hash (no network call; "pushed" is read from that ref). Same rules as round 1: offline, from a `git archive` export at the short path `C:/Users/AnGeLZzZ/AppData/Local/Temp/fq/r2`, my own fresh copy of Ender's catalog copy (sha256 `b16c048a…7256301`, unchanged at the end), no app, no port 5210, no live database, no Z:/Y:, no network, no real-desktop or real-input check. I committed nothing, fixed nothing, stashed nothing. The round-1 report was committed inside b756301 as it stood; this section and the superseded-verdict wording are my only changes.

**Summary: GO for b756301.** F1 is fixed and my controls prove it: the three failing controls (Метро 2033/2034, Fallout 3/4, Area 51/52) and the Фантастика 2021/2022 end-to-end case are now held. The suite shows zero new failures. The 173 grouped books are the same 173 with the same order, 0 wrong. The new separate-part books behave as ruled, including on REAL chaptered M4B fixtures I built and drove through scan, research, approval, media, publication and retirement. No wrong grouping that could retire the wrong originals exists in this build. Open points are observations, listed in R2.7, none gating.

### R2.1 Result per item

| # | Item | Result |
|---|---|---|
| 1 | Suite | PASS. 604 tests, 9 errors, name-for-name identical to the baseline 9 (baseline 2072cf1: 549 tests, 9 errors). Zero new failures. The single full run showed no flake, so no rerun was needed. `test_split_books.py` alone: 55 tests OK |
| 2 | My control set | PASS. 57 scenarios now (the 52 plus 5 new for Senua's fixes): **52 as expected, 5 probes of inherent limits (unchanged), 0 failed**. Same set on 3346da1: 6 FAIL (H2c, H2h, H2i, H13, H14, H15), so the controls are seen to fail where the defects were |
| 3 | Independent scan, all groups plus the new part books | PASS. 173 groups, 940 files, 0 wrong. The new separate-part rows are judged in R2.4 |
| 4 | Imajica: 4 books under `Barker Clive` | PASS (R2.5) |
| 5 | Fixtures with REAL chapters | PASS: 5 scenarios behave as required; 2 measured scenarios behave as designed (R2.6) |

### R2.2 Controls

All of round 1's HOLD controls still hold, and the three that failed now pass:

| Control | Round 1 (3346da1) | Round 2 (b756301) |
|---|---|---|
| H2c "Метро 2033" / "Метро 2034", album "Метро", tracks 1,2 | grouped | held |
| H2h "Fallout 3" / "Fallout 4", album "Fallout", tracks 1,2 | grouped | held |
| H2i "Area 51" / "Area 52", no album, tracks 1,2 | grouped | held |
| E2 / E5 / E9 end to end (Метро pair, "Фантастика 2021" / "2022" under album "Фантастика", Fallout pair) | approvable as one book | each file its own candidate, held "Book identity uncertain"; nothing joined |
| E4 titles "Метро 2033" / "2034", no album, tracks 1,2 | one candidate | two separate candidates, each approvable alone (correct: they are two books) |

New controls for Senua's fixes, all held or grouped as intended on b756301: H13 albums differing only in brackets "Игры (Книга 1)" / "(Книга 2)" (M1) held; H14 a title on one part only "Книга 2 Ловля огня" under a shared album (C1) held; H15 "CD 1 Волчья кровь" / "CD 2 Дорога домой" (M2) held; H16 three parts each with its own title tag under one album held; H17 zero-padded parts "Дорога 0001" / "0002" (M6) still grouped. The positive controls P1-P3c, the legacy CD case and H8b (two books in one folder come out as two groups) still behave. The five probes are unchanged: X1 and E8 (bare-numbered files whose album equals the folder name) still group and E8 is approvable; X2 (missing last part, no total), X3 and E7 (abridgement only in a comment), X5 (absurd length or bitrate difference) still group. These are the inherent limits of round 1 (O2); none occurs in the real library.

### R2.3 Reproduction and scan

My own driver, v0.14.0 against b756301, by member path set:
- 2,416 candidates in v0.14.0 → 1,649 now. Approvable **445 → 539** = 445 + 81 split books + 2 singles (Фантастика 2021, Тёмные Аллеи в Кино) + 11 part books. Ender's count of 539 and 173 grouped reproduces exactly.
- **0** books approvable in v0.14.0 that are not approvable now. All 940 files of the split books were "Book identity uncertain" in v0.14.0, so no approvable book was absorbed.
- 173 split books, 940 files, 81 approvable (707 files), 92 on the research path (233 files). **The member sets of all 173 groups and the order of every member list are identical to round 1**, so nothing was split away from a book that stays whole in the real library (the catalog stores no chapters, so none can be, offline).
- My scan reproduces round 1: 14 hard flags, all the same named or Roman-numeral parts of one novel; track tag equals file-name number in all 160 testable groups; 0 gaps or duplicates, 0 mixed authors, readers or recordings; 0 same-album files left outside a group. Order of the 81 approvable books re-checked against my own reading of the raw numbers: 81 of 81 correct.
- The 14 already approved, reviewed or job-bound groups: unchanged after the regroup (same revision, same approved state).

### R2.4 The new separate-part books (84 candidates)

A single M4B whose same-album numbered siblings form a coherent set is now a "part book": its own title, series and number from evidence, admitted only when the file really has more than one chapter (checked at conversion). Offline: **84** such candidates, **11 approvable, 73 held**.

| Set | Candidates | Outcome | Judgement |
|---|---|---|---|
| Имаджика, 4 parts, total 4 | 4 | approvable | R2.5 |
| Зелёная миля, 6 parts, total 6 | 6 | approvable | Six named serial parts, tracks 1/6..6/6, one reader, title tag = file name for each ("Две убитых девочки", "Мышь на миле", ...), series "Зелёная миля" numbers 1..6. Consistent with Sergei's ruling |
| Hunger Games "Book 2 Cathing Fire", set of 3 | 1 | approvable | A complete 11.7 h novel, not a part: title "Cathing Fire" comes from its tag (typo kept), no series. Books 1 and 3 have no title tag and stay held. See O4 |
| Дюна, Впусти меня, SAO Stories, Торадора x10, Элрик x13, Дом Зверя, Голос ночной птицы, Нужные вещи, Тёмный экзорцист, Однажды, Ночной смотрящий, Мастер собак, Тобол, Нарния x6, Рассказы на ладони x5 | 73 | held (Book identity uncertain, Playback order uncertain, Sources disagree, Source membership uncertain) | Correctly not approved: no title of its own, or sources disagree |

Judged by hand: none of the 11 approvable is a wrong grouping, because none groups anything: each is one file, becomes one book, and keeps its chapters (R2.6 A). The only consequence of a wrong call here would be a part filed as a book of its own, which is exactly what the ruling prescribes.

### R2.5 Imajica rows

Four rows under `Barker Clive` (the same spelling as Barker's other books), set total 4 met, tracks 1/4..4/4 equal the file-name numbers 1..4, one reader (Светлана Смелова), one album "Имаджика", all four approvable:

| # | File | Title (own) | Series | Number |
|---|---|---|---|---|
| 1 | `1. Пятый Доминион. Главы 1-20.m4b` | Пятый Доминион. Главы 1-20 | Имаджика | 1 |
| 2 | `2. Пятый Доминион. Главы 21-36.m4b` | Пятый Доминион. Главы 21-36 | Имаджика | 2 |
| 3 | `3. Примирение. Главы 37-48.m4b` | Примирение. Главы 37-48 | Имаджика | 3 |
| 4 | `4. Примирение. Главы 49-62.m4b` | Примирение. Главы 49-62 | Имаджика | 4 |

The titles are the parts' own names including the "Главы N-M" range. That is what the evidence rules produce; whether "Главы 1-20" belongs in a book title is Sergei's call, not a defect. Whether the real four files carry chapters is unknown offline; without chapters they are held, with chapters each converts alone.

### R2.6 Fixtures with REAL chapters

Real M4B files made with ffmpeg (tones, real `[CHAPTER]` marks written with ffmetadata), in `C:/Users/AnGeLZzZ/AppData/Local/Temp/fq/fx`, driven through the real `Inventory` scan, grouping, offline `PublicResearch.lookup`, `MergeService.approve_automatic`, the media pipeline, publication and retirement. Library code only, no web server, no port, no network.

| ID | Fixture | Result |
|---|---|---|
| A | Imajica-like: 4 parts, each with 3 real chapters, each with its own title | PASS. 4 rows, none joined, all 4 approvable; 4 jobs completed, one source each, media mode `copy`, 3 preserved chapters each; every output re-probed with 3 chapters; outputs `Имаджика - N - <part title> - Barker Clive.m4b`; the 4 originals retired |
| B | Whole book, 3 parts WITHOUT chapters (must stay whole) | PASS. One split book, approved, one job with 3 sources, one M4B, 3 chapters ("Роман 1..3"), originals retired |
| C | Same 3 parts, only part 2 has real chapters, no own titles | PASS as designed, measured: the joined attempt is refused ("Book parts carry their own chapters; each part becomes its own book"), 0 jobs, files intact; after the regroup 3 single rows (part 2 as "Part with its own chapters"), all held "Book identity uncertain". Nothing converted, nothing lost; see O3 |
| D | 4 chapter files, ONE chapter each | PASS. Still joined: 1 job, 4 sources, 4 chapters |
| D2 | 4 chapter files, TWO chapters each | PASS as designed, measured: refused, 0 jobs, files intact, the set dissolves into 4 held singles; see O3 |
| E | One complete single-file book with 5 chapters beside an unrelated file | PASS. Not a part book; approved; `copy` mode; 5 chapters kept |
| F | A part-book candidate (own title, set total met) WITHOUT chapters | PASS. Research approves it, admission refuses "One part of a multi-part set without its own chapters", 0 jobs, files intact |

### R2.7 Spelling, order, other

- Confirmed spellings fell from 12 to 6 (only verified records now confirm; Senua M5): Sanderson, Rollins, Gaiman, Shimada, Tremblay, Обухова. The slip rule now needs the confirming record to have seen the local spelling. 11 absorbed spellings library-wide, all the same person (Sanderson 3, Rollins 3, Gaiman 4 including the one-letter slip "Neil Gayman", Обухова 1).
- **Pratchett reverts**: the 7 approvable Pratchett books are `Pratchet Terry` again, as in v0.14.0 (no confirmation by a verified record exists). The co-authored credit is untouched. This is the intended M5 effect, not a defect; it means the typo folder `Pratchet` stays until a verified record confirms the right one.
- Dick: all 7 approvable books `Dick Philip K.`, one folder. Zahn: `Zahn Thimoty` x3 unchanged. Middle-initial rule: exactly two pairs library-wide, Dick and Howard, both the same person; the new "initial written first" guard does not touch them.
- Order and protected groups: see R2.3.

**Observations (none gating):**
- O3: a chaptered part dissolves its whole set into held singles (fixtures C and D2). That follows from the ruling, and nothing is converted wrongly or lost, but a book with ONE chaptered half, or chapter-per-file sets whose files each carry two embedded chapters, will no longer be auto-joined and stays held. How many real sets are affected is unknown, because the catalog stores no chapters. Disposition: accept for this build; proposed follow-up for Jane and Sergei: a read-only `ffprobe -show_chapters` count over the 940 split files and the 84 part-book files in a window Sergei states, which turns this unknown into a number.
- O4: "Book 2 Cathing Fire" is a complete novel that now passes as a part book; if it has no chapters the refusal text ("One part of a multi-part set... one part is not the whole book") is misleading, though safe. Minor, wording only.
- O5 (carried from round 1, unchanged): inherent limits X1-X5 and E8. Disposition: accept.

**NOT RUN:** the real files' chapters, real conversions on the real library, retirement on real files, real-desktop and real-input checks, the packaged build, Sergei's Restart + Start sequence. The fixtures above are real files but not the library.

**Pattern alerts:** none new. Round 1's alert (file-lock flake in the suite) stays at disposition defer; it did not show in this round's single full run.

**Round 2 method record:** new or updated scripts in the scratchpad `futaba-0150`: `controls.py` (57 scenarios), `e2e_controls.py`, `fixtures_chapters.py` (real-chapter fixtures A-F), `futaba_measure.py` (now also captures part books), `imajica_rows.py`, `spelling_pairs.py` (adapted to the verified-only structure), plus the round-1 scripts unchanged. My copy of the catalog and the fixture folder are disposable and are removed through the hygiene planner at the end; the export directories under `Temp/fq` stay until an owner decides (they hold a `.claude` folder the planner refuses).

Round 2 verdict (superseded by Round 3 below): GO at b756301 — F1 fixed, zero new suite failures, 0 wrong groupings, real-chapter fixtures behave as ruled.


## Round 3 — d3c5526

Delta check of `d3c55261cf64e8b8040ecc4cb86d551f51bdddfa` (d3c5526), one commit on top of b756301. The worktree HEAD and the local remote-tracking ref `origin/codex/books-split-books-0.15.0` both read this hash (no network call). Same rules: offline, from a `git archive` export at the short path `C:/Users/AnGeLZzZ/AppData/Local/Temp/fq/r3`, my own fresh copy of Ender's catalog copy (sha256 `b16c048a…7256301`), no app, no port 5210, no live database, no Z:/Y:, no network, no real-desktop or real-input check, nothing committed, fixed or stashed. The disk was at 100% (under 1 GB free) during this round, so I ran my large steps one at a time; no step failed for lack of space and the suite log has no disk-full error.

**Summary: GO for d3c5526.** The suite shows zero new failures, all 57 controls hold, the 173 grouped books are unchanged, and the new rule works on real chaptered files: a chaptered part is published only when every part of a complete named set has real chapters, otherwise nothing from the set is published. The Оно-like 7-part set either publishes all 7 as "Оно - N - …" or none.

### R3.1 Result per item

| # | Item | Result |
|---|---|---|
| 1 | Suite | PASS. 610 tests, 9 errors, name-for-name identical to the baseline 9 (zero new, zero baseline-only). `test_split_books.py` alone: 61 tests OK |
| 2 | 57 controls plus chapter fixtures | PASS. Controls: 52 as expected, 5 inherent-limit probes (unchanged), 0 failed. The end-to-end cases Метро 2033/2034, Фантастика 2021/2022 and Fallout 3/4 are still held as separate candidates. Fixtures A-F pass again and the 6 new ones below pass |
| 3 | One chaptered part only: whole set held | PASS (fixtures G and I) |
| 4 | Оно-like 7-part set: all 7 as "Оно - N - …" or held, never partial | PASS (fixtures H and I) |
| 5 | .m4a group | PASS (fixtures K1, K2, L) |
| 6 | Scan re-run | PASS. 173 groups, 0 wrong; member lists and order identical to rounds 1 and 2 |

### R3.2 Measurement and scan

My own driver, v0.14.0 against d3c5526:
- Approvable **445 → 538** = 445 + 81 split books + 2 singles + **10** part books (Imajica 4, Зелёная миля 6). Ender's 538 reproduces. **"Cathing Fire" is now held** ("Book identity uncertain"); Hunger Games Books 1 and 3 stay held. 84 part-book candidates in all, 10 approvable, 74 held.
- 0 books approvable in v0.14.0 that stopped being approvable; the 940 split files were all held in v0.14.0, so no approvable book was absorbed.
- 173 split books, 940 files, 81 approvable (707 files), 92 on the research path (233 files). The **ordered member lists of all 173 groups are identical to round 1**. My scan: the same 14 hard flags (named or Roman-numeral parts of one novel), file-name number equals track number in all 160 testable groups, 0 gaps or duplicates, 0 mixed authors, readers or recordings. Order of the 81 approvable books: 81 of 81 correct.
- The 14 already approved, reviewed or job-bound groups are unchanged after the regroup.
- The indexed regroup builds its neighbour index only when a reviewed split book exists; the catalog holds none, so I could not exercise it on real data (covered by Ender's tests, all passing). I make no claim about its speed: my two comparable measurements (b756301 and d3c5526) both took 41.5 s end to end, as expected for a path that is not taken here.

### R3.3 Fixtures with REAL chapters (new ones)

Real M4B or M4A files with real `[CHAPTER]` marks, driven through scan, grouping, offline research, `approve_automatic`, media, publication and retirement, as in round 2.

| ID | Fixture | Result |
|---|---|---|
| G | Imajica-like, 4 parts with own titles, folder repeats the set; ONLY part 2 has chapters | PASS. 0 approved, 0 jobs, 4 files intact. Part 2 is refused with "Another part of this set has no chapters of its own; the whole set is held (never published piecemeal)", the other three with "One part of a multi-part set without its own chapters" |
| H | Оно-like: 7 parts (Часть 1..5 with the two sub-parts of 2 and 4), tracks 1/7..7/7, album "Оно", every part with 2 real chapters | PASS. First a joined 7-part set, refused ("each part becomes its own book"); after the regroup 7 rows; **all 7 approved**, 7 jobs, `copy` mode, each output re-probed with its 2 chapters, 7 originals retired. Names: `Оно - 1 - ТЕНЬ ПРОШЛОГО - King Stephen.m4b`, `Оно - 2 - ИЮНЬ 1958 ГОДА. 1 - …`, `Оно - 3 - ИЮНЬ 1958 ГОДА. 2 - …`, `Оно - 4 - ВЗРОСЛЫЕ - …`, `Оно - 5 - ИЮЛЬ 1958 ГОДА. 1 - …`, `Оно - 6 - ИЮЛЬ 1958 ГОДА. 2 - …`, `Оно - 7 - РИТУАЛ ЧУДЬ - …` |
| I | Same 7 parts, part 4 has NO chapters (6 of 7 chaptered) | PASS. **0 approved, 0 jobs, all 7 files intact.** Every chaptered part is refused with "Another part of this set has no chapters of its own; the whole set is held (never published piecemeal)", part 4 with "without its own chapters". No partial set |
| K1 | .m4a group of 3 (same album, tracks 1..3), part 2 with real chapters | PASS. One group of 3 before and after; refused with "joining them would drop those chapters"; 0 jobs; files intact. The group is not broken up |
| K2 | .m4a group of 3 without chapters | PASS. Joins normally: 1 job, 3 sources, 3 chapters |
| L | .m4a set of 3 with own titles and real chapters on every part | PASS. Not a part book, 1 group of 3, 0 jobs, files intact, refused with "joining them would drop those chapters". An .m4a is never filed as its own book and never re-encoded |

Fixtures A-F (round 2) repeat unchanged: A still turns 4 chaptered Imajica-like parts into 4 separate M4Bs in `copy` mode with 3 chapters each; B and D still join chapterless sets into one M4B; C and D2 still dissolve a set with a chaptered part into held singles (nothing converted); E and F as before.

### R3.4 Findings and observations

No new finding. Carried, unchanged: O3 (a chaptered part leaves its whole set held; now also when only SOME parts of a complete named set have chapters, which is exactly the intent and is safe: nothing from the set is published), O5 (inherent limits). O4 is closed: "Cathing Fire" is held. The number of real sets affected by the chapter rules is still unknown because the catalog stores no chapters; the read-only `ffprobe -show_chapters` survey I proposed in round 2 still turns that into a number.

**NOT RUN:** the real files' chapters, real conversions on the real library, real-desktop and real-input checks, the packaged build, Sergei's Restart + Start sequence.

**Pattern alerts:** none new. Round 1's alert stays at disposition defer; no flake showed in this round's single full run. New environment note for Jane, not a pattern alert: the machine's C: drive was at 100% (under 1 GB free) during this round.

**Round 3 method record:** `fixtures_chapters.py` now has fixtures A-L, `controls.py` and `e2e_controls.py` unchanged; my catalog copy and the fixture folder are disposable and removed through the hygiene planner at the end.

**Verdict:** GO — Books Arranger v0.15.0 candidate round 3, exact commit d3c55261cf64e8b8040ecc4cb86d551f51bdddfa (d3c5526): zero new suite failures, 57 controls hold, 173 groups unchanged, chaptered parts publish only as a complete set.
