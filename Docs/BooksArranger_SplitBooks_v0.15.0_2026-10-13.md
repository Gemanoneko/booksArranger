# Books Arranger v0.15.0 candidate — split books handoff (Futaba / Senua)

Ender, 2026-10-13. Worktree `scratch/split-books-2026-10-13/worktree`, branch `codex/books-split-books-0.15.0`, from main `2072cf1` (v0.14.0). All changes are uncommitted; Sully commits. EXTEND, not a rewrite: the source-scope, order, hashed-membership, admission, media verification, publication, retirement and 24-hour recovery machinery is reused unchanged except where named below.

## What changed

| Area | Change | Files |
| --- | --- | --- |
| Split-book grouping | New pure module. Among single-file candidates (one M4B, or a lone MP3) of one folder, or of one book's CD/part folders, files with the same book title (album; without albums, the title tag or file name minus the part number) become one candidate when every check passes: same author/artist/composer/narrator/reader/language/series tags and readers named in comments; one container and one audio profile (codec, rate, channels); every part is only a number, a chapter/part/CD marker (with or without a chapter name), front/back matter or "unknown title"; positions from embedded track numbers, else part numbers in the file names, else disc folders, with no gaps, no duplicates, start at 0/1, discs 1..n, declared totals equal to the files found, tag and name orders agreeing; no other catalogued file with that title in the same place. Anything else holds: the files stay separate and the v0.14.0 split guard keeps holding them | `split_books.py` (new) |
| Grouping integration | `build()` plans split books once per sync (members/partitions computed once), gives each a `Split book` scope with `split_book` evidence (parts, order basis, shared book name) and proven positions as `disc`/`track`; existing multi-file groups and reviewed/approved/job scopes are never regrouped; a reviewed split book whose parts no longer prove one book is held with every member visible (`source_partition_uncertain`). Algorithm version `public-auto-v1+split-books-v1` re-syncs each root once | `groups.py` |
| Source gate | For a split row the parts are re-proven from the current row (`split_books.check`, media check off because rendered rows carry no probe); a failure is "Source membership uncertain", recorded positions that differ from the proof are "Playback order uncertain"; the per-file "Author - Title - NN - chapter" name is compared through the shared book name; proven positions replace the embedded-track-tag requirement. All other gate checks unchanged | `source_identity.py` |
| Local identity | A split row offers the shared start of its part names ("Dan Brown - The Lost Symbol") as its file-name evidence; research candidates use it too (155 chapter names are not 155 titles) | `local_identity.py`, `public_research.py` |
| Media (joining M4B parts) | The v4 pipeline used to refuse every multi-M4B job. Now it joins them with the existing v4 normalizer (decode each complete part, re-encode once at the parts' bitrate/rate/channels, one chapter per part) and refuses only a job where an M4B part carries its own chapters (checked on the protected snapshot). Admission also holds that case early, and holds split parts whose freshly probed profiles differ. Validation, publication, retirement, recovery unchanged | `audio_pipeline.py`, `merge_service.py` |
| Confirmed spellings | Library-wide list of author spellings that the app cited with a fetched source URL (research results that built a policy, saved reviews, job manifests; read-only SQL, cached by table counts/timestamps). Within the script chosen by ruling 3, a confirmed spelling of the same person (name rules, or a one-letter slip of a local spelling in a 6+ letter word) wins over the local majority; the evidence cites the catalog URL. No confirmation: unchanged | `local_identity.py`, `public_research.py` |
| Middle initial | `middle_initial_same`: "Dick Philip K." = "Дик Филип Киндред" when first name and surname are full on both sides, the only difference is a middle initial vs a middle name, and no library spelling of that person has a different middle name or initial. R2-2 unchanged: an initial never stands for a first name | `local_identity.py` |
| Ruling 1, Булдаков | `RULED_NARRATORS = ('Олег Булдаков',)`: under a collection folder, his exact plain credit, when the library also credits him as a reader, is a reader credit, so ruling 1 files the book under `Сборники`. R3-1 (a folder naming the reader) and R2-1 (any other person credit) still hold | `local_identity.py` |
| Sibling guard | A trailing four-digit number is a year or part of the title, never a part number ("Метро 2033" beside "Метро 2034") | `local_identity.py` |
| Automatic run | A resumed run (and each pass before it waits) adds every current candidate it has not seen, so new split books are researched without a new discovery pass; superseded ids drop out where they come up | `automatic_processing.py` |
| Versions | `AGREEMENT_VERSION` local-agree-v4 (v3 records still validate: approved and completed books), `RESEARCH_VERSION` standing-19-v1 (one fresh pass for waiting/held books), VERSION 0.15.0 | `local_identity.py`, `standing_metadata.py`, `public_research.py` |

### M4B media decision

Joining AAC M4B parts without re-encoding is not safely supported today: each part has its own encoder delay and edit list, so a stream-copy concatenation cannot be verified sample-exact at the part boundaries, and the v4 copy path proves exactly one source. The safe path chosen is the existing v4 normalizer, already used and verified for multi-file books: each complete part is decoded under protection, joined and re-encoded once at the highest source bitrate with the parts' own sample rate and channels (the split check already requires one profile). This is a lossy generation, bitrate-matched to the source. Every existing check still runs: decoded sample count, duration, tags, one cover, chapter titles and boundaries, packet-level publication and retirement. A part that already has its own chapters is held: joining it would keep only one chapter per part (product question below). Staging needs uncompressed space for the whole book (existing normalizer behaviour).

## Measurement (offline, one copy of the live catalog)

Copy: sqlite backup API, source opened `mode=ro`, one step, 1 attempt, 1.5 s, `quick_check` ok, 2026-10-13 10:54:43 UTC, with the app running (v0.14.0, PID 8424, WAL mode). Copy sha256 `b16c048a…7256301`, unchanged after every run. Every measurement copies it to a disposable working file, syncs the grouping of the code under test there, then looks up every waiting/held candidate (plus every new split book) with all public sources closed. No network, no Z:/Y: reads.

| | Before (v0.14.0, `2072cf1`) | After (this candidate) |
| --- | --- | --- |
| Candidates checked | 2,416 waiting/held | 1,649 (1,476 + 173 new split books) |
| **Approvable without the Internet** | **445** | **528** (+81 split books, +2 single books) |
| Identity agrees locally | 479 | 562 |
| Held single part files (v0.14.0 split guard) | 1,299 (+16 multi-file MP3 groups, untouched by design) | 935 grouped into 173 books: **707 files in 81 approvable books**, 228 files in 92 books that need research; 1 file approvable alone; 363 still held |
| Full regroup (`groups.build`, 9,516 files) | 2.7 s | 3.0-3.3 s (full sync with writes 6.8 s vs 6.9 s) |

Largest approvable books: The Lost Symbol (155 chapter files), Deception Point (135), Digital Fortress (129), Inferno (108). The 92 research-path books are held by v0.14.0 identity rules, not by grouping: 58 have the author in only one local source (the folders name a series, e.g. "Battletech"), 13 Wheel of Time books have a series-style folder ("Колесо времени - 01. Око мира") read as an author credit, the rest are collections or title conflicts.

Why the 363 stay held: 343 files form 66 same-title clusters that fail a check (first failing check counted): parts with their own story or book titles 33 clusters / 127 files (Зелёная миля's six named parts, Elric saga, Тобол's two novels); disc tags that disagree with the files found 16 / 35, mostly "disc 2/3" on every part, a series number misused as a disc (Robin Hobb, Honorverse, Expanse 6-7); mixed authors, readers or recordings 8 / 136 (Калейдоскоп, King's "Ночные кошмары" stories, Sword Art Online, Pratchett's "Пастушья корона"); volume or season numbers 4 / 18 (Toradora "Том 1-10", Black Star "Season N"); gaps, duplicates or totals 3 / 8; a same-title file already a separate candidate 2 / 19. The other 20 files have no same-title partner among the single-file candidates.

Other approval changes (all reviewed): 7 Pratchett books `Pratchet Terry` → `Pratchett Terry` (Open Library confirms "Terry Pratchett" on 3 other Pratchett books); 2 Dick books `Дик Филип Киндред` → `Dick Philip K.`; Булдаков "Тёмные Аллеи в Кино" now filed under `Сборники` as "Разные авторы", narrator Олег Булдаков; "Фантастика 2021 (без муз. сопр.)" no longer held as a part of "Фантастика 2018". Zahn is unchanged ("Zahn Thimoty" ×3): no fetched evidence for Zahn exists in the catalog, so current behaviour is kept, as briefed.

### Wrong-grouping scan

An independent script (not importing `split_books`) re-reads raw tags and stream profiles of all 173 grouped books from the copy: mixed author/artist/album_artist tags 0, mixed composer/narrator tags 0, mixed readers in comments 0, mixed album tags 0, mixed container or audio profile 0, gap or duplicate in the recorded order 0, same size and duration twice 0, volume/book marker differing between parts 0, parts spread over several folders 0. **Positive control:** the same scan over six deliberately wrong groups built from real catalog paths (Toradora volumes, Калейдоскоп 4 mixed authors, a Dan Brown gap, Pratchett's mixed profiles, one file twice, Куджо + Чужак) flags all six (seven checks fire; the readers-in-comments and several-folders checks have no planted case). 20-book sample with chips: `Docs/BooksArranger_SplitBooksSample_2026-10-13.md`.

## Tests

New `tests/test_split_books.py` (38 tests, real names): Dan Brown chapter set and Deception Point chapter titles grouped and locally agreed; Чужак/Куджо part sets side by side in one author folder; CD1/CD2 folders (one file per disc, and tracks per disc); part numbers in names without track tags; Roman "Часть I/II"; untouched candidates keep their scopes. Holds: gap, missing first part, duplicate part, declared total, mixed narrators (comments and composer), mixed authors, mixed recordings, Toradora volumes, Elric separate works, tag/name order disagreement, a protected same-title sibling. A reviewed split book stays stable and fails closed when a part changes; the gate re-derives positions. Real ffmpeg: two M4B parts through `approve_automatic` to one verified M4B with two chapters, sources retired, 24-hour recovery retained; parts with their own chapters held at admission and refused by the pipeline; parts whose profiles differ at admission held. Spelling: confirmed spelling wins, unchanged without confirmation (Zahn), unusable evidence ignored, ruling-3 script kept, Dick unified, R2-2 negatives, slip rule narrow. Булдаков routed; not without a reader credit, outside collections, with a reader-named folder, for an unlisted reader, or beside a real author. Year numbers; v3 records validate; resumed runs add new candidates.

Full suite: `python -m unittest discover -s tests -p "test_*.py"` (timeout 600000). Baseline is pristine `2072cf1` exported to a path of identical length (100 characters). See the suite table below.

| Run | Tests | Errors | Failure set |
| --- | --- | --- | --- |
| Baseline, pristine `2072cf1` at the same path length | 549 | 9 | the known 9 (missing untracked fixtures, `baseline_native_io.py`, `BrowserServer.loaded_version`, path length; identical to the v0.14.0 record) |
| Candidate run 1 (code still changing during the run) | 587 | 11 + 1 failure | baseline 9 + two stub inventories without a candidate listing broke the new run reconciliation (fixed: it adds nothing without a listing) + the known `test_web` tearDown `WinError 32` lock flake |
| **Candidate final (frozen code, nothing else running)** | **587** | **9** | **identical to the baseline** |

## Risks — where to look hardest (Senua)

1. **`audio_pipeline.snapshot_manifest` guard change.** The blanket multi-M4B refusal became a per-snapshot "own chapters" refusal; the normalizer then joins M4B parts. Check that no multi-M4B path can reach the copy mode or skip chapter/sample validation.
2. **`split_books.label`.** The line between a chapter ("Часть 1. ТЕНЬ ПРОШЛОГО", "01. Глава 1. Там где ветер", "Пролог") and a separate work ("01. Повелитель Хаоса") or volume ("Том 3"). A false 'part' groups separate books into one M4B and retires them. The shared-prefix cut (`_common_prefix`) moves part and volume words into each label on purpose.
3. **`source_gate` split branch.** Proven positions replace the embedded-track requirement (`use_filenames` true) and per-file names are compared through the shared book name. Verify it can only loosen anything for rows whose current members re-prove one book.
4. **Confirmed spellings.** `confirmed_spellings` trusts any 'authors' evidence with an https source URL in the app's own records; `slip_same` adopts a confirmed spelling one letter away from a local one. Risk: two real people one letter apart with the same first name (guarded by 6+ letters, same first letter, all other words identical).
5. **`middle_initial_same` vs R2-2**, and **`RULED_NARRATORS` vs R2-1/R3-1**: both are narrow exceptions; tests carry the R2-2/R3-1 negatives.
6. **Sibling guard relaxation** for four-digit numbers (weakens the C3 guard only for year-like numbers).
7. **Run reconciliation** in `automatic_processing`: `candidates()` syncs under the group lock on resume and once per pass.

## How to test (Futaba)

1. Full suite as above; compare the failure set with the 9-error baseline.
2. Focused: `python -m unittest discover -s tests -p "test_split_books.py"` (38 tests; 5 use real ffmpeg).
3. Offline measurement: scripts and outputs in the scratchpad `split-books` folder (`scripts/measure_split.py <code dir> <copy> <work dir> <out.json>`, `scripts/wrong_grouping_scan.py`, `scripts/scan_control.py`, `scripts/split_accounting.py`). Expect 445 → 528 approvable, 173 split books, scan all zero, control six of six.
4. Spot-check the 20 sample rows against the copy.
5. After release and Sergei's normal Restart + Start: the resumed run should add the new split books; watch that a split book's admission produces one M4B with one chapter per part, its parts retire, and M4B parts with their own chapters stay held with "Book parts carry their own chapters".

## Product question for Sergei

M4B parts that already have their own chapters are held (joining them keeps only one chapter per part). Join them anyway, one chapter per part? (yes / hold)
