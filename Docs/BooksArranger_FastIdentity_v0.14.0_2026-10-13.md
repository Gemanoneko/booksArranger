# Books Arranger v0.14.0 candidate — fast identity handoff (Futaba / Senua)

Ender, 2026-10-13. Worktree `scratch/fast-identity-2026-10-13/worktree`, branch `codex/books-fast-identity-0.14.0`. Sully committed the first candidate as `67e3d43` (it already includes Jane's standing-rule section, `e68597a`); the review fixes below are uncommitted edits on top of it. Rule implemented: Sergei decision "local evidence is enough when it agrees" (2026-10-12), last section of `Docs/BooksArranger_StandingRules_2026-10-11.md`.

## Round 4 fix (on top of 82bc67d) — Senua round 3

| Finding | Fix | Test |
| --- | --- | --- |
| R3-1 Critical: an author who reads his own book was filed under `Сборники` as "Разные авторы" | A collection filing now requires a collection-folder signal, and a book whose folder or parent folder names its reader is held for research | `Round3Critical.test_r3_1_self_reading_author_is_held_not_routed` (`tests/test_local_identity_fixes.py`) |

**Round 4 results (fresh copy, sha256 `06fa82d7…` unchanged):** 455 approvable (389 author books + 66 under `Сборники`), the same approvable set, reviews and 66 collection filings as 82bc67d. Positive control: the round-3 probe routes on 82bc67d and is held now. Scans unchanged: routed with a person credit 0, reader or collection authors 0, conflicting initials 0, cross-script false pairs 0.

## Round 3 fixes (on top of a7d9b42) — Senua round 2

| Finding | Fix | Test (`tests/test_local_identity_fixes.py`) |
| --- | --- | --- |
| R2-1 Critical: the Сборники route dropped a real author | The route fires only when no person credit remains in the tags after reader and collection credits are set aside, and only this book's own reader credits count as a signal; "credited as a reader on other books" stays a research hold | `Round2Criticals.test_r2_1_route_never_drops_a_person` (King + one "Сборник" tag; Глуховский self-reader; King + "читает Князев" under Сборники) |
| R2-2 Critical: conflicting initials agreed and merged | Initials written on both sides pair one to one, letter for letter; an initial left beside an unmatched first name is a mismatch. The canonical-spelling merge counts only spellings that are the same person without reading an initial as a full first name | `Round2Criticals.test_r2_2_conflicting_initials_stay_distinct` (Стругацкий А./Б., Толстой А.Н./Л.Н., J./K. Sawyer, Иванов А. with two Ивановs) |
| Major M1: lone numbered part read only from the tag | The part check also reads the file name and folder | `MajorFixes.test_m_lone_numbered_part_or_chapter_is_held` (live tags of `5. Игры Немезиды 1.m4b`) |
| Major: sibling check open on a root-string mismatch | `folder_siblings` fails closed unless the range query finds the candidate's own files | `C3SiblingGuard.test_c3_root_string_mismatch_fails_closed` |
| Futaba round 2 N1: an identical artist/album_artist credit with an initial or -ович read as two people | The same words (initials and patronymics included, any order) are one credit; different initials still never merge | `FutabaRound2.test_n1_identical_duplicate_credit_is_one_person` |
| Futaba round 2 residual: a lone chapter file with no catalogued sibling | A single file whose own name or title tag says only "Глава 5" / "Часть 3" / a bare number other than 1 is held; a lone "01" stays allowed (one-file rips) | `FutabaRound2.test_residual_lone_chapter_file_is_held` |
| Futaba round 2: majority-typo spellings ("Pratchet Terry", "Zahn Thimoty") | **Not changed — known limit.** Preferring a catalog-confirmed spelling per book would file one author's books under two folders (books researched online vs not); the safe fix is a persisted library-wide confirmed-spelling list, which needs its own design. Ruling 3 is applied as written | — |

**Round 3 results (offline, fresh copy of the evidence catalog, sha256 `06fa82d7…` unchanged after the run):** **455 approvable** = 389 author books + 66 collections under `Сборники` (445 in a7d9b42). Changes against a7d9b42: +9 Robert J. Sawyer books, +1 "Максим Кабир, Парфенов М.С." and +2 Кабир books (identical credits with initials or a patronymic in artist and album_artist were read as two people: Futaba N1 and F9); −1 `5. Игры Немезиды 1.m4b` (part, now held); −1 Булдаков "Тёмные Аллеи в Кино" (the credit is a person who reads other books: research hold, no longer routed). Identical-credit "two people" holds remaining: 0. The lone-chapter rule changed no approval (none in the copy).

Scans of all 455 approvals: routed with a person credit remaining 0 (66 routed); narrator equal to the credit 0; reader marker in an author 0; collection credit as an author 0; author credited as a reader anywhere in the library 0; a person accepted under a collection folder 0. Initials: 0 catalog spelling pairs with the same names but conflicting initials (837 spellings), 0 approvals whose canonical spelling changes or expands the agreed author's initials. Cross-script: Futaba's 39 pairs — 30 still match, all the same person; fresh population run — 32 unlinked matches, all the same person. Spelling variants: 3 people / 16 books, all one side adding a full middle name the other gives as an initial or omits ("Dick Philip K." / "Дик Филип Киндред"), which is now deliberately not merged.

## Review-fix pass (2026-10-13, on top of 67e3d43) — read this first

Uncommitted edits on top of `67e3d43` in the same worktree, answering `Docs/BooksArranger_QAReport_v0.14.0_2026-10-13.md` (Futaba NO-GO) and `Docs/BooksArranger_CodeReview_v0.14.0_2026-10-13.md` (Senua BLOCKED), plus Sergei's four rulings of 2026-10-13 (last section of `Docs/BooksArranger_StandingRules_2026-10-11.md`, appended by Jane in this worktree). The agreement record is now `local-agree-v3`. Measured on a fresh copy of the evidence catalog copy (sha256 `06fa82d7…`, identical to Futaba's).

| Finding | Fix | Test (file `tests/test_local_identity_fixes.py` unless noted) |
| --- | --- | --- |
| Senua C1 / Futaba F1-F2: reader or compiler taken as author | Credits or path names with a reader marker (читает, чит., исп., исполняет, озвучил, чтец, read by, narrated by, narrator, reader) are recording credits; a credit equal to a reader named in tags or after a marker is set aside; a collection credit (Сборник, Разные авторы, Various …) is a conflict with no fall-through; anything under a collection folder (Сборники, Антология, Anthology …) or with a collection title (Сборник, Коллекция, Рассказы, stories …) goes to research; an author whose exact name is credited as a reader on other books in the library (catalog-wide, cached per catalog revision) is held | `test_c1_reader_credit_never_author_live_antologiya_rows`, `test_c1_collection_credit_never_falls_through_golovin`, `test_c1_reader_named_in_comment_is_held_buldakov`, `test_c1_collection_folder_and_title_held_knyazev`, `test_c1_author_who_reads_other_books_is_held_volkov` |
| Senua C2 / Futaba F6: -ович/-евич/-ич surnames dropped | A patronymic is dropped only from a 3+ word name that keeps 2+ other words; two credits merge only on a full match (`same_person`); an initial pairs with a word starting with the same sound ("Гжендович Я." = "Ярослав Гжендович") | `test_c2_ich_surnames_stay_distinct`, `test_c2_patronymic_dropped_only_from_three_word_names`, `test_c2_credits_merge_only_on_full_match`, `test_c2_initial_pairs_with_given_name` |
| Senua C3: split-part guard fails open | `folder_siblings(database,row,root)` lists exact direct children through the `(root,path)` primary-key range, no LIMIT; a disc or part folder (CD1, "(часть 1)") also sees its sibling disc/part folders; more than 20 folders, no root, no catalog or any read error fails closed (held) | `test_c3_root_level_siblings_exact_without_cap` (2,500 nested + 44 root files), `test_c3_disc_and_part_folders_see_each_other`, `test_c3_fails_closed` |
| Senua M2 / Futaba F3: cross-script matches ignore vowels | Two words in different scripts match only when their consonants match in order and every vowel sound is one standard Russian transcription allows for that English spelling (table in `VOWEL_TABLE`); variants are generated deterministically (sorted, capped) | `CrossScriptNeedsVowels.test_cross_script_requires_vowels`, `test_futaba_controls_hawking_king_and_wild_cards_are_held` |
| Futaba F4 / H1: series name accepted as title | A file or folder name supports a title only as the whole name, its title part or the last real segment ("Траун. Союзники" → "Союзники"); structured-name contradictions now always hold | `MajorFixes.test_m_series_name_is_not_the_title_traun` |
| Senua M1: lone numbered part or chapter | A title ending in a part marker or a short trailing number ("Глава 01", "01") is held; years ("… 2022") and hyphen numbers ("Гелий-3") stay titles. **Correction (round 3):** in a7d9b42 the live `5. Игры Немезиды 1.m4b` was NOT held — its tag says "Игры Немезиды" and only the file name carries the " 1". The part check now also reads the file name and the folder (trailing number or part marker whose removal leaves the title), so it is held | `test_m_lone_numbered_part_or_chapter_is_held` |
| Futaba H14: a bare first name supports a full name | Surname-only support is allowed, a first name alone is not (`GIVEN_NAMES`) | `test_m_bare_first_name_does_not_support_full_author` |
| Futaba F7: invisible characters and stray quotes in titles | `clean_title` removes format characters (U+200E) and unbalanced quotes | `test_m_title_cleaned_of_invisible_and_stray_quotes` |
| Futaba F9: "Robert J. Sawyer" false holds | The source gate uses the agreement's name rules for local identity | `test_m_middle_initial_author_passes_source_gate` |
| Senua M3: cache eviction under the write lock | Side table `public_research_cache_index(url,fetched,size)` plus an index on `public_research_cache(fetched)`; expiry is an index range delete; eviction counts the small table and runs in one batch down to 90% only when over the bound | `M3CacheEviction.test_m3_eviction_uses_the_small_index_and_keeps_newest` |
| Senua M4: research tests ran with the rule off | `AutoTests` and `FallbackTests` now run with the production default; their fixtures name the author only in the tags (file named by title), so the default rule sends them to research and every hold assertion runs under the default. An agreeing fixture is accepted locally with the tag author | `M4DefaultRuleCoverage.*`; all 68 legacy cases pass under the default (the two known timing flakes aside) |
| Senua minors | `merge_service` turns any folder/catalog read error into a per-book hold; NFC normalisation; deterministic variants; CHANGELOG pacing wording | — |

### Sergei's rulings (2026-10-13)

| Ruling | Implementation | Test (`SergeiRulings20261013`) |
| --- | --- | --- |
| 1. Collections compiled or read by a narrator go to `Сборники`; the narrator is only the narrator | When no real author agrees and the credit is a collection credit or a reader, and at least two independent signals agree (collection folder, collection title, collection credit tag, the credited person is the reader), the book is admitted as a collection: `anthology`, author credit `Разные авторы` (the tag's own credit or the collection label), narrator(s) recorded only as narrator, `metadata_facts.collection.kind = narrator_collection`. One signal only stays research. Admission re-derives it (`revalidate`), `validate_policy` refuses a narrator as the credit | `test_r1_narrator_collection_filed_under_collections_root`, `test_r1_unclear_collection_stays_research` |
| 2. Tag and file name spell the title differently: the tag wins | A spelling slip (same digits and script, 1 letter in titles of 6–14 letters, 2 from 15) agrees; the tag spelling is used and the slip is recorded. Different volume numbers and short titles never count | `test_r2_tag_wins_on_spelling_slip` |
| 3. One author, several spellings | `canonical_author`: Russian name for a Russian original, English otherwise (original unknown: English when an English spelling exists locally); within that the most common spelling across the library (book folders, case variants merged, ties alphabetical — the same answer for every book); then surname first when a known first name or initial shows the surname. The choice is stored in `metadata_facts.author_spelling` and cited in the author evidence | `test_r3_one_spelling_per_author_deterministic_and_recorded` |
| 4. Generic titles ("Сборник рассказов") | Accepted when the author agrees locally; reader, compiler and collection-credit safety still applies; inside a collection folder an agreeing person stays research (author or compiler is unclear) | `test_r4_generic_title_accepted_when_author_agrees` |

**Futaba's 7 probable cases, per case:** Булдаков ×3 (`984fe472`, `7fd4e232`, `e10d5261`): correctly attributed — filed under `Сборники` as "Разные авторы", narrator Олег Булдаков (comment "Читает Олег Булдаков" + collection folder). Князев ×3: held for research — `710a6a3c` and `aedf2ae0` (collection folder, and Князев is not credited as a reader anywhere, so author vs compiler is unclear), `d27f8da7` ("неSplatterpunk stories 2" ends in a part number). Лавкрафт episode `ed9488eb`: held (collection folder; the reader is only in `composer`, which this library also uses for authors). The 6 certain cases (Волков-pattern ×5, Головин) are filed under `Сборники` with the readers only as narrators.

**Futaba's 13 suspects (before the rulings):** all held. A ×5 (Волков pattern): collection credit "Сборник" + collection folder; B1 Головин: "Разные авторы" collection credit, no fall-through; B2 Князев ×3: collection folder "Сборники" (and collection titles); B3 Булдаков ×3: collection folder, and the comment "Читает Олег Булдаков" names the credited author as the reader; B3 Лавкрафт episode: collection folder. Also held: the 6 generic collection titles (C) and 2 of the 3 title-text cases (E); `0163bed7` ("ГЕограф глобус пропил") stays approvable, correct identity with a casing typo in the tag.

**Measurement (offline, fresh copy):** 0 before → **445 approvable** = 378 author books + 67 collections filed under `Сборники` (367 after the review fixes alone, 403 in 67e3d43); 479 agree locally. Scan of all 445: reader marker in an author 0, collection credit as an author 0, author credited as a reader anywhere in the catalog 0, a person accepted under a collection folder 0, narrator recorded as a collection's author 0; 10 generic collection titles accepted with their agreeing author (ruling 4). Cross-script: of Futaba's 39 unlinked pairs 30 still match, all the same person (dropped: 4 Hawking/King, Wild Cards/Кард, 4 "Gaiman & Pratchett" two-person credits); a fresh run over the same name population finds 32 unlinked matches, all the same person, 0 false.

**Canonical spelling (F5, ruling 3):** before, 30 people had 2+ spellings across 201 approvals; now 2 people across 9 books, both where one source adds a middle name ("Laymon Richard" / "Лаймон Ричард Карл", "Ходжсон Уильям" / "Ходжсон Уильям Хоуп"), which the matcher does not treat as the same full name. Senua M5: narrator collections now follow ruling 1; other anthology components with an agreeing author inside a collection folder stay research.

**Known false holds by design:** irregular English spellings such as "Michael Crichton"/"Майкл Крайтон" no longer match across scripts (vowel written but not pronounced); a book whose `composer` holds the reader is held only if a marker or narrator tag says so (composer holds the author as often as the reader in this library).

## What changed (first candidate, 67e3d43)

| Area | Change | Files |
| --- | --- | --- |
| Local identity | New pure module. Compares embedded tags (album / title for one file; author, album_artist, artist) with the file name and the two nearest folders, field by field: 🟢 same script, 🟡 other script or word order, 🔴 conflict, ⚪ missing. Accepts identity only when title and author are 🟢/🟡 and series/number are not 🔴. Records which local fields agreed and how. | `local_identity.py` (new) |
| Research entry | `PublicResearch.lookup` runs local agreement first. Accepted: builds the work, policy, evidence and source gate from local data; the Internet is asked only for missing fields. Not accepted: the existing research path runs unchanged. | `public_research.py` |
| Gap search | FantLab, then Wikidata, for original title / language / series; Open Library, Google Books (no key), iTunes Search for a missing full author name. A catalog answer is used only when its title and author match the local agreement. Optional gaps never hold a book; a missing full author name does (required). | `public_research.py` |
| Admission | `approve_automatic` accepts a `local_agreement` source instead of a fetched credit, only for `identity_basis == local_agreement`, and re-derives the agreement from the current row and folder before admission (`revalidate`). Everything after that (probe, encoding, cover, recording review, manifest, queue, publication, retirement, 24-hour recovery) is unchanged. | `merge_service.py` |
| Evidence | Local citations have no URL; `local_evidence` validates them and is accepted only when the standing facts carry `identity_basis: local_agreement`. `manual_evidence` behaviour is unchanged (validation split into a shared helper). | `metadata_sources.py`, `review_backend.py` |
| Policy | `build_policy(local=…)` stores `identity_basis`, the agreement summary and title basis `local_agreement` (cleaned local title, unknown original language). `validate_policy` checks them. | `standing_metadata.py` |
| Source gate | For local identity only, title comparisons accept the agreed title as a segment of a local name ("Series 03. Title", "Title - 01", bracketed narrator notes). Order, membership, disc/track totals and series checks are unchanged. | `source_identity.py` |
| Scheduling | `_wait` picks the time the candidate can progress: the latest earliest-reopening among fully blocked stages (catalog, discovery, credit pages), instead of the earliest closed source. A local book whose optional gap sources are cooling down waits only while the converter is busy, at most 3 queue drains. | `public_research.py`, `automatic_processing.py` |
| Hosts | Per-host pacing (vendor-published limits only), contact User-Agent (repo URL, no e-mail), DuckDuckGo HTTP 202 / challenge = 1-hour pause, research cache 5,000 entries / 64 MB. New hosts: `www.googleapis.com`, `itunes.apple.com`. `RESEARCH_VERSION` standing-18-v1 gives every waiting/held book one fresh pass. | `public_research.py` |
| Tests | 22 new focused tests + 3 end-to-end admission tests with private audio (real ffmpeg). Research-path test classes now switch local agreement off explicitly (`patch.object(PublicResearch,'local_agreement',False)` in `setUp`) because their fixtures agree locally. | `tests/test_local_identity.py`, `tests/test_local_admission.py`, `tests/test_automatic_processing.py`, `tests/test_public_work_identity.py` |

Not done tonight: cover gap search (embedded or neutral cover as before), conversion-throughput tuning (item 4 of the brief), Google human-verification button (needs Judy).

## Measurement (offline, copy of the live catalog)

Copy: sqlite backup API, source opened `mode=ro`, one attempt, 1.6 s, `quick_check` ok, 2026-10-12 21:19 UTC, after Jane confirmed the app idle. No network, no Z:/Y: reads, every public source replaced by an always-closed stub.

| | Before (`90c82db`, v0.13.1 rule) | After (this candidate) |
| --- | --- | --- |
| Waiting/held books checked | 2,426 (2,360 waiting, 66 held) | 2,426 |
| **Approvable without the Internet** | **0** (2,394 "Book identity uncertain", 32 mixed recordings) | **403** |
| Identity agrees locally | — | 461; 58 of them still held by existing gates (32 sources disagree, 21 playback order, 10 source membership, 1 full author name) |
| Local conflict (title or author 🔴) | — | 1,465, of which 1,309 are split-part files (a file beside other files with the same title) |
| Missing locally (⚪ only) | — | 500 |
| Optional gaps among the 461 | — | original title 413, series 461, full author name 11 (required) |

"Approvable" = identity, source scope, playback order and metadata policy pass with every public source closed. Audio probe, encoding, cover and publication run at admission as before and are not simulated. 30-book chip sample: `Docs/BooksArranger_IdentitySample_2026-10-13.md`.

Calibration on the real copy found and fixed, before this number: titles losing a leading number ("81 миля"), bracketed narrator notes breaking the source gate, a narrator taken as author (James S. A. Corey files name the narrator), "Сборник" taken as a person, and split chapter files each "agreeing" on the book title. The last one alone was about 550 false approvals in an earlier run; it is now a hold.

Biggest remaining lever: the 1,309 split-part files. Today every M4B is its own candidate, so a book split into chapter or part files cannot be one book. Grouping them is a grouping/media change and was not attempted.

## Risks — where to look hardest (Senua)

1. **False local identity.** Tags and folder names created by the same tagger agree by construction; Sergei accepted that. Guards: two different people in author/artist tags are a conflict (resolved only when an author folder names exactly one and no file/folder name mentions the other); a credit listing several people never matches one of them; titles never match across languages; files beside other files with the same title are refused (split books). Look at `local_identity._embedded`, `agreement`, `compare_names`.
2. **Cross-script matcher false positives.** Consonant skeleton + ending check + at least one long word. Short names (2-letter skeletons) can collide; every word must still pair one to one.
3. **Admission integration.** `merge_service.approve_automatic`: the `local` branch replaces only the fetched-credit requirement; `revalidate` re-reads the folder listing from the catalog read-only (`folder_siblings`) inside the existing locks; a catalog read error becomes a held candidate, not a run failure.
4. **Evidence without URL.** `review_backend.save` accepts `source_url == ''` only for `identity_basis == local_agreement` facts that `validate_policy` has already checked.
5. **Source gate relaxation.** `source_identity.source_gate` segment matching applies only when `work['identity_basis'] == 'local_agreement'`.
6. **Pacing.** `HOST_POLICY` numbers and their sources are in the comment above it; actual 403/429/Retry-After handling is unchanged.

## How to test (Futaba)

1. Full suite: `python -m unittest discover -s tests -p "test_*.py"` (timeout 600000). Compare with the baseline below.
2. Focused: `python -m unittest discover -s tests -p "test_local_*.py"` — 48 tests after the review fixes (3 use real ffmpeg).
3. Offline measurement: copy the live catalog only with Jane's go-ahead (backup API, read-only source), then run `scratch/fast-identity-2026-10-13/evidence/measure.py <code dir> <copy> <out.json>` for both `90c82db` (`git archive`) and this candidate. Expect 0 → about 400 approvable.
4. Spot-check `Docs/BooksArranger_IdentitySample_2026-10-13.md` rows against the copy with `evidence/probe_row.py <code dir> <copy> "<title text>"`.
5. After release and Sergei's normal Restart: the first automatic pass revisits every waiting/held book once (research version change). Watch that admitted local books show `identity_basis: local_agreement` in the accepted evidence and that split chapter files stay held.

## Suite result (Ender, this worktree, path length 99 characters)

| Run | Tests | Errors | Failure set vs baseline |
| --- | --- | --- | --- |
| Baseline, pristine `90c82db` in this worktree | 490 | 9 | — |
| Candidate run 1 (before the last two matcher refinements) | 514 | 9 | identical |
| Candidate run 2 (final code) | 515 | 10 | baseline 9 + `test_web…test_restart_guard_rejects_wrong_instance_busy_admission_and_active_research`: tearDown `PermissionError [WinError 32]` (temp SQLite file still open during cleanup), no assertion failed; passed 3 of 3 isolated reruns |
| Candidate run 3 (final code) | 515 | 9 | **identical** |

The 9 pre-existing errors are the known environment/fixture set from `Docs/BooksArranger_QAReport_v0.13.1_2026-10-12.md` (missing untracked `scratch/source-fallback-2026-10-11` fixtures, `baseline_native_io.py`, `BrowserServer.loaded_version`, path length). Known flakes seen: `test_waiting_uses_earliest_candidate…` (pre-existing F4, 1 of 3 file runs) and the test_web tearDown lock above.

Evidence kept for QA (not in Git): `scratch/fast-identity-2026-10-13/evidence/` — the catalog copy (377 MB; delete after QA), `measure-before.json`, `measure-after.json`, `copy-receipt.json`, the scripts and the suite outputs.
