# Books Arranger v0.14.0 QA — 2026-10-13

Author: Futaba. Candidate: branch `codex/books-fast-identity-0.14.0`, exact commit `67e3d43cc123a5f33d99a15e6f8778ce85509f72` (the worktree HEAD, and the local remote-tracking ref `origin/codex/books-fast-identity-0.14.0`, agree; I made no network call, so "pushed" is read from that ref and was not re-fetched). Base: tag `v0.13.1` = `8d325bd9a3514ff21b8daa7a4df6bd57aec5146f`.

Offline only, as briefed: no running app, no port 5210, no live database, no Z:/Y:, no external network. The tests start their own servers on ephemeral ports. All evidence below is from my own clones (cloned from the local repository, no GitHub) and my own copy of Ender's catalog copy (sha256 `06fa82d7f039e2294b60470b98245a81ae84913d998f47dc750d01c14799a6d0`, identical to his file; his copy was never edited). No commit, no stash, nothing fixed. Environment: Windows 11, Python 3.14.8, SQLite 3.50.4.

**Summary: NO-GO for v0.14.0 at 67e3d43.** The release is not safe to turn loose on the first automatic pass. The offline run approves 403 books and I reproduced that number exactly, but within those 403 I found **13 approvals whose author is a narrator or compiler, not the author of the work** (6 certain, 7 probable). One of the three required positive controls also fails: "Stephen King" and "Стивен Хокинг" (Hawking) are treated as the same person. The suite shows no new failure, the split-part books stay held, and the diff touches no media, publication, retirement or recovery code. The machine-readable verdict line is the last line of this file.

## Result per check

| # | Check | Result |
|---|---|---|
| 1 | Full suite on 67e3d43 vs v0.13.1, same path depth | PASS, no new failure (two depths measured, details in section 1) |
| 2 | Hunt for false matches on a copy of the catalog copy | FAIL. 0 of 40 random approvals definitely false (2 weak, 1 typo); exhaustive scan of all 403 found 13 suspected false approvals (6 certain). 1,309 split-part books stay held: PASS |
| 3 | Positive controls | FAIL on one family (Latin vs Cyrillic of a different name: Hawking/King). Folder-vs-tag author, same author with another title, and the "Rollins James" / "Джеймс Роллинс" agreement all behave |
| 4 | Ender's 30-book sample doc | PASS for accuracy (regenerates exactly from my own measurement); readability notes in section 4 |
| 5 | `git diff --stat v0.13.1 67e3d43` | PASS, no media / publication / retirement / recovery code changed |

## 1. Full suite

`python -m unittest discover -s tests -p "test_*.py"`, timeout 600000, run in two fresh clones per depth: `cand` at 67e3d43 and `base` at `v0.13.1`, same path length for both.

| Depth (chars) | Tree | Tests | Result |
|---|---|---|---|
| 44 (short, Ender's class) | 67e3d43 | 515 | 9 errors, 0 failures. **Identical name-for-name to Ender's own baseline set of 9.** |
| 44 | v0.13.1 | 490 | 1 failure + 10 errors = 11. These are the same 9 plus two flakes (below) |
| 150 (my scratchpad, deep) | 67e3d43 | 515 | 2 failures + 19 errors = 21 |
| 150 | v0.13.1 | 490 | 2 failures + 18 errors = 20 |

Candidate failure set is a subset of the baseline set at the short depth: **zero new failures**. At the deep depth the candidate has two names the baseline has not, and the baseline has one the candidate has not:
- `test_local_agreement_reaches_verified_ready_with_sources_retired_and_recovery_retained` (the new end-to-end admission test) errors at the deep depth with `ValueError: Verified metadata exceeds the supported Windows output path length`. It is deterministic at depth 150 (2 of 2 reruns) and **passes at depth 44**. It is the same path-length cause already recorded in the v0.13.1 report; it needs a clone path under roughly 100 characters.
- `test_recovery_native_guard_spans_old_close_absence_and_removed_cas` errored once (WinError 32, file in use). Passes 3 of 3 isolated, deep and short, on both trees.
- Baseline-only flakes: `test_enrolled_policy_without_retirement_is_preserved` (deep) and, at the short depth, `test_restart_guard_rejects_wrong_instance_busy_admission_and_active_research` (the tearDown `PermissionError` Ender also saw) and `test_waiting_source_retries_automatically_at_earliest_opportunity` (the known F4 timing flake). All four pass 3 of 3 isolated on **both** trees. The flake set changes from run to run and is not tied to 0.14.0.
- Focused: `python -m unittest discover -s tests -p "test_local_*.py"` at depth 44: 25 tests, OK (3 of them use real ffmpeg).

## 2. Hunt for false matches

### 2.1 Reproduction of Ender's measurement (independent)
Same `measure.py`, my copy of the catalog, my clones:
- v0.13.1 code: 2,426 waiting/held books, **0 approvable** (2,394 "Book identity uncertain", 32 "Mixed recordings").
- 67e3d43 code: 2,426, **403 approvable** (400 from "Waiting for source", 3 from "Held"), 461 accept locally, 58 of those held by existing gates (30 sources disagree, 16 playback order, 7 membership, 5 combinations). Record-by-record the approvable set and all reason lists are identical to Ender's `measure-after.json`.
- 345 of the 403 are single files, 58 are multi-file; 335 have a same-script author, 68 a cross-script one.
- Three of the 403 were "Mixed recordings" in v0.13.1 and are now approved because the local check runs before the mixed-group test. I looked at all three (a 3-file, a 32-file and a 20-file book, each one title and one author across every file): correct.

### 2.2 Random 40 approved books (seeded, my seed 14102026)
I judged each one on tags, file name and folder. **Definite false matches: 0 of 40.** Weak or flawed: 3 of 40.

| # | id | Author — title | Judgement |
|---|---|---|---|
| 1 | 70e5b098 | Хобб Робин — Сага о живых кораблях #3. Корабль судьбы | OK. Translator and reader (comment, album_artist) correctly not used as author |
| 2 | f224b139 | Александр Варго — Полночь | OK |
| 3 | 1418d2e0 | James Swallow — The Flight of the Eisenstein | OK |
| 4 | ec6be5c6 | Mitchel Scanlon — Descent of Angels | OK |
| 5 | fb04364a | Graham McNeill — Fulgrim | OK |
| 6 | 1109d940 | Максим Кабир — Самая страшная книга. Пиковая дама | OK |
| 7 | ab83f855 | Артур Конан Дойл — Сборник рассказов | **WEAK**: all sources agree, but "Collection of stories" does not identify which collection (finding F8) |
| 8 | 7ac2101a | Уна Харт — Когда запоют мертвецы (22 files) | OK. Reader in album_artist ignored |
| 9 | de3a2770 | Кабир Максим — Скелеты | OK work; author written surname-first unlike other Kabir books (F5) |
| 10 | a8a788d0 | Карлос Руис Сафон — Трилогия тумана | OK (omnibus; tag, file, folder agree) |
| 11 | f1ebc7b9 | Сергей Лукьяненко — Фальшивые Зеркала | OK |
| 12 | 3c6f3e36 | Терри Пратчетт — Лорды и леди (86 files) | OK |
| 13 | 7f5c29ef | Брендон Сандерсон — Архив Буресвета 1 - Путь королей | OK |
| 14 | ed0756c5 | Кэмпбелл Рэмси — Усмешка тьмы (52 files) | OK |
| 15 | d7958a17 | Алексей Атеев — Бешеный | OK |
| 16 | 7a339517 | Джастин Хилл — Карантин зараженного блока | OK (one story per file inside a story-collection folder) |
| 17 | afc34506 | Dean Koontz — Whispers | OK |
| 18 | fd39a2c5 | Stephen King — A Face in the Crowd | OK by local evidence; the real book is by King and a co-author, which the local sources do not say and offline cannot check |
| 19 | 9deb19fe | Дженнифер Макмахон — Молчание | OK |
| 20 | 990784b0 | Судзуки Кодзи — Звонок-0: Рождение | OK |
| 21 | 3fb98232 | МакКаммон Роберт — Они жаждут | OK |
| 22 | 389f11af | Райбер Влад — Попробуй уснуть (12 files) | OK |
| 23 | d0d44bca | Уна Харт — Хозяйка Шварцвальда (33 files) | OK |
| 24 | 6e315afb | Суэнвик Майкл — Дочь железного дракона | OK |
| 25 | e9a3cf3b | Симмонс Дэн — Песнь Кали | OK |
| 26 | 03640053 | Мэд Док — Нейт Кроули | OK |
| 27 | da60a1a7 | Иэн Сент-Мартин — Ангрон Раб Нуцерии (5 files) | OK |
| 28 | f03fb0e6 | Дэн Абнетт — Башня Молний | OK |
| 29 | a7f8acf0 | Джон Коннолли — Ночные легенды. Избранное | OK (a collection with a specific title) |
| 30 | 08d0f48f | Ярослав Гжендович — Гелий-3 (14 files) | OK. A second approvable 1-file book has the same title and author (`b7b591a5`); the unchanged duplicate gate decides |
| 31 | 4ec43be8 | Хокинг Стивен, Млодинов Леонард — Кратчайшая история времени | OK (two real co-authors, one credit string) |
| 32 | 40e544c8 | Michael Stackpole — Rogue Squadron 2 - Wedge's Gamble | OK |
| 33 | 0163bed7 | Иванов Алексей — ГЕограф глобус пропил | **FLAWED**: right book, but the tag's casing typo ("ГЕограф") becomes the title although the file name is clean (F7) |
| 34 | 538700b8 | Мусаниф Сергей — Система Дефрагментации-02. Возвышение Физрука | OK |
| 35 | b113bf7f | Дрю Карпишин — Возмездие | OK. File name "Mass Effect - Книга 3 - Возмездие" matched through the title segment; series left as a gap |
| 36 | 6922ca1b | Вонг Дэвид — В финале Джон умрёт (17 files) | OK |
| 37 | b5d8a27c | Кристиан Роберт Винд — Нечто из Блэк Вудс | OK |
| 38 | d73d11dd | Ярослав Гжендович — Владыка Ледяного Сада. 3. Носитель судьбы | OK |
| 39 | 72c07b8c | Анджей Сапковский — Сборник рассказов | **WEAK**: generic collection title, same as #7 (F8) |
| 40 | 9e269854 | Клайв Баркер — Лес на холме | OK |

None of the 13 suspected approvals in 2.4 fell into this random 40 (the chance of that was about one in four), so the random sample alone would have given a false all-clear. The exhaustive scan in 2.4 is what found them.

### 2.3 Random 20 held books, and the 1,309 split parts
- All 1,309 split-part books stay held: 1,309 rows carry the "other file(s) in the same folder carry this title" conflict, **0 of them approvable**, and 0 approvable rows lack local acceptance. The count matches Ender's. The biggest groups are 155, 135, 129 and 108 files (Dan Brown novels); 193 books have exactly one sibling.
- 20 held books (seed 14102026; drawn as 10 locally agreeing but held by an existing gate, 6 not local, 4 split parts). 17 are held for a right reason: 5 existing playback-order holds, 5 genuine part files (the 4 drawn plus "Холли ч.1"), 3 title or author text conflicts (the series or author name inside the title), 2 files with no tags, 1 collection with no author, 1 author named by one source only. **3 are false holds** (friction, not safety): `eddfcf16` and `8ac65d78` ("Robert J. Sawyer", F9), `8b721dc2` ("Таксидермист": the folder says "Гжендович Я.", which the matcher calls a different author, F6).

### 2.4 Suspected false approvals among the 403
Method: an exhaustive scan of every approvable row for narrator, translator, collection, podcast, part and series markers, cross-checked against names that appear as a reader or recording credit elsewhere in the same catalog. Translators as author: **none** (6 rows carry a translator credit; none uses it as author). Chapter or part files: **none certain** (I checked the lone "Игры Немезиды 1.m4b": 923 MB, about double the other 1/2 part files, so it is the whole book). Series-volume mismatch in the 403: **none** (all 28 "title is a segment of the file name" rows keep the correct trailing book title).

**A. Narrator credit accepted as the author — 5 certain.** Folder `Сборники\АНТОЛОГИЯ РУССКОЙ МИСТИКИ`, files named "0N читает Роман Волков - Недобрый глаз". Tags: artist "Сборник", album_artist "читает Роман Волков", comment "исп. Роман Волков". The approved author is the literal text **"читает Роман Волков"**.

| id | Approved author | Title |
|---|---|---|
| 17eecad8 | читает Роман Волков | Недобрый глаз |
| d78860f6 | читает Наташа Белкина | Странный бал |
| 9c188a79 | читает Дмитрий Шабров | Таинственная свеча |
| 6bd27a1f | читает Анастасия Стряпко | Бледная невеста |
| b191663b | читает Радион Нечаев | Прогулка домового |

**B. Narrator or compiler accepted as the author of a multi-author collection — 1 certain, 7 probable.**

| id | Approved author | Title | Evidence |
|---|---|---|---|
| 4249152d | Кирилл Головин | Месяц научной фантастики. Сборник рассказов | **Certain.** artist tag "Разные авторы" (ignored as not a person), then album_artist "Кирилл Головин" taken; comment "читает: Кирилл Головин"; folder "Сборники"; title says "Сборник" |
| 710a6a3c, d27f8da7, aedf2ae0 | Владимир Князев | Коллекция рождественского хоррора; неSplatterpunk stories 2; Русский русский Хоррор 2 - ПОХОРОНЫ | Probable. Folder "Сборники"; collection-style titles; the same catalog lists Князев as an ignored recording credit on another approved book (Ketchum, `bfda742f`) |
| 984fe472, 7fd4e232, e10d5261 | Булдаков Олег / Олег Булдаков | Пока все дома. Новогодняя серия; ТЁМНЫЕ АЛЛЕИ 2.1: Жестокость; Тёмные Аллеи в Кино | Probable. Comment "Читает Олег Булдаков"; folder "Сборники"; the same catalog ignores Булдаков as a recording credit on 8 other approved books (Абарат, Кол, Утеха падали, Застава and others) and carries him in comment, composer or album_artist on more |
| ed9488eb | Лавкрафт Говард Филлипс | Тёмные аллеи 2.2 - Ктулху и аколиты | Probable (an episode of a narrator's collection series filed under one author; composer tag "Булдаков Олег") |

The same people are treated as readers on some books and as authors on others, inside one run. Each of the 13 would be converted, published under a wrong author folder and file name, and its originals retired after the normal verification. The 24-hour recovery window applies, but the identity written down is wrong. **This is the NO-GO.**

**C. Weak identity: generic collection titles — 6.** `72c07b8c` Сапковский "Сборник рассказов", `ab83f855` Конан Дойл "Сборник рассказов", `26376dee` Гибсон "Сборник рассказов", `3fc837c0` Blackwood "Избранные рассказы и повести", `89c8f151` Сандерсон "Рассказы", `570b8f3b` Ходжсон "Рассказы". The sources agree, but the title cannot tell two compilations apart. Not counted as false approvals.

**D. Title text flaws — 3.** `7e6a6dee` "Голос»‎" and `31eb2e0f` "Отпрыски бури»‎" (stray closing guillemet plus an invisible U+200E, copied from the tag; the folder name would carry the invisible character), and `0163bed7` "ГЕограф глобус пропил".

Looked at closely and judged fine, so the next reader need not repeat it: the 26 approved rows whose author field has a separator. 25 are two-person credits (Hawking and Mlodinow, Gaiman and Pratchett, Sanderson and Jordan, Moore and Kuttner, Lukyanenko and Perumov, Obukhova and Timoshenko on 16 books, Averin and Vardunas, Torin and Yakovlev, Kabir with Kostyukevich, Kabir with Parfenov); the 26th, "Scalzi, John", is one person written surname-first. Tag, file name and folder name the same people each time, so I treated them as co-authors; offline I cannot confirm co-authorship for Averin/Vardunas, Torin/Yakovlev and the two Kabir pairs. "Роман Волков" on the three "Легенды школы №4" books looks like the author locally (the reader credits there are other people). "Трилогия тумана" is an omnibus file. "Игры Немезиды 1.m4b" is a whole book (923 MB).

## 3. Positive controls (synthetic fixtures, `local_identity.agreement`, offline)

Required controls, all expected "held":

| Case | Result |
|---|---|
| C1 folder "Stephen King", tag author "Dean Koontz" (and the Cyrillic version) | held (author grey). PASS |
| C2 same author, different title (file or folder names another book by that author), single and multi-file | held (title red). PASS |
| C3a-c Latin folder vs Cyrillic tag of a different name: Dan Brown / Дэн Симмонс, Neil Gaiman / Нил Стивенсон, Michael Crichton / Майкл Коннелли | held. PASS |
| C3d folder "Stephen King", tag "Стивен Хокинг" | **APPROVED (author yellow). FAIL** |
| C3e folder "Stephen Hawking", tag "Стивен Кинг" | **APPROVED (author yellow). FAIL** |
| C3f file name "Robert Silverberg - …", tag "Роберт Хайнлайн" | held (author red). PASS |
| P1 "Rollins James" folder / tag "Джеймс Роллинс" (Sergei's example, two files) | approved, author yellow, title green. PASS |
| P2 surname-first vs given-first, P3 Latin tag and Latin file name | approved. PASS |

Cause of C3d/e: the cross-script key drops vowels and "х" (the sound h), so "Хокинг" and "King" both reduce to the same consonants, and "Стивен" pairs with "Stephen". `compare_names('Стивен Хокинг', 'Stephen King')` returns a cross-script match. It is not hypothetical here: both authors are in this library. On the real name population (803 author-like names in the catalog) the matcher produced 39 cross-script matches that do not co-occur in any row; 34 are the same person split across rows, **5 are false: 4 Hawking/King** (both directions, and the "Бахман Ричард \ Кинг Стивен" credit) **and 1 folder "Wild Cards" against the author "О. С. Кард"** (Orson Scott Card). None of these sits among the 403 approvals today (I checked every one of the 68 cross-script author approvals: 33 distinct pairs, all the same person).

Extra probes beyond the brief (expected "held"):

| Case | Result |
|---|---|
| H1 tag title "Траун" with file "Тимоти Зан - Траун. Союзники" (series name as title) | **APPROVED, title "Траун" (green). FAIL.** The segment rule accepts the first segment as the title. 0 instances in the 403 today |
| H2 tag "Гарри Поттер" with file "…Гарри Поттер и философский камень" | held. PASS |
| H3 reader named in the file name, author in the folder | held. PASS |
| H4-H6 narrator patterns from section 2.4 A and B (artist "Сборник", album_artist "читает …"; "Разные авторы" plus narrator; comment "Читает <same person>") | **all APPROVED. FAIL**, reproduces the patterns behind the 13 |
| H7 generic title "Сборник рассказов"; H8 podcast-style title and episode | approved (no guard) |
| H9 a chapter file ("Глава 5", album = the book) alone in its folder, no catalogued sibling | approved (by design; none certain in the 403) |
| H10 author-credit tag differs from the folder, folder names a translator | approved with the translator as author (low realism) |
| H11/H12 tag title with a casing typo or stray "»" and invisible U+200E, clean file name | approved with the flawed tag text |
| H14 folder "Владимир", tag "Владимир Васильев" | approved (a first name alone supports a full author) |
| H15 no catalog handle (`siblings=None`) skips the split-part check | approved. `PublicResearch._siblings` returns None when the client has no `database` attribute; the real `PublicClient` has one, so this is defensive only |
| H16 folder "Ярослав Гашек", tag "Ярослав Гжендович" | **APPROVED, author becomes "Ярослав Гашек"** |
| H17 folder "Светлана Алексиевич", tag "Светлана Иванова" | approved |
| H18 folder "Wild Cards", tag "О. С. Кард" | **APPROVED, author becomes "Wild Cards" (yellow)** |

Cause of H16/H17: `_significant` treats any word ending in -ович/-евич/-ич as a patronymic and drops it, so a surname such as "Гжендович" or "Алексиевич" vanishes and a bare given name matches any author with the same given name; the "fuller credit" rule then writes the folder's string as the author. The same behaviour makes `compare_names('Гжендович Ярослав', 'Гжендович Я.')` return no match, which is why "Таксидермист" is wrongly held.

## 4. Ender's 30-book sample doc (`Docs/BooksArranger_IdentitySample_2026-10-13.md`)
- Accuracy: regenerating it with his `sample_doc.py` from **my** measurement gives the same 54 lines, identical apart from CRLF line endings. Counts (2,426 / 0 to 403 / 461 / 1,309) match.
- Readable in a Markdown viewer, 7 columns, chips explained at the top. Notes for Sergei's use:
  1. Titled "30 currently stuck books" but 12 of the 30 are approvable now, not stuck.
  2. It cannot reveal the 13 wrong-author approvals: the chip says only that tags and names agree (all of them do, by construction), and paths are not shown. Row 6 prints the stray "»" and an invisible character inside the title. Rows 14 and 15 are green on "title" although the title text contains the author or series. Showing the file or folder name of each approvable row would let Sergei catch these himself.
  3. Authors appear in three orders in one table ("Кабир Максим Ахмадович", "Максим Кабир", "Атеев Алексей"), which previews F5.

## 5. Diff sanity: `git diff --stat v0.13.1 67e3d43`
19 files, +1,451/−34. Product code: `local_identity.py` (new, 574 lines), `public_research.py` (+324), `automatic_processing.py`, `merge_service.py` (only the head of `approve_automatic`: the local-agreement source replaces the fetched-credit requirement, plus `revalidate` and the note text), `metadata_sources.py`, `review_backend.py`, `source_identity.py`, `standing_metadata.py`, `VERSION`. Tests: 4 files. Docs: 6 files. **Not changed:** `replacement_media.py`, `replacement_retirement.py`, `recovery_retention.py`, `replacement_jobs.py`, `audio_pipeline.py`, `source_cleanup.py`, `storage_cleanup.py`, `native_io.py`, `scanner.py`, `groups.py`, `web_server.py`, `web/`. This matches the handoff and CHANGELOG. Doc drift: the handoff still says "uncommitted candidate; Sully commits after GO", while 67e3d43 is committed and pushed and already contains Jane's rule section (F11).

Also checked offline: the new research-cache pruning SQL (window functions) keeps the newest 5,000 entries (entry bound) and the newest 21 of forty 3 MB entries (byte bound), as designed; `length(raw)` counts base64 text, so "64 MB" is about 48 MB of payload.

## Findings

| ID | Severity | Status | Owner | Finding |
|---|---|---|---|---|
| F1 | **Blocker** | Open | Ender | Narrator credit accepted as the author: 5 certain (author text "читает Роман Волков" and four more), section 2.4 A. Control H4 reproduces it |
| F2 | **Blocker** | Open | Ender | Narrator or compiler accepted as the author of a multi-author collection: 1 certain (Головин: artist tag "Разные авторы" ignored, album_artist narrator taken, comment "читает: …"), 7 probable (Князев x3, Булдаков x3, Лавкрафт episode). The same people are ignored as readers on other approved books. Controls H5/H6 reproduce it. Collection folders ("Сборники", "Антология") and titles ("Сборник", "Коллекция", "Рассказы") carry no guard |
| F3 | Major | Open | Ender | Required control C3d/e fails: "Стивен Хокинг" agrees with "Stephen King" and the reverse (consonant key drops "х"); "Wild Cards" agrees with "О. С. Кард". 5 false cross-script pairs among 39 unlinked matches in this library. 0 inside the current 403 |
| F4 | Major | Open | Ender | Series name accepted as the title when the file name carries the volume (H1: "Траун" for "Траун. Союзники"). 0 in the 403 today; can occur on any new file that follows this naming pattern |
| F5 | Major | Open | Ender / Judy / Sergei | No author-name normalisation: 31 people (of 154) are spelled two or three ways across the 403, covering 207 books (Кинг Стивен / Стивен Кинг / Stephen King; Кабир Максим / Максим Кабир / Кабир Максим Ахмадович; Пратчетт Терри / Терри Пратчетт). The approved credit becomes the author folder, so one author's books will land in several folders |
| F6 | Major | Open | Ender | Surnames ending -ович/-евич/-ич are dropped as patronymics (H16/H17): "Ярослав Гжендович" matches "Ярослав Гашек"; the folder string can replace the tag as the approved author; "Гжендович Я." is read as a different author (false hold, "Таксидермист"). A bare given name also matches (H14); "Владимир Несторович" matches every "Владимир …" |
| F7 | Minor | Open | Ender | Tag title text is copied unchecked when it differs from the clean file name only by case, punctuation or invisible characters: "Голос»‎", "Отпрыски бури»‎" (U+200E survives into the output name), "ГЕограф глобус пропил" |
| F8 | Minor | Open | Ender / Jane | Generic collection titles approved (6): identity not distinctive. The unchanged duplicate gate holds or suffixes same-work recordings, so no retirement hazard found, but the output name will not tell the compilations apart |
| F9 | Minor | Open | Ender | False holds (friction): 9 "Robert J. Sawyer" books agree locally but the source gate says "Sources disagree on the title or author" (author with a middle initial; cause not root-caused, flagged only). This gate holds 32 of the 58 locally agreeing books; some are right holds (series or author text inside the title), Sawyer is the largest single-author cluster |
| F10 | Minor | Open | Ender | Lone "Title N" part file with no catalogued sibling is approved (H9, H13 style). None in the 403. `siblings=None` skips the split-part check (H15); production passes a catalog handle |
| F11 | Minor (doc drift) | Open | Ender / Sully | Handoff says "uncommitted candidate", but 67e3d43 is committed and pushed and includes Jane's standing-rule section; the "Sully should commit Jane's section" note is stale |
| F12 | Info | Open | Ender / Sully | NOT VERIFIED offline: the vendor numbers behind `HOST_POLICY` (Open Library 1 request per second without a contact e-mail, iTunes about 20 calls per minute, Google Books courtesy quota), and any live DuckDuckGo behaviour. The unit tests for pacing and the one-hour challenge pause pass; the vendor claims themselves need a source check |
| F13 | Info | Accept | Jane | Suite baseline depends on clone path length (9 errors at 44 characters, 18 at 150) and on flaky tests that change run to run; the new end-to-end admission test also needs a short clone path |

Pattern alerts: none (first build under this rule; no cross-build recurrence to report). Within this build the reader-versus-author confusion appears in three forms (F1, F2, F6), which is one fix area for Ender.

## What would change this verdict
Not a request to widen the work, only the evidence I would re-measure on a new commit: (1) re-run the same offline measurement and re-scan the approvable set for the 13 ids in 2.4 (list kept below); (2) controls C3d/e, H1, H4-H6, H16-H18 flip to "held" while P1-P3 still approve; (3) full suite at a clone path under about 100 characters with no new failure.

Ids to re-check (prefixes, full ids in my scratch evidence): A `17eecad8 d78860f6 9c188a79 6bd27a1f b191663b`; B `4249152d 710a6a3c d27f8da7 aedf2ae0 984fe472 7fd4e232 e10d5261 ed9488eb`.

## Not run / limits
- NOT RUN: the app, a real admission, any network call (so no live gap search, no vendor check), real audio probing of the 403 (the catalog copy holds tags and paths only), the `qa-handoff` entry-check script (not named in the brief).
- Judgements of "right book" rest on tags, file names, folders and what the same catalog says about readers; I cannot open the audio. Probable items in 2.4 B are marked as such.
- The scans use heuristics I wrote (markers for reader, translator, collection, part); a class I did not think of would not be found. The random 40 and random 20 are small.

## Cleanup
- Removed (single-file `rm --`, allowed): my 377 MB copy of the catalog copy, its SQLite `-shm`/`-wal` side files, and my 40 MB derived `rows.json`. Ender's `evidence\catalog-copy.sqlite3` (376,786,944 bytes) and the rest of his `evidence\` folder were never modified.
- **NOT REMOVED**: the four clones. Plain `rm -rf` of my own folders was denied by the permission layer, so I did not try another route. Remaining, all mine (about 42 MB, clean, no uncommitted work in them):
  - `C:\Users\<user>\AppData\Local\Temp\claude\c--Antigravity-Projects-Studio-Illuminati\2b7de6b0-ce4b-4a27-9134-6e4452d270f4\scratchpad\futaba-0140\cand` (67e3d43, 11 MB) and `...\futaba-0140\base` (v0.13.1, 10 MB)
  - `C:\Users\<user>\AppData\Local\Temp\fq\cand` and `...\fq\base` (the same two commits at the short path, 21 MB together; only the depth-44 suite comparison used them)
- Kept as unresolved evidence in `...\scratchpad\futaba-0140`: `scripts\` (scan, fixture and probe scripts), `out\` (suite outputs and fail sets, scan results, fixture results, `suspects.json` with the 13 full ids, `measure-cand.json` and `measure-base.json`). They can be removed once Ender has the findings.
- `Docs/BooksArranger_CodeReview_v0.14.0_2026-10-13.md` appeared untracked in the worktree while I worked. It is not mine; I did not open it, so this verdict is independent of Senua's.

**Verdict:** NO-GO — Books Arranger v0.14.0 / commit 67e3d43
