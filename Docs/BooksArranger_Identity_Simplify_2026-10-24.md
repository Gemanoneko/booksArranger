# Books Arranger: why books are "Book identity uncertain", and what changes when title + author is enough (2026-10-24)

Ender, read-only analysis for Sergei's rulings 5, 6, 6a and 6b (`Team/Docs/BooksArranger_Rulings_2026-10-24.md`). Code read at `main` b467308 (v0.21.2). Nothing was changed, committed or fetched.

## How this was measured

- **Catalog.** One consistent copy of the live `data/inventory.sqlite3` was made with the SQLite backup API from a `mode=ro` + `query_only` connection, at 2026-10-24 06:36 UTC. Every count below comes from that copy.
- **Which books.** A book counts when its current research result lists "Book identity uncertain" and it is the current version of a non-superseded book (the same join the app's status counter uses, `automatic_processing.status()`). That gives **1,248**: 1,227 Waiting for source, 14 Held, and 7 with "Book identity uncertain" plus another reason. The diagnosis's 1,151 was the same count at 2026-10-23 ~21:30 UTC; the sweep kept adding books with the same result.
- **Re-running the app's own code.** `local_identity.agreement()` was re-run with the app's own code, in a throwaway worktree at `main`, on each book's current catalog row. It reproduced the stored record exactly for 1,248 of 1,248 books. `PublicResearch.lookup()` was also re-run with a client that answers only from the app's own response cache, with sockets disabled. It reproduced the stored reasons for 1,241 of 1,248.
- **Simulating the new rule.** The "title + author" rule below was simulated offline with the app's own parsing and name-matching functions. Its accuracy was judged by eye on two random samples of 40 identified books.
- No network requests were made. Z: was not touched.

## 1. Why each book is uncertain

"Book identity uncertain" is one message that covers two failed steps in a row:

1. **The local check** (`local_identity.agreement`). Since 2026-10-12 it needs **two independent local sources to agree** on both the title and the author: an embedded tag, plus the file or folder name.
2. **The public check** (`public_research._lookup`, line 669). FantLab, Wikidata or Open Library must have exactly one work whose title matches exactly.

All 1,248 failed both steps. The table gives the reason the local check recorded, using the first match in the order shown.

| Reason the local check gives | Books | Folders | Has a title + author pair anyway¹ |
| --- | ---: | ---: | ---: |
| **F. One part of a bigger book**: other files beside it carry the same title, it is one part of a numbered set with no title of its own, or its name is a chapter or part | 536 | 124 | 516 |
| **S. Only one local source names the title or the author**: there is no second source to agree with | 469 | 188 | 422 |
| **D. The folder or file name names a different book or author** than the tags | 115 | 77 | 115 |
| **P. Two people are credited (author and reader)**, or the credited person reads other books in the library | 85 | 50 | 85 |
| **X. Collection**: a collection folder, or "Сборник" as the artist | 35 | 12 | 35 |
| **N. No local title or author at all** | 8 | 8 | 0 |
| **Total** | **1,248** | **413** | **1,173** |

¹ Method: the (title, author) pair builder copied line for line from `public_research._lookup`, using tags, file name and folder name.

**The other reasons the brief asked about:**

- **Translation vs original title:** 109 books have a title tag in one script and a file name in another, for example `Watchers.m4b` tagged "Ангелы-хранители". These fall in S 44, D 17, F 39 and P 9. Method: the app's `local_identity.script()` on single-file books that have both a title tag and a title in the file name.
- **Cyrillic/Latin author:** this is not a cause. Cross-script author matches are already accepted: 220 of these books have such a match (state "yellow").
- **Confidence threshold just missed:** 0. The identity check has no numeric threshold.
- **No public match:** across **36,104 research attempts** on these books since 12 Oct (median 28 per book, maximum 71), none found a single public work.
  - Open Library answered on the last attempt for 1,062 books, and Wikidata for 98, with no single match.
  - FantLab searches are not recorded per book. The response cache is capped at 5,000 entries, so it holds the FantLab search for only 21 of these books.
- **Rate limits and search failures** don't cause the uncertainty. They only decide the label: any closed source gives "Waiting for source" instead of "Held" (`automatic_processing.py:640`).
  - The last attempt was blocked by: the shared Wikimedia limit at ru.wikipedia (100 requests per hour) for 994 books, FantLab's hourly limit for 130, DuckDuckGo's human check for 53, en.wikipedia for 42, Wikidata for 15. 14 had no block.

### Five real examples per top reason

**F. One part of a bigger book (536)**
- `Terry Pratchet\…\Терри Пратчетт - Пастушья корона (Макс Потёмкин)\Пастушья корона 20.mp3`. It is one of 77 chapter files in this folder, and each one became its own "book" (no album tag, so `source_identity.partition` files each one separately).
- `Robert R. McCammon\МЭТЬЮ КОРБЕТТ\2. Королева Бедлама\Часть 2. Безумие.m4b`: album "Королева Бедлама", one of 4 part files.
- `Richard Laymon\Beast House Chronicles\Дом Зверя\1. Подвал.m4b`: "part 1 of the 5-part set 'Дом Зверя' has no title of its own".
- `Light Novels\Yuyuko Takemiya\Toradora!\Торадора! Том 5.m4b`: "one part of a 10-part set … how to name it needs a rule".
- `J. R. R. Tolkien\…\Две твердыни. Летопись вторая\2-02 Две твердыни. Книга четвёртая.m4b`: one of 2 halves.

**S. Only one local source (469)**
- `Dean Koontz\Watchers.m4b`, tagged "Ангелы-хранители" / "Кунц Дин". The author agrees across scripts; the title is only in the tag, because the file name is the English original.
- `Dean Koontz\Moonlight Bay Series\1 Fear Nothing.m4b`, tagged "Живущий в ночи" / "Кунц Дин".
- `Червь\Червь 19. Расплата.m4b`, artist "Джон МакКрэй". The title agrees; the author is only in the tag, because the folder "Червь" names no author.
- `Omen\Omen 3 - The Final Conflict.m4b`, artist "Gordon McGill". The author is only in the tag.
- `Z:\Audiobooks\Кровавые иллюзии.m4b`, tagged "Кровавые иллюзии" / "Диана Удовиченко". It sits in the library root, so no folder can agree.

**D. The name disagrees with the tags (115)**
- `Клайв Стейплз Льюис - Хроники Нарнии\2. Хроники Нарнии. Лев, Колдунья и Платяной шкаф\…m4b`: the parent folder names the series as "a different book".
- `John Harwood\John Harwood - Asylum.m4b`, tagged "Мой загадочный двойник": English original vs Russian title.
- `R.L.Stine\Goosebumps Series 2000\R.L. Stajn - Headless Halloween (Vladimir Knyazev).m4b`, tag title "bezbashenniy hallowen".
- `Wheel of Time\Колесо времени - 05. Огни небес\Джордан Роберт (2015) -Колесо времени - 05. Огни небес, Часть 1.m4b`: the file-name parser takes "Джордан Роберт (2015) -Колесо времени" as the author.
- `Brandon Sanderson\Stormlight\Брендон Сандерсон - Архив Буресвета 4 - Ритм войны (Дружинин Степан).m4b`, artist tag "Степан Дружинин", who is the reader. There are 5 such Sanderson books.

**P. Two people credited (85)**
- `Discworld 26. Death 5. Thief of Time.m4b`: artist "Терри Пратчетт", album artist "Александр Клюквин" (the reader).
- `Star Wars\Пухов Сергей - Джо Шрайбер - Солдаты смерти.m4b`: album artist "Пухов Сергей" (the reader), artist "Джо Шрайбер".
- `Дивов. Профессия инквизитор\6\…\01  Новый мир.mp3`: album artist "Вероника Чепегина" (the reader), artist "О.Дивов".
- `Волков Роман\Легенды школы №4 г. Пензы\3 Рукопись … (читает Гарри Стил).m4b`: "Волков Роман" is credited as a reader on other books.
- `OLD_Audiobooks\…Хроники Нарнии.2011.Кирилл Радциг\kn5_g01.mp3`: album artist "sendok", artist "Кирилл Радциг". Neither is the author.

**X. Collection (35)**
- `WH40K\Сборник рассказов Warhammer 40000 (Casper Valter)\Гэв Торп - По зову Льва.mp3`: "unclear whether Гэв Торп is the author or the compiler".
- `Сборники\Тёмные Аллеи\Лавкрафт Говард Филлипс - Тёмные аллеи 2.2 - Ктулху и аколиты.m4b`
- `SCP\Пртоколы SCP. Сейф №1.m4b`: artist "Сборник".
- `Сборники\Владимир Князев - Коллекция рождественского хоррора.m4b`
- `George R. R. Martin\Миры Джорджа Мартина 1.m4b`: artist "Сборник".

**N. Nothing local (8):** `OLD_Audiobooks\Sbornik_Deti_Primarhov\<Author_Title>\Mp3\000.mp3…`. These have no tags, and the folder names are transliterated words joined with underscores.

## 2. Books that already have a clear title + author, and what still fails them

- **1,173 of 1,248** have at least one (title, author) pair from tags, file name or folder name. Method: the app's own pair builder, as in section 1.
- **1,041** have both the title and an author credit in their **embedded tags**. Method: an album or title tag plus an author, album artist or artist tag on the first file.
- **From a search hit: 0.** No book has a single public match. Another 7 have ambiguous or conflicting catalog hits (4 "Independent catalog work identity is ambiguous", 2 "Multiple-author work needs stronger evidence", 1 "Independent catalogs disagree").

What still fails the 1,173 is the rules, not missing data:

| What fails them | Books with a pair |
| --- | ---: |
| Part of a bigger book (F) | 516 |
| No second local source to agree (S) | 422 |
| Name and tags disagree (D) | 115 |
| Two people credited (P) | 85 |
| Collection (X) | 35 |

All of them also failed the public match.

**These 1,248 entries are not 1,248 books.** They sit in 413 folders. The 629 pieces in section 4 form about 300 books, so the real number is about 900.

## 3. What "uncertain" protects against today

Sources: `local_identity.py` module rules; Brief line 73 ("ARTIST must credit verified author(s), never an assumed reader") and lines 283–321; StandingRules rules 5, 9, 13 and 14 and the 2026-10-12/13 rulings.

**What it really prevents** (each seen in this library):

1. **A reader is filed as the author.**
   - The 5 Sanderson books would go under "Степан Дружинин"; "Ширли Джексон - Призрак дома на холме" under "Пухов Сергей".
   - The output's ARTIST tag would name the reader.
   - A reader, editor or label as the author is the most common error in the samples in section 4 (9 of 12 errors).
   - An earlier sample of 40, with no guards at all, had 7 errors: a chapter or story filed as a book (3), a reader or editor as the author (2), the author equal to the title (1), and garbled tags (1).
2. **One chapter or part is filed as the whole book.** This is the biggest real danger.
   - Chapter 20 of "Пастушья корона" would be converted and published as `Пастушья корона - Терри Пратчетт.m4b`.
   - Ruling 2 then allows its source to be deleted, because its output is verified.
   - The other 76 chapters would hit the same destination and be blocked.
   - The book ends up as one chapter in Sorted, with the rest stuck.
3. **A collection is credited to one person or to a label:** "Сборник", "Пять Вечеров", "Вселенная Дозоров", or a compiler.
4. **A series name in the album tag becomes the title.** For example, `Discworld 7. Pyramids.m4b` has album "Плоский мир". Today this is caught only because the file name disagrees.

**What it doesn't add (honest):**

- The public-catalog half adds almost nothing for this library: 0 matches in 36,104 attempts. FantLab, Wikidata and Open Library need an exact title, which misses Russian translations, fan recordings, light novels, WH40K stories and anthologies. Its main effect is endless retries.
- Overwriting a different edition can't happen either way. Publication refuses an existing path ("never overwrite"), and that is a separate gate.
- Wrong covers or series are a small risk. The Internet gap-fill takes catalog answers only when they match the local title and author.
- The two-source rule rejects the most common good case: a single fully tagged `.m4b` whose file name is the English original title, or a book in the library root. That is most of S (469).

## 4. Proposal: title + author is enough

**Rule** (replaces the two-source agreement and the public-match requirement for identity):

- **Title:** the album or title tag, else the file name, else the folder name.
- **Author:** the author, album artist or artist tag, else "Author - Title" in the file or folder name, else a person-named author folder.
- One source is enough. Nothing from the Internet is needed for identity. The Internet only fills optional fields (series, original title, cover), and never holds a book, as the existing gap-fill path already does.

**Four guards to keep.** Each matches a real error from section 3:

1. **A reader is never the author.** This covers names the library credits as readers anywhere: narrator tags, "читает", and names in brackets in file or folder names, such as "(Дружинин Степан)" or "[Пухов Сергей]". If the tag names a reader, the author comes from the file or folder name.
2. **Parts stay together.** Files in one folder with the same title + author are one book. Existing ruling 2026-10-13 still applies: M4B parts that carry their own chapters are separate books.
3. **A collection word or an editor credit is not an author.** This covers "Сборник", "Разные авторы" and "под ред.". The book goes to `Сборники` as "Разные авторы" (ruling 5 of 2026-10-13).
4. **Garbled tag text is not used.** Example: cp1251 read as Latin-1, such as "Òåððè Ïðàò÷åòò".

When the tag and the file or folder name name **different authors**, the book goes to Sergei's to-do list (ruling 6a), not to the Internet.

**Effect on the 1,248.** Method: an offline simulation of exactly this rule with the app's own functions on the catalog copy.

| Outcome | Books | Folders |
| --- | ---: | ---: |
| Identified straight away, no contradiction | 395 | 192 |
| Identified straight away: same author, the tag title wins over a differently worded name (translation, series wording) | 73 | 46 |
| Pieces that become whole books once grouped (guard 2): about 303 books, 291 of them with title + author; 101 folders are exactly one book | 629 | 128 |
| Tag author is a bracketed reader, so the file or folder author is used (guard 1; e.g. the 5 Sanderson books) | 14 | 9 |
| Collection with no author goes to Сборники / Разные авторы (guard 3) | 13 | 7 |
| **Goes to Sergei's to-do list** | **124** | **~75** |
| ↳ two people credited, can't tell which is the author | 49 | 25 |
| ↳ tag author and file/folder author differ | 29 | 27 |
| ↳ no author anywhere (26 of them are stories in the 4 "Ужасы и трэшатинка" folders) | 30 | 7 |
| ↳ no title, or no title and no author (Sbornik_Deti_Primarhov and similar) | 10 | 10 |
| ↳ garbled tags | 6 | 6 |

**Risk, measured.** Two random samples of 40 "identified straight away" books, judged by eye:

- Sample A, before the bracket guard: **34 of 40 right**. Sample B, final rule: **34 of 40 right**. That is about **85%**.
- With the bracket guard, sample A's two Дружинин errors would be caught (36 of 40).
- **The errors:**
  - A reader, uploader or label filed as the author: "Пухов Сергей", "Петроник", "Вселенная Дозоров", "Пять Вечеров".
  - An anthology credited to one person.
  - A messy title: "Хроники2_рез".
  - A chapter that slipped through: "04_Часть Четвертая …".
- **What a wrong book costs.** It lands in the wrong folder or under the wrong name in Sorted, and after verification its source is deleted (ruling 2). The audio is intact, so the fix is a rename or move, but at this rate that is about 40–70 books to correct by hand.
- **Where the errors are.** Every wrong author in both samples was a name not yet in Audiobooks Sorted:
  - 183 of the 468 identified books have an author who already has a Sorted folder.
  - 285 use **170 author names that are new**.
  - Showing those 170 names once, before the first run, would catch most author errors (question 2).
- **Grouping parts.** Two different recordings of the same title by the same author in one folder could be joined. The existing duplicate-recording, order and collision checks still apply, and parts with their own chapters stay separate.

### Option B: research again only when something changes

- **Signal.** Each book's catalog **fingerprint and revision** (`book_groups.fingerprint`, `groups.py:359–365`), which the app already has.
  - It is a hash of the book's file list, sizes, modified times and tags, recomputed by every discovery scan.
  - A changed or added file bumps the revision.
  - A renamed folder gives the files a new scope, so the book gets a new id.
  - Each research result already stores the revision and fingerprint it saw (`automatic_candidates`), and `AutomaticProcessing.candidate()` (`automatic_processing.py:171`) already treats a mismatch as "not researched".
  - It costs no extra disk or network work.
- **Two non-file triggers** already bump the revision or force a pass:
  - Sergei saving values or approving (`review_backend._write` bumps the revision).
  - A research-rules version change (`RESEARCH_VERSION`, one pass, `_refresh_wait`).
- **How the app re-queues when it fires.** A held or asked book gets no retry time ("until something changes") instead of today's retry times:
  - Today, Held retries at up to 24 h backoff (`automatic_processing.py:641`), and Waiting for source retries when the blocking host reopens, about 1 h.
  - The worker skips a book while its stored revision and fingerprint match the book's current ones.
  - When a scan changes them, the book counts as new and is researched in the normal order. This is the same path new books already take (`_add_current_candidates`).
  - Rate-limit waits are left only for optional fields, which never hold a book (existing gap deferral, `GAP_DEFER_LIMIT=3`).
- **What it saves.** The kept history of these 1,248 books shows **0 source changes**, so all 36,104 retries would have been skipped. The app sent 18,966 public requests in the last 8 days, across all books.
- **Limit.** A change is seen only when a discovery scan runs. A new Start runs one (`automatic_processing.py:524–531`); Continue does not. The Iron Inferno file went unnoticed for this reason: no scan had run since 22 Oct.

## 5. Rulings 6a and 6b: what blocks Sergei today

### (i) A book with Sergei-entered title and author ("Entered by you", saved via Edit metadata)

| Gate | Where | Today |
| --- | --- | --- |
| Sergei's values are search hints, not identity | `public_research.py:561–582` (`lookup`), recorded `verified_identity: False` (:573); `local_identity.agreement` never reads them | The book still needs local agreement or a public match |
| No single public work | `public_research.py:669` | "Book identity uncertain" |
| A public work that differs from Sergei's values | `public_research.py:578`, `manual_metadata.compare_research` | Hold: "Saved manual metadata disagrees with researched identity" |
| Open metadata questions | `automatic_processing.py:625`, `merge_service.py:1942` (`metadata_choices.admission`) | Hold until he answers |
| Automatic admission needs a public or local-agreement source | `merge_service.py:1926` and `:1933` | A manual source does not count |
| Editor draft open | `automatic_processing.py:590`, `merge_service.py:1943` | Hold: "Manual draft retained" |
| Module policy | `manual_metadata.py:4` | "No record approves a book or takes precedence over a provider" |

### (ii) A book Sergei approves with no edits (book editor, then Create audiobook)

| Gate | Where | Today |
| --- | --- | --- |
| A typed note and an author are required | `review_backend.py:499` | "Confirm the author role and record metadata evidence" |
| Cover must be chosen | `review_backend.py:502` | "Choose a usable cover" |
| Open metadata questions | `review_backend.py:498` | Approval refused |
| Destination needs an author and a title | `organization.py:22–23` (via `metadata.propose`, `review_backend.py:504`) | "Confirm the author credit" / "Confirm the book title" |
| Separate track and order confirmation, with a typed note | `review_backend.py:679`, `:201` | "Review the exact source files and playback order" |
| Multi-file book without one common album tag | `review_backend.py:207` | "Establish one common book source context…" |
| Single `.m4b` | `review_backend.py:209` | "Single audiobook file" (cleared only by a noted user approval) |
| Grouping conflicts | `groups.py:284–317` (row conflicts) | e.g. "Recording grouping needs stronger evidence" |

**Safety gates that stay** (not identity): sources changed or unreadable, destination already exists (never overwrite), job already exists, media verification, deletion only after the verified output exists in Sorted (ruling 2), and the 24 h recovery copy.

### What would change

**6a: Sergei's values are authoritative.**
- His title and author are the identity. The basis is recorded as "Entered by Sergei", and the Internet is not consulted for those fields.
- A public source that disagrees is noted, but never holds the book. The `compare_research` hold is removed.
- `approve_automatic` accepts that basis as identity.
- The Internet fills only the fields he left blank.

**6b: "Approve as is."**
- One action records his approval: who, when, the exact values, files and order shown.
- It overrides every identity and confidence hold: uncertain identity, sources disagree, not independently verified, mixed recordings, playback order uncertain, open metadata questions, one common source context, and single audiobook file.
- It needs no typed note.
- The cover is chosen automatically: the embedded one, else the neutral cover, as the automatic path already does.
- The title and author are the best ones from section 4.
- The safety gates above stay.

### How the app "asks" today, and why held books don't reach Sergei

- **98% are labelled "Waiting for source".** That is 1,227 of 1,248, and it reads as "the app is still working on it", with an automatic retry time. The label comes from the app's own hourly request limits.
- **That state has no list.** The book-list filters (`review_backend.py:317`) have Held, which shows only the Held state, but nothing for Waiting for source. "Output needs attention" lists only books with a failed conversion job (`review_backend.py:352`).
- **The "Edit metadata" prompt is hidden for them.** It shows only when `row.metadata_holds` is set (`web/app.js:641`), and `manual_metadata.holds()` returns holds only for state Held.
- **Even when he fills values, they don't identify the book** (table (i)).
- **Approving is slow.** It takes three steps (metadata with a note, cover, tracks with a note), then Create.

**Needs for Judy** (needs only, not a design):
- One list, the existing "Output needs attention" (ruling 10), holding every book that needs Sergei: missing title or author, two people credited, author differs between tag and name, and garbled tags.
- Each entry shows the plain reason, the fields to fill, the files and their order, and the destination path it will get.
- Two actions per entry: Save (his values, authoritative) and Approve as is.

**Where an approved-as-is book with no author goes today:** nowhere. `organization.plan` refuses it ("Confirm the author credit").
- A collection already has a rule: `Сборники`, credited "Разные авторы" (2026-10-13).
- A normal book with no author has no rule. That is question 1.

The normal destination is `Audiobooks Sorted\<Author>\<Title> - <Author>.m4b`, or `<Author>\<Series>\<Series> - <N> - <Title> - <Author>.m4b` for a series (`organization.plan`).

## 6. Questions for Sergei

1. **A book you approve that has no author anywhere:** file it in a folder called **"Без автора"**? (yes, or give another name)
2. **Before the first run,** do you want to glance over the **170 new author names** once? This catches most wrong authors (about 15% of the new ones). (yes/no)
3. **Numbered parts with no title of their own** ("Торадора! Том 5", "Шестёрка воронов 1"): name each part **set name + number**, e.g. "Торадора! 5"? (yes/no) This affects 171 of the 629 pieces.
