# Books Arranger: renames in Audiobooks Sorted, listed before anything moves (2026-10-24)

Ender, for 0.22.0 phase 5 (`Team/Docs/BooksArranger_AuthorRulings_2026-10-24.md`: folder language rule, Pratchett, the duplicate pairs; `Team/Docs/BooksArranger_Rulings_2026-10-24.md` items 16 and 17). **Nothing on Z: was renamed, moved or written.** Z: was only listed (`find "Z:\Audiobooks Sorted" -name "*.m4b"`: 505 books in 155 top-level folders); the rest comes from a read-only copy of the live catalog (SQLite backup API, `mode=ro`, `query_only`), taken 2026-10-24 12:45.

## Result

| | Folders | Books |
| --- | ---: | ---: |
| A. Pratchett | 1 | 6 |
| B. Duplicate pairs (merge) | 16 | 27 |
| C. Folder language rule | 16 | 30 |
| **Author folders to rename or merge** | **33** | **63** |
| 16. Converted books shaped like «Сказка» (Russian title, English-spelled author, language Unknown) | — | 127 |
| 17. Series prefix for books in Sorted (series backfill) | — | see section 17 |

**Phase 5 stopped at this list** (the brief's STOP condition): the app's relocation path cannot apply these renames today. Section "What is missing" says why and what it would take.

## Author folders: from -> to

Books: the .m4b files in the folder now (Z: listing). "Target has": books already in the target folder. "check": my reading of the folder language rule (an English folder name for an author who does not write in Russian, a Russian one for an author who does) on a name Sergei did not name; "sure": Sergei named it or it is one of his duplicate pairs.

### A. Pratchett

| From | To | Books | Target has | Why | |
| --- | --- | ---: | ---: | --- | --- |
| Pratchet Terry | Pratchett Terry | 6 | 0 | two t's (AuthorRulings: Merges and spellings) | sure |

### B. Duplicate pairs (merge)

| From | To | Books | Target has | Why | |
| --- | --- | ---: | ---: | --- | --- |
| Баркер Клайв | Barker Clive | 1 | 9 | one person; target by the folder language rule | sure |
| Zahn Thimoty | Zahn Timothy | 1 | 2 | one person; target by the folder language rule | sure |
| Лаймон Ричард Карл | Laymon Richard | 1 | 5 | one person; target by the folder language rule | sure |
| Ходжсон Уильям | Hodgson William Hope | 1 | 0 | one person; target by the folder language rule | sure |
| Ходжсон Уильям Хоуп | Hodgson William Hope | 2 | 0 | one person; target by the folder language rule | sure |
| Хардинг Фрэнсис | Frances Hardinge | 3 | 1 | one person; target by the folder language rule | sure |
| Роулинг Джоан | Rowling J. K | 1 | 1 | one person; target by the folder language rule | sure |
| Шваб Виктория | Schwab Victoria | 1 | 1 | one person; target by the folder language rule | sure |
| Скальци Джон | Scalzi John | 1 | 2 | one person; target by the folder language rule | sure |
| Судзуки Кодзи | Suzuki Koji | 4 | 1 | one person; target by the folder language rule | sure |
| Вилсон Фрэнсис Пол | Wilson F. Paul | 1 | 1 | one person; target by the folder language rule | sure |
| Карпишин Дрю | Drew Karpyshyn | 1 | 2 | one person; target by the folder language rule | sure |
| Хайнлайн Роберт | Heinlein Robert A | 1 | 4 | one person; target by the folder language rule | sure |
| Симада Содзи | Shimada Sōji | 1 | 0 | one person; target by the folder language rule | sure |
| 島田 荘司 _ Shimada Sōji | Shimada Sōji | 1 | 0 | one person; target by the folder language rule | sure |
| Гжендович Ярослав | Jarosław J. Grzędowicz | 6 | 2 | one person; target by the folder language rule | sure |

### C. Folder language rule

| From | To | Books | Target has | Why | |
| --- | --- | ---: | ---: | --- | --- |
| Max Fray | Фрай Макс | 12 | 0 | writes in Russian | sure |
| Хаггард Генри Райдер | Haggard H. Rider | 1 | 0 | English writer (Sergei's example) | sure |
| Фаррер Мэтью | Farrer Matthew | 1 | 0 | English writer (Sergei's example) | sure |
| Бром Джеральд | Brom Gerald | 1 | 0 | American writer | check |
| Данн Кэтрин | Dunn Katherine | 1 | 0 | American writer | check |
| Клэпхем Марк | Clapham Mark | 1 | 0 | British writer | check |
| Колфер Йон | Colfer Eoin | 1 | 0 | Irish writer | check |
| Кэмпбелл Рэмси | Campbell Ramsey | 4 | 0 | British writer | check |
| Леббон Тим | Lebbon Tim | 1 | 0 | British writer | check |
| Лиготти Томас | Ligotti Thomas | 1 | 0 | American writer | check |
| Райаниеми Ханну | Rajaniemi Hannu | 1 | 0 | Finnish, writes in English | check |
| Сафон Карлос Руис | Ruiz Zafón Carlos | 1 | 0 | Spanish writer | check |
| Файлс Джемма | Files Gemma | 1 | 0 | Canadian writer | check |
| Хоар Энди | Hoare Andy | 1 | 0 | British writer | check |
| Хокинг Люси и Хокинг Стивен | Hawking Lucy and Stephen | 1 | 0 | English writers; joint folder like «Moor and Kuttner» | check |
| Хокинг Стивен, Млодинов Леонард | Hawking and Mlodinow | 1 | 0 | English writers; joint folder like «Moor and Kuttner» | check |

Not renamed (the rule is already met, or they are not author folders): `Сборники`, `Warhammer 40K`, `Дозоры Сергея Лукьяненко`, the Russian authors in Cyrillic, the English authors in Latin, and first-name-first Latin folders such as «Tove Jansson» or «Juliet E. McKenna» (word order was not asked).

Future books already follow these targets: `author_rules` (commit d85888b) maps every spelling above that Sergei ruled on to its target, so a new Pratchett, Barker, Haggard, Farrer or Max Fray book lands in the target folder even before the old folder is renamed. The "check" rows are not in `author_rules` until Sergei confirms them.

## 16. Converted books shaped like «Сказка»

Sergei: rename all of them to their English original once a source confirms it ("All"). The original title is not known offline, so the "to" column needs the source lookup the new re-check would make. «Сказка» -> "Fairy Tale" (ruling 7) is the first case. Max Fray's 12 books are Russian originals: their titles stay; only the folder moves (section C).

| Author | Books |
| --- | ---: |
| King Stephen | 33 |
| Max Fray | 12 |
| Barker Clive | 7 |
| Stephenson Neal | 7 |
| Dick Philip K. | 7 |
| Laymon Richard | 5 |
| Pratchet Terry | 5 |
| Sapkowski Andrzej | 3 |
| Doyle Arthur Conan | 3 |
| McMahon Jennifer | 3 |
| Sawyer Robert J. | 3 |
| Sanderson Brandon | 2 |
| Leiber Fritz | 2 |
| Wilson Robert Charles | 2 |
| McCammon Robert R. | 2 |
| Connolly John | 1 |
| McGill Gordon | 1 |
| Blackwood Algernon | 1 |
| Wilson Colin | 1 |
| Russell Craig | 1 |
| Simmons Dan | 1 |
| Martin George R. R. | 1 |
| Hendrix Grady | 1 |
| Masterton Graham | 1 |
| Asimov Isaac | 1 |
| Ketchum Jack | 1 |
| Herbert James | 1 |
| Rollins James | 1 |
| Corey James S. A. | 1 |
| VanderMeer Jeff | 1 |
| Kaku Michio | 1 |
| Moor and Kuttner | 1 |
| Anderson Paul | 1 |
| Fracassi Philip | 1 |
| Yancey Rick | 1 |
| Beckett Simon | 1 |
| Zahn Thimoty | 1 |
| Hawking Stephen | 1 |
| Neil Gaiman &Terry Pratchett | 1 |
| Dembski-Bowden Aaron | 1 |
| Langan John | 1 |
| Malerman Josh | 1 |
| Gibson William | 1 |
| Gaiman Neil | 1 |
| Curran Tim | 1 |
| Little Bentley | 1 |

<details><summary>All 127 books (current path)</summary>

- Anderson Paul - «Три сердца и три льва» - `Z:\Audiobooks\Anderson Paul\Три сердца и три льва - Anderson Paul.m4b`
- Asimov Isaac - «Основание» - `Z:\Audiobooks\Asimov Isaac\Основание - Asimov Isaac.m4b`
- Barker Clive - «Абарат» - `Z:\Audiobooks\Barker Clive\Абарат - Barker Clive.m4b`
- Barker Clive - «Лес на холме» - `Z:\Audiobooks\Barker Clive\Лес на холме - Barker Clive.m4b`
- Barker Clive - «Примирение. Главы 37-48» - `Z:\Audiobooks\Barker Clive\Имаджика - 3 - Примирение. Главы 37-48 - Barker Clive.m4b`
- Barker Clive - «Примирение. Главы 49-62» - `Z:\Audiobooks\Barker Clive\Имаджика - 4 - Примирение. Главы 49-62 - Barker Clive.m4b`
- Barker Clive - «Пропащие души» - `Z:\Audiobooks\Barker Clive\Гарри Д'Амур - 2 - Пропащие души - Barker Clive.m4b`
- Barker Clive - «Пятый Доминион. Главы 1-20» - `Z:\Audiobooks\Barker Clive\Имаджика - 1 - Пятый Доминион. Главы 1-20 - Barker Clive.m4b`
- Barker Clive - «Пятый Доминион. Главы 21-36» - `Z:\Audiobooks\Barker Clive\Имаджика - 2 - Пятый Доминион. Главы 21-36 - Barker Clive.m4b`
- Beckett Simon - «Доктор Дэвид Хантер 05. Мертвые не лгут» - `Z:\Audiobooks\Beckett Simon\Доктор Дэвид Хантер 05. Мертвые не лгут - Beckett Simon.m4b`
- Blackwood Algernon - «Избранные рассказы и повести» - `Z:\Audiobooks\Blackwood Algernon\Избранные рассказы и повести - Blackwood Algernon.m4b`
- Connolly John - «Ночные легенды. Избранное» - `Z:\Audiobooks\Connolly John\Ночные легенды. Избранное - Connolly John.m4b`
- Corey James S. A. - «Истории» - `Z:\Audiobooks\Corey James S. A\Истории - Corey James S. A.m4b`
- Curran Tim - «Подземелье» - `Z:\Audiobooks Sorted\Curran Tim\Подземелье - Curran Tim.m4b`
- Dembski-Bowden Aaron - «Ядро» - `Z:\Audiobooks\Dembski-Bowden Aaron\Ядро - Dembski-Bowden Aaron.m4b`
- Dick Philip K. - «Бегущий по лезвию бритвы» - `Z:\Audiobooks\Dick Philip K\Бегущий по лезвию бритвы - Dick Philip K.m4b`
- Dick Philip K. - «Лабиринт смерти» - `Z:\Audiobooks\Dick Philip K\Лабиринт смерти - Dick Philip K.m4b`
- Dick Philip K. - «Сдвиг времени по-марсиански» - `Z:\Audiobooks\Dick Philip K\Сдвиг времени по-марсиански - Dick Philip K.m4b`
- Dick Philip K. - «Убик» - `Z:\Audiobooks\Dick Philip K\Убик - Dick Philip K.m4b`
- Dick Philip K. - «Унылый незнакомец» - `Z:\Audiobooks\Dick Philip K\Унылый незнакомец - Dick Philip K.m4b`
- Dick Philip K. - «Человек в Высоком замке» - `Z:\Audiobooks\Dick Philip K\Человек в Высоком замке - Dick Philip K.m4b`
- Dick Philip K. - «Электрические сны» - `Z:\Audiobooks\Dick Philip K\Электрические сны - Dick Philip K.m4b`
- Doyle Arthur Conan - «Воспоминания о Шерлоке Холмсе» - `Z:\Audiobooks\Doyle Arthur Conan\Шерлок Холмс - 2 - Воспоминания о Шерлоке Холмсе - Doyle Arthur Conan.m4b`
- Doyle Arthur Conan - «Его прощальный поклон» - `Z:\Audiobooks\Doyle Arthur Conan\Sherlock Holmes - 3 - Его прощальный поклон - Doyle Arthur Conan.m4b`
- Doyle Arthur Conan - «Сборник рассказов» - `Z:\Audiobooks\Doyle Arthur Conan\Сборник рассказов - Doyle Arthur Conan.m4b`
- Fracassi Philip - «Дитя среди чужих» - `Z:\Audiobooks\Fracassi Philip\Дитя среди чужих - Fracassi Philip.m4b`
- Gaiman Neil - «ИСТОРИЯ ОДНОЙ ЛЮБВИ» - `Z:\Audiobooks\Gaiman Neil\ИСТОРИЯ ОДНОЙ ЛЮБВИ - Gaiman Neil.m4b`
- Gibson William - «Сборник рассказов» - `Z:\Audiobooks\Gibson William\Сборник рассказов - Gibson William.m4b`
- Hawking Stephen - «Черные дыры и молодые вселенные» - `Z:\Audiobooks\Hawking Stephen\Черные дыры и молодые вселенные - Hawking Stephen.m4b`
- Hendrix Grady - «Группа поддержки для выживших девушек» - `Z:\Audiobooks\Hendrix Grady\Группа поддержки для выживших девушек - Hendrix Grady.m4b`
- Herbert James - «Туман» - `Z:\Audiobooks\Herbert James\Туман - Herbert James.m4b`
- Kaku Michio - «Гиперпространство» - `Z:\Audiobooks\Kaku Michio\Гиперпространство - Kaku Michio.m4b`
- Ketchum Jack - «"Стервятники" книга 1 "Мертвый сезон"» - `Z:\Audiobooks\Ketchum Jack\_Стервятники_ книга 1 _Мертвый сезон_ - Ketchum Jack.m4b`
- King Stephen - «81 миля» - `Z:\Audiobooks\King Stephen\81 миля - King Stephen.m4b`
- King Stephen - «ВЗРОСЛЫЕ» - `Z:\Audiobooks\King Stephen\Оно - 4 - ВЗРОСЛЫЕ - King Stephen.m4b`
- King Stephen - «Возрождение» - `Z:\Audiobooks\King Stephen\Возрождение - King Stephen.m4b`
- King Stephen - «Воспарение» - `Z:\Audiobooks\King Stephen\Воспарение - King Stephen.m4b`
- King Stephen - «Все предельно» - `Z:\Audiobooks\King Stephen\Все предельно - King Stephen.m4b`
- King Stephen - «Две убитых девочки» - `Z:\Audiobooks\King Stephen\Зелёная миля - 1 - Две убитых девочки - King Stephen.m4b`
- King Stephen - «Дурной Сон Дэнни Кофлина» - `Z:\Audiobooks\King Stephen\Дурной Сон Дэнни Кофлина - King Stephen.m4b`
- King Stephen - «ИЮЛЬ 1958 ГОДА. 1» - `Z:\Audiobooks\King Stephen\Оно - 5 - ИЮЛЬ 1958 ГОДА. 1 - King Stephen.m4b`
- King Stephen - «ИЮЛЬ 1958 ГОДА. 2» - `Z:\Audiobooks\King Stephen\Оно - 6 - ИЮЛЬ 1958 ГОДА. 2 - King Stephen.m4b`
- King Stephen - «ИЮНЬ 1958 ГОДА. 1» - `Z:\Audiobooks\King Stephen\Оно - 2 - ИЮНЬ 1958 ГОДА. 1 - King Stephen.m4b`
- King Stephen - «ИЮНЬ 1958 ГОДА. 2» - `Z:\Audiobooks\King Stephen\Оно - 3 - ИЮНЬ 1958 ГОДА. 2 - King Stephen.m4b`
- King Stephen - «Институт» - `Z:\Audiobooks\King Stephen\Институт - King Stephen.m4b`
- King Stephen - «Как писать книги» - `Z:\Audiobooks\King Stephen\Как писать книги - King Stephen.m4b`
- King Stephen - «Коффи проходит милю» - `Z:\Audiobooks\King Stephen\Зелёная миля - 6 - Коффи проходит милю - King Stephen.m4b`
- King Stephen - «Лангольеры» - `Z:\Audiobooks\King Stephen\Лангольеры - King Stephen.m4b`
- King Stephen - «Мобильник» - `Z:\Audiobooks Sorted\King Stephen\Мобильник - King Stephen.m4b`
- King Stephen - «Мышь на миле» - `Z:\Audiobooks\King Stephen\Зелёная миля - 2 - Мышь на миле - King Stephen.m4b`
- King Stephen - «Низкие люди в желтых плащах» - `Z:\Audiobooks\King Stephen\Низкие люди в желтых плащах - King Stephen.m4b`
- King Stephen - «Ночное путешествие» - `Z:\Audiobooks\King Stephen\Зелёная миля - 5 - Ночное путешествие - King Stephen.m4b`
- King Stephen - «Позже» - `Z:\Audiobooks\King Stephen\Позже - King Stephen.m4b`
- King Stephen - «Полицейский из библиотеки» - `Z:\Audiobooks\King Stephen\Полицейский из библиотеки - King Stephen.m4b`
- King Stephen - «Почти как Бьюик» - `Z:\Audiobooks\King Stephen\Почти как Бьюик - King Stephen.m4b`
- King Stephen - «РИТУАЛ ЧУДЬ» - `Z:\Audiobooks\King Stephen\Оно - 7 - РИТУАЛ ЧУДЬ - King Stephen.m4b`
- King Stephen - «Руки Джона Коффи» - `Z:\Audiobooks\King Stephen\Зелёная миля - 3 - Руки Джона Коффи - King Stephen.m4b`
- King Stephen - «Сказка» - `Z:\Audiobooks Sorted\King Stephen\Сказка - King Stephen.m4b`
- King Stephen - «Страна Радости» - `Z:\Audiobooks\King Stephen\Страна Радости - King Stephen.m4b`
- King Stephen - «Счастливый брак» - `Z:\Audiobooks\King Stephen\Счастливый брак - King Stephen.m4b`
- King Stephen - «ТЕНЬ ПРОШЛОГО» - `Z:\Audiobooks\King Stephen\Оно - 1 - ТЕНЬ ПРОШЛОГО - King Stephen.m4b`
- King Stephen - «Темная половина» - `Z:\Audiobooks\King Stephen\Темная половина - King Stephen.m4b`
- King Stephen - «Томминокеры» - `Z:\Audiobooks\King Stephen\Томминокеры - King Stephen.m4b`
- King Stephen - «Ужасная смерть Эдуарда Делакруа» - `Z:\Audiobooks\King Stephen\Зелёная миля - 4 - Ужасная смерть Эдуарда Делакруа - King Stephen.m4b`
- King Stephen - «Худеющий» - `Z:\Audiobooks\King Stephen\Худеющий - King Stephen.m4b`
- King Stephen - «Цикл оборотня» - `Z:\Audiobooks\King Stephen\Цикл оборотня - King Stephen.m4b`
- Langan John - «Сефира и другие предательства» - `Z:\Audiobooks\Langan John\Сефира и другие предательства - Langan John.m4b`
- Laymon Richard - «Берегись!» - `Z:\Audiobooks\Laymon Richard\Берегись! - Laymon Richard.m4b`
- Laymon Richard - «Зачистка» - `Z:\Audiobooks\Laymon Richard\Зачистка - Laymon Richard.m4b`
- Laymon Richard - «Когда погаснет свет» - `Z:\Audiobooks\Laymon Richard\Когда погаснет свет - Laymon Richard.m4b`
- Laymon Richard - «Кол» - `Z:\Audiobooks\Laymon Richard\Кол - Laymon Richard.m4b`
- Laymon Richard - «Одной дождливой ночью» - `Z:\Audiobooks\Laymon Richard\Одной дождливой ночью - Laymon Richard.m4b`
- Leiber Fritz - «Ведьма» - `Z:\Audiobooks\Leiber Fritz\Ведьма - Leiber Fritz.m4b`
- Leiber Fritz - «Чёрный гондольер» - `Z:\Audiobooks\Leiber Fritz\Чёрный гондольер - Leiber Fritz.m4b`
- Little Bentley - «Округа» - `Z:\Audiobooks Sorted\Little Bentley\Округа - Little Bentley.m4b`
- Malerman Josh - «Птичий короб 02. Мэлори» - `Z:\Audiobooks\Malerman Josh\Птичий короб 02. Мэлори - Malerman Josh.m4b`
- Martin George R. R. - «Пламя и кровь. Том первый» - `Z:\Audiobooks\Martin George R. R\Пламя и кровь. Том первый - Martin George R. R.m4b`
- Masterton Graham - «Джинн» - `Z:\Audiobooks\Masterton Graham\Джинн - Masterton Graham.m4b`
- Max Fray - «02 Неуловимый Хабба Хэн» - `Z:\Audiobooks Sorted\Max Fray\02 Неуловимый Хабба Хэн - Max Fray.m4b`
- Max Fray - «02 Чужак» - `Z:\Audiobooks Sorted\Max Fray\02 Чужак - Max Fray.m4b`
- Max Fray - «06 Корабль из Арвароха и другие неприятности» - `Z:\Audiobooks Sorted\Max Fray\06 Корабль из Арвароха и другие неприятности - Max Fray.m4b`
- Max Fray - «07 ОЧКИ БАККИ БУГВИНА» - `Z:\Audiobooks Sorted\Max Fray\07 ОЧКИ БАККИ БУГВИНА - Max Fray.m4b`
- Max Fray - «08 Волонтеры вечности» - `Z:\Audiobooks Sorted\Max Fray\08 Волонтеры вечности - Max Fray.m4b`
- Max Fray - «102 Туланский детектив» - `Z:\Audiobooks Sorted\Max Fray\102 Туланский детектив - Max Fray.m4b`
- Max Fray - «11 Тёмные вассалы Гленке Тавала» - `Z:\Audiobooks Sorted\Max Fray\11 Тёмные вассалы Гленке Тавала - Max Fray.m4b`
- Max Fray - «14 Сладкие грезы Гравви» - `Z:\Audiobooks Sorted\Max Fray\14 Сладкие грезы Гравви - Max Fray.m4b`
- Max Fray - «15 Возвращение Угурбадо» - `Z:\Audiobooks Sorted\Max Fray\15 Возвращение Угурбадо - Max Fray.m4b`
- Max Fray - «18 Болтливый мертвец» - `Z:\Audiobooks Sorted\Max Fray\18 Болтливый мертвец - Max Fray.m4b`
- Max Fray - «19 Наследство для Лонли-Локли» - `Z:\Audiobooks Sorted\Max Fray\19 Наследство для Лонли-Локли - Max Fray.m4b`
- Max Fray - «23 Тихий город» - `Z:\Audiobooks Sorted\Max Fray\23 Тихий город - Max Fray.m4b`
- McCammon Robert R. - «Они жаждут» - `Z:\Audiobooks\McCammon Robert R\Они жаждут - McCammon Robert R.m4b`
- McCammon Robert R. - «Синий мир» - `Z:\Audiobooks\McCammon Robert R\Синий мир - McCammon Robert R.m4b`
- McGill Gordon - «Последняя схватка» - `Z:\Audiobooks\McGill Gordon\Последняя схватка - McGill Gordon.m4b`
- McMahon Jennifer - «Молчание» - `Z:\Audiobooks\McMahon Jennifer\Молчание - McMahon Jennifer.m4b`
- McMahon Jennifer - «Обещай, что никому не скажешь» - `Z:\Audiobooks\McMahon Jennifer\Обещай, что никому не скажешь - McMahon Jennifer.m4b`
- McMahon Jennifer - «Остров потерянных детей» - `Z:\Audiobooks\McMahon Jennifer\Остров потерянных детей - McMahon Jennifer.m4b`
- Moor and Kuttner - «Механическое эго» - `Z:\Audiobooks\Moor and Kuttner\Механическое эго - Moor and Kuttner.m4b`
- Neil Gaiman &Terry Pratchett - «Добрые предзнаменования» - `Z:\Audiobooks\Neil Gaiman &Terry Pratchett\Добрые предзнаменования - Neil Gaiman &Terry Pratchett.m4b`
- Pratchet Terry - «Ведьмы за границей» - `Z:\Audiobooks\Pratchet Terry\Ведьмы - 3 - Ведьмы за границей - Pratchet Terry.m4b`
- Pratchet Terry - «Вещие Сёстры» - `Z:\Audiobooks\Pratchet Terry\Ведьмы - 2 - Вещие Сёстры - Pratchet Terry.m4b`
- Pratchet Terry - «Книги номов 02. Землекопы» - `Z:\Audiobooks\Pratchet Terry\Книги номов 02. Землекопы - Pratchet Terry.m4b`
- Pratchet Terry - «Книги номов. Кн. 01. Угонщики» - `Z:\Audiobooks Sorted\Pratchet Terry\Книги номов. Кн. 01. Угонщики - Pratchet Terry.m4b`
- Pratchet Terry - «Народ, или когда-то мы были дельфинами» - `Z:\Audiobooks\Pratchet Terry\Народ, или когда-то мы были дельфинами - Pratchet Terry.m4b`
- Rollins James - «Отряд Сигма_01. Песчанный дьявол» - `Z:\Audiobooks\Rollins James\Отряд Сигма_01. Песчанный дьявол - Rollins James.m4b`
- Russell Craig - «Кровавый орёл» - `Z:\Audiobooks\Russell Craig\Йэн Фабель - 1 - Кровавый орёл - Russell Craig.m4b`
- Sanderson Brandon - «Архив Буресвета 1 - Путь королей» - `Z:\Audiobooks\Sanderson Brandon\Архив Буресвета 1 - Путь королей - Sanderson Brandon.m4b`
- Sanderson Brandon - «Рассказы» - `Z:\Audiobooks\Sanderson Brandon\Рассказы - Sanderson Brandon.m4b`
- Sapkowski Andrzej - «Witcher 9 - Вороний перекрёсток» - `Z:\Audiobooks Sorted\Sapkowski Andrzej\Witcher 9 - Вороний перекрёсток - Sapkowski Andrzej.m4b`
- Sapkowski Andrzej - «Сага о Рейневане 03. Свет вечный» - `Z:\Audiobooks\Sapkowski Andrzej\Сага о Рейневане 03. Свет вечный - Sapkowski Andrzej.m4b`
- Sapkowski Andrzej - «Сборник рассказов» - `Z:\Audiobooks\Sapkowski Andrzej\Сборник рассказов - Sapkowski Andrzej.m4b`
- Sawyer Robert J. - «Золотое руно» - `Z:\Audiobooks\Sawyer Robert J\Золотое руно - Sawyer Robert J.m4b`
- Sawyer Robert J. - «Неандертальский параллакс. Гоминиды» - `Z:\Audiobooks\Sawyer Robert J\Неандертальский параллакс. Гоминиды - Sawyer Robert J.m4b`
- Sawyer Robert J. - «Неандертальский параллакс. Люди» - `Z:\Audiobooks\Sawyer Robert J\Неандертальский параллакс. Люди - Sawyer Robert J.m4b`
- Simmons Dan - «Песнь Кали» - `Z:\Audiobooks\Simmons Dan\Песнь Кали - Simmons Dan.m4b`
- Stephenson Neal - «Анафем» - `Z:\Audiobooks\Stephenson Neal\Анафем - Stephenson Neal.m4b`
- Stephenson Neal - «Большая симолеоновая афера» - `Z:\Audiobooks\Stephenson Neal\Большая симолеоновая афера - Stephenson Neal.m4b`
- Stephenson Neal - «Криптономикон» - `Z:\Audiobooks\Stephenson Neal\Енох Роот - 1 - Криптономикон - Stephenson Neal.m4b`
- Stephenson Neal - «Лавина» - `Z:\Audiobooks\Stephenson Neal\История будущего - 1 - Лавина - Stephenson Neal.m4b`
- Stephenson Neal - «Падение, или Додж в Аду. Книга первая» - `Z:\Audiobooks\Stephenson Neal\Падение, или Додж в Аду. Книга первая - Stephenson Neal.m4b`
- Stephenson Neal - «Семиевие» - `Z:\Audiobooks\Stephenson Neal\Семиевие - Stephenson Neal.m4b`
- Stephenson Neal - «Синдром отката» - `Z:\Audiobooks\Stephenson Neal\Синдром отката - Stephenson Neal.m4b`
- VanderMeer Jeff - «Дарден влюбленный» - `Z:\Audiobooks\VanderMeer Jeff\Дарден влюбленный - VanderMeer Jeff.m4b`
- Wilson Colin - «Возвращение ллойгор» - `Z:\Audiobooks\Wilson Colin\Возвращение ллойгор - Wilson Colin.m4b`
- Wilson Robert Charles - «Спин-01 Спин» - `Z:\Audiobooks\Wilson Robert Charles\Спин-01 Спин - Wilson Robert Charles.m4b`
- Wilson Robert Charles - «Спин-02 Ось» - `Z:\Audiobooks\Wilson Robert Charles\Спин-02 Ось - Wilson Robert Charles.m4b`
- Yancey Rick - «Ступени, ведущие в бездну» - `Z:\Audiobooks\Yancey Rick\The Monstrumologist - 4 - Ступени, ведущие в бездну - Yancey Rick.m4b`
- Zahn Thimoty - «Траун» - `Z:\Audiobooks\Zahn Thimoty\Траун - Zahn Thimoty.m4b`

</details>

## 17. Series backfill in Sorted

The series backfill names a book relative to `manifest['root']`, the source root. For a book in Sorted that name never equals its real path, so every Sorted book stops at "The audiobook's name does not follow the app's naming" (Senua 0.21.3 F5). In the catalog copy the backfill has 87 books `done` (all renamed in their source folders before 0.21.3), 375 `deferred` (sources closed or rate-limited) and 8 `held`; none of the Sorted books has reached its rename. Which Sorted books get a prefix is known only once their series lookup finishes, so this section cannot list from -> to yet.

## What is missing (why phase 5 stopped)

The app has two rename paths, and neither can apply sections A-C or 16 today:

1. **The reviewed relocation path** (`migration_planning.py`, `migration_operation.py`, `output_rename.py`) is an offline operator tool. It needs exclusive catalog ownership, so the live app must be closed (the brief says not to stop it). It runs one reviewed publication per call from a SHA-pinned plan file, and it has no in-app entry.
2. **It refuses identity changes by design.** `migration_planning._prepare`: "Routing decision cannot replace canonical identity" (a decision may set only `universe` and `multi_author`). An author-folder rename or a title rename changes the book's canonical author or title, so the planner cannot express it at all.
3. **The output's tags would still name the old author.** A folder rename alone leaves ARTIST, sort-artist and the title items as they are. Sergei asked for corrected tags ("write the corrected tags into the output"). Only the series backfill rewrites tags in place, and only the album, grouping, sort-album and track items (`quicktime_chapters.retag`).
4. **For item 16 there is no original-title re-check.** It would be a third backfill pass, like series backfill: look the original title up, retag the title and sort-title items, rename, record, with the same proofs.

**Proposed shape (needs a decision before building):** one in-app "rename in Sorted" pass built on the series backfill: per book, retag (ARTIST, sort-artist, album-artist, title items) with the same byte proofs, rename on the same volume, never over an existing file, update the catalog and the review in one transaction, and remove the old file only after the new one is proven. Folder merges are then just renames into an existing folder. It runs one book at a time while the app is idle, as series backfill does.

Series backfill (item 17) is different: it is already the app's own in-process rename path with its proofs; only its root is wrong. Fixing F5 (this branch) lets it work in Sorted.
