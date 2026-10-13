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

Round 1 verdict (superseded): NO-GO — Books Arranger v0.14.0 / commit 67e3d43


---

# Round 2 — a7d9b42

Author: Futaba. Candidate: commit `a7d9b4206974f9c6c88504b48d768c3a40c6f0a4` on `codex/books-fast-identity-0.14.0` (parent `67e3d43`; worktree HEAD agrees). Same rules as round 1: offline only, no app, live DB, network or Z:/Y:, Bash, no commit, nothing fixed. The round-1 sections above are unchanged.

Method differences: I made no new clone. The candidate is a `git archive` export of a7d9b42 (44-character path, the same depth as the retained v0.13.1 baseline clone), because `rm -rf` of my round-1 clones is still denied. The catalog copy is a fresh copy of Ender's file (sha256 `06fa82d7f039e2294b60470b98245a81ae84913d998f47dc750d01c14799a6d0`, identical). **The worktree has uncommitted edits made after a7d9b42** (`local_identity.py`, `tests/test_local_identity.py`, `tests/test_local_identity_fixes.py` and four docs). I did not test them; this verdict is for the committed a7d9b42 only.

**Summary: GO for a7d9b42, with the non-blocking findings below.** In all 445 approvals I found no narrator, compiler, translator or series name approved as the author or the title, and no chapter or part file approved as a book. All the controls you listed hold. The suite shows no new failure. One regression remains that only holds books (N1), plus a few Minor items.

## Result per check (round 2)

| # | Check | Result |
|---|---|---|
| 1 | Full suite on a7d9b42 vs v0.13.1 | PASS, no new failure (section R1) |
| 2 | Scan of ALL approvals for wrong authors, narrators, compilers | PASS, 0 found (R2) |
| 3 | 40 random approvals by hand, plus 10 new `Сборники` ones | PASS, 0 false of 40 and 0 false of 10 (R3) |
| 4 | Controls: Hawking/King, Wild Cards, Гжендович/Гашек, Костюкевич/Хазанович, root-level and disc-folder split parts | PASS, all held (R4) |
| 5 | The 39 cross-script pairs again | PASS, 30 still match and all are the same person, the 9 dropped are the 5 false ones plus four two-person credits (R5) |
| 6 | One author, one folder spelling | PASS with caveats: 138 author strings = 138 people, 2 partial-name pairs; typos win (R6) |
| 7 | Sergei's 4 rulings | Implemented; ruling 1 only partly (R7) |

## R1. Full suite
`python -m unittest discover -s tests -p "test_*.py"`, timeout 600000, a7d9b42 export and the v0.13.1 clone, both at path length 44.

| Tree | Tests | Result |
|---|---|---|
| a7d9b42 | 543 (515 + 28 new) | 9 errors, 1 failure. The 9 errors are **name-for-name identical** to the v0.13.1 baseline set (and to Ender's) |
| v0.13.1 | 490 | 9 errors, 0 failures this run |

The one failure, `test_required_working_cleanup_drains_before_retry_is_armed` (`'Needs attention' != 'Paused'`), is a **pre-existing flake**: isolated reruns, 30 per tree, passed 25 and failed 5 on a7d9b42 and passed 25 and failed 5 on v0.13.1. Not caused by this candidate. Focused `test_local_*.py`: 53 tests, OK.

## R2. Scan of all 445 approvals
Reproduction first: 2,426 waiting/held books, **445 approvable = 378 author books + 67 collections filed under `Сборники`**, record for record identical to Ender's `fix2/measure-after-v3.json` (approvable ids and every reason list). Remaining holds: 1,924 "Book identity uncertain", 24 mixed, 19 playback order, 15 sources disagree, 7 membership, 1 full author name.

Checks on the 378 author books (every one, own scripts, not Ender's):
- reader marker or collection word in the author text: **0**;
- author matches a reader-like name seen anywhere in the library (9,520 audio files; 98 names from narrator/reader/performer tags and from "читает / исп. / read by" in any tag): **0**; surname-level cross-check: 1 shared word (Иванов, a different person);
- author matches a name used as composer beside 3 or more different artists (17 such names, likely readers): **0**;
- author equals the reader named on its own row: **0**; author equals a translator: **0**; author under a collection-like folder: **0**;
- every one of the 138 author strings read by eye for a known narrator or compiler: none (the readers that came up in round 1, Булдаков, Князев, Головин, Волков-pattern, are not authors of any approval);
- the 67 collections: credit "Разные авторы" and `anthology` on all; no routed row discards a real person credit (credit tags are 57 collection-only, 6 collection plus reader, 4 reader-only); no narrator named in a collection is the author of another approval.

Round-1 suspects: of the 13 (A, B1-B3) **9 are now filed under `Сборники` as "Разные авторы" with the reader recorded as narrator** (the five "читает …" rows, Головин, Булдаков x3) and **4 are held** (Князев x3, Лавкрафт episode). None is an author book. The 6 generic-title books and `0163bed7` are approved with their real authors (rulings 4 and 2); the two stray-guillemet titles (`7e6a6dee`, `31eb2e0f`) are held.

Chapter or part files: none. Approvable single files with a track or disc tag "N of M, M above 1": 0. No approved single file under 20 MB except a 40-minute short story; 8 author books run under an hour and all are known short works (Лес на холме, Железная преисподняя, Большая симолеоновая афера and similar).

## R3. Hand check
**Random 40** (seed 13102026; 38 author books, 2 collections): **0 false matches**. Every one judged on tags, file, folder: Gaiman, Dick, Обухова/Тимошенко, Laymon, Rollins, Abnett, Шваб, Кайм, Волкодав, Дивов, Nevill, Ходжсон, Митчелл, King x5, Scalzi, Хоар, Гжендович, Варго, Pratchett, Sanderson, Атеев, Мастертон, Сапковский, Суэнвик, Anderson and others, plus `7fd4e232` (Булдаков collection, narrator recorded) and `b580c71a` (a "Глубина" collection). Readers (Булдаков, Большакова, Екатерина Бранд, Ксеноморф) are not used as authors anywhere. Notes only: the author text is the library's majority spelling, e.g. "Pratchet Terry" (R6).

**10 new `Сборники` collections** (seed 20261013, drawn from the 58 not approvable in round 1): all 10 are real collections and correctly filed. 9 are the "Глубина" series (artist "Сборник", composer "разные исполнители", folder `Сборники/Глубина`: Антиутопия, Алкоголь, Собаки, Фантастика, Русская готика, Открытия, Море, Космос из прошлого, Сто лет назад. Рассказы 1923 года); 1 is "Ужастики" (artist "Разные авторы"). **0 false.** Of the 67 collections only 10 name a narrator at all (R7, N3).

## R4. Controls (a7d9b42, real `folder_siblings` and `catalog_index` over a private synthetic catalog, 54 cases)
All held, as required:

| Control | Result |
|---|---|
| Hawking tag in a King folder; King tag in a Hawking folder | **held** both ways (round 1: approved). True pair Hawking/Хокинг still approves |
| Wild Cards folder, "О. С. Кард" tag | **held** (true pair Orson Scott Card still approves) |
| Гашек folder, Гжендович tag and the reverse | **held**; "Гжендович Я." folder with an "Ярослав Гжендович" tag approves |
| Хазанович folder, Костюкевич tag and the reverse; Алексиевич/Иванова; Сенкевич/Ибсен; bare "Владимир" folder | **held** |
| Root-level part file beside its sibling parts (7); root level with 44 root files and 2,500 nested files (no cap) | **held** |
| CD1 beside CD2; "(часть 1)" beside "(часть 2)"; Disc 1 beside Disc 2 | **held** (a lone whole book in a CD1 folder approves) |
| Readers and compilers: "читает X" as author slot, "Разные авторы" plus narrator, comment "Читает <credited author>", author who reads other books in the library, reader named in the file name | none approved as an author book. The first, second, third and file-name patterns are filed as collections under `Сборники`, the library-reader case is held |
| Series name as title ("Траун" vs "Траун. Союзники"), "Гарри Поттер" vs the full title, volume numbers 2033/2034, "Дом"/"Дым" | **held** |
| Ruling 2 ("ГЕограф" tag, clean file), invisible U+200E and stray "»" | approved with the **tag** spelling; control characters and stray quote removed |
| Lone numbered part ("Игры Немезиды 1" with no sibling) | **held** |
| Generic title with an agreeing author; the same inside a collection folder | approved; **held** inside a collection folder |

3 of the 54 cases did not behave as I expected; none changes the verdict (all three are residual or documented): `Michael Crichton` against "Майкл Крайтон" is now held (a documented false hold, vowel not written the standard way); a **lone chapter file with no catalogued sibling** and a title that does not name the part still approves (no instance in the 445); and a folder named for a **translator** with the translator also in album_artist approves with the translator as author (low realism, no instance).

## R5. The cross-script pairs again
- Round-1 39 unlinked pairs: **30 still match, all the same person** (Dembski-Bowden, Blackwood, Counter, Abnett x2, Koontz x2, Martin x2, McGill, McNeill, Frank Herbert x2, Rollins x4, Harwood, Nasu, Gaiman x3, Stine, R. C. Wilson, Howard x2, Pratchett x2, Zahn, Шендеров). **9 dropped**: Hawking/King x4, Wild Cards/Кард, and four "Gaiman & Pratchett" two-person credit strings.
- Fresh pass over the whole name population (801 names): 125 cross-script matches, 93 inside one row, **32 unlinked, all the same person, 0 false** (two new ones, Swallow and Beckett, are correct).
- Pairs the old matcher accepted and the new one refuses: 9 in total; 4 are the false ones, 4 are real same-person pairs now held (Bruce Sterling, Dennis Wheatley, Graham Masterton against "Грэхэм", Michael John Moorcock) and 1 is a title pair. These authors go to research: friction, not safety.
- Same script (886 names): 79 non-exact matches, none between different people; one oddity: "Conan" alone supports "Arthur Conan Doyle" (a middle name, no instance).

## R6. One author, one folder spelling
- 378 author books carry **138 distinct author strings = 138 people**: no person has two spellings by a full match, and none is split between Latin and Cyrillic. Round 1 had 31 people spelled two or three ways across 207 books.
- Two people still have a pair differing by a middle name (`Laymon Richard` 5 books against `Лаймон Ричард Карл` 1; `Ходжсон Уильям` 1 against `Ходжсон Уильям Хоуп` 2): 9 books, 2 people, as Ender states.
- The choice is deterministic and recorded on every book (`author_spelling`: chosen, counts, reason, order).
- Consequences to know: 131 Russian-titled books now get a Latin surname-first folder ("King Stephen", "Rollins James"; the rule sends an unknown-original book to English when an English spelling exists locally). **The majority spelling wins even when it is a typo:** "Pratchet Terry" (20 local folders against 5 correct, 7 books) and "Zahn Thimoty" (2 against 1, 3 books). That follows ruling 3 as written; Sergei may want to see it (N2).
- NOT RUN: whether already-published folders in the live library match these spellings; the catalog copy holds candidates only.

## R7. Sergei's rulings
1. Collections compiled or read by a narrator go to `Сборники`, narrator only as narrator: **done for 9 of the 13 round-1 cases (the Волков-pattern x5, Головин, Булдаков x3).** The 3 Князев collections, Sergei's own example, and the Лавкрафт episode are still held for research (N4).
2. Tag wins on a spelling slip: done (R4). No approval in the 445 actually needed the slip rule.
3. One canonical spelling: done (R6).
4. Generic titles accepted when the author agrees: done (10 approvals; held inside a collection folder).

## R8. What moved between round 1 and round 2
403 approvals in round 1; 445 now: **359 kept, 44 dropped, 86 added** (58 collections, 28 author books; the 28 all read correctly). Of the 44 dropped, 6 were the flawed ones (4 held suspects, 2 title-text); the rest are safe over-holds: about 22 Warhammer story files in collection folders or "Author - Рассказы" folders, 7 whose "Author - Series" folder is read as another book (Хобб x2, Вонг x3, Нарния, Райбер), 3 Волков (the author also reads other books), 3 Кабир (N1), 4 titles ending in a short number or letter ("Apartment 16", "Трофики 64", "К-10 (сборник)", "Н"), 1 Креативщик (20 files). Split parts: 1,306 of the 1,309 round-1 split-part books are still held; the 3 that became approvable are correct (Траун, book 1 of a series whose siblings are books 2 and 3; Перерождение, volume 1; Пока все дома, an episode beside "… Новогодняя серия"). 1,303 rows now carry the sibling conflict, 69 more are held because the title names a part or a number, none because the folder could not be read.

## New findings (round 2)

| ID | Severity | Status | Owner | Finding |
|---|---|---|---|---|
| N1 | Major (friction, safe direction) | Open | Ender | `same_person(x, x)` is false for an identical credit that contains an initial or a "-ович/-евич/-ич" word in a name of three or more words (`"Robert J. Sawyer"`, `"Laurell K. Hamilton"`, `"Кабир Максим Ахмадович"`, `"О. С. Кард"`). When artist and album_artist hold the **same** string, the book is read as two people and held with "name different people". 40 books are held this way (about 23 single-author or two-author books). It cost 3 Кабир approvals from round 1, and it is why all 9 Robert J. Sawyer books are **still held** although F9 was listed as fixed: the unit test passes the source gate, the real rows stop earlier. Holds only, no false approval. Worktree edits made after a7d9b42 touch `compare_names`; not tested |
| N2 | Minor (rule outcome) | Open | Jane / Sergei | The majority local spelling is used even when it is a typo: "Pratchet Terry", "Zahn Thimoty" will be written into the library names |
| N3 | Minor (scope) | Open | Jane / Ender | 57 of the 67 "narrator collections" have no narrator (artist "Сборник" or "Разные авторы", folder `Сборники`, mostly the "Глубина" series). They are correctly collections, but ruling 1 spoke of narrator-compiled ones and these used to go to collection research. Fact kind is still `narrator_collection`. A reader named in a bracket ("[Илья Дементьев]") is not recorded as narrator |
| N4 | Minor (ruling gap) | Open | Ender / Jane | Князев x3 (`710a6a3c`, `aedf2ae0`, `d27f8da7`, Sergei's own example) and the Лавкрафт episode `ed9488eb` are held, not filed under `Сборники`: Князев is never credited as reader locally, so author against compiler is "unclear" |
| N5 | Minor | Open | Ender | A reader named inside closing brackets, "(читает Гарри Стил)", is cut to the first name, so "author equals reader" is missed. Only matters when an author reads his own book (Глуховский, correctly approved) |
| N6 | Minor | Open | Ender | Residual mechanisms with no instance in the 445: lone chapter file with no catalogued sibling; a middle name alone ("Conan") supports a full author; translator folder. "Michael Crichton" no longer matches "Майкл Крайтон" (documented) |
| N7 | Minor | Open | Ender | The identity sample doc and the handoff were re-issued in a7d9b42; I did not re-check the doc this round |

Round-1 findings: F1 and F2 fixed (A-class and B-class); F3 fixed; F4 fixed; F5 fixed (caveat N2); F6 fixed; F7 fixed by ruling 2; F8 accepted by ruling 4; **F9 not fixed in the data (N1)**; F10 partly fixed (N6); F11 fixed in the handoff; F12 still not verifiable offline (the CHANGELOG now calls the Google Books cap a courtesy cap below the default and raises only Open Library and iTunes); F13 unchanged.

Pattern alerts: 1. **PA1, a claimed fix that did not show in the real-catalog run:** F9 ("Robert J. Sawyer") is described as fixed with a unit test, while all 9 real rows stay held by a different rule. Proposed disposition for Jane: fix, by listing the rows a fix claims to unblock in Ender's measurement run.

## Not run / limits (round 2)
- NOT RUN: the app, a real admission, any network call, live-library folder spellings, audio probing beyond the durations stored in the catalog copy, `qa-handoff` entry script.
- Judgements rest on tags, names, folders and what the same catalog says about readers; the 445 were scanned by my own rules and read in samples (50 books by hand, all 67 collections by one line each, all 138 author strings). A class I did not think of would not be found.
- This verdict covers only the committed a7d9b42. The uncommitted edits in the worktree after it are untested. This file now holds two verdict lines (round 1 NO-GO at 67e3d43 above, round 2 below); the checker should read the last one.

## Cleanup (round 2)
- Removed: my two copies of the catalog copy (377 MB each, single-file `rm --`), their SQLite side files, the derived `rows2.json` and the private fixture database. Ender's evidence folder untouched.
- **NOT REMOVED** (`rm -rf` still denied): `C:/Users/<user>/AppData/Local/Temp/fq/new2` (a7d9b42 export), `.../fq/base` and `.../fq/cand` (round-1 clones, v0.13.1 and 67e3d43), and in `C:/Users/<user>/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/2b7de6b0-ce4b-4a27-9134-6e4452d270f4/scratchpad/futaba-0140`: `cand` and `base` (round 1). About 55 MB in all.
- Kept as unresolved evidence in the same scratchpad folder: `scripts/` (round 1 and round 2 scan and control scripts, including `fixtures2.py` and `scan_r2.py`) and `out2/` (suite outputs, fail sets, scans, control results, spelling and pair lists).

Round 2 verdict (superseded): GO — Books Arranger v0.14.0 / commit a7d9b42


---

# Round 3–4 — 82bc67d and abd70ef

Author: Futaba. Round 3 candidate: `82bc67d4476a7a771b911387e64e543978ddecbe` (parent a7d9b42). Round 4 candidate, the one this section gives its verdict on: `abd70efacf77465b8efc664081568cbce2b21a4b` (parent 82bc67d; worktree HEAD; no uncommitted code edits, only docs). Same rules: offline only, no app, live DB, network or Z:/Y:, Bash, no commit, nothing fixed. Both candidates are `git archive` exports at path length 44, tested beside the v0.13.1 baseline clone at the same depth. Fresh copy of Ender's catalog copy (sha256 `06fa82d7f039e2294b60470b98245a81ae84913d998f47dc750d01c14799a6d0`, identical).

Release-gate housekeeping: the earlier bold verdict lines of rounds 1 and 2 are now plain "(superseded)" text and nothing else in those rounds was changed, so the only machine-readable verdict line in this file is the last line. The sentence in round 2 about "two verdict lines" is historical and no longer true.

**Summary: GO for abd70ef.** Round 3 fixed N1 (the identical-credit holds) and the lone-part gap from round 2, and round 4 closes Senua's R3-1 without changing a single approval. The 455 approvals (389 author books and 66 collections) were scanned again and no narrator, compiler, translator, series name or part file is approved. Controls you named all hold, including the Глуховский-style ones that 82bc67d still got wrong. Two Minor items are new.

## Result per check (round 3–4)

| # | Check | Result |
|---|---|---|
| 1 | Full suite from `git archive` exports vs baseline | PASS, no new failure (R1) |
| 2 | Full scan of ALL approvals | PASS, 0 wrong authors, narrators, compilers (R2) |
| 3 | 20 random approvals by hand | PASS, 0 false (R3) |
| 4 | Controls incl. Стругацкий А./Б., Толстой А.Н./Л.Н., King + "Сборник", the Sawyer books, Глуховский-style | PASS (R4) |
| 5 | Round 4 delta: abd70ef vs 82bc67d | PASS, identical 455 and 66, identical review text (R5) |

## R1. Suite
`python -m unittest discover -s tests -p "test_*.py"`, timeout 600000, path length 44 for every tree.

| Tree | Tests | Result |
|---|---|---|
| v0.13.1 baseline | 490 | 9 errors (the known set) |
| 82bc67d | 548 | the same 9 errors, plus 2 intermittent: `test_catalog_owner_lock_and_strict_port` (a `test_web` setUp lock, 12 of 12 isolated reruns pass on both trees) and `test_waiting_uses_earliest_candidate_and_does_not_revisit_later_source_early` (the old F4 timing flake: isolated reruns fail 4 times in 102 on 82bc67d and 3 times in 102 on v0.13.1) |
| abd70ef | 549 | the same 9 errors plus `test_restart_guard_rejects_wrong_instance_busy_admission_and_active_research` (the known `test_web` tearDown lock: 2 of 10 isolated reruns fail on abd70ef, 1 of 10 on v0.13.1; it has also hit the baseline in earlier rounds) |

No new failure: every extra name is a flake that fails at the same rate on the baseline. Focused `test_local_*.py`: 58 tests OK on 82bc67d, 59 OK on abd70ef.

## R2. Full scan of all approvals (abd70ef)
Reproduction: 2,426 waiting/held books, **455 approvable = 389 author books + 66 collections**, matching Ender. 82bc67d and abd70ef give the **same ids, the same reason lists and the same approved review text** for every book.

Same scan as round 2 on the 389 author books: reader marker or collection word in the author text 0; author equals a reader-like name seen anywhere in the library (9,520 audio files, 98 names) 0; author equals a composer used beside 3 or more artists 0; author equals the reader on its own row 0; author equals a translator 0; author under a collection-like folder 0; no narrator named in a collection is the author of another approval.

The 66 collections: every one sits under a collection-like folder (`Сборники`, a "Сборник - …" folder); none carries a person credit tag (credit tags: 57 collection-only, 6 collection plus reader, 3 reader-only); none has a reader-named folder. 9 of the 66 record a narrator. Chapter or part files approved: none; author books under an hour are the same 8 short works as in round 2.

Changes since round 2 (445 approvals): 443 kept, **2 dropped, 12 added**.
- Dropped: `bf893305` "Игры Немезиды" (the file is "5. Игры Немезиды 1": held as a numbered part by design; I showed in round 2 that this 923 MB file is a whole book, so this is one accepted false hold) and `e10d5261` Булдаков "Тёмные Аллеи в Кино" (his only credit is a plain person credit and he is a reader elsewhere, so it is held for research instead of being filed).
- Added: the **9 Robert J. Sawyer books** and the **3 Кабир books** (Мухи, Мокрый мир, Голоса из подвала) that N1 had held. All 12 read correctly. PA1 is closed.

## R3. 20 random approvals by hand (seed 20261013)
Koontz x2, Кристиан Роберт Винд, Шваб, Tim Curran, Джеймс Гилмер (a story in the "Бойся Чужого" anthology folder), Stephenson, **Robert J. Sawyer "Конец эры"**, a "Пять вечеров" collection, Уна Харт, McMahon, Хайнлайн, Обухова/Тимошенко, Конан Дойл "Сборник рассказов", Тимошенко, King x2, Рэмси Кэмпбелл, a "Глубина" collection, Вилсон "Застава" (32 files): **0 false**. Readers (Милюхин, Большакова, Финагин, Булдаков, Кашникова, Casper Valter) are never used as authors.

## R4. Controls (82bc67d and abd70ef; real `folder_siblings` and `catalog_index` over a private synthetic catalog, 91 cases)
All of these hold on both commits, except where marked:

| Control | Result |
|---|---|
| Стругацкий А. tag, folder Борис Стругацкий; Аркадий Стругацкий tag, folder Стругацкий Б.; one author listed as "А. Стругацкий, Б. Стругацкий" with only А. tagged | **held**. The true pair "Стругацкий А." with folder "Аркадий Стругацкий" and the same letters on both sides approve |
| Толстой А.Н. against folder Толстой Л.Н. (also artist plus album_artist identical); А. Н. Толстой against Лев Толстой; Алексей Толстой against Лев Толстой | **held**. The true pairs Л. Н. Толстой / Лев Николаевич Толстой and А. Н. Толстой / Алексей Николаевич Толстой approve |
| Stephen King + "Сборник" album_artist in a `Сборники` folder; King + "Разные авторы"; "Сборник" artist + King album_artist | **held**, never filed. A pure "Сборник" credit under `Сборники` still routes |
| Sawyer: artist and album_artist identical with a middle initial; Кабир Максим Ахмадович twice; Laurell K. Hamilton twice | **approve**. Robert J. Sawyer against folder Robert K. Sawyer: held |
| "5. Игры Немезиды 1.m4b" with the album lacking the number; "Название (часть 1)"; a lone "Глава 5"; a single file tagged "2" | **held**. A single file with title tag "1" (A Face in the Crowd pattern), "Гелий-3", "Волкодав 02. Право на поединок" stay whole books and approve |
| Sibling check with a root that does not match the catalog | **fails closed**: siblings unreadable, agreement not accepted; the right root approves |
| Carried over: Hawking/King both ways, Wild Cards, Гашек/Гжендович, Хазанович/Костюкевич, root-level and disc-folder split parts, series-name titles | all **held** |
| **Глуховский-style (round 4):** Глуховский reads his own "Рассказы о Родине" (comment or narrator tag, folder named for him); a Глуховский-named or Булдаков-named folder inside `Сборники` with a collection credit and reader marker; a collection credit plus reader marker with no collection folder | **abd70ef holds all five. 82bc67d filed all five as collections** (so R3-1 was real and is fixed). The "Антология" pattern and the Булдаков "Тёмные Аллеи" pattern under `Сборники` still route; Глуховский "Пост" (his own book, not a collection) approves as his book and is not routed |

Three of 91 cases differ from my expectation, none new: "Michael Crichton" against "Майкл Крайтон" is held (documented false hold), a folder named for a translator with the translator in album_artist approves (low realism, no instance), and two different people in artist and album_artist where an author folder names one resolve to that one (existing designed rule).

## R5. Round 4 delta
`git diff 82bc67d abd70ef`: `local_identity.py`, a few lines (a route now needs a collection folder and no reader-named folder) and one new test class. No real approval changed: the offline run gives the same 455 and 66 on both commits.

## Findings (round 3–4)

| ID | Severity | Status | Owner | Finding |
|---|---|---|---|---|
| N1 | was Major | **Fixed** | Ender | Identical duplicate credits are one person: the 9 Sawyer and 3 Кабир books are approved |
| N6 | was Minor | **Mostly fixed** | Ender | Lone chapter and numbered-part files with no sibling are held (cost: "Игры Немезиды 1", a whole book, is held). Not re-tested: a lone middle name ("Conan") supporting a full author |
| N8 | Minor (ruling 3) | New | Ender / Jane | One author is split again: "Philip K. Dick" has `Dick Philip K.` on 5 books and `Дик Филип Киндред` on 2, because the new initial rule treats "K." against "Киндред" as a different person in the canonical-spelling step. 7 books, 1 person; round 2 had none. The same rule is why Лаймон and Ходжсон still differ by a middle name |
| N9 | Minor | New | Ender | `e10d5261` Булдаков "Тёмные Аллеи в Кино" is now held, not filed under `Сборники`: ruling 1 names Булдаков, so Jane may want it filed; same family as N4 |
| N2, N3, N4, N5 | Minor | Open, unchanged | Jane / Ender | Majority typos in author spelling ("Pratchet Terry" 7 books, "Zahn Thimoty" 3); 57 of 66 collections have no narrator at all; Князев x3 and the Лавкрафт episode held; reader in closing brackets not parsed |

Pattern alerts: PA1 (a claimed fix not visible in the real-catalog run) is **closed**: the 9 Sawyer and 3 Кабир rows named in round 2 are approved in the real run. No new pattern alert.

## Not run / limits (round 3–4)
- NOT RUN: the app, a real admission, any network call, published-library folder spellings, audio probing beyond the stored durations, the `qa-handoff` entry script.
- Judgements rest on tags, names and folders; a class of error I did not think of would not be found. 20 books by hand in this round, 70 across rounds 2 to 4, plus rule-based scans of all 455.
- The suite's intermittent failures are attributed to flakes by isolated reruns on both trees (rates above); a rate of about 3 in 100 means a single red run can still occur.

## Cleanup (round 3–4)
- Removed: my copies of the catalog copy, their SQLite side files, the derived row files and the private fixture databases (single-file `rm --`). Ender's evidence folder untouched.
- **NOT REMOVED** (`rm -rf` still denied): `C:/Users/<user>/AppData/Local/Temp/fq/` (`base`, `cand`, `new2`, `new3`, `new4`) and, in `C:/Users/<user>/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/2b7de6b0-ce4b-4a27-9134-6e4452d270f4/scratchpad/futaba-0140`, `cand` and `base`. About 60 MB in all.
- Kept as unresolved evidence in the same scratchpad folder: `scripts/` (including `fixtures4.py`, `scan_r2.py`) and `out3/` (suite outputs, fail sets, scans, control results).

**Verdict:** GO — Books Arranger v0.14.0 / commit abd70ef
