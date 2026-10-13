# Books Arranger — split books sample, 2026-10-13

Ender, offline run of the v0.15.0 candidate against one consistent copy of the live catalog (sqlite backup API, source opened read-only, 2026-10-13 10:54 UTC, the app running). No network and no Z:/Y: reads: everything below comes from the tags, file names, folder names and stream profiles already in the catalog.

**Chips:** 🟢 tags and file/folder names agree · 🟡 agree across languages or scripts (or, for order, part numbers in the names instead of track tags) · 🔴 local sources disagree · ⚪ missing (fewer than two local sources name it).

## Whole waiting/held list

| | Before (v0.14.0) | After (v0.15.0 candidate) |
|---|---|---|
| Waiting/held books checked | 2416 | 1649 (173 of them new split books) |
| Approvable without the Internet | 445 | **528** |
| Split-part files held | 1,299 single files | 173 books from 940 files (935 held part files + 5 MP3 chapters): 707 files in 81 approvable books, 233 in 92 books needing research; 363 still held |

A split book is grouped only when every part has the same album (book title), the same author, reader and recording tags, the same audio format, and gap-free numbering with no duplicates. Anything else stays held as separate files: gaps, duplicates, mixed readers or recordings, "Том 3" / "Книга 2" volume numbers (may be separate books), and parts with their own story or book titles.

At conversion every part is checked again; the parts are joined into one M4B with one chapter per part. An M4B part that already has its own chapters is held, so no chapter marks are lost.

## 20 grouped books (14 approvable, 6 needing research)

| # | Folder | Files | Order evidence | Author | Title | Outcome |
|---|---|---|---|---|---|---|
| 1 | Dan Brown\Robert Langdon series\3 The Lost Symbol | 155 | 🟢 track tags 1–155, no gaps or duplicates | 🟢 Dan Brown | 🟢 The Lost Symbol | **Approvable now** — one M4B, 155 chapters: "The Lost Symbol" by Brown Dan |
| 2 | Dan Brown\Robert Langdon series\4 Inferno | 108 | 🟢 track tags 1–108, no gaps or duplicates | 🟢 Dan Brown | 🟢 Inferno | **Approvable now** — one M4B, 108 chapters: "Inferno" by Brown Dan |
| 3 | Stephen King\Под куполом | 4 | 🟢 track tags 1–4, no gaps or duplicates | 🟡 Кинг Стивен <br><sub>other script; order ignored</sub> | 🟢 Под куполом | **Approvable now** — one M4B, 4 chapters: "Под куполом" by King Stephen |
| 4 | Dan Simmons\Мерзость | 3 | 🟢 track tags 1–3, no gaps or duplicates | 🟡 Симмонс Дэн <br><sub>other script; order ignored</sub> | 🟢 Мерзость | **Approvable now** — one M4B, 3 chapters: "Мерзость" by Simmons Dan |
| 5 | Stephen King | 3 | 🟢 track tags 1–3, no gaps or duplicates | 🟡 Стивен Кинг <br><sub>other script; order ignored</sub> | 🟢 Ловец снов | **Approvable now** — one M4B, 3 chapters: "Ловец снов" by King Stephen |
| 6 | Dan Simmons\Дэн Симмонс - Песни Гипериона - Книга 2 - Падение Гипериона | 3 | 🟢 track tags 1–3, no gaps or duplicates | 🟢 Дэн Симмонс | 🟢 Падение Гипериона | **Approvable now** — one M4B, 3 chapters: "Падение Гипериона" by Simmons Dan |
| 7 | Сборники | 2 | 🟢 track tags 1–2, no gaps or duplicates | 🔴 — <br><sub>embedded artist "Сборник" names a collection, not an author</sub> | 🟢 Страшные истории от Ворона | **Approvable now** — one M4B, 2 chapters: "Страшные истории от Ворона" by Разные авторы |
| 8 | James S. A. Corey\4. Пожар Сиболы | 2 | 🟢 track tags 1–2, no gaps or duplicates | 🟡 Джеймс Кори <br><sub>other script; order ignored; initials/patronymic ignored</sub> | 🟢 Пожар Сиболы | **Approvable now** — one M4B, 2 chapters: "Пожар Сиболы" by Corey James S. A. |
| 9 | ПАМЯТЬ О ПРОШЛОМ ЗЕМЛИ\Лю Цысинь - Вечная жизнь Смерти (Оробчук С.) | 2 | 🟢 track tags 1–2, no gaps or duplicates | 🟢 Лю Цысинь | 🟢 Вечная жизнь Смерти | **Approvable now** — one M4B, 2 chapters: "Вечная жизнь Смерти" by Лю Цысинь |
| 10 | Robert R. McCammon | 2 | 🟢 track tags 1–2, no gaps or duplicates | 🟡 Роберт Маккаммон <br><sub>other script; order ignored; initials/patronymic ignored</sub> | 🟢 Моё! | **Approvable now** — one M4B, 2 chapters: "Моё!" by McCammon Robert R. |
| 11 | Stephen King\Стивен Кинг - Безнадёга (BIGBAG) | 2 | 🟢 track tags 1–2, no gaps or duplicates | 🟢 Стивен Кинг | 🟢 Безнадёга | **Approvable now** — one M4B, 2 chapters: "Безнадёга" by King Stephen |
| 12 | Peter Straub | 2 | 🟢 track tags 1–2, no gaps or duplicates | 🟡 Питер Страуб <br><sub>other script; order ignored</sub> | 🟢 Магия кошмара | **Approvable now** — one M4B, 2 chapters: "Магия кошмара" by Straub Peter |
| 13 | Clive Barker | 2 | 🟢 track tags 1–2, no gaps or duplicates | 🟡 Клайв Баркер <br><sub>other script; order ignored</sub> | 🟢 Явление тайны | **Approvable now** — one M4B, 2 chapters: "Явление тайны" by Barker Clive |
| 14 | Leigh Bardugo | 2 | 🟢 track tags 1–2, no gaps or duplicates | 🟡 Ли Бардуго <br><sub>other script; order ignored</sub> | 🟢 Продажное королевство | **Approvable now** — one M4B, 2 chapters: "Продажное королевство" by Leigh Bardugo |
| 15 | Robert R. McCammon\МЭТЬЮ КОРБЕТТ\6. Свобода Маски | 3 | 🟢 track tags 1–3, no gaps or duplicates | ⚪ Роберт Маккаммон <br><sub>only one local source names it</sub> | 🟢 Свобода Маски | Grouped; identity needs research (existing path): author: only one local source names it |
| 16 | Herbert Frank\Dune\3 Children of Dune | 3 | 🟢 track tags 1–3, no gaps or duplicates | ⚪ Фрэнк Герберт <br><sub>only one local source names it</sub> | 🟢 Дети Дюны | Grouped; identity needs research (existing path): author: only one local source names it |
| 17 | Пехов Алексей\Страж\Золотые костры | 2 | 🟢 track tags 1–2, no gaps or duplicates | ⚪ Пехов Алексей <br><sub>only one local source names it</sub> | 🟢 Золотые костры | Grouped; identity needs research (existing path): author: only one local source names it |
| 18 | ПАМЯТЬ О ПРОШЛОМ ЗЕМЛИ\1383. Шаровая молния (Игорь Князев) | 2 | 🟢 track tags 1–2, no gaps or duplicates | ⚪ Лю Цысинь <br><sub>only one local source names it</sub> | 🟢 Шаровая молния | Grouped; identity needs research (existing path): author: only one local source names it |
| 19 | Harry Potter\67. Книга 6 - Гарри Поттер и Принц-полукровка (Александр Клюквин) | 2 | 🟢 track tags 1–2, no gaps or duplicates | ⚪ Джоан Роулинг <br><sub>only one local source names it</sub> | 🟢 Гарри Поттер и Принц-полукровка | Grouped; identity needs research (existing path): author: only one local source names it |
| 20 | Сборники\Splatterpunk Stories\Splatterpunk stories 2 (Шокирующие истории 2) | 2 | 🟢 track tags 1–2, no gaps or duplicates | ⚪ Лаймон Ричард, Фрост Грегори, Меллик Карлтон, Мьёвиль Чай… <br><sub>only one local source names it</sub> | 🔴 Splatterpunk stories 2 (Шокирующие истории 2) <br><sub>the title names a part, chapter or numbered file; one part is not the whole book</sub> | Grouped; identity needs research (existing path): title: the title names a part, chapter or numbered file; one part is not the whole book; author: only one local source names it |

Sample: the largest approvable book plus a fixed-seed (20261013) draw of 13 more approvable and 6 research-path books. Candidate ids and member paths are in the measurement output (scratchpad, not in Git).
