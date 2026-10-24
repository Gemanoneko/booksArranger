# Books Arranger: screening the new author names (2026-10-24)

Ender, read-only, for ruling 12 (`Team/Docs/BooksArranger_Rulings_2026-10-24.md`). It screens the author folders that "title + author is enough" (`BooksArranger_Identity_Simplify_2026-10-24.md` § 4) would create in `Z:\Audiobooks Sorted`. Code read at `main` b467308 (v0.21.2) in a throwaway worktree. Nothing was changed, committed or fetched. Z: was only listed.

## Result

| | Folders | Books |
| --- | ---: | ---: |
| New author folders the rule would create | **233** | **496** |
| **Suspicious**: Sergei answers (questions 1–24) | **148** | **287** |
| Clean: no question | 85 | 209 |

**Readers credited as the author anywhere in the current library** (Sergei's ruling: a reader is never an author). This covers all 2,084 current books: 654 conversion jobs and 1,430 books not yet converted.

| | Readers | Books |
| --- | ---: | ---: |
| Converted books in `Audiobooks Sorted` whose output credits a reader | 0 | **0** |
| Top-level Sorted folders named after a reader | 0 | — |
| Converted books whose source tag credited a reader, but the output already credits the real author | — | 77 |
| **Books not yet converted that credit a reader as the author** | **87** | **183** |
| ↳ already in questions 6–9 (new-folder cases) | 17 | 32 |
| ↳ question 25: the library itself marks them as readers | 40 | 95 |
| ↳ question 26: readers found by context, and uploader handles | 30 | 56 |

**Nothing in Sorted has to move.** The reader problem is in books not yet converted: their tag or file name puts a reader where the author goes.

- **The proposal's list was rebuilt exactly.** It has 170 raw author names and 285 books, identical line for line.
- **But the real list is longer.** The app does not name a folder after the raw tag. It runs the tag through `canonical_author()` first (`public_research.py:882`). Measured on that real folder name:
  - The books identified straight away give **171** new folders (297 books).
  - **13 of the books the proposal counted as "already in Sorted" would open a duplicate folder.** The proposal's test was a fuzzy name match, not the folder name. Examples: «Haggard H. Rider» beside «Хаггард Генри Райдер», «Мартин Джордж» beside «Martin George R. R», «О.Дивов» beside «Дивов Олег».
  - 1 book the proposal counted as new lands in an existing folder: «Warhammer 40K», which is a universe folder, not an author.
  - The same rule makes **62 more folders** that the proposal did not count: 57 from parts grouped into whole books (guard 2) and 5 from the reader guard (guard 1).
- **Of the proposal's 171 folders, 96 are suspicious (133 books) and 75 are clean (164 books).** Most suspicious names fall into a few patterns, so 24 questions cover all 148. Questions 25 and 26 cover the readers in the rest of the library.

## Questions for Sergei (ready to paste)

Answer with the word in brackets. "yes" means "do what is suggested". Each answer is saved as a lasting rule, so the same name is never asked again (see "Learning from the answers" below).

**Authors you already have, written another way**

1. **Pratchett.** Sorted has «Pratchet Terry», with one "t" (6 books). 10 new books would open a second folder, «Pratchett Terry» («Night Watch», «Thud!»). 3 more have a broken author: «Т.Пратчетт. Зимних дел мастер» and «Терри Пратчетт. Шляпа полная небес» (the title is glued on), and «Опочтарение», tagged «Albert Kramer», who is probably the reader. One folder for all 13 and every other Pratchett book: **Pratchet** (as now) or **Pratchett** (correct spelling; the old folder is renamed later)?
2. **15 spellings of authors you already have.** Merge into your existing folder? (**yes** / name the ones to keep apart)
   - «Kuntz Dean» (Ticktock) → Koontz Dean
   - «Niel Gaiman» (Stardust) → Gaiman Neil
   - «Maks Frai» (2) and «22 Лабиринт Менина» (a title in the author tag) → Max Fray
   - «H. Rider Haggard» / «Хаггард Райдер» (2) and «Khaggard-"Ledyanye bogi"» → Хаггард Генри Райдер
   - «Джордж Мартин» (3, the Dunk and Egg stories) → Martin George R. R
   - «О.Дивов» (2, Профессия инквизитор) → Дивов Олег
   - «Дэн Абнетт «Первый и Единственный»» (5) and «Часть Шестая» (part 6 of the same book) → Abnett Dan
   - «Мэтью Фарерр» → Фаррер Мэтью
   - «Наталья Тимошенкова» (Кровавый рубин) → Тимошенко Наталья
   - «Грэм Мастертон Пария Ugrum Ugrumov» (Pariah) → Masterton Graham
   - «Кинг___Легенда_о_пуле» → King Stephen
   - «Мэд Док»: the title and author are swapped. The file is «Мэд Док - Нейт Кроули» → Crowley Nate
3. **«Бахман Ричард \ Кинг Стивен»** («Регуляторы»). Bachman is King's pen name. File under King Stephen? (**yes** / no)
4. **Clive Barker.** Sorted has both «Barker Clive» (9 books) and «Баркер Клайв» (1). Two new books: «Книга Крови II» (tagged «Клайв Баркер/Spichkin») and «Книга Крови. Том 4» (garbled tag). Which folder? (**Barker** / **Баркер**)
5. **«Лена Летняя»** («Пробуждение куклы», in your «ЛЕНА ОБУХОВА, НАТАЛЬЯ ТИМОШЕНКО» folder). I think this is Лена Обухова's pen name, but I am only about 60% sure. (**Обухова** / **both**, meaning the joint Обухова + Тимошенко folder / **keep** separate)

**A reader or label in the author tag**

6. **The reader is credited as the author; the real author already has a folder.** File each book there? (**yes** / name exceptions)
   - «BIGBAG» (Игра Джералда; also «Тьма – и больше ничего») → King Stephen
   - «Владимир Князев» (5 books): «Ритуал» → Nevill Adam; his 4 horror collections → Сборники
   - «Сергей Бурунов» (Бронепароходы) → Иванов Алексей
   - «Светлана Смелова» (2, The Passage) → Cronin Justin; also «История Лизи» → King Stephen
   - «Илья Сланевский» (2, «1986») and «Юлия Яблонская» («Чёрная звезда») → Ersgard Jesper
   - «Puffin Cafe» (Все Тенали Бороговы) → Moor and Kuttner
   - «vendigo» (Wendigo) → Blackwood Algernon
   - «Ключ судного дня» (the title, sitting in the author tag; The Doomsday Key) → Rollins James
7. **The reader is credited as the author; the real author is new.** Use the real author? (**yes** / name exceptions)
   - «Пухов Сергей» (7 books): «Призрак дома на холме» → Shirley Jackson; «Реван» → Дрю Карпишин; «Солдаты смерти» → Джо Шрайбер; 2 → Джеймс Герберт
   - «Григорий Перель/Максим Суханов» (Последний день лета) → Андрей Подшибякин
   - «Чайцын Александр» («На странных берегах») → Tim Powers. The book is «On Stranger Tides» (about 80% sure).
8. **Readers or compilers on 3 collections in your Сборники folder:** «Петроник» (Все новые сказки), «Зачиняев Александр» (Клыки: Истории о вампирах), «Anna Samoilova» (Призраки ХХ века). File them as Сборники / «Разные авторы»? (**yes** / no) «Петроник» is the reader «Петров Никита»; he is also credited on «Техподдержка» (→ Дивов Олег) and «Военрук».
9. **«Волков Роман»** names the folder of 3 books, «Легенды школы №4 г. Пензы» (Военрук, Физрук, Рукопись из школьной библиотеки). He is the reader on 70+ other books in your library, e.g. «читает Роман Волков». The only other credit on these 3, «Петров Никита» (Петроник), is a reader too. Who is the author? (**Волков** really is the author / type a name / **Без автора**)

**A series, collection or title used as the author**

10. **«Моногатари короткие истории» (49 files), «Ёимоногатари» (32), «Хякумоногатари» (7).** These are series names. The folders name the author: Нисио Исин. File under Нисио Исин? (**yes** / no)
11. **9 anthology series used as the author.** File as Сборники / «Разные авторы»? (**yes** / name exceptions)
    - Созвездие Льва (6), Манускрипты Аркхэма (3), Мистика и Ужасы (3; Калейдоскоп 1–3), Пять Вечеров (2)
    - Тёмные Аллеи (2), plus «Лавкрафт Говард Филлипс» on «Тёмные аллеи 2.2 Ктулху и аколиты»
    - Вселенная Дозоров (Затерянный дозор), Разные писатели (Сборник страшилок), Сборник (ССК 2024)
12. **Anthology editors credited as the author:** Датлоу Эллен (Легенды о призраках), Мари О'Риган & Пол Кейн (Проклятие или дар), Д. Костюкевич & М. Парфенов (ССК. Твари), Стивен Кинг & Бев Винсент (Летать или бояться). File as Сборники / «Разные авторы»? (**yes** / name exceptions)
13. **12 long lists of authors**, for example «Мураками Харуки, Миямото Тэру, …», Splatterpunk stories 1–4, and «Сундук сказок» with 12 names. File as Сборники / «Разные авторы»? (**yes** / no)
14. **«Гробница Саргераса»** (4 files in Unsorted\Warcraft, no tags) is a title, not an author. Who is the author? (type a name / **Без автора**)
15. **«Пристань желтых кораблей»** (OLD_Audiobooks, no tags) is a title, not an author. I believe it is a novella by Владислав Крапивин (about 75% sure). File under Крапивин Владислав? (**yes** / another name)
16. **«Народный фольклор»** («Самые страшные русские народные сказки»): keep it as the author, or file as Сборники / «Разные авторы»? (**keep** / **Сборники**)

**Two spellings among the new names**

17. **One folder for each person, with this spelling?** (**yes** / name exceptions)
    - «Юн Айвиде Линдквист» (4) and «Линдквист Йон Айвиде» (3) → Lindqvist John Ajvide (as in your source folder)
    - «Юкито Аяцудзи» (3) and «Аякудзи Юкито» (a typo) → Аяцудзи Юкито
    - «Риггз Рэнсом» and «Риггз Ренсом» → Риггз Ренсом
    - «Orson Scott Card» (3), «О. С. Кард» and «Орсон Скотт Кард Голос тех кого нет» → Orson Scott Card
    - «Кристофер Мур» (2) and «Кристофер Мур пер М. Немцова» (the translator is glued on) → Moore Christopher
    - «R.L. Stajn», «Роберт Лоуренс Стайн» and «Goosebumps HorrorLand» → Stine R. L.

**Garbled or glued tags**

18. **Fix each one from the file or folder name?** (**yes** / name exceptions)
    - «Ìàêñ Áðóêñ» (garbled «Макс Брукс», Мировая война Z) → Брукс Макс
    - an unreadable tag; the folder says «Головачев Василий (Посланник…)» → Головачев Василий
    - «Хищнец» (ССК 2025): this is the story's title; its author is «Оксана Заугольная» → Заугольная Оксана
    - «home2» (a story in «Ужасы и трэшатинка. Сборник рассказов») → Сборники
    - «Ж. Батай. История глаза» → Батай Жорж
    - «Марк Фрост-Последнее досье(genagame)» → Frost Mark

**Co-authors**

19. **7 real co-author pairs:** Уэйс & Хикмен (3 books), Кинг & Страуб («Чёрный дом»), Кинг & Чизмар («Гвенди и её шкатулка»), Брэдли & Паксон, Ллойд & Митчинсон, де Кастро & Бирс, Стив & Стефани Перри. Give each pair one joint folder, as you did with «Moor and Kuttner»? (**joint** / **first** author's folder)

**Anthologies split by story**

20. **3 anthology folders would become one folder per story author**: 44 new folders, each holding one story. They are ССК 2025 (16 folders), Калейдоскоп 4–5 (17) and the WH40K «Сборник рассказов» (11). Keep each anthology together in Сборники instead? (**yes** / no)

**Not sure**

21. **«Не Спать 1» and «Не Спать 2»** (in Сборники\Не Спать!). One tag reads «ne-spat-german-shenderov». Is the author Шендеров Герман? (**yes** / **Сборники**)
22. **«Джеймс Д. Прескотт»** («Вымирание 1. Код») is in your «A.G. Riddle\The Extinction Files» folder. Keep Prescott as the author? (**yes** / **Riddle**)
23. **3 names I can't place:** «Sanyendis» (Свет Вечный), «Имакаев Владимир» (Тайны прошлого), «Андрей Прил» (Фантомные мысли, in Сборники). Keep them as authors? (**yes** / name the readers)
24. **«Баошу»** («Возрождение времени», the Three-Body follow-up). This is a real one-word pen name. Keep it? (**yes** / no)

**Readers elsewhere in your library** (your ruling: a reader is never an author)

Nothing in `Audiobooks Sorted` credits a reader. These are books not yet converted. Each tag or file name below puts a reader where the author goes. A "yes" saves each name as "a reader, never an author", so these books and every future book with that reader go under the real author. The full lists, with an example for each reader, are in the evidence tables for questions 25 and 26.

25. **40 readers your library itself marks as readers** ("читает …", a narrator tag, or the name in brackets on many folders). Today they are credited as the author on 95 books. File those books under the real author? (**yes** / name exceptions)
    - «Степан Дружинин» (9): Brandon Sanderson ×5 («Архив Буресвета»), Ричард Кнаак ×2, Роберт Брукс, Гевин Юргенс-Фиари
    - «Александр Клюквин» (17): Terry Pratchett
    - «Олег Булдаков» (7): collections, Stephen King, Brandon Sanderson
    - «Кирилл Головин» (5): James S. A. Corey, Чарльз Соул, collections
    - «Антон Ческидов» (4): Gene Wolfe
    - «Игорь Князев» (4): Ханну Райаниеми, Neil Gaiman, Dan Simmons
    - «Пожилой Ксеноморф» (4): Laymon, Koontz, Атеев
    - and 33 more with 1–3 books each (Герасимов appears under two spellings): Смекалов, Иванов Станислав, Кирсанов, Аравушкин, Райциз, Маслаков, Большакова, Солоха, Прокопов, Гайсина, Дунин, Зверев, Пахомов, Беляев, Зайцев, Воробьёва, Герасимов, Дементьев, Бранд, Зубкова, Капитан Абр, Радциг, Потёмкин, Суслов, Максимова, Попов, Овуор, Воротилин, Покровский, Мендельсон, Зимин, Швец.
26. **30 readers found by context, and uploader handles.** The same name sits on books by different authors, the file name reads "Reader - Title", or it is a web handle. Credited as the author on 56 books. Are they all readers or uploaders? (**yes** / name exceptions)
    - «Олег Троицкий» (5 Firefly books by 3 authors), «Воронецкий Станислав» (4 Дозоры books by 4 authors), «Алексей Данков» (2 books by 2 authors: Пылаев, Лукьяненко), «Юрий Красиков» (3, John Scalzi)
    - «sendok» (11: Narnia ×10, «Тобол»), «Stix37», «nikto1971», «Max Plissken», «Библиотекарь», «Mystery Basket», «Sonata», «Puffin Сafe»
    - «Вероника Чепегина», «Полонецкая Елена», «И. Зубкова» (Дивов, «Профессия: инквизитор»), «Мартынова Наталья» («Мартынова Наталья - Милые детки»), «Никитина Марина», «Виктор Бабков», «Carolyn McCormick» (The Hunger Games), «Павел Константиновский» (Thrawn)
    - and 10 more with one book each: Комиссаров («Диктор: Алексей Комиссаров»), Тихонов, Андрей Кузнецов, Меркулова, Максим Сергеев, Панкрашкин, Постригайло, Габриэлян, Стаховский, Кузаков.

Everything else (85 names, 209 books) looks clean and needs no answer.

## How this was measured

- **Catalog.** One consistent copy of the live `data/inventory.sqlite3` was made with the SQLite backup API from a `mode=ro` + `query_only` connection, at 2026-10-24 07:06 UTC. It holds the same 1,248 "Book identity uncertain" books as the proposal, with an identical id list.
- **Same rule as the proposal.** The proposal's own scripts were re-run unchanged on this copy, using the app's code from a worktree at `main`:
  - The buckets came out identical: 395 / 73 / 629 / 49 / 30 / 29 / 14 / 13 / 7 / 6 / 3.
  - Its "new author" step was re-run too. The 170-name list is identical (`diff` is empty).
- **The folder the app would write.** For every book the rule files, the author is passed through `local_identity.canonical_author(author, [author], catalog_index(root), '')` and `metadata.safe_name()`. This is the same call the local-agreement path makes (`public_research.py:882`).
  - The language is left unknown, because no catalog match is used for identity under the rule.
  - A folder is **new** when no top-level folder in the live `Z:\Audiobooks Sorted` listing (155 folders) has that exact name, ignoring case.
  - **Assumption:** the new rule reuses this path. If a later gap-fill supplies the original language, the script of a few names could change (Russian vs English).
- **Which books.** Three groups:
  - The 468 books identified straight away (group A, the proposal's group).
  - One entry per part set with a title and author: 291 sets from 597 files (guard 2).
  - The 14 bracketed-reader books, using the author from the file or folder name (guard 1).
- **Existing names compared against: 332.** These are the Sorted listing, plus every author or destination folder named in the 654 conversion jobs, the 505 verified outputs and the 507 admitted ("Queued") candidates.
- **Checks, run on every new name against every existing name and every other new name:**
  - (a)(b) The app's own `compare_names()` (any word order, transliteration, surname only).
  - (a)(b) An edit distance of 3 or less on a transliterated, word-order-free form (names of 6+ letters).
  - (a)(b) A shared surname word.
  - (d) The app's own reader list: 58 names from `catalog_index()`.
  - (e) Shape checks: one word, digits, `_` `/` `\`, mojibake, several people, a title, translator or reader glued on.
  - (c) Pseudonyms from my own knowledge. My confidence is stated where it matters.
- **Every one of the 233 names was then read by eye with its tags and path.** The automatic "shared word" signal mostly hit common first names, such as «Александр» or «Robert». Only the cases confirmed by eye are flagged.
- **Reader screen (questions 25–26), on every current book.** That is all 654 conversion jobs (their source tags and their output) and the 1,430 other current book groups.
  - **Reader evidence** comes from every audiobook file's tags and path, and every job's source tags:
    - a narrator, reader or performer tag;
    - a name after «читает», «чит.», «исп.», «озвучил» or «read by» in any tag, file or folder name (the app's own `narrator_names()`);
    - a person's name in ( ) or [ ] in a file or folder name;
    - a job's own narrator field;
    - my own list of well-known narrators.
  - **The composer tag was not used on its own.** In this library it holds the author as often as the reader. On the Narnia files, for example, it holds «Клайв Стейплз Льюис», with the uploader as artist.
  - **A name counts as a reader only when the evidence sits on books whose main credit is someone else.** An author who reads their own books is not flagged.
  - Each reader was matched against every author field: the author / album artist / artist tag (the app's own order), the converted job's author, the research's proposed author, and the new-rule author.
  - **By eye**, I added names that sit on books by several different authors, "Reader - Title" file names, and web handles (question 26).
  - **Two-person books.** The identity doc's category P has 85 books that credit two people.
    - Once these readers are removed, 52 keep exactly one author.
    - 19 credit only readers, so the author comes from the file or folder name.
    - 14 still name 2–3 people: real co-authors, a universe creator, or a title in the tag.
    - Of the proposal's 49 "two people, can't tell" books, 42 resolve and 7 stay.
- No network requests were made. Z: was only listed (`ls`, `find`).

## Evidence for each question

Tables are numbered like the questions.
- "Books (files)": books after grouping, then the files behind them.
- "Rule group": A = identified straight away (the proposal's group); B = grouped parts or the reader guard.

#### Q1
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Pratchett Terry | 10 (10) | A | «Discworld 24. The Fifth Elephant» · «Discworld 29. Night Watch» | Audiobooks\Terry Pratchet\Discworld\City Watch |
| Kramer Albert | 1 (1) | A | «Опочтарение» | Audiobooks\Terry Pratchet\Discworld\Moist von Lipwig |
| Т.Пратчетт. Зимних дел мастер | 1 (1) | A | «Терри Пратчетт "Зимних дел мастер"» | …\Discworld\Tiffany Aching\Т.Пратчетт. Зимних дел мастер |
| небес Терри Пратчетт. Шляпа полная | 1 (1) | A | «исп. Капитан Абр и Nelly» | …Пратчетт. Шляпа полная небес .(чит Капитан Абр и Nelly) |

#### Q2
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Дэн Абнетт «Первый и Единственный» | 5 (5) | A+B | «Первый и Единственный» · «01_ Часть Первая - Нубилийский Пролив» | …H40K\Дэн Абнетт - Первый и Единственный [Casper Valter] |
| Мартин Джордж | 3 (3) | A | «Межевой Рыцарь» · «Присяжный Рыцарь (Верный меч)» | …- Повести о Дунке и Эгге [Mones Fits]\01 Межевой Рыцарь |
| Haggard H. Rider | 2 (2) | A | «Montezuma's Daughter» · «Озвучено по книге издательства: "Советский писатель",… | Audiobooks\H. Rider Haggard |
| Maks Frai | 2 (2) | A | «Moi Ragnarek (chit. Ovuor)» · «Objora_Hohotun (Ovuor)» | …_Audiobooks\Max Fray\Макс Фрай\MaksFrai_MoiRagnarek_MP3 |
| О.Дивов | 2 (2) | A | «Леди не движется-2» · «Дама с собачкой-3» | …еди не движется – 2 [Ирина Зубкова, 2018, 64 kbps, MP3] |
| 22 Лабиринт Менина | 1 (1) | A | «Макс Фрай» | …iobooks\Max Fray\Макс Фрай\22 Лабиринт Менина\Макс Фрай |
| Khaggard-_Ledyanye bogi_ | 1 (1) | A | «Allan and the Ice-gods» | Audiobooks\H. Rider Haggard |
| Kuntz Dean | 1 (1) | A | «Ticktock» | Audiobooks\Dean Koontz |
| Niel Gaiman | 1 (1) | A | «Stardust» | Audiobooks\Niel Gaiman |
| Ugrumov Грэм Мастертон Пария Ugrum | 1 (1) | A | «Pariah» | Audiobooks\Graham Masterton |
| Кинг___Легенда_о_пуле | 1 (1) | A | «Легенда о пуле» | Audiobooks\Stephen King |
| Мэд Док | 1 (1) | A | «Нейт Кроули» | …WH40K\Сборник рассказов Warhammer 40000 (Casper Valter) |
| Тимошенкова Наталья | 1 (1) | A | «Кровавый рубин» | …оклятые артефакты 3, Кровавый рубин [Ксения Большакова] |
| Фарерр Мэтью | 1 (1) | A | «После Деш'Эа» | …WH40K\Сборник рассказов Warhammer 40000 (Casper Valter) |
| Часть Шестая | 1 (1) | B | «Первый и Единственный» | …H40K\Дэн Абнетт - Первый и Единственный [Casper Valter] |

#### Q3
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Бахман Ричард _ Кинг Стивен | 1 (1) | A | «Регуляторы» | Audiobooks\Stephen King\Регуляторы |

#### Q4
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Êëàéâ Áàðêåð | 1 (1) | B | «Книга Крови. Том 4» | …oks\Клайв Баркер\Книга Крови - Том 4\4 - Изыди, Сатана! |
| Клайв Баркер_Spichkin | 1 (1) | A | «Книга Крови II» | OLD_Audiobooks\Клайв Баркер_Страх |

#### Q5
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Летняя Лена | 1 (1) | A | «Пробуждение куклы» | …books\ЛЕНА ОБУХОВА, НАТАЛЬЯ ТИМОШЕНКО\Городские легенды |

#### Q6
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Князев Владимир | 5 (5) | A+B | «Адам Невилл - "Ритуал"» · «Коллекция рождественского хоррора» | Audiobooks\Adam Nevill |
| Сланевский Илья | 2 (2) | B | «1986 Сезон 2» · «1986» | Audiobooks\JESPER ERSGARD |
| Смелова Светлана | 2 (2) | A+B | «Перерождение 3. Город зеркал» · «Джастин Кронин. Перерождение 2» | Audiobooks\Justin Cronin\The Passage Trilogy |
| Bigbag | 1 (1) | A | «Игра Джералда» | Audiobooks\Stephen King |
| Puffin Cafe | 1 (1) | A | «Все Тенали Бороговы, Жилищный Вопрос» | Audiobooks\Moor and Kuttner |
| vendigo | 1 (1) | A | «Wendigo» | Audiobooks\Algernon Blackwood |
| Бурунов Сергей | 1 (1) | A | «Алексей Иванов. «Бронепароходы»» | Audiobooks\Иванов Алексей |
| Ключ судного дня | 1 (1) | A | «чит. Кирсанов С.» | …udiobooks\James Rollins\Sigmа Force\6. The Doomsday Key |
| Яблонская Юлия | 1 (3) | B | «Чёрная звезда» | Audiobooks\JESPER ERSGARD |

#### Q7
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Григорий Перель_Максим Суханов | 1 (1) | A | «Андрей Подшибякин. «Последний день лета»» | Audiobooks\Андрей Подшибякин |
| Пухов Сергей | 1 (1) | A | «Ширли Джексон - Призрак дома на холме» | Audiobooks\Shirley Jackson |
| Чайцын Александр | 1 (1) | A | «Na strannyh beregah» | OLD_Audiobooks\Na strannyh beregah |

#### Q8
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Samoilova Anna | 1 (1) | A | «Призраки ХХ века» | Audiobooks\Сборники |
| Зачиняев Александр | 1 (1) | A | «Клыки: Истории о вампирах» | Audiobooks\Сборники |
| Петроник | 1 (1) | A | «Все новые сказки» | Audiobooks\Сборники |

#### Q9
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Волков Роман | 3 (3) | A | «Военрук» · «Физрук» | Audiobooks\Волков Роман\Легенды школы №4 г. Пензы |

#### Q10
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Моногатари короткие истории | 49 (49) | B | «Вступление от переводчика» · «Буфет Хитаги» | …ogatari Series - Сборник коротких историй (Adrenalin28) |
| Ёимоногатари | 32 (32) | B | «Эпизод 2 Глава 01-02» · «Эпизод 2 Глава 03» | …- Monogatari Series v24 - История сумерек (Adrenalin28) |
| Хякумоногатари | 7 (7) | B | «Предисловие переводчика» · «Истории 1-17» | …ио Исин - Monogatari Series - Сто историй (Adrenalin28) |

#### Q11
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Созвездие Льва | 6 (7) | B | «Созвездие Льва 3. Том 2» · «Созвездие Льва 2» | Audiobooks\Сборники\Созвездие Льва |
| Манускрипты Аркхэма | 3 (3) | B | «Манускрипты Аркхэма» · «Манускрипты Аркхэма 2» | Audiobooks\Сборники\Манускрипты Аркхэма |
| Мистика и Ужасы | 3 (3) | A | «Калейдоскоп № 1» · «Калейдоскоп № 2» | Audiobooks\Сборники\Мистика и Ужасы - Калейдоскоп |
| Пять Вечеров | 2 (2) | A | «Пять вечеров: Такое странное будущее» · «Пять вечеров: Сказки Джека-Aонаря» | Audiobooks\Сборники\Пять Вечеров |
| Тёмные Аллеи | 2 (2) | A | «ТЁМНЫЕ АЛЛЕИ 23: Russian edition» · «Тёмные аллеи 2.4: Удиви меня!» | Audiobooks\Сборники\Тёмные Аллеи |
| Вселенная Дозоров | 1 (1) | A | «Затерянный дозор. Лучшая фантастика 2017 (сборник)» | …Сергей Лукьяненко\Вселенная Дозоров - Межавторский цикл |
| Лавкрафт Говард Филлипс | 1 (1) | A | «Тёмные аллеи 2.2 - Ктулху и аколиты» | Audiobooks\Сборники\Тёмные Аллеи |
| Разные писатели | 1 (1) | A | «Сборник страшилок» | Audiobooks\Сборники |
| Сборник | 1 (1) | B | «Самая страшная книга 2024» | …га\Сборник - Самая страшная книга 2024 [Дементьев Илья] |

#### Q12
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Д.Костюкевич, М.Парфенов | 1 (1) | A | «Самая страшная книга. Твари» | …шная Книга\Самая страшная книга. ТВАРИ [Илья Дементьев] |
| Датлоу Эллен | 1 (1) | A | «Легенды о призраках» | …атлоу Эллен - Легенды о призраках_Пожилой Ксеноморф_128 |
| Мари О'Риган, Пол Кейн | 1 (1) | A | «Проклятие или дар» | …ерная книга страшных сказок (антология) [Игорь Ломакин] |
| Стивен Кинг, Бев Винсент | 1 (1) | A | «Летать или бояться» | Audiobooks\Stephen King |

#### Q13
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Вильгельм Гауф, Петр Ершов, Владимир Одоевский, Эдуард Рене… | 1 (15) | B | «Сундук сказок» | OLD_Audiobooks\Сундучок Сказок |
| Джон Раттлер;Анна Пейчева;Глеб Леонидович Кащеев;Дана Арнау… | 1 (1) | A | «Городские легенды» | Audiobooks\Сборники |
| Кузнецов В. Матюхин А. Павлов В. Колыхалова В. Костюкевич Д… | 1 (8) | B | «Новая плоть» | Audiobooks\Сборники\Новая плоть (2016) |
| Лаймон Ричард, Фрост Грегори, Меллик Карлтон, Мьёвиль Чайна… | 1 (1) | B | «Splatterpunk stories 2 (Шокирующие истории 2)» | …k Stories\Splatterpunk stories 2 (Шокирующие истории 2) |
| Ли Эдвард, Лаймон Ричард, Кетчам Джек, Лансдейл Джо, Литтл … | 1 (1) | A | «Splatterpunk stories 4 (Шокирующие истории 4): Последняя глава» | Audiobooks\Сборники\Splatterpunk Stories |
| Майк Гелприн, Александр Матюхин, Дмитрий Тихонов и др | 1 (1) | A | «Самая страшная книга. Чёрные сказки (Сборник)» | …га\Самая страшная книга. Черные сказки [Илья Дементьев] |
| Мураками Харуки, Миямото Тэру, Маруяма Кэндзи, Исигуро Кадз… | 1 (1) | A | «Сборник рассказов японских авторов Причуды Жизни» | Audiobooks\Сборники |
| Мьевиль Ч., Лансдэйл Дж., Буковски Ч., Айриш У., Кортасар Х… | 1 (1) | A | «Адамово яблоко» | Audiobooks\Сборники |
| По Эдгар, Кольер Джон и др | 1 (1) | A | «Тёмные аллеи 2.0 - Тёмные звёзды. Антология рассказов мистики и хоррора» | Audiobooks\Сборники\Тёмные Аллеи |
| Ричард Лаймон, Джек Кетчам, Эдвард Ли, Шон Хатсон, Джо Ланс… | 1 (1) | B | «Splatterpunk stories 3 (Шокирующие истории 3)» | Audiobooks\Сборники\Splatterpunk Stories |
| Эдвард Ли, Ричард Карл Лаймон, Поппи Брайт, Джо Лансдэйл , … | 1 (1) | B | «Splatterpunk stories (Шокирующие истории)» | Audiobooks\Сборники\Splatterpunk Stories |
| Юки Синъити, Огава Ёко, Иноуэ Ясуси, Кадзио Синдзи, Хоси Си… | 1 (1) | A | «Сборник рассказов японских авторов Сад Камней» | Audiobooks\Сборники |

#### Q14
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Гробница Саргераса | 4 (4) | A | «ГробницаСаргераса1» · «ГробницаСаргераса2» | Audiobooks\Unsorted\Warcraft\Гробница Саргераса |

#### Q15
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Пристань желтых кораблей | 1 (1) | A | «Пристань желтых кораблей» | OLD_Audiobooks\Пристань желтых кораблей |

#### Q16
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Народный фольклор | 1 (1) | A | «Самые страшные русские народные сказки» | Audiobooks\Сборники |

#### Q17
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Юн Айвиде Линдквист | 4 (8) | A+B | «Движение. Место второе» · «Блаженны мёртвые» | Audiobooks\John Ajvide Lindqvist\Place Trilogy |
| Orson Scott Card | 3 (3) | A | «Игра Эндера» · «The Worthing Chronicle» | Audiobooks\Orson Scott Card\Enderverse |
| Линдквист Йон Айвиде | 3 (3) | A | «Икс. Место последнее» · «Человеческая гавань» | Audiobooks\John Ajvide Lindqvist\Place Trilogy |
| Юкито Аяцудзи | 3 (3) | A | «Иная. Эпизод S» · «Убийство в десятиугольном доме» | Audiobooks\Light Novels\Yukito Ayatsuji\Another |
| Moore Christopher | 2 (2) | A | «На подсосе. Вампиры-2 чит. Капитан Абр» · «Выкуси. Вампиская сага-3 чит.Капита… | …obooks\CHRISTOPHER MOORE\Bloodsucking Fiends Love Story |
| Goosebumps HorrorLand | 1 (1) | A | «Проект СВиД - Сказки для Взрослых и Детей» | Audiobooks\R.L.Stine\Goosebumps HorrorLand |
| Stajn R.L | 1 (1) | A | «bezbashenniy hallowen (Vladimir Knyazev)» | Audiobooks\R.L.Stine\Goosebumps Series 2000 |
| Аякудзи Юкито | 1 (1) | A | «Иная» | Audiobooks\Light Novels\Yukito Ayatsuji\Another |
| Кард О. С | 1 (1) | A | «Тень Эндера» | Audiobooks\Orson Scott Card\Enderverse |
| Немцова Кристофер Мур пер М | 1 (1) | A | «Изверги-кровососы» | …obooks\CHRISTOPHER MOORE\Bloodsucking Fiends Love Story |
| Орсон Скотт Кард Голос тех кого нет | 1 (1) | A | «Speaker for the Dead» | Audiobooks\Orson Scott Card\Enderverse |
| Риггз Ренсом | 1 (1) | A | «Город пустых. Побег из Дома странных детей» | …стых. Побег из Дома странных детей (Панкрашкин А)\Audio |
| Риггз Рэнсом | 1 (1) | A | «Дом странных детей» | …с Перегрин - 1. Дом странных детей (Панкрашкин А)\Audio |
| Стайн Роберт Лоуренс | 1 (1) | A | «Добро пожаловать в старый дом» | Audiobooks\Goosebumps |

#### Q18
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| home2 | 1 (1) | B | «Без имени» | …\Unsorted\Ужасы и трэшатинка. Сборник рассказов\Сборник |
| Ìàêñ Áðóêñ | 1 (1) | B | «ÌÈÐÎÂÀß ÂÎÉÍÀ Z» | OLD_Audiobooks\Война Z 1 |
| Хищнец | 1 (1) | B | «Самая страшная книга 2025» | …га\Сборник - Самая страшная книга 2025 [Илья Дементьев] |
| глаза Ж. Батай. История | 1 (1) | A | «Ж. Батай. История глаза» | Audiobooks\Unsorted\Ж. Батай. История глаза |
| досье Марк Фрост-Последнее | 1 (1) | A | «Марк Фрост-Последнее досье» | Audiobooks\Mark Frost |
| ��������� ������� | 1 (1) | B | «��������� (����� ���� 1)» | OLD_Audiobooks\Головачев Василий (Посланник-Вирус тьмы) |

#### Q19
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Маргарет Уэйс, Трейси Хикмен | 3 (3) | A | «Драконы Осенних Сумерек» · «Драконы Зимней Ночи» | Audiobooks\Dragonlance |
| Адольф де Кастро, Амброз Бирс | 1 (1) | A | «Монах и дочь палача» | Audiobooks\Сборники\Все оттенки ужаса |
| Джон Ллойд, Джон Митчинсон | 1 (1) | A | «Книга всеобщих заблуждений» | Audiobooks |
| Мэрион Зиммер Брэдли, Дайана Паксон | 1 (1) | A | «Владычица магии» | Audiobooks\Marion Zimmer Bradeley\The Mists of Avalon |
| Стив и Стефани Перри | 1 (1) | A | «Война без правил» | Audiobooks\ALIEN |
| Стивен Кинг, Питер Страуб | 1 (1) | A | «Чёрный дом» | …ing\Стивен Кинг, Питер Страуб - Чёрный дом (BIGBAG) M4B |
| Стивен Кинг, Ричард Чизмар | 1 (1) | A | «Гвенди и её шкатулка» | Audiobooks\Stephen King |

#### Q20
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Авгур Александр | 2 (2) | B | «Калейдоскоп 4» · «Калейдоскоп 5» | …obooks\Unsorted\Калейдоскоп 1-5 (Сборник)\Калейдоскоп 4 |
| Логинов Геннадий | 2 (2) | B | «Калейдоскоп 4» · «Калейдоскоп 5» | …obooks\Unsorted\Калейдоскоп 1-5 (Сборник)\Калейдоскоп 4 |
| Swallow James | 1 (1) | A | «Голос»‎» | …WH40K\Сборник рассказов Warhammer 40000 (Casper Valter) |
| Артемьева Мария | 1 (1) | B | «Калейдоскоп 4» | …obooks\Unsorted\Калейдоскоп 1-5 (Сборник)\Калейдоскоп 4 |
| Блох Роберт | 1 (1) | B | «Калейдоскоп 5» | …obooks\Unsorted\Калейдоскоп 1-5 (Сборник)\Калейдоскоп 5 |
| Брогден Джеймс | 1 (1) | A | «Кровопийца» | …WH40K\Сборник рассказов Warhammer 40000 (Casper Valter) |
| Возный Сергей | 1 (1) | B | «Самая страшная книга 2025» | …га\Сборник - Самая страшная книга 2025 [Илья Дементьев] |
| Волков Владимир | 1 (1) | B | «Калейдоскоп 4» | …obooks\Unsorted\Калейдоскоп 1-5 (Сборник)\Калейдоскоп 4 |
| Гаямов Артем | 1 (1) | B | «Самая страшная книга 2025» | …га\Сборник - Самая страшная книга 2025 [Илья Дементьев] |
| Гиреев Герман | 1 (1) | B | «Самая страшная книга 2025» | …га\Сборник - Самая страшная книга 2025 [Илья Дементьев] |
| Глебов Виктор | 1 (1) | B | «Калейдоскоп 4» | …obooks\Unsorted\Калейдоскоп 1-5 (Сборник)\Калейдоскоп 4 |
| Гэв Торп | 1 (1) | A | «По зову Льва» | …WH40K\Сборник рассказов Warhammer 40000 (Casper Valter) |
| Давыденко Павел | 1 (1) | B | «Самая страшная книга 2025» | …га\Сборник - Самая страшная книга 2025 [Илья Дементьев] |
| Дани Вейл | 1 (1) | A | «Бальшая Пасть» | …WH40K\Сборник рассказов Warhammer 40000 (Casper Valter) |
| Дедов Александр | 1 (1) | B | «Самая страшная книга 2025» | …га\Сборник - Самая страшная книга 2025 [Илья Дементьев] |
| Дж. С. Стернз | 1 (1) | A | «Налетчица жива» | …WH40K\Сборник рассказов Warhammer 40000 (Casper Valter) |
| Джастин Хилл | 1 (1) | A | «Карантин зараженного блока» | …WH40K\Сборник рассказов Warhammer 40000 (Casper Valter) |
| Дмитрий Лазарев, Павел Давыденко | 1 (1) | B | «Самая страшная книга 2025» | …га\Сборник - Самая страшная книга 2025 [Илья Дементьев] |
| Игнат Федотов | 1 (1) | B | «Калейдоскоп 5» | …obooks\Unsorted\Калейдоскоп 1-5 (Сборник)\Калейдоскоп 5 |
| Килворт Гарри | 1 (1) | B | «Калейдоскоп 4» | …obooks\Unsorted\Калейдоскоп 1-5 (Сборник)\Калейдоскоп 4 |
| Кларк Эштон Смит | 1 (1) | B | «Калейдоскоп 5» | …obooks\Unsorted\Калейдоскоп 1-5 (Сборник)\Калейдоскоп 5 |
| Кожин Олег | 1 (1) | B | «Калейдоскоп 5» | …obooks\Unsorted\Калейдоскоп 1-5 (Сборник)\Калейдоскоп 5 |
| Лаконский Александр | 1 (1) | B | «Калейдоскоп 5» | …obooks\Unsorted\Калейдоскоп 1-5 (Сборник)\Калейдоскоп 5 |
| Лансдейл Джо | 1 (1) | B | «Калейдоскоп 4» | …obooks\Unsorted\Калейдоскоп 1-5 (Сборник)\Калейдоскоп 4 |
| Линдси Пэйтон | 1 (1) | A | «А поутру он проснулся» | …WH40K\Сборник рассказов Warhammer 40000 (Casper Valter) |
| Лопухов Дмитрий | 1 (1) | B | «Самая страшная книга 2025» | …га\Сборник - Самая страшная книга 2025 [Илья Дементьев] |
| Мавроди Сергей | 1 (1) | B | «Калейдоскоп 4» | …obooks\Unsorted\Калейдоскоп 1-5 (Сборник)\Калейдоскоп 4 |
| Майк Ли | 1 (1) | A | «Волк у ворот» | …WH40K\Сборник рассказов Warhammer 40000 (Casper Valter) |
| Миллер Станислав | 1 (1) | B | «Самая страшная книга 2025» | …га\Сборник - Самая страшная книга 2025 [Илья Дементьев] |
| Молчан Юрий | 1 (1) | B | «Калейдоскоп 4» | …obooks\Unsorted\Калейдоскоп 1-5 (Сборник)\Калейдоскоп 4 |
| Оксана Ветловская | 1 (1) | B | «Самая страшная книга 2025» | …га\Сборник - Самая страшная книга 2025 [Илья Дементьев] |
| Оксана Росса | 1 (1) | B | «Самая страшная книга 2025» | …га\Сборник - Самая страшная книга 2025 [Илья Дементьев] |
| Павлов Михаил | 1 (1) | B | «Калейдоскоп 5» | …obooks\Unsorted\Калейдоскоп 1-5 (Сборник)\Калейдоскоп 5 |
| Подольский Александр | 1 (1) | B | «Калейдоскоп 5» | …obooks\Unsorted\Калейдоскоп 1-5 (Сборник)\Калейдоскоп 5 |
| Рейнольдс Энтони | 1 (1) | A | «Отпрыски бури»‎» | …WH40K\Сборник рассказов Warhammer 40000 (Casper Valter) |
| Рубцов Александр | 1 (1) | B | «Самая страшная книга 2025» | …га\Сборник - Самая страшная книга 2025 [Илья Дементьев] |
| Саймоназари Юлия | 1 (1) | B | «Самая страшная книга 2025» | …га\Сборник - Самая страшная книга 2025 [Илья Дементьев] |
| Старков Дэн | 1 (1) | B | «Самая страшная книга 2025» | …га\Сборник - Самая страшная книга 2025 [Илья Дементьев] |
| Сулимов Владимир | 1 (1) | B | «Самая страшная книга 2025» | …га\Сборник - Самая страшная книга 2025 [Илья Дементьев] |
| Темхагин Антон | 1 (1) | B | «Самая страшная книга 2025» | …га\Сборник - Самая страшная книга 2025 [Илья Дементьев] |
| Френч Джон | 1 (1) | A | «Горнило» | …WH40K\Сборник рассказов Warhammer 40000 (Casper Valter) |
| Харффи Мэтью | 1 (1) | A | «Шепчущий клинок» | …WH40K\Сборник рассказов Warhammer 40000 (Casper Valter) |
| Шендеров Герман | 1 (1) | B | «Калейдоскоп 5» | …obooks\Unsorted\Калейдоскоп 1-5 (Сборник)\Калейдоскоп 5 |
| Щетинина Елена | 1 (1) | B | «Самая страшная книга 2025» | …га\Сборник - Самая страшная книга 2025 [Илья Дементьев] |

#### Q21
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| ne-spat-german-shenderov | 1 (1) | A | «Не Спать 1» | Audiobooks\Сборники\Не Спать! |
| Не Спать! | 1 (1) | A | «Не Спать 2» | Audiobooks\Сборники\Не Спать! |

#### Q22
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Прескотт Джеймс Д | 1 (1) | A | «Вымирание 1. Код» | Audiobooks\A.G. Riddle\The Extinction Files |

#### Q23
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Sanyendis | 1 (1) | A | «Свет Вечный» | OLD_Audiobooks\Svet_vechniy |
| Имакаев Владимир | 1 (1) | A | «Тайны прошлого» | OLD_Audiobooks\Тайны прошлого |
| Прил Андрей | 1 (1) | A | «Фантомные мысли» | Audiobooks\Сборники |

#### Q24
| New folder name | Books (files) | Rule group | Example titles | Source folder |
| --- | ---: | --- | --- | --- |
| Баошу | 1 (1) | A | «Возрождение времени» | Audiobooks\ПАМЯТЬ О ПРОШЛОМ ЗЕМЛИ |


#### Q25
| Reader (spellings) | Books not yet converted | Real author (other credit or folder) | Example |
| --- | ---: | --- | --- |
| Александр Клюквин / Клюквин Александр | 17 | Terry Pratchett | «Мор, ученик смерти» · «Вор времени» |
| Степан Дружинин | 9 | Брендон Сандерсон, Ричард Кнаак, Гевин Юргенс-Фиари | «Архив Буресвета 2 - Слова сияния (Дружинин Ст» |
| Булдаков Олег / Олег Булдаков | 7 | Разные авторы (collections), Стивен Кинг, Брендон Сандерсон | «Пока все дома» |
| Головин Кирилл | 5 | Разные авторы, Джеймс Кори, Чарльз Соул | «Игры Немезиды» |
| Антон Ческидов | 4 | Джин Вулф | «Меч и Цитадель - Меч ликтора» |
| Игорь Князев | 4 | Ханну Райаниеми, Neil Gaiman, Дэн Симмонс | «Баллада о змеях и певчих птицах» |
| Пожилой Ксеноморф | 4 | Лаймон Ричард Карл, Кунц Дин, Алексей Атеев | «МИР ДИНА КУНЦА часть 2» |
| Валерий Смекалов | 3 | Лукьяненко Сергей, Николай Желунов, Ник Перумов | «Цветной дозор» |
| Иванов Станислав | 3 | Шваб Виктория | «Оттенки магии 03. Сотворение света» |
| Кирсанов Сергей | 3 | Робин Хобб, Хобб Робин | ««Сага о живых кораблях» Книга 1. Волшебный ко» |
| Александр Аравушкин | 2 | Константин Образцов, Нил Стивенсон | «Единая теория всего. Том 3» |
| Вероника Райциз | 2 | Шваб Виктория, Пол Дж. Тремблей | «Кэссиди Блейк 01. Город призраков» |
| Владимир Маслаков | 2 | С. Лукьяненко | «Самоволка» |
| Ксения Большакова | 2 | Наталья Тимошенко | «Кошки-мышки» |
| Людмила Солоха | 2 | Роберт Ирвин Говард, Роберт Говард | «Сага о Конане. 1-й свиток «Конан-Варвар»» |
| Михаил Прокопов | 2 | Влад Райбер | «Плюшевая голова» |
| Айгель Гайсина | 1 | Александра Яковлева | «Александра Яковлева. «Иные»» |
| Александр Дунин | 1 | Роберт Чарльз Уилсон | «Слепое озеро» |
| Андрей Зверев | 1 | Джеймс Роллинс | «Пекло» |
| Артем Пахомов | 1 | Джонатан Страуд | «Амулет Самарканда» |
| Беляев Юрий | 1 | РУ Мэделин | «World of Warcraft. Восход теней» |
| Владимир Зайцев | 1 | Роберт Брукс | «World of Warcraft» |
| Воробьёва Ирина | 1 | Кэтрин Данн, Харвуд Джон | «Мой загадочный двойник» |
| Вячеслав Герасимов | 1 | Стивен Кинг | «Сердца в Атлантиде» |
| Герасимов В | 1 | Dean Koontz | «Кунц Дин - Повести и рассказы» |
| Дементьев Илья | 1 | an anthology (Сборники) | «Самая страшная книга 2024» |
| Екатерина Бранд | 1 | Лена Обухова, Лена Летняя | «Пробуждение куклы» |
| Ирина Зубкова | 1 | Олег Дивов | «Профессия: инквизитор 1. Леди не движется» |
| Капитан Абр | 1 | Terry Pratchett | «Терри Пратчетт "Зимних дел мастер"» |
| Кирилл Радциг | 1 | Сергей Лукьяненко | «Соглашение 3. Прыжок» |
| Макс Потёмкин | 1 | Терри Пратчетт | «Плоский мир» |
| Максим Суслов | 1 | Максим Кабир, Александр Лепехин | «Дозоры Тень сумеречных крыльев» |
| Максимова Елена | 1 | Нагоски Эмили | «Как хочет женщина. Мастер-класс по науке секс» |
| Марк Попов | 1 | Кэмерон Джонстон | «Вероломный бог» |
| Овуор Владимир | 1 | Фрай Макс | «Гнезда Химер. Хроника Овётганны» |
| Олег Воротилин | 1 | Stephen King | «Стивен Кинг.Уилла» |
| Руслан Покровский | 1 | Максим Кабир | «Максим Кабир - Тантеом» |
| Семён Мендельсон | 1 | Сергей Лукьяненко | «Пограничье: Застава» |
| Сергей Зимин | 1 | Влад Райбер | «Сброд» |
| Тамара Швец | 1 | Грэхэм Мастертон | «Дьяволы Судного дня» |

#### Q26
| Reader (spellings) | Books not yet converted | Real author (other credit or folder) | Example |
| --- | ---: | --- | --- |
| sendok | 11 | Клайв Стейплз Льюис, Иванов Алексей | «Тобол. Дилогия» |
| Олег Троицкий | 5 | Джеймс Лавгроув, Лавгроув Джеймс, Тим Леббон | «Firefly. Великолепная девятка» |
| Воронецкий Станислав | 4 | Сергей Недоруб, Виталий Каплан, Иван Кузнецов | «Севастопольский дозор» |
| Carolyn McCormick | 3 | Suzanne Collins | «The Hungar games» |
| Виктор Бабков | 3 | Дэн Симмонс, Ханну Райаниеми | «Dale Stewart 04 - Darwin's Blade 1» |
| Юрий Красиков | 3 | Джон Скальци | «Война старика» |
| Sonata | 2 | Дейв Косак, Сара Пайн | «Сильвана Ветрокрылая: Перед рассветом» |
| Алексей Данков | 2 | Валерий Пылаев, Сергей Лукьяненко | «Дозоры. Запах Сумрака» |
| Вероника Чепегина | 2 | О.Дивов | «Профессия: инквизитор 5. Великий дракон» |
| Max Plissken | 1 | Элджернон Блэквуд | «Джон Сайленс» |
| Mystery Basket | 1 | Элджернон Блэквуд | «Джон Сайленс» |
| Puffin Сafe | 1 | Moor and Kuttner | «Изобретатель Гэллегер» |
| Stix37 | 1 | Джеймс Роллинс | «Отряд сигма, книга десятая» |
| nikto1971 | 1 | Вилсон Полл | «Вилсон Полл - Перекрестья (Герасимов В)» |
| Алексей Комиссаров | 1 | Митио Каку | «Уравнение Бога: В поисках теории всего» |
| Алексей Тихонов | 1 | Moor and Kuttner | «Генри Каттнер. Истории о Хогбенах.» |
| Андрей Кузнецов | 1 | Кристи Голден | «Ученик тьмы» |
| Библиотекарь | 1 | Элджернон Блэквуд | «Джон Сайленс» |
| Евгения Меркулова | 1 | Мария Ясинская | «Чужой Дозор» |
| И. Зубкова | 1 | Олег Дивов | «Профессия: инквизитор 7. Война миров» |
| Константиновский Павел | 1 | Тимоти Зан, Timothy Zahn | «Thrawn Ascendancy: Chaos Rising (2020)» |
| Максим Сергеев | 1 | Константин Образцов | «Красные цепи» |
| Мартынова Наталья | 1 | Голдинг Мелани | «Милые детки» |
| Никитина Марина | 1 | Райаниеми Ханну | «Страна вечного лета» |
| Панкрашкин Андрей | 1 | Симмонс Дэн, Герберт Джеймс | «Тайна Крикли-холла» |
| Полонецкая Елена | 1 | О.Дивов | «Профессия: инквизитор 4. Настоящие индейцы» |
| Постригайло Г | 1 | Arthur Conan Doyle | «Карр Д Д - ШХ 06. Тайна закрытой комнаты» |
| Сергей Габриэлян | 1 | Дмитрий Ячевский | «Форсайт» |
| Стаховский Е | 1 | Stephen King | «Кинг Стивен - Рассказы» |
| Юрий Кузаков | 1 | Алекс де Клемешье | «Клинки кардинала» |

## Clean names: 85 folders, 209 books

No signal survived the check by eye. Ten examples:

| Folder | Books | Example |
| --- | ---: | --- |
| МакКрэй Джон | 31 | «Червь 1. Созревание» |
| Страуд Джонатан | 8 | «Крадущаяся тень» |
| Robin Hobb | 6 | «Сага о живых кораблях. Волшебный корабль» |
| Вебер Дэвид | 6 | «Честь Королевы» |
| Льюис Клайв Стейплз | 6 | «Хроники Нарнии. Племянник чародея» |
| Перумов Ник | 5 | «Гибель богов» |
| Пехов Алексей | 4 | «Аутодафе» |
| Лю Цысинь | 4 | «Шаровая молния» |
| Хилл Джо | 3 | «Коробка в форме сердца» |
| Хаксли Олдос | 1 | «О дивный новый мир» |

Clean names that were checked on purpose:
- **Pen names with no real-name folder in Sorted**, so nothing merges:
  - «Вонг Дэвид» is Jason Pargin.
  - «Измайлов Наиль» is Шамиль Идиатуллин.
  - «Олди Генри Лайон» is two authors writing together.
  - «МакКрэй Джон» is Wildbow's real name.
- **Different people, despite similar names:**
  - «Кинг Уильям» (William King, WH40K) is not King Stephen.
  - «Хилл Джо» is King's son, a separate author.
  - «Брукс Майк», «Брукс Роберт» and «Брукс Макс» are three different people.
  - «Чизмар Ричард» alone on «Гвенди и её волшебное пёрышко» is right: he wrote it alone.
- **«Перумов Ник»** already appears in the joint folder «Сергей Лукьяненко, Ник Перумов». A solo folder for his solo books is normal.

## Learning from the answers: what exists, and the minimal storage

### What exists today

Checked by grepping `main` for alias, canonical author and the narrator/collection lists.

- **No alias or merge table, and no "not an author" table.** The app can store Sergei's answers only per book. Neither store applies to another book:
  - `manual_metadata_sources` ("Entered by you"): bound to one candidate and fingerprint; 0 rows today.
  - `metadata_choices`: append-only, bound to one candidate, fingerprint and revision.
- **`local_identity.canonical_author()`** (ruling 3, 2026-10-13) picks one spelling per person automatically:
  - It uses the library majority, prefers Latin when a Latin spelling exists locally, and lets a spelling confirmed by fetched catalog evidence win (`confirmed_spellings()`). It writes the surname first.
  - It only joins names that `compare_names()` calls the same person: word order, transliteration, surname only.
  - It cannot hold Sergei's choice. It cannot join one-letter slips in short surnames (Kuntz/Koontz), Niel/Neil, Йон/Юн, a pen name (Bachman), a title glued to a name, or a reader.
  - In this run it splits Pratchett by itself: «Pratchet Terry» for 17 books and «Pratchett Terry» for 10 (question 1).
- **Hard-coded lists in `local_identity.py`.** Changing any of them takes a release:
  - `RULED_NARRATORS = ('Олег Булдаков',)` (Sergei's ruling 1 of 2026-10-13). This is already a one-row "not an author" rule, written in code.
  - `NOT_PEOPLE`, `VARIOUS_AUTHORS`, `CONTAINER_NAMES` and `COLLECTION_FOLDER`.

### Minimal storage (not built)

One append-only table in `data/inventory.sqlite3`, the long-lived catalog that already holds jobs and per-book choices. For example, `author_rules`:

| Column | Holds |
| --- | --- |
| `rule_id` | uuid |
| `kind` | `same_as`: other spellings, script or pen name → one folder. `not_author`: a reader, label, studio or uploader. `collection`: a series or anthology name, or an editor → Сборники / «Разные авторы». `keep`: Sergei confirmed a separate author, so never ask again |
| `credit_key` | the credit normalised the way `same_person()` already compares names: `words()` (case, ё/е and punctuation removed), sorted, initials kept |
| `credit_as_seen` | the credit as written, for display |
| `target` | the folder for `same_as` (e.g. `Koontz Dean`); empty otherwise |
| `scope` | empty = the whole library; or a source-folder prefix when the answer is "only here" |
| `actor`, `saved_utc`, `question` | who answered, when, and which question |

Like `metadata_choices`, it should refuse UPDATE and DELETE with triggers. A changed mind is a new row that replaces the old one. This batch adds about 150 name rows and about 90 reader rows.

### Where the rules apply

Every book, on every identity pass:

1. **Before `canonical_author()`:** a `same_as` key gives the target folder, and the spelling vote is skipped.
2. **`not_author`** keys join the reader list (`catalog_index()['readers']`). Guard 1 then drops them and takes the author from the file or folder name, or asks.
   - Questions 6–9, 25 and 26 add about 90 `not_author` rows.
   - Guard 1 must check every author source, not only the tags: «Олег Троицкий - Firefly…», «Мартынова Наталья - Милые детки» and «Григорий Перель - Андрей Подшибякин…» put the reader in the file name's author slot.
3. **`collection`** keys go to Сборники / «Разные авторы», the path from ruling 5 of 2026-10-13.
4. **`keep` keys and every `same_as` target** join the screen's list of existing names, so the screen never asks twice.
5. **The screen runs on the final folder name, not the raw tag.** The proposal's raw-tag test missed 13 duplicate-folder books.
6. **Each book records which rule chose its author** (`rule_id`). `standing_metadata.py:108` accepts only `surname_first` and `verified_full_name` as the author basis today, so it needs a third value.

### How one answer covers similar cases

- **The same credit written differently:** any word order, case, ё/е or punctuation produces the same key.
- **Other spellings of a target:** these go through the app's existing matcher. Once «Koontz Dean» is a target, a later «Кунц Дин» or «Dean R. Koontz» joins it through `compare_names()` (other script, extra initial). If it does not, the screen flags it against the target and asks once.
- **A reader is a reader everywhere:** a `not_author` answer extends the reader list across the library. The same reader on another book is caught by guard 1 with no question.
- **Questions 19 and 20 are policies, not name rules:** joint co-author folders, and anthologies kept whole. Each is one standing ruling, like the 2026-10-13 rulings.

## Notes for Jane (not questions for Sergei)

1. **Grouping gaps seen while screening.** These are guard 2 gaps, not author names, so they belong to the implementation:
   - The 3 Monogatari folders would become 88 one-file books.
   - The 6 parts of Абнетт's «Первый и Единственный» do not group into one book.
   - 3 anthology folders split into one book per story (question 20).
2. **The proposal's "170 new names" undercounts.** The real figure is 233 folders and 496 books once grouped parts and the reader guard are included. 13 books it counted as known would open duplicate folders.
3. **«Рассказы» from `OLD_Audiobooks\Sbornik_Deti_Primarhov`** credits «Warhammer 40K» as its author. It would land in the existing «Warhammer 40K» universe folder, so it is not a new name. It is still a wrong author.
4. **Duplicate folders already in Sorted** (seen, not asked; an offer only). These 14 pairs are one person under two names:
   - Barker Clive / Баркер Клайв
   - Zahn Thimoty / Zahn Timothy
   - Laymon Richard / Лаймон Ричард Карл
   - Ходжсон Уильям / Ходжсон Уильям Хоуп
   - Frances Hardinge / Хардинг Фрэнсис
   - Rowling J. K / Роулинг Джоан
   - Schwab Victoria / Шваб Виктория
   - Scalzi John / Скальци Джон
   - Suzuki Koji / Судзуки Кодзи
   - Wilson F. Paul / Вилсон Фрэнсис Пол
   - Drew Karpyshyn / Карпишин Дрю
   - Heinlein Robert A / Хайнлайн Роберт
   - Симада Содзи / 島田 荘司 _ Shimada Sōji
   - Jarosław J. Grzędowicz / Гжендович Ярослав
5. **Readers: nothing converted needs fixing.**
   - 77 converted books had a reader in the source tag's author slot. Every output credits the real author, and no Sorted folder is named after a reader.
   - The risk is the new rule. It takes the author / album artist / artist tag, and album artist is where these libraries usually put the reader. Guard 1 is only as good as the reader list, which is why questions 25 and 26 matter before the first run.
6. **Titles sitting in an author tag** (not readers; not asked): «Melkie bogi» (Small Gods), «Human Remains» (Clive Barker), «Отряд "Сигма"» and «Чёрный орден» (Rollins). Each sits beside the real author in a two-person credit.
7. **Word order is mixed (style; not asked).** Some new folders keep the first name first, e.g. «Anne McCaffrey» and «Блейк Крауч». Most Sorted folders put the surname first. `surname_first()` only swaps when it recognises the first name.
