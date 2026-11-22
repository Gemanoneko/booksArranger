# Books Arranger 0.31.0 — series, English titles, honest status

Scope and rulings, 2026-11-22 (Jane, from Sergei's answers that day). Diagnosis: Ender, read-only, on HEAD `e1f822d` (0.30.1) and a copy of the live catalog. Source research: `Team/Research/BooksArranger_WikidataSeriesSource_2026-11-22.md` in the studio repo (Makoto).

## Sergei's report

1. **Sprawl Trilogy (Gibson).** Two files, `02-Граф Ноль` and `03-Мона Лиза овердрайв`, both titled "Sprawl Trilogy", both going to one destination file, offered "Approve as one book". They are two novels of a series.
2. **Тёмный лес (Liu Cixin).** No series folder (Remembrance of Earth's Past), a Russian title for a book not written in Russian, and the author folder is `Cixin Liu`.
3. "The app should check the Internet more before it converts. Wikipedia is a great source for series and English names."
4. "How do I know that the app finished its queue and has nothing to do anymore?" and "what is 'Updating Metadata'?"

## Rulings — Sergei, 2026-11-22

| # | Ruling | Replaces |
| --- | --- | --- |
| R1 | **A translated book gets its English title, and its series folder is named in English.** Russian originals stay Russian. | 0.30.0 item 6 for non-Latin originals (Chinese, Japanese); completes Brief "Confirmed rules": "All other original works use English canonical titles/authors, including Russian translations." |
| R2 | **A book may wait for the online answer before it converts.** A limit of a few tries, then it converts as before. | "The book must not wait" (0.22.1) for the fields this scope names |
| R3 | **No English title found: keep the Russian title.** Do not ask. | — |
| R4 | **A series named in the file's own tags files the book without asking.** | — |
| R5 | **One online source naming a series is enough to file it.** No approval step. | — |
| R6 | **Already-sorted books are re-checked and moved into series folders as a separate job, run from the studio, not as an app feature.** New books must convert correctly by themselves. | — |
| R7 | **Start with steps 1 and 4 below.** | — |

### Second round — Sergei, 2026-11-22 (after the engine build and Judy's spec)

| # | Ruling |
| --- | --- |
| R8 | **The series look-up writes nothing into a finished book without approval until English names ship** (step 3). The write guard stays at `hold`; this covers the 282 flat-named finished books. |
| R9 | **Look-up tries: 3 per source, 6 hours apart.** Approved as built. |
| R10 | **The approval list shows every kind of change the plan holds: series and author folders too**, not series only. |
| R11 | **"Leave as it is" on a wrong series stops asking about that book for good** (the book, not the whole series). It can be taken back. |
| R12 | **Books whose original is Chinese or Japanese are held out of the approval list until English series names ship.** |
| R13 | **The window title shows the state** (`Books Arranger: all done`), so the taskbar answers. |
| R14 | **A drive that is not answering holds back "All done".** |
| R15 | **A file whose only clue is a title tag shaped "Series NN - Title" is filed without asking** (Neuromancer). R4 covers it. |
| R16 | **The look-up for original titles and author names gets the same limit** as the series look-up (3 tries per source). |
| R17 | **Where pieces of one book would all get one name and Approve is blocked, the reason may say "Join them into one book, or change this title."** Only on a blocked press; the 2026-11-18 "no Join hint on rows" otherwise stands. |

Left as they work today (Sergei did not change them): no "Try again" count for look-ups that gave up; no "Convert now" button on a book waiting for the online answer; a book already queued to convert is not stopped by a later same-name clash; the 22 older jobs planned without the series their tags name wait for R6's job.

Not ruled yet (ask before building on them): which source wins a disagreement; whether a parent folder named after the series counts as confirmation (ruling 55 says no); what to do with author names the app cannot order beyond the Liu Cixin fix; whether the series back-fill of old books keeps running once R6's job has been done.

## Steps

1. **Use what the files say** (no internet).
   - A volume the app separated is named from its own title tag, the same as one Sergei separated.
   - Series name and number are read from the sort-album and grouping tags ("Series. Книга N").
   - Two books never share one destination: when a planned name equals another row's or a queued job's, both are held.
2. **Look up before review, not after.** Wikidata for the English title, original language and series of translated books; FantLab for Russian originals. A match needs title + author + "is a written work", never the title alone. (R2, R5)
3. **One title rule in one place** (R1, R3), and the name order fix for authors such as Liu Cixin.
4. **Honest status.**
   - The series look-up of finished books must come to an end instead of retrying without limit.
   - A clear "all done" state that is true only when nothing is pending, background look-ups included.
   - Every background job is named in plain words; "Metadata: Updating series" says what it is.
   - A page control for the series-move approval, which today exists only as an API and a script.
   - Wording and layout: Judy, `BooksArranger_0.31.0_UX.md`.
5. **Already-sorted books** (R6): a separate job after steps 1–3 exist, since it needs their rules.

**0.31.0 = steps 1 and 4.** Steps 2 and 3 follow as the next version. Step 5 is a job, not a release.

## Facts the work rests on (Ender's diagnosis)

- Title is taken from the album tag before the title tag (`metadata.py:79`, `local_identity.py:2392-2393`); the volume-from-own-tag branch runs only for volumes Sergei separated (`local_identity.py:2524`).
- A held book returns before any online request (`public_research.py:1069-1073`).
- The sort-album tag is read only as a number cross-check (`source_identity.py:57-67`).
- Title language: `public_research.py:1469-1472` and `:746`. Wikidata's English label is read (`public_work_identity.py:96`) and dropped (`public_research.py:2009-2011`).
- `_latin_surname_first` (`public_research.py:2409-2419`) reverses a two-word name it cannot order.
- "Goes to" checks only the disk for a taken name (`merge_service.py:3541-3579`).
- Series back-fill: `series_backfill.py`. 741 of 903 ledger rows deferred, 706 re-tried within one hour, one row deferred 3,282 times; a book is recorded "no series" only when every source answered (`:439-441`), and DuckDuckGo is behind a human check. 55 books wait for a move approval that has no page control. Nothing written since 20 Oct.
- No "all done" state: `web/app.js:1344`, `:1494`, `:1650`, `:2913-2916`. Back-fill and gap fill between tries appear nowhere.
- Scale: 112 of 1,510 current books carry a sort-album or grouping tag with a book number and have no series; 92 finished books have a recorded English title never applied; 63 finished books sit in Latin author folders whose order the rule cannot check.
