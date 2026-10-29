# Books Arranger — POST-023-01…05 diagnosis (2026-10-29)

Ender, Phase 1, read-only diagnosis of the five reports logged after 0.23.0 (`BooksArranger_0.22.1_Backlog.md` § "Open reports after 0.23.0"), of ruling 68, and of the new destination-override feature in rulings 69/70 (§ 7).
Code base: `WIP/Books Arranger` HEAD `4ae072f` (0.23.0 code, clean). No code change, test, build, app launch or git write was made.

## How it was measured

- **Catalog:** the live catalog files `data/inventory.sqlite3` and `inventory.sqlite3-wal` were copied as files (no sqlite backup) at 09:15 on 2026-10-29 into `%LOCALAPPDATA%/Temp/ba-post023/`. Every count below comes from small Python probes run on that copy: `files`, `book_groups` (with `superseded=0` unless stated), `catalog_group_members`, `automatic_candidates`, `audio_jobs`, `source_retirements`, `cleanup_members`, `source_folder_cleanup_directories`, `author_rules` and `names_entries`. The last full scan of `Z:\Audiobooks` was generation 6 on 2026-10-22, so the catalog does not yet know about later disk changes.
- **Z: (read-only):** directory listings of the five source folders and of `Z:\Audiobooks Sorted` (Abnett Dan, Pratchett Terry, Джин Вулф, Warhammer 40K, Сборники); the two Gene Wolfe `info.txt` files; and the raw ID3 header bytes of two Pratchett files (`004-01.MP3` and `002-01.MP3`). Nothing was written.
- **Code:** read at HEAD. The code's own helpers (`local_identity.garbled`, `foreign_given`, `surname_first`, `original_titles.translation`) were imported read-only to test real values.

## Summary

1. **Ruling 68:** `source_identity.partition()` gives every MP3 its own scope from its album+artist tags or its file name. One folder is split whenever those differ. Lyons: 5 rows. Wolfe: 38+40. Pratchett: 105+13. Abnett: 6 rows.
2. **Scale:** 162 folders are split across 2 or more active books. 144 of them hold only whole `.m4b` files (author and series folders, the source root). 18 hold MP3 files.
3. **Damage already done:** four parts of Abnett's novel «Первый и Единственный» were converted as **four separate books** (completed 28 Oct), and their sources were deleted by the app. Parts 5–10 are now gone from Z:, and the app has no record of removing them. «Гробница Саргераса» went the same way (4 parts → 4 books).
4. **Mojibake:** ffprobe reads the ID3v2 frames of 13 Pratchett files, which are marked ISO-8859-1 (encoding byte 0) but hold cp1251 bytes. The app never re-decodes them. Partition sees different tags, so the folder splits. Identity ignores the garbled tags and falls back to the folder name, so the destination looks readable while the clue columns show the raw mojibake.
5. **Narrator used as title:** `исп. Капитан Абр и Nelly` is the album tag. The album-as-title path checks for garbled and junk values, but not for narrator markers.
6. **«Джин Вулф» in Cyrillic, given name first:** «джин» is missing from `GIVEN_NAMES`. As a result, `surname_first` keeps the name as written, `foreign_given` is False, the ruling-39 English-name lookup never fires, and the Approve guard for ruling 59 is skipped. Measured: 30 Cyrillic credits (about 50 books) fall into this blind spot.
7. **Stale verdicts:** `RESEARCH_VERSION` has been `standing-22.2-v1` since 0.22.2 and was not bumped in 0.22.3 or 0.23.0. As a result, 289 Held verdicts are never re-researched against the new rules. Approved jobs keep their destination frozen in the job record: «Тень и Коготь» completed on 29 Oct into `Sorted\Джин Вулф\`.
8. **Misleading Order/Files reasons:** these are computed per row, not per folder. "The other tracks aren't here" is false for Lyons (all 38 files are present). "Track numbers skip" is false for «Солнце и Замок»: tracks run 1–70, but every file is tagged disc 5.
9. **Open source folder:** the backend already opens Explorer (`/api/open-folder`). List rows never carry `source_directory_count`, so every row falls into the "Source folders" branch. That branch opens the details panel instead of the folder.
10. **Batch:** all five fit one batch and one rebuild **if** Sergei answers Q1–Q5 first. The ruling-68 part changes the grouping model, so it should ship as a minor version, not a patch.
11. **Rulings 69/70 (§ 7):**
    - The pieces that fit this batch: the folder picker (the existing setup-only `dialog.showOpenDialog` pattern), a per-book override that outranks the planner, and the "open the converted file's folder" fallback (the backend route already exists).
    - Moving a **finished** book is the largest new piece. The app's journaled relocation protocol exists, but only as an offline tool that allows **one** move per book. 432 of the 624 finished books already used that one move in the 0.20 migration. Making it in-app, repeatable and self-recovering is a batch of its own.

---

## 1. Ruling 68 — where one source folder is divided (POST-023-05, and the root of 02/03/04/01)

### Evidence

- **Lyons** `Z:\Audiobooks\Unsorted\WH40K\Стив Лайонс - Криг + рассказы (Casper Valter)`:
  - On Z: (listing): 38 MP3 files. `01. Криг` … `34. Криг`, then `35. Брошенный умирать`, `36. Исход`, `37. Сильные среди нас` and `38. Среди мертвецов`.
  - In the catalog: track tags `01/38`…`38/38` with no gap. File-name numbers 01–38 with no gap. Artist `Стив Лайонс` on every file. **Album = `Криг` on 1–34 and the story's own name on 35–38.**
  - Active groups: `633d4ff0` (34 files, Held "Source membership uncertain") and `ed0f7aa6`, `78b4dbfd`, `16591d22`, `b04fd786` (1 file each, Held). None of them has a job, an approval, a review or an entered name.
  - Track 35 exists; its row was simply off-screen. **The folder is complete: 38/38.**
- **Wolfe «Меч и Цитадель»:**
  - 78 files. Album `…- Меч ликтора` on 38 files (disc 03, tracks 01–38) and `…- Цитадель Автарха` on 40 files (disc 04, tracks 39–78).
  - Two groups: `baadccff` (38 files, auto-approved on 27 Oct; job `ce8bb6ba` is in "needs attention: Source changed") and `62527411` (40 files, Held).
- **Pratchett «Шляпа полная небес»:**
  - 118 files on Z: and in the catalog, named `001-00 вступление` … `118 пример срыва во время записи…`.
  - Two groups: `164b0f5d` (105 files) and `30425b10` (13 files: 004, 005, 006, 008, 017, 018, 024, 060, 073, 088, 098, 109, 115).
  - A superseded group `bfcafefc` once held all 118 files. It came from the old folder-scoped algorithm and was never approved.
- **Abnett «Первый и Единственный»:**
  - 10 files `01_Часть Первая…` … `10_Часть Шестая…` → 6 groups (1, 1, 1, 1, 3 and 3 files). See § 6 for what already happened to them.

### Root cause

- `source_identity.py:39-54` `partition()` gives a scope to **each file**:
  - `folder | Album <album> | Artist <album_artist or artist>` (lines 45-48);
  - else `folder | Filename work <author> | <title>`, parsed from "X - Y" in the file name (49-51; `filename_identity` at 13-21 treats `Часть Пятая` as an author);
  - else "Unverified numbered source set" (53);
  - else "Standalone source" (54);
  - and every `.m4b` is its own scope (44).
- `groups.py:503` adopts these scopes, and `groups.py:552-553` buckets files by them. The joiners re-join only in narrow cases:
  - `_same_title_sets` (296-360): same title tag and no album, or a shared start of the numbered file name that is not a person.
  - `_same_album_parts` (424-451): the same album apart from a trailing CD number, **and** one author.
  - `_part_sets` (379-422): `.m4b` only.
  - `_split_plan` (285-294): single-file candidates only.

  A novel + stories (different album per story), two halves of an omnibus (different album suffix), a mojibake subset (different album bytes) and «Часть N - Name» files (different file-name "author") all fall through every joiner.
- `groups.py:631-641` can split a scope further into "Provisional subgroup" rows. Those are held, but they are still separate rows.
- The explanations are computed per row: `todo_causes.py:86-118`. `one_of_many` (line 99) prints "This file is tagged as track 36 of 38. The other tracks aren't here." and `track_total` (line 108) prints "The tags say 38 tracks, but 34 files are here." Neither looks at the rest of the folder.

### Inventory of within-folder splitters and older rules against ruling 68

| Rule / mechanism | What it does today | Against ruling 68 |
|---|---|---|
| `partition()` album/artist, file-name work, standalone (source_identity.py:39-54) | Splits one MP3 folder by tags or file names | **Cleanly superseded.** This is exactly what 68 forbids. |
| Joiners `_same_title_sets` / `_same_album_parts` / `_split_plan` (groups.py) | Patch the partition back together in narrow cases | Superseded. Redundant for MP3 folders once the folder is the unit. They stay only for disc/part subfolders (`split_books.unit`, already rolled up to the parent). |
| G3/N6 "title tags name more than one book" (`_works`, groups.py:453-475, 663-680; Ведьмак case) | Holds a folder as Files unclear; does **not** split it | Compatible. It already keeps the folder together. |
| Ruling 19/19a/19c (join parts, `Часть N` keeps joining), ruling 50 (CD/Том/Часть are parts) | Join | Compatible. Ruling 68 strengthens them. |
| Ruling 19b "Never join the volume pattern" (`.m4b` files that each restart at Глава 1, `part_sets.decide` → "Volume of a series") | Keeps separate `.m4b` volumes in one folder apart | **Genuine conflict → Q1.** |
| Ruling 54 (single-file books in one folder are siblings of a series), ruling 53/57 (numbered self-confirming sets, e.g. «Шерлок Холмс. Аудиоспектакль 1, 2, 3…») | Presuppose several books in one folder | **Genuine conflict → Q1.** They hold only if a folder can hold several whole books. |
| "Keep as separate books" (`kept_parts`, groups.py:101-107: Sergei's own press) | Sergei-recorded separate volumes | Sergei's explicit per-book answer. Ruling 68 does not say whether it overrides his own earlier press → covered by Q1. |
| `.m4b` = "Single audiobook file" (groups.py:200-202, source_identity.py:44) | Every whole `.m4b` is its own book | **Genuine conflict → Q1.** 144 of the 162 split folders are of this kind: `Stephen King\` (56 books), `Сборники\Глубина` (49 volumes), `Сборники\Созвездие Льва` (12), and the `Z:\Audiobooks` root itself (44 loose books). |
| Ruling 64/65 named anthology volumes (`anthology_volumes`, groups.py:506-523) | Reserve the whole folder as one volume; one owned story blocks a partial volume | Compatible. It is the model for the bound-files rule below. The «Ужасы и трэшатинка» volume-1 pending claim (`c1276721`, job pending, plus 12 "Anthology membership conflict" files) must stay exactly as it is. |
| Ruling 23/24 Delete book "never touch other books' files in the same folder" | Assumes multi-book folders | No conflict. It stays correct, just with less to do. |
| Ruling 2 / 1a deletion invariant | Sources are removed only after their book is verified in Sorted | Unchanged. Under ruling 68 a folder's sources are removed only when the **whole-folder** book is verified. |

The remaining MP3 folders with a real ambiguity (they are not container folders):

- **A folder holding a whole series of separately tagged novels.** `OLD_Audiobooks\…Хроники Нарнии…Радциг` is 7 albums of 15–17 files each, now 7 rows. `…Космическая трилогия…Исаев` is 3 albums, now 3 rows. → **Q2.**
- **`Unsorted\Warcraft`** holds two loose novels by different authors (one completed, one pending) next to a subfolder. It is a container, not a release → **Q1.**

### Measured scope (probe over `catalog_group_members` + active `book_groups`, audio files only)

- 700 folders hold active groups; **162 are split across 2 or more active books**. 144 of those hold only `.m4b` files; 18 hold MP3 or other formats.
- The 18 non-`.m4b` folders: Pratchett (105+13); Война Z 1 (58+1); Lyons (34+1+1+1+1); Wolfe «Меч и Цитадель» (38+40); Abnett (1+1+1+1+3+3); Брукс «Месть Гоббо+…» (12+1+1, 3 jobs pending); Макнилл «Рассказы» (4×1, all completed); «Бойся Чужого» (10×1, 9 completed, 1 needs attention); «Сборник рассказов Warhammer 40000» (14×1, 1 completed, 13 needs attention); Кинг «Рассказы» (5×1, 1 pending, 4 needs attention); Warcraft container (2); «Гробница Саргераса» (4×1, all completed); Страуд «Кричащая лестница» (26 + `Словарь.mp3`, both pending); Страуд «Шепчущий череп» (30 pending + `Словарь.mp3` Held); «Ужасы и трэшатинка» volume 1 (12 + 1 pending, preserved); Lewis Космическая трилогия (3); Хроники Нарнии (7); the `Z:\Audiobooks` root (44 loose books).
- **Split folders where some groups are already bound** (approved, reviewed, job or completed) and others are not: **49**, most of them `.m4b` author folders.

### How bound files are preserved (proposal)

- **Protected stays protected.** A group that is approved, reviewed or has a job (any state) keeps its exact scope and members. This is the existing `assigned`/`protected` path (groups.py:500-503, `_sync_inputs` 704). A completed book in Sorted is never touched, renamed or merged.
- **A partly bound folder is never re-joined silently and never gets a free partial book.** If any file of the folder belongs to a protected group that does not cover the whole folder, the remaining files form **one** held group. It carries `source_partition_uncertain` and a conflict such as "Part of this folder is already a separate book: «X» (completed / waiting to convert)". This generalises the anthology `owned_folders`/`blocked` rule (groups.py:510-519) from named anthologies to every folder. The row shows which files are bound where, and Sergei decides (Q3, Q4).
- **No change to existing records.** Nothing migrates and nothing is reassigned: no job manifest is edited, no group is re-scoped while protected, and no source or Sorted file is renamed.
- **Sergei's own entries.** None of the five cases has an entered name (`names_entries`) or a manual draft.

### Proposed fix

1. **Folder as the unit.** In `partition()`, MP3/track files get one scope per source folder: `str(base) + '\x1fSource folder'`, with the existing disc/part subfolder roll-up from `split_books.unit`. `.m4b` folders stay as today until Q1 is answered. Bump `GROUP_VERSION` (one regroup per root; protected scopes keep theirs).
2. **Inside the book:** per-file album/title tags become chapter or story titles and per-file artist credits stay story credits. This reuses the anthology `anthology_story` pattern and the existing chapter-title path. Ruling 68 says a novel plus stories needs no multi-author book credit, so the book author is the folder's one author when all files agree (Lyons). Mixed authors follow the existing collection route.
3. **`source_gate` (source_identity.py:206-246).** For a source-folder book, differing album tags are no longer "Mixed recordings" (line 215). The real recording checks stay: audio profile in `split_books.check`, readers, unreadable files.
4. **Partly bound folders** are held as described above.
5. **Explanations** use the whole folder (see § 4).

**Tests:** new `tests/test_folder_unit_grouping.py` with these fixtures:
- Lyons 38 (34+4 albums, one book, track total 38 = files 38).
- Wolfe 78 (two album suffixes, one book, order from file-name sequence 1..78).
- Abnett 10 (`Часть N - Name`, one book).
- Pratchett 118 (cp1251 subset, one book).
- Страуд 26 + `Словарь.mp3` (one book).
- Partly bound folder (one completed or pending member → remainder held, nothing joined).
- «Ужасы» volume-1 claim unchanged.
- Глубина and Созвездие Льва `.m4b` boundaries unchanged.

Extend `tests/test_join_parts.py` and `tests/test_todo_holds.py`.

**Risk:**
- Sergei's entered names are keyed by the book's exact member paths (`entered_names.book_key`, entered_names.py:57-61). A fragment row that grows into the whole-folder book therefore gets a new key, so names typed on the fragment would no longer apply. Measured: 0 of the 18 book-level entries sit on a split MP3 folder today. The fix must still carry or surface such entries rather than drop them.
- The 162 split folders regroup once. Unbound groups get new ids, so their research verdicts restart. Protected ones keep their ids.
- 26 unfinished jobs in 7 MP3 folders still hold single-story or single-part scopes (Брукс 3, «Бойся Чужого» 1, WH40K сборник 13, Кинг 5, Wolfe 1, Страуд 3). They stay as they are until Sergei answers Q4.

---

## 2. Mojibake — the 118 → 105 + 13 Pratchett split (POST-023-04, cross-check of the 0.23.0 audit)

### Evidence

- **Raw bytes, read from Z:.**
  - `004-01.MP3` has an ID3v2.3 tag with `TPE2`, `TPE1`, `TALB` and `TCON`, all with **encoding byte 0 (ISO-8859-1)**, carrying cp1251 bytes (`\xd2\xe5\xf0\xf0\xe8` = «Терри»). It also has an ID3v1 tag (genre 3 = "Dance").
  - `002-01.MP3` has `TPE1` and `TALB` with **encoding byte 1 (UTF-16 + BOM)** and no ID3v1.
- **Catalog.** The 13 files store `album "èñï. Êàïèòàí Àáð è Nelly"`, `artist "Òåððè Ïðàò÷åòò. Øëÿïà , ïîëíàÿ íåáåñ"` and `album_artist "Òåððè Ïðàò÷åòò Øëÿïà ïîëíàÿ íåáåñ"`. Re-decoding them latin-1 → cp1251 gives exactly «исп. Капитан Абр и Nelly» and «Терри Пратчетт. Шляпа , полная небес». The 105 files carry the readable values.
- **The 0.23.0 audit observation is confirmed.** All 118 files are on Z:; there are 105 readable and 13 garbled. The 13 are interleaved (004 … 115) and have no gap of their own. All 118 are one book.
- **Library-wide, measured over 13,502 audio files that are not missing** with `garbled()` on album/artist/album_artist/title:
  - 8 folders have values that latin-1 → cp1251 repairs; 0 need cp866.
  - 1 folder is unrecoverable: Головачев in `OLD_Audiobooks` has U+FFFD, so the bytes are lost.
  - **2 folders are split by it:** Pratchett (105+13) and `OLD_Audiobooks\Война Z 1` (58 files with garbled album + 1 file with readable album and garbled artist).

### Root cause

- **Where decoding happens.** In ffprobe/libavformat: an ID3v2 frame with encoding byte 0 is decoded as ISO-8859-1. `metadata.py:51-82` stores ffprobe's strings verbatim. No code repairs a codepage. `local_identity.garbled()` (1560-1570) only **detects** mojibake and discards it.
- **Why the folder splits.** `partition()` (source_identity.py:42-48) normalises the raw garbled album/album_artist, so the 13 files get scope `Album èñïêàïèòàíàáðènelly | Artist òåððèïðàòåòò…`, which differs from the 105.
- **Why the preview looks readable while the clues stay garbled.**
  - For group `30425b10`, identity ignores the three garbled tags ("garbled text is not used"). Title falls back to the **folder name** (`Т. Пратчетт. Шляпа полная небес .`), and author falls back to the ancestor folder `Terry Pratchet` through Sergei's seed rule → `Pratchett Terry`. So "Goes to" is readable.
  - The **Title clue** and **Author / reader** columns render the group's raw `title_clue` and `artists`, built from the stored tags in `groups.py:241-266`. They are never repaired, so they show mojibake.
  - The readable destination is itself wrong: its title still contains «Т. Пратчетт.» (§ 3b).

### Proposed fix

- **A pure repair function** `tag_text.repair(value)`. It applies latin-1 → cp1251 only when all of these hold:
  - `garbled(value)` is True;
  - every character is ≤ U+00FF;
  - the result is not garbled and has at least 3 Cyrillic letters.
  - (A cp1251 → utf-8 branch for «РўРµ…» is cheap; it has 0 hits today.)
- **Apply it in one tag accessor** used by `partition`, `groups.member`/`_legacy_build` clues, `source_identity.clues` and `local_identity._tags`. Raw values stay in the catalog and in the source files (sources are never written). The clue shows "repaired from a mis-encoded tag".
- U+FFFD values stay "not used".
- Under ruling 68 the Pratchett folder is one book anyway; the repair is still needed for readable clues, for identity, and for the 7 fully garbled folders.

**Tests:** new `tests/test_tag_repair.py` (the real Pratchett byte strings; a readable value is untouched; U+FFFD is untouched; Latin-script names such as «Ángel Béjar» are untouched because they don't satisfy `garbled()`). Extend `tests/test_identity_v5.py` so that a repaired album becomes a title clue.

**Risk:** low. The repair is read-side only. Group scopes of the 8 folders change once, and none of them is bound (probe: no job or approval on the Pratchett or Война Z groups).

---

## 3. Misleading identity (POST-023-01, 02, 03)

### 3a. Narrator credit used as the title (03)

- **Evidence.** Group `164b0f5d`, verdict from 27 Oct: title `исп. Капитан Абр и Nelly`, "how: the embedded album tag". The uploader swapped the tags: album = reader credit, artist = «Терри Пратчетт. Шляпа полная небес».
- **Root cause.** `local_identity.py:2194-2210` takes the album value as the title after only two checks: `garbled` and `JUNK_TITLES`. It never tests `NARRATOR_MARKER` (line 57, which matches «исп.»), although the same file applies that test to other title sources (line 2011).
- **Fix.** An album or title tag value that matches `NARRATOR_MARKER` is ignored ("names the reader, not the book") and its names become narrator clues. Title then falls back to the next source. An artist value of the form «Person. Title», with the person known through the author rule seed `b980cd4f…`, can supply the title through the existing dotted-split code (2214-2225).
- **Tests:** `tests/test_local_identity_fixes.py` (swapped album/artist → title «Шляпа полная небес», narrator «Капитан Абр и Nelly»).

### 3b. The folder title keeps an "Initial. Surname." prefix (04, and the 03 fallback)

- **Evidence.** `30425b10` has title `Т. Пратчетт. Шляпа полная небес .`, taken from the folder `Т. Пратчетт. Шляпа полная небес .(чит Капитан Абр и Nelly)`.
- **Root cause.**
  - The dotted author split (`local_identity.py:2214`, `^\s*([^.\d]{3,60}?)\.\s+(\S.*)$`) needs at least 3 non-dot characters before the first dot, so «Т. Пратчетт.» never matches. It is also applied only to tag values, not to the folder title.
  - The reader tail «.(чит …)» leaves a stray " ." behind. `NARRATOR_MARKER` requires «чит.» with a dot, so «чит » without one is not recognised.
- **Fix.** Accept an initials-plus-surname prefix (`INITIALS` + surname) in the dotted split, for the folder title as well. Add «чит» without a dot as a narrator marker inside brackets.
- **Tests:** `tests/test_local_identity_fixes.py`.

### 3c. An author clue that contains a quoted title (02)

- **Evidence.** The artist tag on 9 of the 10 Abnett files is `Дэн Абнетт «Первый и Единственный»`. Sergei's seed rule `1856bcba…` maps the **whole string** to `Abnett Dan`, so the author is right. The quoted title is never used as title evidence: the single-file rows took their titles from the file names (`01_ Часть Первая - Нубилийский Пролив`), and the 05–07 row took its title from the folder.
- **Root cause.** No code splits «…» out of a person credit. `filename_identity` (source_identity.py:13-21) splits only on " - ".
- **Fix.** When an author or artist credit carries a «quoted» or "quoted" segment, the person part is the author clue and the quoted part is a title clue. Rules keep matching the full credit as before.
- **Tests:** `tests/test_identity_v5.py`.

### 3d. Cyrillic author «Джин Вулф», given name first (01) — rulings 33/39/58/59

- **Evidence.**
  - No author rule exists for Wolfe in `author_rules`. All four Wolfe verdicts (27 Oct, 11:28–11:30 UTC) say "author green «Джин Вулф» — the artist tag; the folder name agrees".
  - Job `4ab4fdaa` («Тень и Коготь», 67 files) **completed on 29 Oct at 03:51 UTC into `Z:\Audiobooks Sorted\Джин Вулф\Тень и Коготь - Джин Вулф.m4b`** (the file is on Z:, 1.30 GB).
  - Job `ce8bb6ba` («Меч ликтора») still carries `Джин Вулф\Меч и Цитадель - Меч ликтора - Джин Вулф.m4b` as its destination.
- **Root cause, in two parts:**
  1. **`GIVEN_NAMES` (local_identity.py:74-101) lacks «джин».** Measured: `foreign_given('Джин Вулф')` returns False and `original_titles.translation('Тень и Коготь','Джин Вулф')` returns False. Consequences:
     - `surname_first` (1038-1057) keeps the name "as written", so it stays given-name first, contrary to ruling 58.
     - The ruling-39 lookup at `public_research.py:1321-1323` never fires, so FantLab is never asked and Sergei is never asked.
     - The Approve guard for ruling 59 at `merge_service.py:3065-3072` requires `foreign_given(...)` **and** an old keep rule, so Approve, including "Approve this order", files the book under `Джин Вулф\`. That is the "order approval bypasses author checks" in 01.
     - Blind-spot size, measured over all verdicts: **30 Cyrillic credits / about 50 books** have no rule, no known foreign given name and no known Russian given name. Examples: Вулф, Лю Цысинь, Туве Янссон, Альфред ван Вогт, Брукс Майк, Крис Метцен, Мьевиль Чайна, Перес-Реверте, Блейк Крауч, Хаксли Олдос, Амброз Бирс, Кавабата Ясунари, Буццати Дино. The list also contains Russian writers with uncommon given names, such as Измайлов Наиль and Шаинян Карина.
  2. **Stale verdicts and frozen destinations.**
     - `RESEARCH_VERSION` (`public_research.py:84`) is `standing-22.2-v1` at the v0.22.2, v0.22.3 **and** v0.23.0 tags; checked with `git show <tag>:public_research.py`. Code comment `automatic_processing.py:631-633` says new rules mean a new research version, but 0.22.3 and 0.23.0 added rulings 39/52/58/59 without bumping it.
     - `automatic_processing.py:629-636` therefore skips every Held verdict with `until_change` (289 Held at the current version).
     - Approved jobs freeze `destination` and `metadata` in their manifest at approval time, and they run later without an author-language re-check.
     - Measured over `audio_jobs` with the existing heuristic: 47 completed, 13 needs attention and 2 pending jobs carry a Cyrillic author with a known foreign given name (e.g. Скальци Джон, Судзуки Кодзи ×4, Вестерфельд Скотт ×2, Хайнлайн Роберт). Wolfe's job is extra, because the heuristic misses him. «Перумов Ник» is a false positive: a Russian writer.
- **Fix.**
  - Add «джин» (and audit `GIVEN_NAMES` against the 30 blind-spot credits).
  - More robustly: for a Cyrillic credit with **no** rule whose given name is unknown, run the existing ruling-39 lookup anyway. FantLab answers "foreign → learn same_as" or "Russian → learn keep"; if it is inconclusive, ask Sergei (ruling 51).
  - Extend the Approve guard to "Cyrillic, no English rule, not known Russian → ask for the English name".
  - Bump `RESEARCH_VERSION` so Held verdicts re-research.
  - Re-check frozen job authors before a run: **Q6**.
- **Tests:**
  - `tests/test_local_identity.py`: «Джин Вулф» → foreign; `surname_first` gives «Вулф Джин».
  - `tests/test_series_research.py` or a new `tests/test_english_author_lookup.py`: an unknown given name triggers the lookup; a Held verdict from an old version re-researches.
  - `tests/test_identity_0222.py`: the Approve guard without a keep rule.

### 3e. «Антон Ческидов» — role

- **Evidence.**
  - The tag is `album_artist`. Sergei's seed rule `c43afb33…` says `not_author` ("Sergei 2026-10-24").
  - The verdicts list it under "ignored: … not an author (a reader, label or uploader)".
  - Both `info.txt` files say «Чтец: Антон Ческидов». He is the narrator, and the preview author is correctly the artist tag.
- **Root cause of the misleading column.**
  - The "Author / reader clues" column shows `group.artists`, which `groups.py:245` builds from `metadata.get('artist') or metadata.get('author')`.
  - These catalog rows were read by an older `read_metadata` that stored no `artist` key. In that version, `author` was `album_artist or artist` (`metadata.py:79`, same order today).
  - So the column shows the reader, with no role label.
- **Fix.** Build the clue from tags: artist as a writer clue; album_artist/narrator as a reader clue when a `not_author` rule or `NARRATOR_MARKER` says so. Label the role. Judy specs the wording.
- **Tests:** `tests/test_todo_holds.py`.

### 3f. Original English title (ruling 49) and saved overrides

- **No saved overrides.** None of the 13 case groups has `names_entries` or a manual draft. The "reviews" on `baadccff`, `fafe202a` and the Abnett part rows are the automatic pass's own approvals (actor `assistant` in the cleanup intents). There is nothing of Sergei's to preserve or overrule.
- **No English title ever looked up.** No verdict has an English original title (`original_title: none/null`). For Wolfe this is a consequence of 3d: the lookup path also supplies the English title (`public_research.py:1342-1347`). For Pratchett, the narrator title (3a) was what got searched: the research history shows Wikidata/OpenLibrary queries for «исп. Капитан Абр и Nelly».
- **Expected English titles.** These are my general knowledge; research must confirm each, and none should be hard-coded:
  - «Шляпа полная небес» = *A Hat Full of Sky* (Discworld 32, Tiffany Aching 2). Sorted already uses the `Discworld NN. Title - Pratchett Terry` pattern and has a `Discworld\` folder.
  - «Криг» = *Krieg* (Steve Lyons, Warhammer 40,000).
  - «Первый и Единственный» = *First and Only* (Gaunt's Ghosts 1).
  - «Тень и Коготь» / «Меч и Цитадель» = the omnibuses *Shadow & Claw* / *Sword & Citadel*.
  - «Солнце и Замок» has no English omnibus equivalent, so ruling 38 applies: the existing title.

### 3g. Cycle and position

- **Wolfe — verified from source evidence, not from `#3`:**
  - `info.txt` says «Меч и Цитадель … Из серии: Книга Нового Солнца #2», written 1981–1982, and «Солнце и Замок … #3», written 1987. The publisher is fanzon/Эксмо, the translator Д. Старков.
  - The **disc tags are the novel numbers:** 03 = «Меч Ликтора» (title tags), 04 = «Цитадель Автарха», 05 = the 1987 novel. In «Солнце и Замок», prefixes 06–09 are appendices, the «Сказка…» stories, «Истории из эпохи Севериана» and «Замок Выдры. Книга о Книге Нового Солнца» (title tags). «Тень и Коготь» uses prefixes 01/02 = «Тень палача» / «Коготь Миротворца».
  - So **`#3` is the Russian omnibus volume number, not the novel number.** The edition numbers its volumes 1–3; they contain novels 1–2, 3–4 and 5 plus extras.
  - The app reads no series because there is no series tag. The «(Книга Нового Солнца #3)» in the album is stripped as a bracket by `clean_title`, the sibling folders carry no series name, and nothing exists in Sorted to confirm one (ruling 52).
  - Which numbering to file under is Sergei's call → **Q5**.
- **Abnett.** The app had no series or universe evidence: no series tag, no `Вселенная …` folder (ruling 30), and no `Gaunt's Ghosts` folder in Sorted. Sorted's WH40K layout is `Warhammer 40K\<Series>\<Series> - N - <English title> - <Author>.m4b` (Horus Heresy, Чёрный Легион). Research (FantLab/Litres) is the route, and ruling 52 asks once if research finds a series that nothing confirms.

---

## 4. Fragment rows and numbering gaps (01: `04-39`, `05-01`; 02: parts 05–07; 04: `004-01 … 017-02`)

### What the code concludes now, and why it is wrong

| Row | Members | Hold reason (source_gate) | Text shown (`todo_causes.order_cause`, 46-71) | Actual situation |
|---|---|---|---|---|
| Wolfe «Цитадель Автарха» (40) | disc 04, tracks 39–78 | tracks don't start at 1 (source_identity.py:233); disc [4] ≠ [1] (235) | "Track numbers skip or don't start at 1." | Tracks 1–38 are in the sibling row `baadccff` (same folder, a job). The folder runs 1–78 without a gap. |
| Wolfe «Солнце и Замок» (70) | disc 05 on every file, tracks 01–70 complete | discs [5] ≠ [1] (235) | "Track numbers skip or don't start at 1." | **False:** tracks start at 1 with no gap. The only oddity is the disc tag 5 (the novel number). Folders 01–02 and 03–04 are siblings. |
| Abnett «Эмпирей» (3) | no tags; file numbers 05, 06, 07 | file positions don't start at 1 (233) | "No file has a track number. The order comes from the file names." | Parts 01–04 had already been converted as 4 separate books. 08–10 was another row. |
| Pratchett 105 / 13 | no tags; file numbers with gaps | gaps (233) | "No file has a track number…" | The other row of the same folder fills every gap. The folder runs 001–118 complete. |
| Lyons 34 / 1 / 1 / 1 / 1 | `NN/38` tags | track total ≠ files in row (source_gate 241-246; single file 155-159) | "The tags say 38 tracks, but 34 files are here." / "This file is tagged as track 36 of 38. The other tracks aren't here." | **False:** all 38 are in the same folder. |

`order_cause` returns `no_tracks` before looking at file-name numbers (line 54). It never names the missing numbers and never says where they are. `files_cause` (86-118) counts only the row.

### Rule the code should follow (proposal)

1. **Membership first.** The book is the whole source folder (§ 1), with disc/part subfolders rolled up as today. No order or completeness claim is made before that.
2. **Order:**
   - (a) a clean file-name sequence over the **whole** folder (`track_order.filename_sequence`). With this, Pratchett 001–118, Wolfe «Меч и Цитадель» 1–78 and Lyons 01–38 all resolve with no question.
   - (b) else (disc, track) tags over the whole folder.
   - (c) else ask, giving the real reason.
3. **Completeness** is claimed only from whole-folder evidence: a number missing from an otherwise 1..N run, an `N/M` total larger than the folder, or a disc total.
   - Before calling a file "missing", look for it (i) in other rows or bound books from the same folder and (ii) in sibling folders that continue the same numbering (Wolfe 01–02 / 03–04 / 05–09). If it is found, say where: "Files 03-01…03-38 are in «Меч и Цитадель - Меч ликтора» (waiting to convert)".
   - A lone disc number says so: "Every file is marked disc 5; discs 1–4 are not in this folder (the sibling folders hold 01–04)."
   - Under ruling 51 the app still asks in that disc case, because a CD5-only folder looks the same. The text must be true, though.
4. **"Approve this order"** is offered only when order is the **only** doubt. Missing or partial membership shows the ruling-10 missing-files hold with its options instead.
   - Identity holds (English author name, series question) stay separate and are not cleared by an order approval (ruling 59).
   - Today the Abnett 05–07 row offered "Approve this order" on three middle files of a novel. Approving would have converted a fragment and then deleted its sources.

**Fix:**
- `todo_causes.order_cause` and `files_cause` take the folder context: the members of other rows in the same folder (`catalog_group_members` by parent directory) plus sibling-folder numbering. They return `{cause, missing_numbers, found_in:[{title, state}], disc_only}`.
- Judy specs the sentences in `web/app.js` 2449-2460.
- `source_gate` gets a distinct reason for "single disc ≠ 1", so the text cannot claim a skip.

**Tests:** extend `tests/test_todo_holds.py` and `tests/test_todo_holds_frontend.js` (Lyons-before-fix rows report "in this folder"; the disc-5 text; missing numbers listed; Approve this order hidden when membership is in doubt).

---

## 5. "Open source folder" on every review row (POST-023-03) — technical side only

- **Where rows render.** `web/app.js` `renderRows` (522 on). The action cell is built at 585-592; the to-do (attention) list uses the same builder.
- **Root cause.**
  - `app.js:589` shows **"Source folders"** whenever `row.source_directory_count !== 1`, and **"Open folder"** otherwise.
  - Only the inspect payload sets `source_directory_count` (`merge_service.py:4350`); list rows never carry it. So `undefined !== 1` is always true and **every candidate row gets "Source folders"**.
  - "Source folders" calls `viewMetadata(row, true)`, which reads all metadata, scrolls to the details panel and expands the folder list. Sergei must then press a second "Open folder" there (`app.js:866`).
  - The direct "Open folder" branch is unreachable for candidate rows. That is the "no usable folder access" complaint.
- **Existing IPC.** None is needed in Electron.
  - The page calls `POST /api/open-folder` (`web_server.py:1037-1053`; it is a "looking" route, so it is not queued) → `MergeService.open_folder` (`merge_service.py:4353-4377`).
  - That resolves the candidate's folders through `_source_directories` (4267-4272: sorted parents of members, each with a uuid5 id), checks them inside `DirectoryBoundary(root, directory)`, and launches `explorer.exe <dir>` (`dispatch_folder`, 4379-4385).
  - With one folder no `directory_id` is needed; with several, `directory_id` picks one. "Output folder" uses the same route with `folder_kind='output'`.
  - Electron's `shell.showItemInFolder` is used only for the installer (`desktop/main.js:700`); `shell.openPath` is not used.
- **Fix (technical).**
  - Add `source_directories: [{id, path, present}]` to each candidate row payload. This is cheap: parents of members are already in the row.
  - Always render the direct action. One folder: one button. Several: one button per folder, or a small menu; layout per Judy.
  - Folders that are gone (completed books whose sources were cleaned, or the Abnett folder) return the existing "Folder unavailable…" message instead of an exception. Today `DirectoryBoundary` raises, and the page shows the error text.
  - Keep the action out of the busy queue (ruling 35: looking actions just work).
  - Ruling 70 (29 Oct) extends this: when the source folder is gone, the same button opens the converted file's folder instead. See § 7(d).
- **Tests:** extend `tests/test_web.py` (the row payload carries `source_directories`; open by id; a gone folder gives a clean message) and `tests/test_todo_frontend.js` (button present on Order unclear, Files unclear and ask rows).

---

## 6. Damage already done (found while verifying; nothing was changed)

- **Abnett «Первый и Единственный» was converted as 4 books.**
  - Jobs `84235548`, `279a5c15`, `f63e0a4e`, `0ac5c6f7` (approved automatically on 27 Oct, 10:51–10:54 UTC; completed on 28 Oct, 14:22–14:55 UTC) made `Z:\Audiobooks Sorted\Abnett Dan\01_ Часть Первая - Нубилийский Пролив - Abnett Dan.m4b` … `04_Часть Четвертая - Город Крация, Пирит - Abnett Dan.m4b`.
  - Their four sources were retired (`source_retirements` state `removed`). Their app recovery copies are no longer under `data/source-recovery/`.
  - At 14:59 UTC on 28 Oct the app left the folder in place ("retained_nonempty"), with parts 05–10 and `Cover.jpg` still inside.
  - **Today the folder is absent from Z: and from `Z:\@Recycle\Audiobooks\Unsorted`.** The catalog has no record of the app removing 05–10. Who removed them cannot be told from read-only data → **Q7**. The 05–07 and 08–10 rows will turn into missing-files rows on the next scan.
- **«Гробница Саргераса»** (`Unsorted\Warcraft\Гробница Саргераса`): 4 "Standalone source" files `ГробницаСаргераса1..4.mp3` were all completed as 4 separate books.
- **Story folders converted per story under the old grouping:** «Бойся Чужого» (9 completed, e.g. `Abnett Dan\The Gardens of Tycho - Abnett Dan.m4b`), Макнилл «Рассказы» (4), WH40K сборник (1).
- **«Тень и Коготь»** went into the Cyrillic folder `Sorted\Джин Вулф\` (3d). Rulings 21/48 already cover this: the rename pass, later.

These are completed books in Sorted with their sources gone. Under ruling 68 they must not be silently changed → **Q3**.

---

## 7. Destination override (69/70)

Ruling 69: Sergei can choose the destination folder on any row, through the Windows folder picker. The choice overrides the computed destination. On a finished book the app moves the file, and a destination change alone never reconverts.

Ruling 70: "Open the source folder" opens Explorer. If the sources are gone, it opens the folder that holds the converted file, which is then the book's current source.

The evidence image (`Docs/BugEvidence/2026-10-29-destination-override/sparse-info-rows.webp`) shows rows with title clue «Mp3», author Unknown and transliterated folder titles, each going to `Sorted\Без автора\<folder name>.m4b`.

### (a) Where the computed destination lives, and where an override goes

**The computed destination is never stored as a folder choice. It is recomputed at each stage:**

1. **Before approval: computed on every render.** `groups.render` → `metadata.propose` (metadata.py:177-197) → `organization.plan` (organization.py:14-63). The inputs are the review's title, author/canonical_author, series, number, universe, anthology and multi_author, plus `metadata_facts` for the recording suffix (66-75). That review is assembled from:
   - the automatic verdict (`automatic_candidates.result.review`);
   - Sergei's entered names (`names_entries`, `entered_names.effective`);
   - a saved review (`book_groups.review`).

   The planner's branch order decides the folder:
   - `Без автора\<Title>.m4b` (27-31);
   - `Сборники\<Series>\…` for numbered collections (33-44);
   - otherwise `<Universe>\<Series>\` or `<Author>\<Series>\` or `Сборники\` or `<Author>\` (45-60).

   The Approve-time copy is `_approval_destination` (merge_service.py:2580-2591), and Approve refuses if the destination changed after it was shown (3073-3076).
2. **At approval: frozen into the job.** `audio_jobs.manifest` gets `destination`, `output_root` and `metadata`. They are hashed into `manifest_hash`, which source-cleanup intents and relocation bindings pin.
3. **At job start: re-derived.** `destination_admission.observe` (destination_admission.py:16-24) recomputes `frozen_plan(manifest, output_root, metadata)` (organization.py:78-91). If the result differs from `manifest['destination']`, the job is held as "Queued destination needs review".
4. **After publication: recorded.** The receipt is `audio_jobs.output` (`final_path`, `sha256`, `size`, `root`, `parent_identity`, `validation`). Alongside it sit `owned_artifacts(kind='output')` and `verified_outputs`. The **effective** location is resolved through `publication_locations.resolve` (626-664) from `output_relocations`/`migration_events`. Measured on the catalog copy:
   - 624 completed jobs, all with outputs on Z:;
   - **432 relocations, all at stage `complete`**: the 0.20.x offline migration into Sorted. Their receipts still point at the old library path, which is why 433 receipts lie outside `Z:\Audiobooks Sorted`;
   - 87 series-backfill renames, which instead rewrote the receipt in place (series_backfill.py:597-650).

**Where the override lives (proposal):**
- **Before conversion:** a per-book "Entered by you" value. Either a new `names_entries` field `destination_folder` (kind `book`, keyed by `book_key` like the other names, with the same press, retraction and "Entered by you" display), or a small `destination_overrides` table on the same key. It records:
  - the absolute folder;
  - its native identity (volume + file id via `DirectoryBoundary`), so a later rename or replacement of that folder fails closed;
  - the time and the press.
- **Frozen at approval** into the manifest as `destination_override: {folder, identity}`.
- **Outranks everything.** `organization.plan` takes the override first. When it is present, the destination is `<chosen folder>\<computed file name>`, and none of the `Без автора`, `Сборники`, universe/series or author folder branches apply.

  The file name stays the planner's (`Title - Author`, the series pattern, or `<Title>` for Без автора, plus any recording suffix). The 240-character limit still applies. Whether the file name is also overridable → **Q9**.

  Every caller uses the same function — preview/Goes to, `routing_preview`, `_approval_destination`, `frozen_plan` and `destination_admission.observe` — so an override is never flagged as "destination needs review".
- **After conversion:** the override is keyed by the publication (job id + receipt), not by member paths. Sources may be gone, and under ruling 68 member sets can change.

### (b) Folder picker and Explorer open

- **What exists.**
  - The Electron shell already uses `dialog.showOpenDialog(setupWindow, {properties: ['openDirectory', 'createDirectory']})`, but only for the setup window's data folder (`books:browse`, desktop/main.js:734; the sender is checked by `trustedSender`, 597-602).
  - The app window's preload bridge (`window.booksDesktop`, desktop/preload.js) has no folder picker.
  - Electron's `shell` is used only for `showItemInFolder(installer)` (main.js:700) and `openExternal`.
  - Explorer is already opened by the **Python backend**: `/api/open-folder` → `MergeService.open_folder` → `dispatch_folder` runs `explorer.exe <dir>` after `DirectoryBoundary(root, dir)` (merge_service.py:4353-4385).
- **Picker (proposal).**
  - New IPC `books:choose-folder`, accepted only from the `app` sender. It calls `dialog.showOpenDialog(state.win, {title, defaultPath: <current computed folder>, properties: ['openDirectory', 'createDirectory', 'dontAddToRecent']})` and returns the chosen path or `null`.
  - Parenting the dialog to the app window keeps it modal to that window. It is user-initiated, so taking focus is acceptable at runtime. It cannot be exercised while Sergei is at the machine.
  - The renderer forwards the path to a new backend route, e.g. `POST /api/candidate/destination {library, id, revision, folder}`. Ruling 35 applies: it queues if busy.
  - **The backend is the only validator.** It checks that:
    - the path is absolute, ordinary and not a reparse point (`DirectoryBoundary(anchor, folder)` gives an identity);
    - it **exists and is a directory**;
    - it is **writable**, proven by creating and removing a uniquely named zero-byte probe through the boundary (user-initiated at runtime; tests use a seam);
    - it is **not inside any source root**, so the output never becomes a new source book (the same overlap rule as `source_config.sorted_problem`);
    - it is not inside the app's data folder;
    - the folder plus the planned file name stay within 240 characters.

    The result also says whether the folder is inside `Z:\Audiobooks Sorted` and whether it is on the same volume as the current output.
  - The web-only build (`launch-web`) has no `booksDesktop`, so it gets no picker. That is acceptable; Judy decides whether to hide the control there.
- **Explorer open (ruling 70).** Prefer the existing backend route over a new `shell.openPath` IPC. It already resolves the folder **from the book id** (never from a renderer-supplied path), proves it inside its root, and works in both builds. If `shell.openPath` is used instead, main.js must ask the backend for the resolved folder by book id and pass only that. Both are user-initiated focus changes and are mocked in tests.

### (c) Moving a finished book

- **What a move must update.** The existing in-app precedent, series backfill, shows the set: `audio_jobs.output` (`final_path`, `sha256`, `size`, `parent_identity`) and `manifest.destination`, plus `verified_outputs`, `owned_artifacts(kind='output')`, `book_groups.review`, `candidate_context` and the in-memory caches (`merge._validated_outputs`, `invalidate_status`). For relocated books, the authoritative record is instead a new `output_relocations` generation with its `migration_events` history.
- **Existing machinery:**
  - `output_rename.RenameWorker` (output_rename.py:21-217): same-volume native rename with no replace (`rename_no_replace`). It journals `rename_intent → renamed → location_committed → complete`, refuses cross-volume moves (line 75, `cross_volume_move`, no copy fallback) and collisions (line 103), and has fully specified restart recovery (122-139).
  - `output_migration.MigrationWorker`: the cross-volume path. It copies to a temporary file, verifies it (full SHA-256 plus an injected media verifier), publishes with `publish_no_replace`, commits the location, then either removes the old file under a removal intent or **retains** it (`copied_verified_original_retained`).
  - Both have `fault=` hooks at every boundary.
- **Why they can't simply be called from the app today:**
  1. They require an **offline drained catalog owner** lease (`drained: True`, a native owner proof; migration_operation.py:182).
  2. `require_no_pending_moves` (publication_locations.py:598-624) **refuses app startup** while a move awaits recovery ("Finish the reviewed offline move before opening Books Arranger").
  3. **One relocation per book.** `output_relocations.publication_id` is the primary key, and `plan()` refuses "A different relocation already exists" (255-291). A second move is impossible, and that includes **any** move of the 432 books already relocated.
  4. Series backfill reads `output['final_path']` directly (series_backfill.py:383) and rewrites the receipt. It is not aware of relocations, so a backfill after a ruling-69 move would act on a stale path; it fails closed as "held".
- **Proposal:**
  - Extend the relocation protocol to **chained generations**: one row per move with a predecessor pointer; `resolve` follows the chain.
  - Give it an **in-engine lease**: an exclusive per-book lease, no conversion of that book running, catalog commits in a writer transaction, inside `critical_sections` like ruling 27's "finish once begun".
  - Replace the startup refusal with **in-engine reconciliation** that uses the workers' existing recovery rules.
  - Strategy:
    - **Same volume** (same native volume id; a rename within one SMB share is a single server-side operation): no-replace native rename of the exact held file.
    - **Cross volume**: copy, flush, full hash plus media check, no-replace publish, location commit, then exact-handle disposal of the old file. The old file is removed only after the new one is verified **and** recorded; any doubt retains both and explains on the row.
  - **Collisions:** never overwrite; same-name existence is checked case-insensitively and normalised. The row holds with "A file with this name already exists in that folder" and the options Choose another folder or Cancel. Moving to the current folder is a no-op.
  - **Ownership:** the move belongs to the completed job (no new job and no change to the conversion's `manifest_hash`). History is the append-only `migration_events`. Consumers already go through `resolve` (Delete book, Remove this copy, chapter repair, replacements; covered by `test_publication_consumers`/`test_relocated_*`). Series backfill must be made relocation-aware or skip moved books.
  - **Never reconvert:** a destination change on a finished book only plans a relocation. It creates no `audio_jobs` row, makes no `create_private`/encoder call and leaves no source-cleanup intent.
  - **Pending (not started) job:** no conversion has happened yet, so the override is a manifest change. Re-approve the job with the override frozen into it; `destination_admission` honours it. **Running job:** the change queues and applies as a move after completion (ruling 35).
- **Sources and ruling 2.**
  - Source deletion requires the effective output to be inside the configured output root (`source_config.require_sorted`, 55-65; `source_cleanup._sorted`, 183-190). Publishing outside it already runs the copy flow and keeps the sources (merge_service.py:4055-4056).
  - So a chosen folder outside `Z:\Audiobooks Sorted` means the sources are **kept**, unless Sergei rules otherwise → **Q8**.
  - Moving the last book out of a Sorted folder leaves it empty, and ruling 24a lets only Delete book and Remove this copy remove empty folders → **Q10**.

### (d) Ruling 70 — knowing the source folder is gone, and finding the converted file

- **Catalog signals.**
  - `files.missing=1` is set by a scan (`scanner.gone`, scanner.py:106-122), so it is stale between scans. Abnett's 05–10 still read `missing=0` today although the folder is gone.
  - `source_retirements(state='removed')` and `cleanup_members` record sources the app removed after conversion.
  - `source_folder_cleanup_directories` (`removed` or `retained_nonempty`) records what happened to the folder.
- **The live check decides.** At the click, `DirectoryBoundary(root, folder)` either proves the folder or raises. The catalog only supplies the wording, e.g. "removed by the app after conversion on <date>" versus "not found".
- **The converted file's current folder.** For the book's completed job, `self.publications.describe(jobs, id)` (`CurrentAudiobooks`) returns the **effective** path, which follows relocations and future ruling-69 moves; its parent is the folder to open. This is exactly `open_folder(folder_kind='output')` (merge_service.py:4364-4373), which requires state `verified`. If the state is `verifying`/`unavailable`, the row says the converted book is not where the app recorded it. It never searches by file name.
- **Edge cases:**
  - **Several source folders, some gone:** each existing folder opens; the gone ones collapse into one "converted book" entry.
  - **Never converted and sources gone** (Abnett 05–10): nothing to open, so the row says so and the ruling-10/23 missing-files options apply.
  - **Folder exists but the app removed some files** (`retained_nonempty`): the source folder opens.
- **Making the converted file the book's source** (ruling 70) needs no new record. The row's folder action resolves to the effective output, and a ruling-69 override on that row is a relocation (c).

### (e) Test plan (no real dialogs, Explorer launches or focus changes)

- **Seams.**
  - The picker lives in a small module (`desktop/folder-picker.js`, `choose({dialog, win, defaultPath})`). `main.js` injects the real `dialog`; tests inject a fake.
  - The backend validator takes injected filesystem probes (`exists`, `is_dir`, `probe_writable`).
  - `dispatch_folder` (already mocked in tests) and any `shell.openPath` are injected.
  - The move workers keep their `fault=` hooks and gain an injectable volume-identity seam, so cross-volume behaviour can be tested on a single-volume machine.
- **New `tests/desktop-folder-picker.test.mjs`:** cancel returns `null`; a pick returns the path; `defaultPath` is passed through; a non-`app` sender is refused; the IPC returns nothing else.
- **New `tests/test_destination_override.py`:**
  - Validation: missing folder, file instead of folder, not writable (seam), inside a source root, inside the data folder, over 240 characters, reparse point.
  - Planner precedence: the override beats `Без автора`, `Сборники`, universe/series and author folders. Preview, Goes to, Approve, `frozen_plan` and `destination_admission.observe` all agree, so there is no "destination needs review".
  - The override survives a revision change; retracting it restores the computed path; it is frozen at approval.
- **Extend `tests/test_publication_locations.py`, `tests/test_output_rename.py` and `tests/test_output_migration.py`:**
  - Chained second and third moves; a move of an already 0.20-relocated book.
  - An in-engine lease instead of the offline owner.
  - A no-replace collision.
  - A fault at every journal boundary, then a restart that reconciles in-engine (no startup refusal).
  - Cross-volume copy plus verify, with the old file retained when unprovable.
  - **Never reconvert:** after a destination-only change the `audio_jobs` row count and states are unchanged and `create_private` is never called.
- **Extend `tests/test_publication_consumers.py` and `tests/test_series_backfill.py`:** Delete book, Remove this copy and chapter repair after a ruling-69 move; series backfill skips or follows a moved book.
- **Extend `tests/test_web.py`:**
  - The ruling-70 fallback: source folder missing → output folder opened (mocked); several folders with some gone; never converted and gone → message.
  - Row payloads carry `source_directories`.
- **One packaged smoke of the real picker and Explorer** needs an away window stated by Sergei (ProcessRules § Sergei is not QA, real-input checks). Everything else runs headless.

---

## 8. Batch estimate

| Fix | Size | Files |
|---|---|---|
| F1 Folder as the unit + partly-bound hold + source_gate + whole-folder explanations | Large: changes the grouping model and regroups once | `source_identity.py`, `groups.py`, `todo_causes.py`, `web/app.js` (copy) |
| F2 Mojibake read-side repair | Small | new `tag_text.py`, call sites in `source_identity.py`, `groups.py`, `local_identity.py` |
| F3 Identity: narrator title, initials prefix, quoted title, «джин» + unknown-name lookup, Approve guard, role labels, `RESEARCH_VERSION` bump | Medium | `local_identity.py`, `public_research.py`, `merge_service.py`, `groups.py` |
| F4 Order and missing reasons (§ 4) | Medium, plus Judy copy | `todo_causes.py`, `source_identity.py`, `web/app.js` |
| F5 Open source folder + ruling-70 fallback to the converted file's folder | Small, plus Judy layout | `merge_service.py`/row payload, `web/app.js` |
| F6 Ruling 69 before conversion: picker IPC, backend validation, override precedence in the planner and admission, re-approve pending jobs | Medium, plus Judy layout | `desktop/main.js`, `desktop/preload.js`, new `desktop/folder-picker.js`, `organization.py`, `destination_admission.py`, `entered_names.py`, `merge_service.py`, `web/app.js` |
| F7 Ruling 69 after conversion: in-app, repeatable, self-recovering move (chained relocations, in-engine lease and recovery, cross-volume copy+verify, series-backfill awareness) | Large: extends the relocation protocol into the running app | `publication_locations.py`, `output_rename.py`, `output_migration.py`, `merge_service.py`, `series_backfill.py`, startup fence |

**One batch, one rebuild for F1–F6: yes**, on two conditions: Sergei answers Q1–Q5 and Q8–Q9 before implementation starts, and Judy's specs (F4 copy, F5/F6 layout, F3e labels) arrive together.

**F7** is the risky part: it moves finished books, on Z:, whose sources are usually already deleted. It should be its own batch and rebuild, right after F1–F6, so its recovery paths get a dedicated review and QA. If Sergei wants everything in one release, it fits only as a single larger 0.24.0 with one longer QA pass.

- **Version.** F1 changes how books are formed across 18 MP3 folders now, and up to 162 depending on Q1. Per ProcessRules § Escalate rewrites it belongs in a **minor version (0.24.0)**, not a patch.
- **Test time.** The entry suite's slowest worker was 484.8 s of its 540 s limit (0.23.0, 13 workers). Adding about 6 test modules may need the worker plan revisited, and capacity changes need Sergei's approval (ruling 66).
- **One-time cost after install:**
  - one regroup of each root;
  - re-research of about 350 Held/Waiting verdicts at the current version, plus every new folder-unit group;
  - about 30 English-name lookups (bounded by the existing per-site budgets).

---

## Questions for Sergei

1. Should "never divide one folder" also apply to folders where **each file is already a whole book**? Examples: `Stephen King\` (56 `.m4b`), `Сборники\Глубина` (49 volumes), the `Z:\Audiobooks` root, `Unsorted\Warcraft` (two novels by different authors). There are 144 such folders. **Yes / No**
2. A folder holding a **whole series of separately tagged novels** (`Хроники Нарнии`, 7 novels; `Космическая трилогия`, 3): **One book / One per novel**?
3. Books **already converted** from part of one folder (Abnett «Первый и Единственный» ×4, «Гробница Саргераса» ×4, «Бойся Чужого» ×9, Макнилл ×4): **Leave as is / Put on my list**?
4. **Unfinished jobs** that convert part of one folder (26 jobs in 7 folders: Брукс, «Бойся Чужого», WH40K сборник, Кинг «Рассказы», Wolfe «Меч ликтора», Страуд ×2): **Regroup the whole folder / Run as queued**?
5. Wolfe «Книга Нового Солнца»: should the three volumes be numbered **1, 2, 3 as the Russian edition does**, or by the novels inside (1–2, 3–4, 5)? **Edition / Novels**
6. About 15 unfinished jobs still carry a foreign author in Cyrillic (e.g. Скальци Джон, Судзуки Кодзи, Вестерфельд Скотт, Джин Вулф). Re-check the author before they run (ruling 59), or let them file now and fix it in the rename pass (ruling 48)? **Re-check / Run**
7. Did **you** remove the «Первый и Единственный» folder (parts 5–10) from Z: after 28 Oct, 14:59 UTC? **Yes / No**
8. May the folder you choose be **outside `Audiobooks Sorted`**? If it is, the source files are kept (ruling 2). **Yes / No**
9. Should the chosen folder replace **only the folder**, with the file name still built from Title/Author, or **the file name too**? **Folder only / Folder and name**
10. After a finished book is moved away, should the app **remove its old Sorted folder if it is left empty**? **Yes / No**
