# Books Arranger 0.31.0: UX spec (honest status)

Judy, 2026-11-22. For Ender. Source: `BooksArranger_0.31.0_Scope.md` (`d134484`; second round `d28f9ff`; third round `4a6c3a8`; fourth round `32ced7c`): Sergei's report, rulings R1 to R7 and, since the amendments of the same day, R8 to R22, step 4 ("Honest status"), the part of step 1 that shows on the page and, since the fourth round, the parts of steps 2 and 3 that show on the page. Sergei, 2026-11-22: "How do I know that the app finished its queue and have nothing to do anymore? ... But what is 'Updating Metadata'? Is it re-researching old books? Or is it still a first pass?"

**This is an EXTEND of `BooksArranger_0.30.0_UX.md`.** The jobs panel, the Waiting list, the freshness cue, the blocker sentence and every string not named here stay as built. Where this spec replaces a 0.30.0 line it says so.

Basis: read-only look at `web/app.js` (`jobsFirstPart`, `renderWaitingForYou`, `WORK_LABELS`, `workStep`, `waitingLines`, `renderAutomatic`, `holdSentence`, `HOLD_APPROVE`, `destPlan`, `placeText`, `scopeBasisText`), `web/index.html`, `web/style.css`, `background_work.py`, `series_backfill.py`, `gap_fill.py`, `sorting_moves.py`, `merge_service.py` (`sorting_moves`, `sorting_moves_apply`), `web_server.py` (`needs_you_only`, the two sorting routes). Nothing was launched and no rect was measured (Sergei's copy was converting). The app has one theme, dark (`color-scheme: dark`, no light tokens), so contrast is checked against the dark tokens only.

## Amended 2026-11-22 after build

Ender built sections 1 and 2 (branch `ender/0.31.0`) and hit nine gaps. Each is ruled here and written into its section, marked **Amended 2026-11-22 after build**. Read for this round, read-only: his `web/app.js` (`statusParts`, `jobsFirstPart`, `notReadable`, `badgeState`, `renderWaitingForYou`, `waitingLines`), `destination_clash.py`, and `merge_service.py` (`ask_payload`, `approval_preview`, `series_origin`, the two `same_name` refusals). Nothing launched, no rect measured.

Engine facts settled since the first version: 3 tries per source, 6 hours apart (since approved, R9); the detail look-up has no tries limit (since given the same one, R16); a guard holds every series write into a finished file until he approves it (**superseded by the fourth round, R20: the guard is switched to automatic in 0.31.0**); a book already waiting to convert keeps its name and only the newcomer row is held.

| Gap | Ruling | Where |
|---|---|---|
| G1 | "Not known" with no unread source is not a failed read. It reads `Checking what is left`. The "could be read" words stay for an unread source only. | 1.1, 1.3 |
| G2 | Not acceptable: the line never starts with the counts. While a finished state is reported and its badge is not up yet, the first part is `Checking what is left`. | 1.2 |
| G3 | Both singulars confirmed (with G5's noun). Every singular is in the table of 6.1. | 6.1 |
| G4 | Keep the line, as written. In a build without the dialog it has no button and is not reworded. It is released only together with section 3. **Withdrawn by the third round (R18): there is no such line and no dialog; the line is taken out.** | 1.4 |
| G5 | One count, one list. The word changes from "series moves" to **series changes**; in the dialog each book says `Moves to` or `Renamed to`. `Move N books` is `Add series to N books`; `Keep here` is `Leave as it is`. **Withdrawn by the third round (R18): there is no list, no dialog and no button of this kind under any name.** | 3.1 |
| G6 | Tooltip given. That the detail look-up never gives up is a product question (Question 8). **Superseded by Sergei's answers: R16 gives it the limit, and its tooltip is the series one.** | 2.2 |
| G7 | Not intended. A paused queue names the look-up that still runs, as 0.30.0 names any work Pause does not stop. | 2.1 |
| G8 | The tooltip takes the engine's numbers (tries per source, hours apart). Example corrected to 3. | 2.2 |
| G9 | The presentation follows the row's own question, never the mere presence of `shared`. Only a row held for the clash itself reads `Same name as another book`; a row with its own question keeps it, `Approve as one book` included. No new engine fact is needed. | 4.1, 4.2, 4.2a |

Also closed while reading the build: the Place line had no words for the engine's `folders` and `unknown` origins (4.3).

## Amended 2026-11-22, Sergei's answers

Sergei answered every question of this spec. His rulings are R8 to R17 in `BooksArranger_0.31.0_Scope.md` ("Second round", `d28f9ff`), which is the authority. Each is written into its section, marked **Amended 2026-11-22, Sergei's answers**.

**Three of these answers were replaced the same day by the third round (next section):** R10 and R11 are not built, and R12 is generalised by R19. The approval list this round named `Renames and moves`, its dialog, its shortcut, `Review changes`, `Leave as it is`, `Offer again` and `Left as they are` are withdrawn. None of those names is live anywhere in this spec.

| Question | Answer | Ruling | Where it went |
|---|---|---|---|
| 1 | The list holds every kind of change the plan holds, author folders too | R10 | **withdrawn by R18: there is no approval list** |
| 2 | `Leave as it is` is about the book, for good, and can be taken back | R11 | **withdrawn by R18: there is no refusal** |
| 3 | Books written in Chinese or Japanese are held out of the list | R12 | **generalised by R19: such a book is simply not moved yet**. **Fourth round (R20): English names ship in 0.31.0, so no book is held back for them.** |
| 4 | No count or Try again for look-ups that gave up | as recommended | 2.3 |
| 5 | No `Convert now` button | as recommended | 5 |
| 6 | The window title shows the state | R13 | 1.5: a title for every state |
| 7 | A drive that is not answering holds back `All done` | R14 | 1.1, as already specced |
| 8 | The look-up for titles and author names gets the same limit | R16 | 2.2: one tooltip for both look-ups |
| 9 | The blocked press may say `Join them into one book, or change this title.` | R17 | 4.2a |
| also | Nothing is written into a finished book without approval | R8 | **its "without approval" half replaced by R18**. **Fourth round (R20): the guard is switched to automatic in 0.31.0.** |
| also | Tries: 3 per source, 6 hours apart, approved as built | R9 | 2.2 |
| also | A title tag shaped "Series NN - Title" is filed without asking | R15 | 4.3 |

Questions 10 and 11, opened by this round, were closed by the third round.

## Amended 2026-11-22, third round (R18, R19)

Sergei dropped the approval list. The rulings are R18 and R19 in `BooksArranger_0.31.0_Scope.md` ("Third round", `4a6c3a8`), which is the authority. Every change they cause is marked **Amended 2026-11-22, third round (R18, R19)**. Where this round and an earlier one disagree, this round wins.

- **R18.** Finished audiobooks are renamed and moved by the rules, with no approval step, when author and series are found. A result that could be wrong is treated as if nothing was found: no question, no move. Sergei: "Why would you ask me in such a case? If the author and series are found, then put it in the folder according to our rules."
- **R19.** A book is not moved now if the next version will move it again. Such books wait and move once. **Fourth round (R20): English names ship in 0.31.0, so R19 is met inside the version and no book waits.**

**Two states, one page.** **Superseded by the fourth round (R20): there is one state. The guard is switched to automatic in 0.31.0, and the "guard at hold" variant is removed from every section.** As written in the third round: the write guard was at hold, the automatic move was to be switched on after Sergei approved Ender's certainty rule, and the page was the same in both states.

| What | Change | Where |
|---|---|---|
| Section 3 (the dialog, its shortcut, `Review changes`, `Leave as it is`, `Offer again`, `Left as they are`, the groups) | **Withdrawn. Not built.** The text is removed from this spec; it is in git at `9a10b46`. | 3 |
| Renames and moves as something he approves | Gone from "waits for you", from the status parts, from the Waiting-for-you block and from the finished-state logic | 1.1, 1.3, 1.4 |
| G4's interim line and check 16 | Removed: there is no line 2 and nothing to gate | 1.4, 9 |
| Books with a series found that are not moved | One quiet line, no count in the status, no hold on `All done` | 3.2 |
| A finished book being renamed or moved by the rules | Its own row label while the series is written; grouped Waiting items above 5 | 2.1, 2.2, 3.3 |
| What was moved, afterwards | A record: `Renamed or moved by the app · N`, read-only | 3.4 |
| A doubtful result | The book says nothing, anywhere | 3.5 |
| Series look-up tooltip | No longer mentions approval | 2.1 |
| Questions 10 and 11 | Closed by R18 and R19 | end |
| Row questions that ask about a series today | **Not changed.** One open point for Sergei (Question 12). **Fourth round (R22): answered yes; the three questions are gone, 4.4.** | end |

**What Ender changes on the page already built** (branch `ender/0.31.0`, read at `e1af686` plus his working changes):
1. Take out the status part `N series changes to approve` (`statusParts`).
2. Take out Waiting-for-you line 2 (`#jobs-you-moves`). The block shows for books that need attention only (1.4).
3. Engine: a series found and not applied is no longer a reason something waits for him (`moves` leaves the waits-for-you reasons and the state; the count stays, for the quiet line of 3.2).
4. Reword the series row's step tooltip: two sentences, by state, neither about approval (2.1).
5. Add the quiet line (3.2). **Fourth round: built; its words and its number change (3.2).**
6. A series write counts as main work, not as a look-up (1.1); the grouped Waiting items (2.2, 3.3); the record (3.4). **Fourth round: all of it is built in 0.31.0, with the additions listed in the fourth round's own section.**

The series row keeps its one label in both steps, as built.

Nothing of the old section 3 was built, so nothing of it has to be removed.

## Amended 2026-11-22, after the final build

Ender finished the 0.31.0 page (`ender/0.31.0`, `89f1f2a`) and reported six gaps. Each is ruled here and written into its section, marked **Amended 2026-11-22, after the final build**. Read for this round, read-only: his `web/app.js` (`sameNameSentence`, `sharedOf`, `buildShowBoth`, `showSameName`, `buildAskActions`, `seriesOriginText`) and `merge_service.series_origin`, `local_identity.py` at the brackets rule. Nothing launched, no rect measured.

| Gap | Ruling | Code | Where |
|---|---|---|---|
| 1. A same-name row whose clash has ended | Not confirmed. The sentence follows the row's latest answer, not the recorded hold: `The name is free now. Approve files the book under it.`, or the Name taken sentence when a file is now on disk. | yes, small: one function | 4.1 |
| 2. `Show both books` and the list's search | Change what the button does, with what exists: it lists **the other book**, by the folder or file name the engine already sends. New face `Show the other book`. Showing both at once needs a list filter by book ids, which is more than a small change: not in this spec (fourth round: it was marked "next version"; it is not one of the things R20 folds in). | yes, small: face, tooltip, search text | 4.2, 4.2a |
| 3. "Last button of the row" | Confirmed as built: after the row's ordinary buttons, before the break; `Delete book` and `Remove this copy` keep their own last line. | no | 4.2a |
| 4. The reason line on Missing files rows | Confirmed as built: it shows for `Convert what's there`, the press that is blocked. `Scan again` stays enabled. | no | 4.2a |
| 5. A series read from brackets | Not accepted: `from the file's tags` is untrue when the brackets were in the folder's name. Its own origin, with words true for all three places: ` · from the brackets in its name`. | yes, small: one origin in the engine, one string on the page | 4.3 |
| 6. `1 other book would get this file name.` | Keep. It is the right singular for a book the engine cannot name. | no | 4.1, 6.1 |

For the record, no objection to any of the three:
- The same-name presentation is tested with the engine's own fact, `ask.hold.kind`. That is the test 4.1 asked for; the interim test is withdrawn.
- The origins `title_tag` (` · from the title tag`) and `file_name` (` · from the file name`) are built, as 4.3 words them.
- A series found and not applied counts as done in the look-up's bar. That is 2.1's "settled": the look-up has finished with that book.

## Amended 2026-11-22, fourth round (R20–R22)

Sergei folded the whole scope into one release. The rulings are R20 to R22 in `BooksArranger_0.31.0_Scope.md` ("Fourth round", `32ced7c`), which is the authority. Every change they cause is marked **Amended 2026-11-22, fourth round (R20–R22)**. Where this round and an earlier one disagree, this round wins.

Read for this round, read-only: the build at `ender/0.31.0`, `4484f8f` (`web/app.js`, `web/index.html`, `web/style.css`, `background_work.py`, `series_backfill.py`, `sorting_moves.py`, `book_move.py`, `public_research.py`, `automatic_processing.py`, `metadata_choices.py`, `canonical_names.py`, `desktop/main.js`). That build is from before this round: nothing of R20 to R22 is in it. Nothing launched, no rect measured.

| # | Ruling | Effect on this spec |
|---|---|---|
| R20 | **One release.** The online look-up before review (R2), English titles and English series names (R1, R3), the author name-order fix and the automatic rename and move of finished books (R18) all ship in 0.31.0. The write guard is switched to automatic. | Section 5 is this version. The "guard at hold" state does not ship: section 3 has one state. Nothing in this spec is "next version" any more. |
| R21 | **FantLab alone is good enough to file a series**, with a number the app counts from the cycle order. Doubtful is: local facts contradict it, more than one series on the book, a "universe" in place of a series, a number mismatch. | 3.5 says what "doubtful" is. The Place line of such a book reads `found on FantLab`. |
| R22 | **A book not converted yet stops asking about a doubtful series:** `Number unclear`, `Title unclear` (a title that only looks like a series name and number) and `Sources disagree — which is correct?` (about a series). The series counts as not found and the book goes on without it. | 4.4. Question 12 is closed: yes, in this version. |
| R19 | Met inside the version: English names ship together, so every finished book moves once. | No book waits for a later version (3.2). |

| What | Change | Where |
|---|---|---|
| Waiting for the online answer | This version. Final wording for the row, the Waiting item, the tries text and the three ways the wait ends; one more hint for a book whose tries do not go on by themselves | 5 |
| A translated book's row | New Title line `English title found on Wikidata.`; the Place line gains ` · English name from Wikidata` only where the name's source is not the origin already named; a book with no English title found says nothing on its row (R3) | 4.5 |
| Author folders, surname first | No new words. What to do when the app cannot tell the order is Question 13 | 4.5 |
| The three series questions | Gone from books not converted yet. The row is an ordinary row; nothing about the dropped series is shown anywhere | 4.4, 3.5 |
| The "guard at hold" variant | Removed everywhere: one tooltip for the series row, one state | 2.1, 3 |
| The quiet line | Re-decided: one case is left, a book the rules could not rename or move. New words, new number | 3.2 |
| Rows and Waiting items for renames and moves | Finished as buildable: one more row for a rename, grouped items above 5, no Cancel on a move the app queued by its rules | 3.3 |
| Several hundred at once (the first launch after the update) | New notice above the Running list: a count and what is happening. Nothing says "interrupted" or "resumed" after a Quit | 3.3a |
| The record | Finished as buildable: where it opens, 200 entries with scroll, search over all, empty states, keyboard, one more reason (`English title`) | 3.4 |
| A list of the books that could not be moved | Specced, **not built** until Question 14 is answered | 3.4a |
| Finished states and window title | Checked against R20 to R22: the table holds. Three clarifications, no new state, no new title | 1.1, 1.5 |
| The detail look-up's name | `Finding English titles and author names` (R1: the app looks for the English title, which for a Chinese book is not the original one) | 2.1, 2.2 |
| Acceptance checks | 26, 28 and 31 replaced; 1, 12, 13, 21, 27, 29, 30 and 32 amended; 36 to 46 added | 9 |
| Singular forms | The quiet line's row replaced; rows added for the grouped renames, the notice, the record's search, the list of 3.4a and section 5 | 6.1 |
| Notes for Ender, assumptions, open facts | A fourth-round list per section; A15 to A18 and F8 to F13 added; F1 and F6 closed | end |
| Question 12 | Closed by R22 | end |
| Questions 13 to 16 | New, each with a default and with what is built until he answers | end |

**What Ender changes on the page already built** (branch `ender/0.31.0`, read at `4484f8f`):
1. The series row's tooltip: the "guard at hold" sentence goes, one sentence stays (2.1). The page stops reading whether the app applies a found series by itself.
2. The quiet line: new words and a new number (3.2).
3. The detail look-up: its label and its tooltip (2.1); its Waiting item takes the new label (2.2).
4. `Waiting for source` on a row that waits for an online source becomes `Waiting for an online answer`, with its hint; the `Metadata sources` Waiting item becomes the one of section 5.
5. `Number unclear` and the `Title unclear` sentence about a series name and number: their copy, their inline Series and Number fields and their `Also:` line go with the questions (4.4).
6. New: the Title line and the English-name part of the Place line (4.5); the notice (3.3a); the rename row, the grouped Waiting items and the missing Cancel (3.3); the record (3.4).

## Decisions in brief

- **Three finished states, one badge.** When no job runs, waits or is queued, the status line starts with a badge: `All done`, `Waiting for you` or `Background look-ups only`. The badge is there only when the queue is finished, so its presence alone answers Sergei's question; its words say which of the three.
- **The engine decides the state.** The page never works it out from rows (the 0.29.0 rule for `needs_you_only`, kept).
- **Bare `Nothing running` goes from the status line.** It read as "done" while work waited. With work waiting it says `Continues by itself`.
- **Two background look-ups get plain names** that say which books they are for and whether a file changes. Their bar counts the whole look-up, not one pass, so `691 of 903 books` answers "how much is left".
- **A look-up between tries is a Waiting item**, grouped, with the next try time.
- **Nothing about a finished book's name or place is asked of him** (amended, third round, R18 and R19: the approval dialog of the earlier rounds is withdrawn). The app renames and moves a finished audiobook by its rules when author and series are found for certain, and leaves it alone otherwise. He sees it happen as ordinary rows, reads afterwards what moved where in a record, and is told in one quiet line how many books the app could not rename or move (amended, fourth round: the line counted books with a series found that was not applied). Several hundred at once get one notice with a count (3.3a).
- **A doubtful series is silent everywhere** (amended, fourth round, R21 and R22): on a finished audiobook and on a book not converted yet. No status, no question, no note. The book reads as a book with no series.
- **A translated book says once where its English names came from** (amended, fourth round, R1 and R3): `English title found on Wikidata.` on its row, and the origin on its Place line. A book for which no English title was found keeps its Russian title and says nothing on its row.
- **A book held only because another book has its name** reads `Same name as another book` and is offered a name change. A row with a question of its own keeps that question and its buttons (amended, G9).
- **Section 5 is this version** (amended, fourth round, R20). A book may wait a few tries for its online answer and reads `Waiting for an online answer`. Then it converts, with the answer or without it.

## 1. "All done" and the other finished states

### 1.1 The states

"Main work" is everything the 0.30.0 Running and Waiting lists show (conversions, cleanups, checks, queued actions, moves, scans, research of books not converted yet, automatic processing running, stopping, start pending or between tries, timed retries, saved decisions). "Background look-ups" are the two jobs of section 2 only. "Waits for you" is: books that need attention, books on hold, a drive that is not answering (R14, Sergei's answers: confirmed). **Amended 2026-11-22, third round (R18, R19):** a rename or move of a finished audiobook is never one of them. He approves none, so none waits for him.

| State | True when | Status line starts with |
|---|---|---|
| Working | at least one main job runs | as 0.30.0: `Converting: Dune`, `3 tasks running`, `Paused · …` |
| Paused | paused and nothing runs | `Paused` (0.30.0) |
| Continues by itself | nothing runs, main work waits to run | `Continues by itself` **new** (was `Nothing running`) |
| **Waiting for you** | no main work runs, waits or is queued; something waits for you | badge `Waiting for you` |
| **Background look-ups only** | no main work; nothing waits for you; a background look-up runs or waits for its next try | badge `Background look-ups only` |
| **All done** | no main work; no background look-up left; nothing waits for you | badge `All done` |
| Not readable | a source is unread (0.30.0 section 3.3) | `Nothing running that could be read` (no badge) |
| Still counting **(amended, G1 and G2)** | the engine says "not known" and no source is unread (a look-up has not counted its books yet: about 2 minutes after start or after a book finishes); or a finished state is reported and its badge is not up yet (1.2) | `Checking what is left` (no badge) |

- **Amended 2026-11-22 after build (G1).** "Not known" has two causes and two wordings. An unread source is a failed read and keeps the 0.30.0 words. A look-up that is still counting is no failure: nothing "could not be read", so those words are wrong for it. Test: "not known" with an empty unread list is `Checking what is left`; "not known" with a source unread for 3 s or more is `Nothing running that could be read`. The Waiting-for-you block is hidden in both.
- **Both at once** (things wait for you and background look-ups remain): the badge is `Waiting for you`. His action is the one thing he can miss at a cost; the look-ups need nothing from him and stay visible as a row or a Waiting item, and as the status part `212 background look-ups left`.
- **`All done` invariant, checkable:** when the badge reads `All done`, the Running list, the Waiting list, the On hold list and the Waiting-for-you block are all empty. Any item in any of them means another state.
- **Paused is never a finished state.** A pause can hold work the app has not counted yet.
- **Loading:** no badge until the jobs part has loaded.
- **Amended 2026-11-22, third round (R18, R19); amended 2026-11-22, fourth round (R20–R22): finished books and the states.** One state: the guard is switched to automatic.
  - A book the app is about to change is work like any other: writing new names into a finished file and moving a finished book are **main work**, because they change his files. Only the asking online is a background look-up. So `Background look-ups only` never shows while a write, a rename or a move of a finished book runs or waits, and `All done` waits for them.
  - A finished audiobook the rules could not rename or move (3.2) is not main work, is not a background look-up and does not wait for him. **It does not hold back `All done`** and is part of no state. It shows in one quiet line only.
  - A doubtful result is the same as no result (3.5, 4.4): it leaves nothing pending, on a finished audiobook and on a book not converted yet.
- **Amended 2026-11-22, fourth round (R20–R22): the table was checked with moves automatic and look-ups before review. It holds.** Three clarifications, no new state:
  - **A book waiting for an online answer (section 5) is main work.** A conversion follows by itself, so the queue is not finished: the first part is `Continues by itself` and there is no badge. This holds also while books need attention: `N need attention` stays in the status line, and `Waiting for you` comes up when the wait is over. The wait is bounded (R2), so that badge is late by a few tries at most. Why no badge: a badge means "the queue is finished" (Decisions in brief), and here a book will still convert.
  - With automatic processing stopped, a book in that wait does not go on by itself. The engine then counts it as nothing pending, as it counts every book that waits for Start (read in `background_work.py`), and the book's row says what to press (section 5).
  - A background look-up that finds a series for a finished audiobook turns `Background look-ups only` into working while the book is written and moved, and back afterwards. That is correct: a file is changing. The 3 s before a badge comes up (1.2) are the only smoothing.

### 1.2 The badge

`<strong id="jobs-state">`, the first thing in `#jobs-status`, followed by the 0.30.0 status parts. Not a control: no hover change, no focus stop. It has a tooltip (`title`).

| Badge | Look | Tooltip |
|---|---|---|
| `All done` | filled: background `--notice`, text `--notice-text`, 1 px border `--notice-border` | `Nothing is running, queued or waiting, background look-ups included. Nothing waits for you.` |
| `Waiting for you` | outlined: background `--surface`, text and 1 px border `--warning` | `No conversion, cleanup or other job is running or queued. The items under Waiting for you need your answer.` |
| `Background look-ups only` | filled: background `--raised`, text `--text`, 1 px border `--border` | `No conversion, cleanup or other job is running or queued, and nothing waits for you. Only online look-ups are left.` |

- Size: 15 px, weight 600, padding 0 8 px, radius 4 px, one line, never wraps inside (`white-space: nowrap`). The longest badge is about 210 px.
- The words carry the state; fill against outline is the second cue; colour is the third. No glyph, no animation, no sound, no toast.
- The border is 1 px, never 3 px, so the amber badge is not mistaken for the focus ring (same token value).
- **No layout shift:** `#jobs-status` has the same height with and without the badge when it fits on one line (reserve the badge's height as the line's minimum). The toolbar rect (Pause, Resume) does not move when the badge comes or goes (0.30.0 check 11).
- **No flicker:** the badge shows once its state has been reported for 3 s in a row, and goes once another state has been reported for 1 s (the same 1 s that gives a job its row).
- **Amended 2026-11-22 after build (G2).** The status line never starts with the counts. Whenever a finished state is reported and no badge is showing (the 3 s before a badge comes up, and the gap when one finished state follows another), the first part is `Checking what is left`. It is true in both cases: the page is confirming that the state holds. At the end of a queue he reads, in order: `Converting: Dune`, `Checking what is left`, then the badge.
- **Counts behind** (0.30.0 section 3.2): from 30 s, ` (as of 14:03:21)` follows the badge as plain text, as it follows the other stale counts.

### 1.3 Status line and idle line

Status parts, in order (new parts marked): badge or first part, books waiting to convert, cleanup phrase, actions waiting, `N need attention`, `N converted out of M approved books`, `N waiting for retry checks`, **`212 background look-ups left`** (new, zero left out; series and detail look-ups together). Singulars: 6.1.

Examples:
- `[All done] · 0 need attention · 1,510 converted out of 1,510 approved books`
- `[Waiting for you] · 329 need attention · 1,181 converted out of 1,510 approved books · 212 background look-ups left`
- `[Background look-ups only] · 0 need attention · 1,510 converted out of 1,510 approved books · 212 background look-ups left`
- `Continues by itself · 3 books waiting to convert · 329 need attention · …`

`· N on hold` stays as a part after the badge (it was glued to `Nothing running`).

**Amended 2026-11-22, third round (R18, R19).** The status part for renames and moves to approve (`N series moves to approve`, then `N series changes…`, then `N renames and moves…`) is removed and has no replacement. There is one new part in this version, `212 background look-ups left`. Books the app could not rename or move are not a status part (3.2; amended, fourth round). Books waiting for an online answer are not a part either: their Waiting item says it (section 5).

The idle line `#jobs-idle` (shown, as today, only when the Running list is empty):

| When | Line |
|---|---|
| `All done`, or `Waiting for you` with no look-up left | `Nothing is running, queued or waiting.` |
| a look-up waits for its next try, or `Continues by itself` | `Nothing is running right now.` |
| `Checking what is left` (amended, G1) | `Nothing is running right now.` |
| paused, unread | unchanged (0.30.0) |

**Supersedes:** 0.30.0 section 4 "otherwise `Nothing running` plus its counts"; the idle strings `Nothing running` and `Nothing running.`.

### 1.4 The Waiting-for-you block

**Amended 2026-11-22, third round (R18, R19).** The block has one line again. The second line (renames and moves waiting for his approval) and its button are removed with the approval itself. G4's note about a line without its button is removed too: there is no such line, in any build, and check 16 goes with it.

Shown, as today, only in the `Waiting for you` state, and only when at least one book needs attention. Heading `Waiting for you` (the look of `Waiting` and `On hold`), then the line, with its button at the right (96 x 32 minimum).

```
Waiting for you
 329 books need attention.                                        [ Review them ]
```

- The line and **Review them** are the 0.29.0 line and button (tooltip `Show every book that needs you.`). One book: `1 book needs attention.` The as-of suffix stays: `329 books need attention (as of 14:03:21).`
- The sentence `The app can't do more until you review them.` goes: the badge says it, and it was untrue while look-ups ran.
- A drive that is not answering and a book on hold keep their own homes (the Waiting item with its instruction, the On hold list). They make the badge `Waiting for you` but add no line here. If they are the only reason, the block is hidden and the badge sits above the item that explains it.
- Nothing about a finished book's name or place ever appears in this block.

### 1.5 The window title

**Amended 2026-11-22, Sergei's answers (R13: yes).** The main window's title ends with the state, so the taskbar and Alt+Tab answer without opening the window. One title for every value the engine sends:

| Engine state | Window title |
|---|---|
| all done | `Books Arranger: all done` |
| waiting for you | `Books Arranger: waiting for you` |
| background look-ups only | `Books Arranger: background look-ups only` |
| working | `Books Arranger: working` |
| paused | `Books Arranger: paused` |
| continues by itself | `Books Arranger: continues by itself` |
| not known, still counting (1.1) | `Books Arranger: checking what is left` |
| not known, a source unread; and before the jobs part has loaded | `Books Arranger` |

- The words are the status line's own, in lower case, so the two never disagree. The one difference: while working the status line names the job and the title says only `working`. A title that changed with every book would flicker in the taskbar.
- The title follows what the status line shows, the badge's wait included (1.2): in the 3 s before a badge comes up it reads `checking what is left`, never a finished state the badge has not confirmed.
- Every state starts with a different word, so a taskbar label cut after about 22 characters still tells them apart (`Books Arranger: all d…`, `…: waiti…`, `…: backg…`).
- The title changes only when the state changes. No flashing taskbar button, no focus, no sound, no notification.
- Only the main window. The set-up window keeps its own title.
- **Amended 2026-11-22, fourth round (R20–R22): checked, no new title.** A book waiting for an online answer: `Books Arranger: continues by itself`. Finished audiobooks being renamed or moved by the rules, one or several hundred: `Books Arranger: working` (or `continues by itself` while they wait for another job). A book the app could not rename or move, and a doubtful series: no effect on the title.

## 2. Plain names for the background look-ups

Each row answers four things in a fixed place: what it is and whose books (the label), how much is left (the detail), what it does this second and whether a file changes (the step).

### 2.1 Running rows

Replaces the `series` and `gap_fill` lines of 0.30.0 table 1.5. Row anatomy is unchanged (label and subject, detail, bar, step, elapsed).

| Kind, step | Label: subject | Step line | Detail and bar |
|---|---|---|---|
| `series`, looking up | `Finding series for finished audiobooks: <book>` (was `Metadata: Updating series`) | `Asking online sources. No file is changed.` | `691 of 903 books`, determinate |
| `series`, writing (amended, fourth round: always, the guard is switched to automatic) | the same label | `Writing the series into the file and renaming it. Audio unchanged.` | the same |
| `gap_fill` | `Finding English titles and author names: <book>` (was `Looking up book details`, then `Finding original titles and author names`; amended, fourth round, R1) | `For books you already approved. Recorded only, no file is changed.` | `40 of 71 books`, determinate |

- **Amended 2026-11-22, fourth round (R1): the detail look-up's name.** Under R1 a translated book is filed under its English title. For a book written in Chinese that is not its original title, so `original titles` in the label was untrue. One word changes, in the row and in its Waiting item (2.2). The step line is kept: it is true of this look-up, which only asks and records.

- **The count is the whole look-up:** done = books settled (a series found, none found, or given up), total = every book that needed the look-up. It only grows and ends at the total. It is never the count of one pass, which starts again every ten minutes and reads as no progress.
- **No time estimate** on these two rows. Their pace is set by how often the sources may be asked; a guess would be wrong. The elapsed time stays.
- **Step tooltip** (the step line's `title`, as the chapter check uses it):
  - `series`: **amended 2026-11-22, third round (R18, R19); amended 2026-11-22, fourth round (R20).** The sentence about approval is withdrawn: he approves nothing. The "guard at hold" sentence (`…A series that is found is recorded. No audiobook is renamed or moved.`) is withdrawn too: that state does not ship. One sentence, always:

    `Finished audiobooks without a series are looked up online, one by one. When author and series are found for certain, the book is filed under them. Otherwise it stays as it is.`

    The page no longer reads whether the app applies a found series by itself.
  - `gap_fill`: **amended 2026-11-22, fourth round (R1, R20).** `Books approved without an English title or a full author name are looked up online, one by one. The answers are recorded. This look-up changes no file.` (was `…without an original title… No audiobook is renamed.`). The last sentence is about this look-up only: a finished audiobook may be renamed afterwards by the rules, and that is its own row (3.3). A tooltip that said no audiobook is renamed would be untrue.
- The step and the label are one line each with an ellipsis (the 0.30.0 row); at widths where the step is cut, its `title` holds the full sentence.
- These rows count in `tasks running` only beside main work. Alone, the badge leads the status line and the row shows below it. **Amended, third round:** this holds for the series row while it looks up. In its writing step the row is main work (1.1): the status line names it, `Finding series for finished audiobooks: Dune`, and no badge shows.
- **Amended 2026-11-22 after build (G7).** That rule is for the first parts that already say the app is not busy: a badge, `Continues by itself`, `Checking what is left`. It is not for `Paused`. A paused queue with a look-up still running reads as 0.30.0 reads any work Pause does not stop: `Paused · Finding series for finished audiobooks: Dune` (two or more: `Paused · 2 tasks running`). Without the name, a bar moves under a line that says only `Paused`, and nothing explains it.
- `Researching books` (books not converted yet), `Looking up metadata` (a Find metadata press) and `Re-checking finished audiobooks` (a file check, nothing online) keep their names. Read beside the two labels above, they no longer look like the same job.

### 2.2 Between tries: the Waiting list

A look-up that waits for its next try showed nowhere. It is a Waiting item, one per look-up, grouped (the cleanups precedent). Engine order: after `metadata_sources`, before `drive`.

| What waits | Line 1 | Line 2 | Button |
|---|---|---|---|
| series look-ups between tries | `Finding series for finished audiobooks: 212 books` | `Waiting for online sources. Next try 14:05. No file is changed.` | none |
| detail look-ups between tries | `Finding English titles and author names: 31 books` (amended, fourth round, R1) | `Waiting for online sources. Next try 14:05. No file is changed.` | none |
| a series the app is about to write, held by a job | `Write series into audiobook: <book>` | the 0.30.0 blocker sentence: `It runs when Converting: Dune finishes.` (a cleanup or a scan the same way) | Show in list |
| more than 5 of those (amended, third round) | `Writing series into finished audiobooks: 290 books` | `Next: <book>.` then that book's blocker sentence, or `They run one at a time.` | Show in list, for that book |

**Amended 2026-11-22, fourth round (R20).** The last two rows are no longer conditional: the app writes a found series by itself in 0.31.0. The renames and the moves that wait are worded in 3.3, with the same grouping. Books that wait for an online answer before they convert have their own item (section 5).

- The count is the books waiting for a later try. Books due in the running pass are in the row, not here, so no book is counted twice.
- `Next try 14:05.` is left out when the engine has no time.
- **Amended 2026-11-22 after build (G8, G6).** Line 2 tooltip, one per item. Every number is the engine's; none is written into the page.
  - Series look-ups (a limit exists): `Each source is asked up to 3 times for a book, 6 hours apart. With no answer after that, the book is left as it is and the app stops asking.` The page fills in the tries per source and the hours between tries. If the engine sends no hours, `, 6 hours apart` is left out. One try: `Each source is asked once for a book. With no answer, the book is left as it is and the app stops asking.`
  - Detail look-ups: **amended 2026-11-22, Sergei's answers (R16).** This look-up gets the same limit, so its item takes the same sentence as the series item, with its own numbers from the engine: `Each source is asked up to 3 times for a book, 6 hours apart. With no answer after that, the book is left as it is and the app stops asking.` The no-limit text of the "after build" round (`A book waits here until its sources answer…`) is withdrawn and is not built.
  - R9 approved the numbers as built (3 per source, 6 hours apart). They are still the engine's; the page prints what it is sent.
- A look-up that pauses inside one book for a source's pacing leaves the Running list and waits here. The row's `No progress for 5 min` text must never show on a look-up that is only being polite to a source.
- The two look-up items (between tries) do not make the state "Working": with only them left, the badge is `Background look-ups only`. **Amended, third round:** a series write that waits is main work, not a look-up (1.1): while one waits, the first part is `Continues by itself` and there is no badge.

### 2.3 At the end of the look-up

- When every book is settled there is no row and no item. `All done` is the signal. No summary line, no count of books the look-up gave up on, no Try again (Sergei's answers, Question 4: as recommended).
- **Amended 2026-11-22, third round (R18, R19).** What used to be "after approval" is section 3.3 now: there is no approval, and a finished book the app renames or moves by its rules is described there, with the grouping of many moves at once.

## 3. Finished audiobooks renamed and moved by the rules

**Amended 2026-11-22, third round (R18, R19).** This section replaces "Renames and moves: the approval control" whole. Build from this text only.

**Amended 2026-11-22, fourth round (R20–R22).** The write guard is switched to automatic in 0.31.0, so this section has **one state**: the app renames and moves a finished audiobook by its rules whenever author and series (or an English title, or the author's folder name) are found for certain. Every "guard at hold" variant and every "only when the automatic move is on" is removed. 3.2 is replaced, 3.3 and 3.4 are finished, 3.3a and 3.4a are new.

### 3.1 Withdrawn: the approval control

Sergei, on being asked to approve moves: "Why would you ask me in such a case? If the author and series are found, then put it in the folder according to our rules." (R18). So nothing here asks him, lists books for his decision or lets him refuse one.

**Not built:**
- the dialog `Rename or move N finished audiobooks?`, its groups (`Series found`, `Author folder`, `Series name`), `Select all` and `Select these N`, its per-book lines with `Moves to` and `Renamed to`, and the button `Rename or move N books`;
- the list shortcut `Renames and moves · N` and the button `Review changes`;
- `Leave as it is`, `Offer again`, the list `Left as they are` and its reason sentences, the R12 sentence among them;
- the result lines, the changed-list warning and every loading and sending state of the dialog;
- the status part and the Waiting-for-you line about renames and moves to approve (1.3, 1.4).

Their singulars (6.1), control rows (7), layout states (8), acceptance checks (9) and engine notes are withdrawn with them. The full text is in git at `9a10b46` and is not to be used.

### 3.2 A finished audiobook the rules could not rename or move

**Amended 2026-11-22, fourth round (R20). This replaces "A series found and not applied" whole.** That section had two causes: the guard at hold, and R19's books kept for a later version. Both are gone: the guard is automatic, and English names ship in the same version, so no book waits for a switch or for a version. The line `Series found for N finished audiobooks. They are recorded and stay where they are.` is withdrawn with them.

**One case is left, and it is a different one.** The rules have a new name or folder for a finished audiobook, found for certain, and the change cannot be made, for a lasting reason that only he could clear:

| Why the book stays (the engine's key) | Counted |
|---|---|
| a file with the new name is already there (`name_exists`) | yes |
| another finished audiobook would get the same name (`same_target`) | yes |
| the file's name is not one the app gave it (`not_app_name`) | yes |
| the file is not where the app left it (`not_where_recorded`) | yes |
| the app could not work out the new name (`no_name`) | yes |
| a rename or move that started and did not finish, for good | yes |
| a doubtful result (3.5) | no: silent |
| he chose its folder with `Choose folder…`, or chose to keep its files | no: his decision, not a failure |
| the book is outside Audiobooks Sorted | no: the rules do not manage it |
| the book is being renamed or moved, or waits its turn (3.3) | no: that is work |

Such a book is not pending work: nothing happens to it while its reason lasts. So:

- **It holds nothing back.** No status part, no row, no Waiting item, no line under Waiting for you, no effect on the badge or the window title. `All done` shows with any number of them (1.1).
- **It is said once, quietly.** The line that is built, in its place and look (bottom of the Audiobook jobs panel, directly above the two help lines; `field-help`: 13 px, `--muted`; not `aria-live`, no button, no tooltip), with new words:

  `12 finished audiobooks could not be renamed or moved. They stay where they are.`

  One book: `1 finished audiobook could not be renamed or moved. It stays where it is.` Hidden at zero, and when the engine sends no number.
- **Why it is shown at all.** After the app has filed several hundred books by itself, a book he knows belongs to a series and is still outside its folder reads as a fault of the look-up. The line says the app knows about it. A doubtful result is different and stays silent (3.5): there the app has nothing it relies on.
- **Why these words.** They say what happened and that nothing is lost. No "yet" and no promise: the app does not know that it will ever be able to move the book.
- **A count only, until Question 14 is answered.** Which books, and why each stays, is a list (3.4a). It is specced and not built: a list is a new surface and that is his to say. If he says yes, the count becomes the summary of that list and this line is not shown. If he says no, this line stays as written here.
- Nothing is added to the books' own rows.
- The number is books, each once. It falls when a reason is gone (the file that was in the way is removed). Whether the rules then file the book by themselves is the engine's (F12); if they do, it shows as a row of 3.3 and an entry of 3.4, and nothing else explains it.
- The line and the record of 3.4 are not part of the `All done` invariant of 1.1. Both may show under `All done`: neither is pending work.

### 3.3 While the app renames or moves a finished book

**Amended 2026-11-22, fourth round (R20): always, and finished as buildable.** Nothing asks. One book or a few read as ordinary work in the jobs panel, in rows and items of the kinds that already exist. Many at once also get the notice of 3.3a.

| Moment | Where | Words |
|---|---|---|
| the series is being written into the file | Running row (built) | `Finding series for finished audiobooks: <book>`, step `Writing the series into the file and renaming it. Audio unchanged.` (2.1) |
| another name is being written into the file: an English title, the author's name, the series' name (new, fourth round) | Running row | `Renaming finished audiobook: <book>`, step `Writing the new names into the file and renaming it. Audio unchanged.` |
| the book is moving to another folder | Running row, the 0.30.0 move | `Moving: <book>`, step `Copying to <folder>` |
| a series write waits for a job | Waiting item (built) | `Write series into audiobook: <book>` and the blocker sentence (2.2) |
| a rename waits for a job (new, fourth round) | Waiting item | `Rename finished audiobook: <book>` and the blocker sentence |
| a move waits its turn | Waiting item, the 0.30.0 queued action | as 0.30.0 |
| more than 5 series writes wait | one grouped Waiting item | `Writing series into finished audiobooks: 290 books` / `Next: Оно. It runs when Converting: Dune finishes.` |
| more than 5 renames wait (new, fourth round) | one grouped Waiting item | `Renaming finished audiobooks: 92 books` / the same line 2 |
| more than 5 moves wait | one grouped Waiting item | `Moving finished audiobooks: 338 books` / the same line 2 |

- **Three kinds of change, three sets of words.** The series look-up writes its own series (its row, built). A move is the 0.30.0 move. The rename row is for a write of names that is neither: an English title (R1), an author's name in its new order, a series name in English. Its row is the 0.30.0 row: label and subject, a sliding bar unless the engine sends an amount, the step, the elapsed time; its step's tooltip is the step's own text. If the engine does every such write inside the series row or inside the move, the rename row and its items are never sent, and nothing else in this section changes (F10).
- **The groups.** At the first launch after the update every book the rules can file is released at once: several hundred. The 0.30.0 Waiting list draws one item per waiting write and per queued move, which would be a wall. So the cleanups' cap applies to each of the three: with 5 or fewer, each book is its own item; with more, one grouped item replaces them. Line 2 is `Next: <book>.` followed by that book's blocker sentence when something blocks it, else `Next: <book>. They run one at a time.` The button is Show in list, for that book.
  - The group's number is the engine's whole count, never the number of items it lists (it lists at most 100 waiting writes).
  - Only the app's own renames and moves are grouped. A move he queued himself with `Choose folder…` stays its own item whatever the number, as 0.30.0.
  - Show in list on these items has the plain tooltip, `List this book: sets Status to All and searches for its title.`, never the one that ends `Its row has Cancel.` (next bullet).
  - The status part `338 actions waiting` is unchanged.
- **No Cancel on a rename or move the app queued by its rules.** A 0.30.0 queued move has `Cancel` on the book's row, and `Choose folder…` is disabled with `Move is queued for this book. Cancel it to use this.` For the app's own move that pair is wrong: he approves and refuses none (R18), and the rules would queue a cancelled move again, so `Cancel` would be a button whose effect does not last. So, on the row of a finished audiobook whose rename or move the app queued:
  - the destination line reads `Moves to` and the new path, as 0.30.0;
  - `Cancel` is not shown;
  - `Choose folder…` is `aria-disabled`, with the tooltip `The app is about to move this audiobook. Choose another folder when it has moved.` (a rename in place: `The app is about to rename this audiobook. Choose a folder when it is done.`);
  - once the book has moved, `Choose folder…` works as on any finished audiobook, and the folder he chooses then is his: the rules leave such a book where he put it (0.30.0).
  - A move he queued himself keeps `Cancel` and its tooltip, unchanged.
  - This is what is built until Question 16 is answered.
- **State.** A write, a rename or a move of a finished book is main work (1.1): the first part names it or reads `Continues by itself`, the window title reads `working` or `continues by itself`, and `All done` comes only after the last one.
- **The book's own row** in the list reads as 0.30.0 reads any move: `Moves to`, `Moving to`, then `Now in`. Nothing is added but the two points above.
- No toast, no sound, no focus change, no confirmation of any kind, before or after.

### 3.3a Many at once: the notice

**Amended 2026-11-22, fourth round (R20). New.** At the first launch after the update the rules have several hundred finished audiobooks to rename and move. Without a word he opens the app and reads `Moving:` and the name of a book he did not touch, and `338 actions waiting`. One notice says what this is, how many, and that it is safe.

**Where.** In the Audiobook jobs panel, directly under the toolbar (Pause, Resume), above the unread line and the Running list. In normal flow: it pushes the lists down and covers nothing.

**Look.** The app's existing notice box (class `notice`: background `--notice`, text `--notice-text`, 1 px border `--notice-border`, radius 6 px, padding 12 px), as `Verified audiobooks replace their included originals.` has it. Two lines:

```
Filing 212 finished audiobooks under the names found for them.
A book is renamed or moved to match its author, series and title. The audio is not changed. If you quit, the app goes on next time.
```

1. Line 1: 15 px, weight 600. The number is the books left: being renamed or moved now, or waiting for it. It only goes down. One: `Filing 1 finished audiobook under the names found for it.`
2. Line 2: 13 px, `--notice-text`. The same words for every number.

**When.**
- It comes up when more than 5 books are left at once (the grouping threshold of 3.3).
- Once up, it stays until none is left, also below 5. A notice that left at 5 would read as the end.
- With 5 or fewer from the start it never shows: the rows and items say it.
- When none is left it goes, and nothing takes its place: no summary, no "done" line. The record's summary (3.4) holds the total, and the state moves on by its own rules (1.1).
- While paused it stays, with its number. The status line says `Paused` and the Waiting items say what they wait for.

**What it is not.** Not a control: no button, no close box, no tooltip, no focus stop. `aria-live="off"`: its number changes with every book, and the status line already announces the state. No sound, no toast, nothing in the taskbar beyond the window title (1.5).

**Quit, and the next launch.**
- Quit asks nothing new. It waits for the one file change in progress and then closes, as 0.30.0 does (read in `desktop/main.js`). Books not started stay as they are.
- At the next launch a move that was cut is finished first, under the 0.30.0 row `Finishing interrupted moves`. The rules then queue the rest again by themselves (A16), and the notice comes up with the number that is left, for example `Filing 84 finished audiobooks under the names found for them.` With 5 or fewer left there is no notice, only rows and items.
- The record (3.4) keeps the entries made before the Quit.
- No word says "interrupted", "resumed" or "again". The notice states what is left, in the same sentence every time, so it needs no memory of the Quit.

**Why these words.** `under the names found for them` is the reason, in his terms: the app found a series, an English title or an author's name and files the book by it. `The audio is not changed` answers the first worry on seeing hundreds of files move. `If you quit, the app goes on next time` answers the second: hundreds of moves on a network drive take hours, and he will close the app before they end. That sentence rests on A16; if the rules do not queue the rest again by themselves, it is taken out.

### 3.4 Afterwards: what was renamed or moved

He no longer sees a move before it happens, so he must be able to read afterwards what moved where. A plain, read-only record, from what the engine already keeps for every move (from where, to where, when).

**Amended 2026-11-22, fourth round (R20): built in 0.31.0, and finished as buildable.** The additions are marked in place: one more reason on an entry, the rule for the search, the disabled state of Show in list, the Escape key, and what is and is not there (no paging, no empty record).

**Where it opens from.** A `<details>` at the bottom of the Audiobook jobs panel, after the Waiting-for-you block and above the quiet line of 3.2, built like `Author rules learned online` in the scan panel. Its summary line is the only way in: there is no button elsewhere and no shortcut. Closed by default at every launch; while the page is open it stays as he left it. **No empty record:** the whole element is hidden while the app has never renamed or moved a finished audiobook by its rules, and appears with the first entry.

**Summary.** `Renamed or moved by the app · 340 · last 22 Nov, 14:05`. One: `Renamed or moved by the app · 1 · 22 Nov, 14:05`. Tooltip: `Finished audiobooks the app renamed or moved by its rules, newest first.` Dates are in the form the page already prints dates.

**Inside,** top to bottom:
1. One help line (`field-help`): `The app files a finished audiobook under the author, series and title it found for certain. The audio is never changed.` (amended, fourth round, R1: was `…under its author and series when both are found for certain.`, which left out a book renamed for its English title alone)
2. `Find book`, a search field (the look and behaviour of `Find author` in Author rules). Tooltip: `Show only entries whose title, author or path contains this text.`
3. The list, newest first, scrolling inside (`max-height: 40vh`), `role="group"`, `aria-label="Books renamed or moved by the app"`, `tabindex="0"`.

**An entry.** Three lines and one button.

```
Граф Ноль · Gibson William · 22 Nov, 14:05 · Series: Sprawl Trilogy · No. 2 · found on FantLab     [ Show in list ]
  Was in   Gibson William\Граф Ноль - Gibson William.m4b
  Now in   Gibson William\Sprawl Trilogy\2 - Граф Ноль - Gibson William.m4b
```

1. `Title · Author · date`, then one part per reason the rules had, ` · ` between: `Series: <name> · No. <n> · found on <source>` (the source names and origin words of 4.3 and 4.5, the ` · English name from <source>` part included), `English title found on <source>` (amended, fourth round, R1; the words of 4.5's Title line without the full stop), `Author folder: <the new folder's name>`, `Series name: <the new name>`. Title in weight 600: the title it is filed under now. The author is the one it is filed under now.
2. `Was in` and the path before the app touched the book, under Audiobooks Sorted (the full path is the `title`).
3. `Now in` and the path after. The leading folders it shares with line 2 are `--muted`; what is new is `--text`. A book only renamed in its folder uses the same two labels; the file name shows the change.
- **Show in list** (quiet, 96 x 32 minimum): the existing button, tooltip `List this book: sets Status to All and searches for its title.`
  - Amended, fourth round: it searches for the title the book has now (the entry's own title), which for a translated book is the English one.
  - Amended, fourth round: a book that has since been deleted from the app keeps its entry (the record says what happened). Its button is `aria-disabled`, keeps its focus stop, and its tooltip is `This book is not in the app.`
- One entry is one time the rules were applied to one book: from where it was to where it ended. A series written and then a move to the series folder are one entry, not two, and the in-between name is not shown. If the app moves the same book again later, that is a second entry.
- Only finished changes. A book being written or moved is a row (3.3), not an entry. A change that did not happen is not an entry.
- Only the app's own. A folder he chose with `Choose folder…` is his move and is not listed.

**Other states.**

| Moment | Shows |
|---|---|
| opened, the list not here yet | `Loading…` |
| the list could not be read | `The list couldn't be loaded. Close and open it again.` (`--warning`) |
| Find book matches nothing | `No entry matches.` |
| more than 200 entries | the newest 200, and under them `Showing the newest 200 of 1,240. Find book searches all of them.` |
| Find book has text and more than 200 entries match (amended, fourth round) | the newest 200 that match, and under them `Showing the newest 200 of 312 that match.` |

- The summary's count and date come with the normal state, so they are right while the record is closed. The entries are fetched when it is opened, and again each time the count changes while it is open; the scroll position holds.
- **Amended 2026-11-22, fourth round: how much it shows.** At most 200 entries at a time, newest first, in one list that scrolls inside itself (`max-height: 40vh`). **No paging, no "Show more".** Older entries are reached with `Find book`, which searches every entry, not only the 200 on screen: the first launch alone can leave several hundred, and a page-side filter would silently miss the older ones. The search runs 300 ms after he stops typing; until its answer is there the list stays as it is (no `Loading…`, no flicker). An empty field shows the newest 200 again. If a search cannot be read, the `couldn't be loaded` line shows in place of the list.
- **Amended 2026-11-22, fourth round: keyboard.** The summary is a tab stop (Enter or Space opens and closes). Then `Find book`, then the list (one stop: arrow keys, Page Up and Page Down scroll it), then each entry's Show in list in order. **Escape** on the list or on an entry's button puts the focus back on the summary and leaves the record open, so 200 buttons need not be tabbed through to get out. In `Find book`, Escape clears the field and does nothing else. Section 7 has the rows.
- **If a move was wrong:** the book's own row has `Choose folder…`, as for any finished audiobook. No undo is added here (offered at the end).

### 3.4a The books that could not be renamed or moved: a list

**Amended 2026-11-22, fourth round. New. Not built until Question 14 is answered yes.** Until then 3.2's line stands alone, with its count.

If yes: the count of 3.2 gets the list it lacks, read-only like the record, and 3.2's line is not shown (the summary below carries the number).

**Where.** A second `<details>`, directly under the record's, built the same way. Closed by default. Hidden while the number is zero.

**Summary.** `Could not be renamed or moved · 12`. One: `Could not be renamed or moved · 1`. Tooltip: `Finished audiobooks the app has a new name or folder for and could not use, each with the reason.`

**Inside.** One help line (`field-help`): `These audiobooks stay where they are.` Then the list, by author folder and title, scrolling inside (`max-height: 40vh`), `role="group"`, `aria-label="Books that could not be renamed or moved"`, `tabindex="0"`. No search: the number is small. More than 200: the first 200, and `Showing 200 of 312.`

**An entry.** Four lines and one button.

```
Граф Ноль · Gibson William                                                  [ Show in list ]
  Now in       Gibson William\Граф Ноль - Gibson William.m4b
  Would be in  Gibson William\Sprawl Trilogy\2 - Граф Ноль - Gibson William.m4b
  A file with that name is already there.
```

The last line is the reason, in `--text`, by the engine's key:

| Key | Sentence |
|---|---|
| `name_exists` | `A file with that name is already there.` |
| `same_target` | `Another audiobook would get the same name.` |
| `not_app_name` | `Its file name is not one the app gave it.` |
| `not_where_recorded` | `The file is not where the app left it.` |
| `no_name` | `The app could not work out its new name.` (no `Would be in` line) |
| a rename or move that did not finish | `The rename or move did not finish.` |

- `Now in` and `Would be in` follow the record's rules for paths (shared folders `--muted`, what differs `--text`, the full path as `title`).
- **Show in list**: the existing button and tooltip, as in the record. Escape returns to the summary, as in the record.
- Nothing here acts on a file: no "Move anyway", no "Leave it". He clears the reason himself (removes the file in the way, or gives the book a folder with `Choose folder…`).
- Other states: `Loading…`; `The list couldn't be loaded. Close and open it again.`

### 3.5 A doubtful result

**Amended 2026-11-22, fourth round (R21, R22).**
- **What is doubtful (R21):** a result that local facts contradict, more than one series on the book, a "universe" in place of a series, a number mismatch. Nothing else.
- **What is not:** a series found on FantLab alone, with a number the app counts from the cycle order. It is filed, and its Place line reads `Series: Sprawl Trilogy · No. 2 · found on FantLab`, as for any series a source gave. The row does not say the number was counted.
- **The same rule now holds for a book that is not converted yet (R22):** 4.4.

R18: a result that could be wrong is treated as if nothing was found. On the page that means **the book says nothing, anywhere**:

- no status word, no hint, no chip, no count, no line on its row, in its details panel, in the jobs panel or in the record;
- it reads exactly as a finished audiobook for which no series was found, and the look-up counts it as settled (`691 of 903 books`);
- it is not in the quiet line's number (3.2; amended, fourth round: that number counts only books for which the app has a certain result it could not apply).

Why nothing: any visible "possible series" is a question in other clothes. It would sit on the book until he dealt with it, which is the thing he asked not to have. If the app is not sure, the honest display is the one a book without a series has.

## 4. Two books, one destination

### 4.1 The held rows

**Amended 2026-11-22 after build (G9, blocking).** The engine reports `destination.shared` on every to-do row whose planned name another book also has, whatever that row is asking: a row held for the clash itself, and equally a real piece of one book that is named after its set. This section, as first written, read as if every such row took the `Same name as another book` presentation and lost `Approve as one book`. It does not. **The presentation follows the row's own question, never the mere presence of `shared`.**

| Row | Test (facts the page has) | Presentation |
|---|---|---|
| **S.** The clash is its only question | group Name taken, **and** the row's own hold kind is `same_destination` | this section: `Same name as another book`, 4.1 and 4.2 |
| **D.** A file with the name is on disk | group Name taken with any other hold (`destination.taken` is true) | the 0.30.0 Name taken row (`Already there`), unchanged. `shared` adds nothing to it |
| **Q.** It has a question of its own | every other group: `part_of_book` (every cause: chapter, numbered part, siblings, part of a set, a set), `files_unclear` (the folder question included), `order_unclear`, `title_author`, `author_unclear`, `same_author`, `files_missing`, `other` | its own status, sentence, fields and buttons, unchanged. `Part of a bigger book`, `Approve as one book` and `Keep as separate books` all stay. `shared` adds only what 4.2a lists |

- **Do not test `destination.shared.kind`.** It reads `same_destination` on every row that carries `shared` (the object is the hold's shape). The test is the row's own hold: why the engine is holding this row.
- **No new engine fact is needed** to tell the three apart: the row's group and its own hold kind decide. If the row does not carry its own hold kind apart from `destination.shared`, that is the one fact to add; until then "group Name taken, `taken` false, `shared` set" is the same test. **Amended 2026-11-22, after the final build:** the row carries it (`ask.hold.kind`) and the page tests it. The interim test is withdrawn.
- `shared` and `taken` are read from the row's latest answer: the ask's own, then the `Goes to` preview once he types.
- Why this is the right split: a class S book has nothing else in doubt (the app would have filed it by itself had the name been free), so the name is the whole question. A class Q row is asking something the clash does not answer: whether a file is a piece or a whole book, which files belong, what order. Replacing that question with the clash would hide it. After step 1 the two Sprawl volumes are no longer class Q at all: each is named from its own title tag (4.3), and if two names still met they would be class S.
- The preview's series origin and `title_from_title_tag` play no part in this split. They are for 4.3 only.
- In the build a book already waiting to convert keeps its name and is not held; only the row is (the Scope says both). The sentences below fit either.

When a row is held because another row plans its name, or a book waiting to convert has it (class S), the row shows:

- **Status:** `Same name as another book`. It is counted and listed under the existing **Name taken** chip (the same question: this name cannot be used, change it). Chip tooltip becomes `Show books whose name is already used, in Audiobooks Sorted or by another book here.`
- **Sentence** (the row's hint): what holds the name, then the fix.

| The other is | Sentence |
|---|---|
| one row | `Another book would get this file name: «03-Мона Лиза овердрайв». Change a title, author, series or number so they differ.` |
| a book waiting to convert | `A book waiting to convert has this file name: «03-Мона Лиза овердрайв». Change a title, author, series or number so they differ.` |
| several | `2 other books would get this file name. Change a title, author, series or number so they differ.` |

The quoted text is the other book's own folder or file name, never its title: the titles are the same, which is the problem.

- **Destination line:** label `Both go to` (three or more: `All 3 go to`), in the warning style `Already there` uses, then the shared path. The number is the engine's count of other books plus this one (the engine names at most ten of them one by one; the count is whole).
- **Fields:** Title and Author on the row, as a Name taken row; Series and Number through **Edit names**, as today.

**Amended 2026-11-22, after the final build (gap 1): when the clash has ended.** A class S row can stay listed for a while after the other book has been renamed, removed or converted, until the engine's re-check takes it off the list. Built: it keeps naming the recorded other book. That sentence is then untrue, so the sentence follows the row's **latest answer** (the ask's own, then the `Goes to` preview once he types), never the recorded hold. The status stays `Same name as another book` throughout: it is why the engine lists the row.

| Latest answer | Sentence | Label, Approve, show button |
|---|---|---|
| another book still has the name (`shared`) | the table above, naming the other book | as 4.1 and 4.2 |
| the name is free (a path, no `shared`, not `taken`) | `The name is free now. Approve files the book under it.` | `Goes to`, Approve enabled, no show button (as built) |
| a file with the name is now on disk (`taken`) | `A book with this name is already in Audiobooks Sorted.` (the Name taken row's own) | `Already there`, Approve disabled with the Name taken reason (as built) |
| no name could be worked out (no path in the answer) | the recorded other book, as built: unknown is not free | as built |

- The second case is also what he reads once the name he types is free: the sentence, the label and the button turn together.
- The row still leaves by the 0.29.0 rule and strip line when the engine's re-check clears it.

**Amended 2026-11-22, after the final build (gap 6).** `1 other book would get this file name. Change a title, author, series or number so they differ.` is kept, for one other book the engine sends without a name. Real jobs always have a name, so it is a guard, and it is the right singular of the "several" sentence.

### 4.2 What he is offered (class S)

| Control | State and words |
|---|---|
| **Approve** | `aria-disabled` while the names are the same. The line under the buttons: `Another book would get this name. Change the title, author, series or number.` Enabled as soon as this row's `Goes to` differs. |
| **Show the other book** (new, quiet, 96 x 32 minimum; was `Show both books`, amended after the final build: the table below) | Lists the other book by its own folder or file name. |
| the other row actions a Name taken row has | unchanged |

**Amended 2026-11-22, after the final build (gap 2): the show button lists the other book.** `Show both books` searched the list for the shared title, but the list's search matches a book's title clue, its grouping and its file paths, not the title the app proposes. So it could list one book, or neither, under a face that promised both. With what exists, on class S and class Q rows alike:

| | One other book | Several |
|---|---|---|
| Face | `Show the other book` | `Show one of the others` |
| What it does | Lists that book: sets Status to All, searches for **its own folder or file name** (the name the engine sends and the sentence quotes), and goes to its row by its id, as `Show in list` does | the same, for the first other book the engine names |
| Tooltip | `List the other book: sets Status to All and searches for its folder or file name.` | `List one of the other books: sets Status to All and searches for its folder or file name.` |
| `aria-label` | the face, `: `, that book's name | the same |

- This is reliable: that name is part of the book's own file paths, which the search does match.
- The way back is the same button on the other row: its sentence names this book.
- If the engine sends no name for the other book, the button is not shown: there is nothing to search for.
- It replaces `Show both books` and `Show all 3 books` everywhere in this spec (the table above, 4.2a, 6.1, 7).
- Showing the books side by side needs a list filter that lists given books by their ids. That is more than a small change and is not in 0.31.0. If it is built later, the face can be `Show both books` again.

- **Never on a class S row** (amended, G9: class S only, not every row with `shared`): the status `Part of a bigger book`, the face `Approve as one book`, `Keep as separate books`. A class S row never had them: the engine held it for the name alone. No Join hint either (Sergei's answer 10, 2026-11-18).
- When one row's name changes and the clash ends, the other row leaves by the 0.29.0 rule and strip line: `«Title» left this list: the name is free now. The book is checked again.`
- If the clash appears only at the press (the engine's `same_name` refusal, on a row of any class), Approve answers: `Another book would get this name. Change the title, author, series or number, then approve.` The row's `Goes to` line refreshes, as for Name taken.

### 4.2a A row with its own question whose name another book also has (class Q)

**Amended 2026-11-22 after build (G9).** The row keeps everything it has. While `shared` is set, three things are added. If `taken` is set too, the name on disk wins and the row shows as it does today.

| What | Words |
|---|---|
| Destination label | `Both go to` (`All 3 go to`), in the warning style, in place of `Goes to` or `As one book`. The path is unchanged. |
| The row's own approve press, whatever its face (`Approve`, `Approve as one book`, `Approve this order`, `Approve these files`, `Convert what's there`) | Face and tooltip unchanged. `aria-disabled`, with the reason on the line under the buttons: `Another book would get this name. Change the title, author, series or number.` (on a `part_of_book` row the line is R17's, below). The engine refuses that press while the clash stands (`same_name`), so the page prevents it instead of letting it be refused, exactly as it does for a name already on disk. The offer is not removed: it works again as soon as the name he types is free. |
| **Show the other book** (was `Show both books`; 4.2 as amended after the final build) | Added as the last button of the row, after the row's own. A press that is blocked by another book must show him that book. |

- **Amended 2026-11-22, after the final build (gap 3): its position, confirmed as built.** "Last" means last of the row's ordinary buttons: after the row's own, `Edit names`, `View metadata` and the folder button, and before the line break. `Delete book` and `Remove this copy` keep their own last line, alone: a button that deletes stays apart from every other.
- **Amended 2026-11-22, after the final build (gap 4): Missing files rows, confirmed as built.** There the blocked press is `Convert what's there`, the row's second button, and the reason line under the buttons is about it. `Scan again`, the first button, stays enabled and is not part of the clash. This is how a name already on disk reads on the same row today; the disabled button carries the same reason as its tooltip, so the line is never without its button.
- Untouched and enabled as before: the status, the sentence, the fields, `Keep as separate books`, `Scan again`, `Change order`, `Choose files`, `Remove from list` and every other button the row has.
- No `Also:` line and no second sentence. The label and the reason line carry the clash; the row's sentence stays its own question.
- When the name he types is free, the label and the approve press return to normal at once.
- **Amended 2026-11-22, Sergei's answers (R17: yes).** On a `part_of_book` row (every cause) whose approve press is blocked this way, the reason line names both ways out: **`Another book would get this name. Join them into one book, or change this title.`** For real pieces of one book joining is the answer and renaming is not. Build this line, not the plain one, on those rows.
  - Only there, and only while the press is blocked. Every other class Q row (the folder question included), every class S row and the late refusal of 4.2 keep the plain line. The line goes when the press is free again.
  - Nothing else about Join is added: no hint on a row that is not blocked, no Join button on the row. His "no Join hint on rows" of 2026-11-18 otherwise stands. "Join them" is the existing `Join into one book` in the bar above the list, for the rows he selects.

### 4.3 A volume named from its own tags (R4)

The book is filed without asking, so the row carries no question. It says where the series came from, on the Place line of the status cell:

`Series: Sprawl Trilogy · No. 2 · from the file's tags`

- **Amended 2026-11-22 after build.** The suffix, by the origin the engine sends: `tags`: ` · from the file's tags`; `folders`: ` · from the folder names`; `entered`: ` · entered by you`; `source`: ` · found on Wikidata` (source names: `FantLab`, `Goodreads`, `Wikidata`, `Litres`, `the publisher's site`; a source with no name: ` · found online`; the same names are used in the record of 3.4); `unknown`: no suffix. `folders` and `unknown` had no words. `source` shows whenever the engine says so. **Amended 2026-11-22, fourth round (R20, R21):** with look-ups before review a book not converted yet often has it, FantLab alone included; the English-name part that can follow the suffix is in 4.5.
- Details panel, the `Book metadata` basis line of a `volume` (0.30.0 section 10), gains two sentences after `Kept as a separate book: …`: `Title from this file's own title tag. Series and number from its tags.`
- The title cell shows the volume's own title (`Граф Ноль`), never the album.

**Amended 2026-11-22, Sergei's answers (R15).** A file whose only clue is a title tag shaped "Series NN - Title" (`Sprawl Trilogy 01 - Neuromancer`) is filed without asking, as R4 files a book whose series is in its series tags. Its row carries no question either, and it must not say the series came from somewhere it did not.

- Title cell: the title part only (`Neuromancer`), never the whole tag.
- Place line: `Series: Sprawl Trilogy · No. 1 · from the title tag`.
- Details panel, basis line, after the sentence its kind already has: `Title, series and number from this file's title tag.`
- The suffix words, by where the series was really read:

  | Read from | Suffix |
  |---|---|
  | the series tags (sort-album, grouping) | ` · from the file's tags` |
  | the title tag's own text (R15) | ` · from the title tag` |
  | the file name | ` · from the file name` |
  | brackets in the book's name, `Солнце и Замок (Книга Нового Солнца #3)` (amended after the final build, gap 5) | ` · from the brackets in its name` |

- **Amended 2026-11-22, after the final build.** The engine now sends the title tag and the file name as origins of their own, and the page words them as above. The earlier note that all three arrived as `tags` is withdrawn.
- **Amended 2026-11-22, after the final build (gap 5): a series read from brackets.** Not accepted as built. The brackets rule reads the album tag, the title tag **or the folder's name**, and the record does not keep which. The engine sends it as `tags`, so the row says `from the file's tags` when the text may be the folder's. A row must not say a series came from somewhere it did not. So the brackets rule gets an origin of its own and the words ` · from the brackets in its name`, which are true for all three places and tell him exactly where to look. One more origin in the engine, one more string on the page. Until it is built, such a row must send `unknown` (no suffix) rather than `tags`.

### 4.4 A doubtful series on a book that is not converted yet (R22)

**Amended 2026-11-22, fourth round (R22). New.** R22 answers Question 12: yes, and in this version. A book that is not converted yet no longer asks about a doubtful series. The series counts as not found and the book goes on without it.

| What was asked | What is there now |
|---|---|
| Row status `Number unclear`, sentence `The title says book 2, but FantLab says book 3.`, the Title, Series and Number fields, `Approve` | No question. An ordinary row (below). |
| Row status `Title unclear`, sentence `The title starts with what looks like a series name and number.`, the same fields, `Approve` | No question. An ordinary row. |
| Details panel, `Sources disagree — which is correct?`, where the sources differ only in the series or in the number in it | That question is not listed. If it was the only one, the whole block is hidden. |

**An ordinary row** is exactly what a book with no series reads today. Nothing is new, so nothing can be left over:

- **Status:** the one its real state gives (`Pending`, `Queued`, `Processing`, `Waiting for an online answer`, and so on). Never `Number unclear`. Never `Title unclear` for this cause.
- **Sentence:** none. Nothing on the row reads as a question.
- **Fields:** no Title, Series or Number field on the row. They are in `Edit names`, as on every row.
- **Buttons:** the row's ordinary ones (`Edit names`, `View metadata`, the folder button, `Choose folder…`). **No `Approve`:** the button belonged to the question, and with no question there is nothing for it to confirm. No button stays behind without its question.
- **Place line:** none. A book with no series has none.
- **Chips and counts:** the book is not counted under `Title or author` or in `N need attention`, and it is not in the Waiting-for-you count.
- **`Also:` line:** a Missing files row never carries `Also: the title starts with what looks like a series name and number.`

**The details panel block.** `Sources disagree — which is correct?` (its heading, help line, `Resolve metadata`, the choices, `Save choices` and its status line) shows only while at least one question that is not about a doubtful series is listed. With none it is hidden whole, as it is today for a book with no question: no heading over an empty list, no `Save choices` with nothing to save. With other questions left it lists those and only those. `Which series should this book use?` and `Which number should this book use?` are never among them, and `Sources disagree — choose again.` never comes up for a series.

**Nothing about the dropped series is shown.** The same decision as 3.5, for the same reasons, so the two kinds of book read alike:
- no status word, hint, chip, count or line, on the row, in the details panel or in the jobs panel;
- any visible "possible series" is a question in other clothes: it would sit on the book until he dealt with it;
- R22's own words: the series is "treated as not found".

What he can still do, as today: `Edit names`, Series and Number. A series he types is his answer, never a doubt: it is filed as typed and the row says `Entered by you: series, number.` (0.22.2, unchanged). A series he already approved on one of these rows stays.

If the series is found for certain later, after the book has converted, the book is filed by the rules like any finished audiobook (3.3).

**Not changed.** Every question that is not about a doubtful series keeps its status, sentence, fields and buttons exactly as built:
- `Title missing`, `Author missing`, `Title and author missing`, `Tags unreadable`;
- `Author unclear`, all seven causes (two people credited; the tags and the folder name differ; the file name and the folder name differ; the only name may be the reader; underscores in the name; a Latin name that may be a Russian writer's; no English spelling found);
- `Title unclear` for its two other causes: `The title ends with a number that looks like a bitrate.` and `The title looks like Russian written in Latin letters.`;
- `Same author?`;
- `Name taken` and `Same name as another book` (4.1);
- `Part of a bigger book` (every cause), `Files unclear`, `Order unclear`;
- `Missing files`, `All files missing`;
- `Needs you`;
- in the details panel, `Sources disagree — which is correct?` for a title, an author, the original language, a universe, a genre, a topic or a reader, and `Which book is this recording of?` where the sources differ in title or author. In that last question each choice still prints its source's Cycle and Number in cycle beside its title and author: by choosing the book he chooses its series, and that is his answer, not a doubt.

Two points this spec does not settle: under which title a book shaped "Series N. Title" is filed once its series is dropped (F9: the page shows whatever title the engine files it under), and whether other stops of the same kind follow the same rule (Question 15).

### 4.5 English names on a row (R1, R3)

**Amended 2026-11-22, fourth round (R20: R1 and R3 ship in 0.31.0). New.** A translated book is filed under its English title, in a series folder named in English, in an author folder in Latin letters, surname first. Its files are still named in Russian. The row says once where the English came from, and asks nothing.

«Тёмный лес» by Liu Cixin, a row that asks nothing, status cell:

```
Queued
English title found on Wikidata.
Series: Remembrance of Earth's Past · No. 2 · found on Wikidata
In       D:\Audiobooks\Лю Цысинь\Тёмный лес
Goes to  Liu Cixin\Remembrance of Earth's Past\2 - The Dark Forest - Liu Cixin.m4b
```

**The Title line (new).** One line in the status cell, directly above the Place line, in its look (`field-help`: 13 px, `--muted`). With no Place line it stands in that line's place.

| The title the book is filed under | Title line |
|---|---|
| an English title an online source gave, in place of the files' own | `English title found on Wikidata.` |
| the same, from a source with no name the page knows | `English title found online.` |
| the files' own title (a book written in Russian; a book whose files are titled in English already) | none |
| no English title found, or no answer (R3) | none |
| a title he typed | none: `Entered by you: title.` says it, as built |

- Source names are those of 4.3 (`FantLab`, `Goodreads`, `Wikidata`, `Litres`, `the publisher's site`).
- It is on every row of the book, before and after conversion, like the Place line's origin.
- Not a control: no tooltip, no focus stop. Never a question.
- **The title itself stays where it is today:** the Title field's proposal on a row that asks and in `Edit names`; `Canonical title: The Dark Forest` in the title cell once the book is approved; the file name in `Goes to` or `Now in`. Nothing is added for it.
- **The files' own title stays where it is today:** `Title clue: Тёмный лес`, in the title cell of a row not approved yet and under the Title field of a row that asks. Nothing is added for it either.
- The list's search still finds the book by its Russian name: it matches the title clue and the file paths (as built).

**The Place line (R1).** The series is named in English. The origin suffix of 4.3 keeps its meaning: where the series and the number came from. One part is new, and it is added only where the line would otherwise be untrue:

| Series and number from | English name from | Place line |
|---|---|---|
| an online source | the same source | `Series: Remembrance of Earth's Past · No. 2 · found on Wikidata` (unchanged) |
| an online source | another source | `… · No. 2 · found on FantLab · English name from Wikidata` |
| the files (tags, the title tag, the file name, brackets, folder names) | an online source | `… · No. 2 · from the file's tags · English name from Wikidata` |
| anywhere | he typed the series | `… · No. 2 · entered by you` (unchanged) |
| a book written in Russian, or no English name found | none | unchanged: the name its origin gave |

- Why the new part: without it a row says `from the file's tags` beside a name the tags do not contain. 4.3's rule: a row must not say a name came from somewhere it did not.
- A source with no name the page knows: ` · English name found online`.
- The record (3.4) uses the same words in an entry's series reason.

**No English title found (R3).** The Russian title stays and nothing asks. **The row says nothing:** no Title line, no note, no hint. He has nothing to do, and a note would stand on every such book. The details panel says it once (section 5, the facts).

**The details panel.** The fact labelled `Original title` is labelled **`English title`** (R1: for a book written in Chinese the app looks for the English title, which is not the original one). Its values are in section 5.

**Author folders (the name-order fix).** An author's folder is the Latin name, surname first: `Liu Cixin`. The row shows it where it shows the author today (the `Author` line, the line under the title, the `Goes to` path). **No new words:** no origin is added for the author's spelling, and the `Author unclear` questions keep their causes (4.4).

**When the app cannot tell which word is the surname.** Not ruled (Scope: "what to do with author names the app cannot order beyond the Liu Cixin fix"). Until Question 13 is answered the page has no words for it: the row shows the author as the engine files it and asks nothing, and a finished audiobook in such a folder is left alone and says nothing (3.5). If the answer is "ask", it is one more cause of the existing `Author unclear` question, with the sentence `The app can't tell which word is the surname.` and the two orders as its choices. Nothing else on the row would change.

## 5. Waiting for the online answer

**Amended 2026-11-22, fourth round (R20): this version. The wording below is final.** R2: a book may wait a few tries for the online answer before it converts; then it converts as before.

### 5.1 While a book waits

| Place | Words |
|---|---|
| Row status | `Waiting for an online answer` (replaces `Waiting for source` on a book that waits for an online source) |
| Row hint, the tries go on by themselves | `No online answer yet about its English title and series. Try 2 of 3 at 14:05. Nothing to do.` |
| Row hint, automatic processing is stopped | `No online answer yet about its English title and series. Press Start automatic processing to try again.` |
| Jobs panel, Waiting item, several books | `Waiting for an online answer: 3 books` / `Next try 14:05. After 3 tries a book converts with the names from its files.` No button. |
| Jobs panel, one book | `Waiting for an online answer: Тёмный лес` / the same line 2 / Show in list |
| Jobs panel, while it asks | the 0.30.0 row `Researching books: <book>`, unchanged |
| Automatic block detail (`Waiting for metadata sources; …`) | `Waiting for an online answer. Next try 14:05.` |

- **The asked part follows the book:** `its English title`, `its series`, `its English title and series`. If the engine does not say what is asked: `No online answer yet about this book.`
- **The tries.** `Try 2 of 3 at 14:05.` is the number of the next try, the number of tries in all, and the time of the next one. All three are the engine's; none is written into the page. With no time: `Try 2 of 3 is next.` With no numbers the sentence is left out. Read in the build: a book waits for its series at most 3 times in a row (`SERIES_WAIT_LIMIT`), at the time the source gave; whether the wait for a title uses the same number is the engine's (F2).
- **Only an online wait.** `Waiting for source` is also the status of a book that waits because the library drive answered slowly or the catalog was busy for a minute (read in `automatic_processing.py`). Those keep `Waiting for source` and are not counted in the Waiting item: "an online answer" would be untrue for them.
- **The hint** sits where every row's hint sits, under the status, in its look. The details panel's Automatic result shows the same status and hint. It is not a question, and the row keeps its ordinary buttons. No `Convert now` (Sergei's answers, Question 5).
- **Automatic processing stopped.** The tries do not go on, so `Nothing to do.` and a next try time would be untrue. The second hint names the button that starts them. There is no Waiting item then: nothing is waiting to run by itself.
- **State.** This is main work: while a book waits and the tries go on, the state is `Continues by itself`, never a badge (1.1).
- The Waiting item replaces 0.30.0's `Metadata sources` item (`3 books wait for a source to answer. Next try 14:05.`) for these books. `Next try 14:05.` is left out when the engine has no time.
- The Automatic block's line replaces `Waiting for metadata sources; saved research retries automatically.` and its two endings (`Next automatic retry check: …`, `Automatic retry time unavailable`). With no time it reads `Waiting for an online answer.` alone. It is used while the books that wait are waiting for an online source; if they wait for something else only (A17), the 0.30.0 line stays.
- No new control anywhere in this section.

### 5.2 How the wait ends

| End | The row | The details panel, facts |
|---|---|---|
| **Answered** | It leaves the wait and reads as any book does next: `Queued`, `Processing`, or a question of its own that is not about a doubtful series. The Title line and the Place line name the source (4.5). Nothing is said about the wait. | `English title: The Dark Forest` (as built) |
| **Nothing found** (the sources answered) | It goes on. The row says nothing (R3, 4.5). | `English title: No English title found online. Filed under the Russian title.` (the existing `Not found.` fact). No line for a missing series. |
| **No answer after the limit** | It converts under the names from its files. One note in the hint's place, while the row is `Queued` or `Processing`: `No online answer about its English title and series after 3 tries.` After that the row says nothing. | `English title: No online answer after 3 tries. Filed under the Russian title.` and `Series: No online answer after 3 tries.` |
| **A doubtful answer** (R21, R22) | As nothing found: the row says nothing (4.4). | nothing |

- "No answer" (the sources did not reply) and "nothing found" (they replied) are different sentences and are never merged.
- The note's asked part follows what got no answer, in the words of 5.1: a book whose title was answered and whose series was not reads `No online answer about its series after 3 tries.`
- The numbers (`3`) are the engine's.
- Nothing promises a later look-up. If the background look-ups find the names after the book has converted, the book is filed by the rules and shows as 3.3 and 3.4 describe.
- If he types the missing names in `Edit names` while the book waits, they are his answer. Whether that ends the wait at once is the engine's (F8); the page adds no words for it.

## 6. Other places this touches

- **Automatic block**, `Automatic pass complete — 12 converted · 3 held` (`app.js` 2913 to 2916): it speaks of one pass and read as "all done". It gains a suffix from the state: main work left: ` Other jobs are still running or waiting.`; only look-ups left: ` Background look-ups continue.`; otherwise nothing.
- **Busy notice** (`Busy with: …`): uses the row labels, so it takes the two new names. Amended, fourth round: also `Finding English titles and author names` (2.1) and `Renaming finished audiobook` (3.3).
- **`needs_you_only`**: the page stops reading it; the finished state replaces it.
- **0.30.0 spec**: mark as superseded: table 1.5 rows `series` and `gap_fill`; section 4 "First part when only cleanups wait"; and table 1.6 row `metadata_sources` (amended, fourth round: section 5 ships in 0.31.0).
- **Earlier specs, amended 2026-11-22, fourth round:** mark as superseded the rows `Number unclear` (ruling 74b) and `Title unclear` with `The title starts with what looks like a series name and number.` (ruling 52) wherever they are specced, and the 0.22.2 label `Original title` of the details panel's fact (now `English title`, 4.5).
- **The Quit question** (`Quit after the current book?`) and everything else the shell says on Quit: unchanged. Nothing new is asked when finished audiobooks are being renamed or moved (3.3a).
- **Unchanged:** Pause and Resume, the freshness cue, the unread line, On hold, every other row and Waiting item, the review table's columns, the chips other than Name taken's tooltip, themes and colours.

### 6.1 Singular forms

**Amended 2026-11-22 after build (G3); amended 2026-11-22, third round (R18, R19): every row about the approval list is removed with the list, and the rows of section 3 as it now stands are added. Amended 2026-11-22, fourth round (R20–R22): the quiet line's row is replaced, section 5's row is final, and the rows for 3.3, 3.3a, 3.4, 3.4a and 5 are added.** Every count this spec prints, one and many.

| Place | One | Many |
|---|---|---|
| status part | `1 background look-up left` | `212 background look-ups left` |
| Waiting-for-you | `1 book needs attention.` | `329 books need attention.` |
| look-up Waiting items, line 1 | `…: 1 book` | `…: 212 books` |
| look-up rows, detail | `1 of 1 book` | `691 of 903 books` |
| tries tooltip (2.2) | `Each source is asked once for a book.` | `…asked up to 3 times for a book` |
| tries tooltip, the gap | `, 1 hour apart` | `, 6 hours apart` |
| the quiet line (3.2; replaced, fourth round) | `1 finished audiobook could not be renamed or moved. It stays where it is.` | `12 finished audiobooks could not be renamed or moved. They stay where they are.` |
| grouped writes waiting (3.3), line 1 | never one: it groups above 5 | `Writing series into finished audiobooks: 290 books` |
| grouped renames waiting (3.3; fourth round), line 1 | never one: it groups above 5 | `Renaming finished audiobooks: 92 books` |
| grouped moves waiting (3.3), line 1 | never one: it groups above 5 | `Moving finished audiobooks: 338 books` |
| the notice (3.3a; fourth round), line 1 | `Filing 1 finished audiobook under the names found for it.` | `Filing 212 finished audiobooks under the names found for them.` |
| the notice, line 2 | the same words for every number | the same |
| the record's summary (3.4) | `Renamed or moved by the app · 1 · 22 Nov, 14:05` | `Renamed or moved by the app · 340 · last 22 Nov, 14:05` |
| the record, more than 200 | never one | `Showing the newest 200 of 1,240. Find book searches all of them.` |
| the record, more than 200 match (fourth round) | never one | `Showing the newest 200 of 312 that match.` |
| the list of 3.4a (fourth round; built only on a yes to Question 14), summary | `Could not be renamed or moved · 1` | `Could not be renamed or moved · 12` |
| the list of 3.4a, more than 200 | never one | `Showing 200 of 312.` |
| same name, destination label | `Both go to` (this book and one other) | `All 3 go to` |
| same name, sentence | one other book: it is named (4.1). One the engine cannot name: `1 other book would get this file name.` (kept, after the final build, gap 6) | `2 other books would get this file name.` |
| same name, button (amended after the final build, gap 2) | one other book: `Show the other book` | several: `Show one of the others` |
| section 5 (amended, fourth round: this version), Waiting item | `Waiting for an online answer: <the book's title>` | `Waiting for an online answer: 3 books` |
| section 5, the limit | `After 1 try a book converts…`, `No online answer … after 1 try.` | `After 3 tries…`, `…after 3 tries.` |
| section 5, the next try | no singular: a book that waits has at least a second try | `Try 2 of 3 at 14:05.`, `Try 2 of 2 at 14:05.` |

Not in this spec's list of changes, noted only: the 0.30.0 status part `N need attention` prints `1 need attention` for one book. `1 needs attention` would be right.

## 7. Controls: tooltip, disabled state, keyboard

| Control | Tooltip | Disabled when, and what it says | Keyboard |
|---|---|---|---|
| the record's summary, `Renamed or moved by the app · N` (3.4) | `Finished audiobooks the app renamed or moved by its rules, newest first.` | never disabled; hidden while the record is empty | in the jobs panel's tab order after the Waiting-for-you block; Enter or Space opens and closes |
| `Find book` (3.4) | `Show only entries whose title, author or path contains this text.` | never | typing filters 300 ms after the last key (amended, fourth round: it searches every entry, 3.4); Escape clears the field (and does nothing else) |
| the record's list (3.4) | none: a scrolling region, `aria-label="Books renamed or moved by the app"` | never | one tab stop; arrow keys and Page Up, Page Down scroll it; Escape puts the focus on the record's summary (amended, fourth round) |
| **Show in list**, on a record entry (3.4) | `List this book: sets Status to All and searches for its title.` | amended, fourth round: `aria-disabled` when the book has been deleted from the app since; tooltip `This book is not in the app.` | follows its entry in tab order; Enter or Space; Escape puts the focus on the record's summary |
| **Show in list**, on a grouped Waiting item (3.3) | the same; never the variant that ends `Its row has Cancel.` (amended, fourth round) | never | as on any Waiting item |
| **Show in list**, on the one-book item `Waiting for an online answer: <book>` (5.1; fourth round) | `List this book: sets Status to All and searches for its title.` | never; the several-books item has no button | as on any Waiting item |
| **Choose folder…**, on a finished audiobook whose rename or move the app has queued (3.3; fourth round: an existing control, a new disabled reason) | enabled: unchanged | `aria-disabled` while the app's own rename or move is queued. Tooltip: `The app is about to move this audiobook. Choose another folder when it has moved.` A rename in place: `The app is about to rename this audiobook. Choose a folder when it is done.` While the move runs: disabled with the 0.30.0 tooltip `Moving the audiobook. Choose another folder when it finishes.`, unchanged | keeps its focus stop, as every `aria-disabled` button here |
| **Cancel**, on a queued move (0.30.0) | unchanged | not shown on a rename or move the app queued by its rules (3.3; fourth round); shown as before on a move he queued | unchanged |
| the summary `Could not be renamed or moved · N` (3.4a; fourth round; **built only on a yes to Question 14**) | `Finished audiobooks the app has a new name or folder for and could not use, each with the reason.` | never disabled; hidden at zero | follows the record's summary in tab order; Enter or Space opens and closes |
| its list and its **Show in list** buttons (3.4a) | the list: none, `aria-label="Books that could not be renamed or moved"`; the button: `List this book: sets Status to All and searches for its title.` | never | as the record's list and buttons, Escape included |
| **Show the other book** / `Show one of the others` (was `Show both books`; amended after the final build) | 4.2: `List the other book: sets Status to All and searches for its folder or file name.` | never disabled; not shown when the name is free, when a file with it is on disk, or when the engine sends no name for the other book | class S: in the row's action order after Approve. Class Q (4.2a): last of the row's ordinary buttons, before `Delete book`'s own line |

- **Amended 2026-11-22, third round (R18, R19).** Every row of the withdrawn dialog is removed: the shortcut, `Review changes`, `Select all`, the groups, the books' checkboxes, `Left as they are`, `Leave as it is`, `Offer again`, `Cancel`, `Rename or move N books`. The record of 3.4 is the only new thing with controls, and none of them changes anything: it has no button that acts on a book's files.
- The quiet line of 3.2 is not a control and has no tooltip.
- **Amended 2026-11-22, fourth round (R20–R22).** New things that are **not** controls and have no tooltip and no focus stop: the notice (3.3a), the Title line and the English-name part of the Place line (4.5), the hint and the note of a book that waits for an online answer (5.1, 5.2). Everything they say is on screen.
- **Controls that go, fourth round (R22):** on a row that asked `Number unclear` or `Title unclear` about a series, the inline Series and Number fields and the row's `Approve` go with the question; in the details panel `Resolve metadata` and `Save choices` are hidden with their block when no question is left (4.4). No control is left without the thing it acted on.
- **No new control** in sections 4.4, 4.5 and 5. No `Convert now` (ruled).
- Opening the record, typing in `Find book` and a refresh of its entries never move focus and never reset the scroll position.
- Hover-only texts on things that are not controls: the badge (1.2), the two step lines (2.1), line 2 of the grouped look-up items (2.2), the source name on a record entry (its address). None carries anything that is not also on screen in short form.
- Every `aria-disabled` button keeps its focus stop and says why in its tooltip (the app's existing pattern).

## 8. Layout, overlap and contrast

**Narrow layouts.** No string differs by width.
- Review table: every new row text is in the status cell or the destination cell, which the medium (600 to 799) and compact (under 600) bands never hide. Nothing new goes into columns 3 and 4, which they fold.
- Jobs panel under 560 px: rows stack as built; labels and steps keep their one-line ellipsis and full `title`. The status line wraps; the badge stays whole on the first line.
- The record (3.4) under 600 px: the label (`Was in`, `Now in`) sits above its path; paths wrap anywhere; an entry's Show in list drops to its own line under the paths, left-aligned.
- **Amended 2026-11-22, fourth round (R20–R22).**
  - The notice (3.3a) is a block as wide as the panel; both lines wrap, never an ellipsis; it has no button to place.
  - The Title line and the Place line (4.5) are in the status cell, which no band hides. Each wraps; a long English series name with two origin parts takes two or three lines and pushes the `In` and `Goes to` lines down.
  - The hint of a waiting book (5.1) and the note of 5.2 wrap in the hint's place, as every row hint does.
  - The list of 3.4a (if built) follows the record's narrow layout: `Now in` and `Would be in` above their paths, the reason under them, Show in list on its own line.

**No element covers another.** By construction, not by measurement: everything new is in normal flow (no absolute, fixed or sticky positioning), so it can only wrap or push. **Amended, third round:** with the dialog withdrawn, this spec adds no overlay at all. States walked through on paper: each of the eight first parts of 1.1 (with `Checking what is left`, amended) with 0, 1, 2 and 5 rows; `Paused` beside a running look-up row; the badge with and without the as-of suffix; the Waiting-for-you block with its one line; the freshness cue and the unread line shown; the quiet line of 3.2 shown and hidden, alone and under an open record; the record closed, open with 1, 200 and 1,240 entries, loading, failed, with `Find book` matching nothing, with long Cyrillic paths, at each width; the Waiting list with 5 and with 338 queued moves and 290 waiting writes (3.3); the same-name row (class S) in the wide, medium and compact bands with Edit names open; a class Q row with its own buttons plus Show the other book, before `Delete book`'s line, in the same three bands; the Place line with a long series name and each origin suffix. Futaba measures the rects (check 12).

**Amended 2026-11-22, fourth round (R20–R22).** Everything this round adds is in normal flow too, and it adds no overlay. States walked through on paper, by name:
- **The notice (3.3a):** shown and hidden, under the toolbar with the freshness cue showing and with the unread line showing; with 0, 1, 2 and 5 Running rows; beside `Paused`; with a five-digit number; at 560 px and at 200% zoom. It sits below the toolbar, so the Pause and Resume rects do not move when it comes or goes; the lists below it move down by its height once, at the start, and up once, at the end. A badge and the notice are never on screen together (the notice means main work, and a badge means there is none).
- **The Waiting list (3.3, 5.1):** three grouped items at once (series writes, renames, moves) beside the two look-up items and the item `Waiting for an online answer`, with one book (a button) and with several (no button).
- **A finished audiobook's row with the app's move queued (3.3):** `Moves to` and its path, `Choose folder…` disabled, no `Cancel`: the destination controls keep their places and nothing moves into the gap `Cancel` leaves.
- **A translated book's row (4.5):** the Title line alone, the Place line alone, both, neither; with the longest Place line (two origin parts); on a row that asks (the Title field and `Title clue:` above, the lines below) and on one that does not; with `Edit names` open; in the wide, medium and compact bands.
- **A waiting book's row (5.1):** the status with each of the two hints, three sentences wrapping in the compact band; the same row once `Queued` with the note of 5.2.
- **A row that used to ask about a series (4.4):** no hint, no inline fields, no `Approve`: the row's ordinary buttons close up and the row is as high as any row that asks nothing.
- **The details panel (4.4):** the `Sources disagree` block hidden whole, and shown with one remaining question: the `Names` block and the fields under it move up into its place.
- **The record (3.4)** with a disabled Show in list among enabled ones; with `Showing the newest 200 of 312 that match.`; **the list of 3.4a** (if built) open under an open record, each scrolling inside itself, the quiet line and the help lines pushed down and not covered.

Futaba measures these rects too (check 12, as amended).

**Contrast, dark tokens (the only theme).** Computed ratios, text against its background:

| Use | Pair | Ratio |
|---|---|---|
| `All done` badge text | `--notice-text` on `--notice` | 10.8:1 |
| `All done` badge edge against the panel | `--notice-border` on `--surface` | 5.0:1 (needs 3:1) |
| `Waiting for you` badge text and edge | `--warning` on `--surface` | 11.2:1 |
| `Background look-ups only` badge text | `--text` on `--raised` | 11.3:1 |
| its edge against the panel | `--border` on `--surface` | 4.1:1 (needs 3:1) |
| the record's text, titles, paths (3.4) | `--text` on `--surface` | 13.9:1 |
| muted path folders, labels, the quiet line (3.2), help lines | `--muted` on `--surface` | 8.9:1 |
| warning lines | `--warning` on `--surface` | 11.2:1 |
| quiet button text (Show in list, Show the other book) | `--accent` on `--surface` | 8.0:1 |
| disabled button text (a blocked approve press, 4.2a) | `--disabled-text` on `--disabled` | 6.1:1 |
| focus ring | `--focus` on `--surface` | 11.2:1 |
| **fourth round:** the notice's two lines (3.3a) | `--notice-text` on `--notice` | 10.8:1 |
| the notice's edge against the panel | `--notice-border` on `--surface` | 5.0:1 (needs 3:1) |
| the Title line, the Place line's new part, the hint and note of a waiting book (4.5, 5), on a row at rest | `--muted` on `--surface` | 8.9:1 |
| the same lines on a hovered row | `--muted` on `--row-hover` | 6.6:1 |
| the same lines on the selected row | `--muted` on `--row-selected` | 5.0:1 (needs 4.5:1) |
| `Find book`, typed text (3.4) | `--text` on `--field` | 15.8:1 |
| `Find book`, its edge against the panel | `--border` on `--surface` | 4.1:1 (needs 3:1) |
| disabled `Choose folder…` and a disabled Show in list (3.3, 3.4) | `--disabled-text` on `--disabled` | 6.1:1 |
| the reason line of an entry in 3.4a | `--text` on `--surface` | 13.9:1 |

Nothing new relies on colour alone: each state, warning and disabled reason is also words. Fourth round: the notice box shares its colours with the `All done` badge; the two are never on screen together (above), and each says in words what it is.

## 9. Acceptance checks (Futaba)

1. **All done is true.** Force every other state in turn (a conversion, a queued action, a timed cleanup retry, automatic processing between tries, a series look-up between tries, a detail look-up running, one book needing attention, a drive not answering (R14), one series write waiting, one rename waiting, one move of a finished book queued, and one book waiting for an online answer with automatic processing running): the badge never reads `All done`. Positive control: with all of them cleared it does, within 3 s, and the four lists are empty. (Amended, third round: a rename or move waiting for his approval is no longer a state. Amended, fourth round: the writes and moves are no longer conditional, the waiting book is added, and check 37 covers the books that could not be moved.)
2. **Three badges.** Each of `All done`, `Waiting for you`, `Background look-ups only` shows for its state, and `Waiting for you` wins when both apply while the look-up item stays on screen.
3. **No bare `Nothing running`** in the status line in any state.
4. **No flicker.** A job under 1 s does not remove the badge.
5. **Counts behind.** At 45 s the badge is followed by `(as of …)`.
6. **Names.** A running series look-up reads `Finding series for finished audiobooks: <book>`, its step says no file is changed, and its count is the whole look-up (it does not start again at the next pass). Writing shows the writing step.
7. **Between tries.** With look-ups deferred and none running: a grouped Waiting item with a count and a next try time; the badge is `Background look-ups only`; no row carries `No progress for 5 min`.
8. **Withdrawn 2026-11-22, third round (R18).** Was the dialog. Not built, not tested.
9. **Withdrawn 2026-11-22, third round (R18).** Was the dialog's changed list.
10. **Withdrawn 2026-11-22, third round (R18).** Was Leave as it is and Offer again.
11. **Same name (class S).** Two books the app would have filed by itself under one name: each row held for it reads `Same name as another book`, names the other's folder or file, has Approve disabled with its reason, and shows neither `Part of a bigger book` nor `Approve as one book`. Changing one title frees both.
12. **Layout, measured rects.** At 1280, 960, 760, 600 px and 200% zoom, long Cyrillic names: the toolbar rect is identical with and without the badge; no rect of the badge, the block line, the quiet line, the record's summary, its entries and their buttons, or row buttons intersects another; an open record with 200 entries scrolls inside itself and pushes the help lines down without covering them. (Amended, third round: the dialog's rects are gone with it. Amended, fourth round: also every state named in section 8's fourth-round list: the notice, three grouped items, a finished row with the app's move queued, a translated book's row, a waiting book's row, a row that used to ask about a series, the details panel with its block hidden.)
13. **Keyboard.** The record (3.4) can be opened, searched, scrolled and left without the mouse, and Show in list on an entry works from the keyboard. (Amended, third round: was the dialog. Amended, fourth round: Escape on the list or on an entry's button puts the focus on the record's summary; in `Find book` it only clears the field.)
14. **R4 row.** A volume with its own title tag and a series in its tags shows its own title and `· from the file's tags`, and carries no question.

Added 2026-11-22 after build:

15. **Own question kept (class Q, G9).** Pieces of one book that all carry the set's name, each a `Part of a bigger book` row with `shared` set: every row still reads `Part of a bigger book` with its own sentence, still has `Approve as one book` (disabled, with R17's reason line `Another book would get this name. Join them into one book, or change this title.`) and `Keep as separate books` (enabled), its label reads `All N go to`, and it has the show button of 4.2 (`Show one of the others`; `Show the other book` when there is one). None reads `Same name as another book`. Typing a free title enables the approve press at once. Positive control for the split: a class S pair on the same list (check 11) reads `Same name as another book`, so both presentations are seen from the same `shared` fact.
16. **Withdrawn 2026-11-22, third round (R18).** Was G4's gate on line 2. Its replacement is check 27: the line and the status part are gone in every build.
17. **Still counting (G1, G2).** In the 2 minutes after the last book finishes, and in the 3 s before a badge comes up, the status line starts with `Checking what is left`: never with the counts, never with `…could be read`. With a source really unread for 3 s it reads `Nothing running that could be read`.
18. **Paused beside a look-up (G7).** Pause with only a series look-up running: the line starts `Paused · Finding series for finished audiobooks: <book>`.
19. **Tries tooltip (G8, R16).** Both look-up items' tooltips print the engine's tries per source and hours apart (3 and 6 today, each look-up its own numbers); change the engine's numbers and the tooltip follows. The no-limit sentence appears nowhere.

Added 2026-11-22, Sergei's answers:

20. **Withdrawn 2026-11-22, third round (R18).** Was every kind of change in one approval list.
21. **Withdrawn 2026-11-22, third round (R19).** Was the held books under Left as they are. Check 26 replaced it; check 26 is itself replaced by check 37 (fourth round).
22. **Withdrawn 2026-11-22, third round (R18).** Was Leave as it is on a book with two kinds of change.
23. **Window title (R13).** Force each engine state: the main window's title is the one in table 1.5, and it changes with the status line, never ahead of the badge. No taskbar flash, no focus change.
24. **Withdrawn 2026-11-22, third round (R18).** Was the grouped item after an approval. Check 29 replaces it.
25. **Title tag (R15).** A file whose only clue is the title tag `Sprawl Trilogy 01 - Neuromancer`: no question on its row, title `Neuromancer`, Place line `Series: Sprawl Trilogy · No. 1` with the tag suffix of 4.3.

Added 2026-11-22, third round (R18, R19):

26. **Replaced 2026-11-22, fourth round (R20).** Was the quiet line with the guard at hold (`Series found for 61 finished audiobooks…`). That state does not ship. Check 37 replaces it.
27. **Nothing asks.** With books that have a series found: no status part about renames or moves to approve, no second line under Waiting for you, no shortcut, no dialog, no button that approves or refuses a move anywhere on the page. (Amended, fourth round: was "in both states"; there is one.)
28. **Replaced 2026-11-22, fourth round (R20).** Was the tooltip that followed the guard. Check 36 replaces it.
29. **Many at once.** With a backlog of more than 5 finished audiobooks the rules can file: the series row shows its writing step for the book being written; `Moving: <book>` shows for the one moving; the Waiting list has at most one grouped item for the series writes, one for the renames and one for the moves, each with `Next: <book>.` and the engine's whole number; with 5 or fewer, one item each. The status line names the work, no badge shows, and `All done` comes only after the last book. (Amended, fourth round: no switch to turn on; the renames' group is added. The notice is check 38.)
30. **The record.** After that run: `Renamed or moved by the app · N · last <date>` is at the bottom of the jobs panel; opened, its newest entry is the last book moved, with the right `Was in` and `Now in`, the series, number and source it was filed by, and one entry per book (a write followed by a move is one entry). A book only renamed in its folder has an entry. A move he made with `Choose folder…` has none. `Find book` narrows the list; Show in list finds the book's row. Before any automatic move, the record is not on the page. (Amended, fourth round: a book renamed for its English title has the reason `English title found on <source>`, and Show in list finds it by that title; with more than 200 entries the newest 200 show with the `Showing the newest 200 of N` line, and `Find book` finds an entry that is not among them; a book deleted from the app since has a disabled Show in list with `This book is not in the app.`)
31. **Replaced 2026-11-22, fourth round (R20).** Was R19's books kept for a later version. No book is kept back: English names ship in 0.31.0.
32. **A doubtful result is silent.** A finished audiobook whose series result the engine treats as not found: its row, its details panel, the jobs panel and the record say nothing about a series; it is not in the quiet line's number; the look-up counts it as settled. (Amended, fourth round, R21: force each doubtful shape in turn: local facts contradict the result, two series on the book, a universe in place of a series, a number mismatch. Positive control: a series found on FantLab alone with a counted number is filed, and its Place line reads `found on FantLab`.)

Added 2026-11-22, after the final build:

33. **A clash that has ended (gap 1).** A class S row whose other book is renamed away while the row is still listed: its sentence reads `The name is free now. Approve files the book under it.`, never the other book's name; the label is `Goes to` and Approve is enabled. Convert the other book instead, so its file is in Audiobooks Sorted: the sentence is the Name taken one and the label `Already there`. Typing a free title on a clashing row gives the first sentence at once.
34. **The show button (gap 2).** On a class S row and on a class Q row with one other book: the face is `Show the other book`; a press lists that book (Status All, its own folder or file name in the search) and its row is on screen, whatever the two books' titles are. Positive control: two books whose proposed title is nowhere in their tags or paths.
35. **Brackets (gap 5).** A series read from brackets in the folder's name: the row's suffix is ` · from the brackets in its name` (or none), never `from the file's tags`.

Added 2026-11-22, fourth round (R20–R22):

36. **One state (R20).** The series row's step tooltip always reads `…When author and series are found for certain, the book is filed under them. Otherwise it stays as it is.` The words `recorded and stay where they are`, `No audiobook is renamed or moved.` and `next version` are nowhere on the page. The detail look-up reads `Finding English titles and author names`, in its row and in its Waiting item, and its tooltip ends `This look-up changes no file.`
37. **Could not be renamed or moved (3.2).** A finished audiobook with a certain series whose new file name already exists in the series folder: it is not moved, has no row and no Waiting item, the badge reads `All done`, and the bottom of the jobs panel reads `1 finished audiobook could not be renamed or moved. It stays where it is.` With twelve: the plural. With none: no line. Controls that the number is the right one: a doubtful result is not counted; a book whose folder he chose is not counted; a book that is being moved or waits its turn is not counted. Positive control that the line is not a state: add one book needing attention and the badge turns `Waiting for you` with the line unchanged.
38. **The notice (3.3a).** With more than 5 finished audiobooks to rename or move: the notice is under the toolbar, reads `Filing N finished audiobooks under the names found for them.` with the engine's number, and its number goes down as books are done; it stays below 5 and goes at zero, and nothing takes its place. With 5 or fewer from the start: no notice. It has no button, no tooltip and no focus stop. Quit in the middle and start again: no question beyond the 0.30.0 Quit; after the start the notice is back with the number that is left; the record still has the entries made before the Quit; the words `interrupted`, `resumed` and `again` are nowhere. Positive control for the last sentence of line 2: with nothing pressed, the remaining books are filed after the restart.
39. **No Cancel on the app's own move (3.3).** A finished audiobook whose move the app queued: its row reads `Moves to` and the new path, has no `Cancel`, and `Choose folder…` is `aria-disabled` with `The app is about to move this audiobook. Choose another folder when it has moved.` After the move `Choose folder…` works, and a folder chosen then is kept: the rules do not move the book back. Positive control: a move he queued with `Choose folder…` has `Cancel`, as 0.30.0. The Waiting item's Show in list tooltip does not end `Its row has Cancel.`
40. **Waiting for an online answer (5.1).** A book whose online sources are closed: the row reads `Waiting for an online answer`, its hint names what is asked and prints the engine's `Try N of M` and time, the Waiting list has the item with `After M tries a book converts with the names from its files.`, the first part of the status line is `Continues by itself`, the window title `Books Arranger: continues by itself`, and no badge shows, also with books needing attention. Change the engine's limit and both texts follow. Stop automatic processing: the hint ends `Press Start automatic processing to try again.`, with no try number and no time. Control: a book that waits because the library drive is slow still reads `Waiting for source` and is not in the item's count. No `Convert now` anywhere.
41. **How the wait ends (5.2).** Answered: the row goes on, with the Title line and the Place line naming the source, and nothing about the wait. Nothing found: the row says nothing, and the details panel reads `English title: No English title found online. Filed under the Russian title.` No answer after the limit: the book converts, the row carries `No online answer about … after M tries.` while `Queued` or `Processing` and nothing afterwards, and the details panel has the two `No online answer after M tries` facts. The two outcomes are never worded alike.
42. **English names (4.5).** A translated book with an English title from Wikidata: `English title found on Wikidata.` directly above the Place line, before and after conversion; the Place line names the English series with its origin; where the series came from the file's tags and its English name from Wikidata, the line ends ` · from the file's tags · English name from Wikidata`. A book written in Russian, a book with no English title found and a title he typed: no Title line. The details panel's fact is labelled `English title`. Searching the list for the Russian title finds the row.
43. **A doubtful series on a book not converted yet (R22, 4.4).** Three books, one for each former question (a number that disagrees with FantLab; a title that only looks like a series name and number; two sources that differ only in the series): none is on the to-do list, none reads `Number unclear` or `Title unclear`, none has a sentence, inline Series or Number fields or `Approve`; none has a Place line; the details panel has no `Sources disagree` block, no `Resolve metadata` and no `Save choices`; each goes on to convert. Positive controls, on the same list: a book with two people credited still reads `Author unclear` with its choices; a title ending in a bitrate still reads `Title unclear`; two sources that differ in the title still show the `Sources disagree` block, without a series question in it.
44. **Author folders (4.5).** A translated book's author folder is the Latin name, surname first (`Liu Cixin`), on the row and in the `Goes to` path. No new line on the row about the author's name. (What happens to a name the app cannot order is Question 13; until it is answered there is nothing to test.)
45. **Rename row (3.3).** If the engine sends a rename of a finished audiobook as a job of its own: its row reads `Renaming finished audiobook: <book>` with the step `Writing the new names into the file and renaming it. Audio unchanged.`, it counts as main work (no badge), and one that waits reads `Rename finished audiobook: <book>` with its blocker sentence. If the engine sends no such job, this check does not apply.
46. **The list of 3.4a.** Only if Question 14 is answered yes: `Could not be renamed or moved · N` is under the record, check 37's line is gone, each entry has `Now in`, `Would be in`, one reason sentence of the table and Show in list, and nothing in it changes a file. If the answer is no or not given: the element is not on the page.

## Notes for Ender

What the page needs from the engine, in plain words. How is yours.

**Section 1**
- One finished-state value per poll, decided by the engine from live facts: working, paused, continues by itself, waiting for you, background look-ups only, all done; and "not known" while a source is unread. The truth rules are table 1.1 and its bullets.
- For every row and Waiting item: whether it is a background look-up (so the page never guesses which work is "main").
- Counts: background look-ups left (series and detail, apart and together); drives not answering; books on hold (existing).
- The reasons something waits for him, as keys: attention, hold, drive.
- **Amended 2026-11-22, third round (R18, R19).** A rename or move of a finished audiobook is no longer a reason something waits for him. Today the engine sends `moves` among those reasons and lets it make the state `waiting for you`; that has to go, in both states. The number itself stays, for the quiet line (Section 3 below).
- **Amended, third round.** Which work is "main": writing a series into a finished file, and a write that waits for a job, are main work, not background look-ups (1.1). Today the series row and the waiting write are both marked as background whatever the step. Only the asking online is a look-up. This matters only once the automatic move is on.
- **Amended 2026-11-22, fourth round (R20–R22).**
  - The automatic move is on in 0.31.0, so the line above is always in force. A rename of a finished audiobook (3.3), running or waiting, is main work too.
  - A book that waits for an online answer before it converts is main work while its tries go on by themselves: the state is `continues by itself`. I read that the build already does this for the 0.30.0 wait (the `metadata_sources` item is not a background look-up, and a next retry time makes the state `continues`). Keep it so for the new wait.
  - With automatic processing stopped such a book is nothing pending, as today. The row then needs to know that its tries do not go on (Section 5 below).
  - A book the rules could not rename or move, and a doubtful result, are in no state and in no reason. The state table needs nothing new.
- Amended, Sergei's answers (R13): nothing new for the window title. It is made from the state the page already has. If the shell does not take its title from the page (F3), that is the one thing to wire.
- Amended after build (G1): when the state is "not known", whether a source is unread or the engine is still counting. The page reads this today from the unread list being empty; that is enough.

**Section 2**
- For the series and the detail look-up rows: done and total over the whole look-up (settled books, all books that needed it), and the step (looking up, writing).
- For each look-up between tries: how many books wait, the time of the next try, the tries limit. Amended after build (G8): the limit is tries per source, and the tooltip also prints the hours between tries, so the page needs that number too; without it that part of the sentence is left out.
- For a series write held by a job: the book, and a blocker object of the 0.30.0 shape.
- A look-up that waits on a source's pacing is not a running row.
- A real end: each book is settled after a limited number of tries (the limit is a product number, not mine). Amended, Sergei's answers: both look-ups have one now (R9: 3 per source, 6 hours apart; R16: the detail look-up the same). The detail look-up's Waiting item needs its own tries per source and hours apart, as the series item has; the page prints one sentence for both.
- Question 4 was answered no: nothing is needed for books a look-up gave up on.
- **Amended 2026-11-22, third round.** The series row's step tooltip follows one fact: does the app apply a found series by itself (no while the guard is at hold, yes once the automatic move is on). That is the only place the page reads which state it is in.
- **Amended 2026-11-22, fourth round (R20).** The page no longer reads that fact: the tooltip has one sentence (2.1). Nothing on the page depends on the guard any more.
- **Amended 2026-11-22, fourth round (R1).** The detail look-up's label and tooltip change on the page only (2.1, 2.2). Nothing new from the engine. One thing to tell me: if this look-up itself ever changes a file, the step line `Recorded only, no file is changed.` and the tooltip's `This look-up changes no file.` are untrue and I reword them.

**Section 3**
**Amended 2026-11-22, third round (R18, R19).** Everything the withdrawn dialog needed is withdrawn with it: the list for approval, the kinds of change per book for it, the digest sent back, leave-as-it-is and its undo, the approve answer per book, the reason keys of Left as they are. The page asks for none of it. What it needs instead:

**Amended 2026-11-22, fourth round (R20–R22). What section 3 needs now, in one list.** The third round's notes under it are kept for the record; where they say "in both states" or "once the automatic move is on", read "always".

*For the quiet line (3.2), fourth round*
- One number, with a new meaning: finished audiobooks for which the rules have a certain new name or folder and could not make the change, for a lasting reason. Books, each once. The reasons that count and the ones that do not are the table in 3.2 (your keys `name_exists`, `same_target`, `not_app_name`, `not_where_recorded`, `no_name` and a change that failed for good count; a doubtful result, a folder he chose, files he chose to keep, a book outside Audiobooks Sorted and a book being moved or waiting do not).
- The number the page reads today counts series held by the guard. With the guard automatic that number is empty or means something else; tell me which field carries the new one.
- F12: once the reason is gone (he removes the file that was in the way), do the rules file the book by themselves at the next pass?

*For the rows and items (3.3), fourth round*
- Whether a rename of a finished audiobook for an English title, an author's name or a series name runs as a job of its own, inside the series row's writing step, or inside the move (F10). If it is its own job: a row kind and a waiting kind for it, with the book and the 0.30.0 blocker, marked as main work. Its words are in 3.3.
- For each of the three groups (series writes, renames, the app's own moves that wait): the whole number, and the first one's book and blocker. The page groups above 5. The build lists at most 100 waiting writes; the group's number must be the whole count.
- On a book's row and on a queued move: whether the rename or move is the app's own or one he queued with `Choose folder…`. The page shows no `Cancel` for the app's own and disables `Choose folder…` with its reason while it is queued or running (3.3; Question 16).
- Confirm two things 3.3 rests on. A folder he chooses for a book after the app has moved it is kept: the rules do not move it back (I read "You chose its folder; left as it is" in `sorting_moves.py`). And a cancelled rule-made move would simply be queued again, which is why `Cancel` is not offered.

*For the notice (3.3a), fourth round*
- One number per poll: finished audiobooks the rules are renaming or moving now or are about to, books, each once (a book with a write and then a move counts once until both are done). It only goes down within a run.
- A16, to confirm: at start the engine cancels every move that was queued and not started (`book_move.py`: "The app closed before the move ran") and finishes the one that was cut. The rules must then queue the rest again by themselves, with nothing pressed. Line 2's last sentence (`If you quit, the app goes on next time.`) rests on it; if it is not so, tell me and the sentence goes.
- Nothing for Quit: no new question, no new text in the shell.

*For the record (3.4), fourth round*
- One more reason per entry: an English title, with the name of the source it was found on. And for the series reason, the source of the English name when it is not the source of the series (the same two facts the row gets, Section 4 below).
- The title sent with an entry is the one the book is filed under now.
- Per entry: whether the book is still in the app (Show in list is disabled if not).
- A search over every entry by a text (title, author, either path), newest first, at most 200 back, with the whole number that match. The first 200 without a text come with the whole number of entries, as before.
- Everything else as the third round's list below.

*For the list of 3.4a, only if Question 14 is answered yes*
- The books counted in 3.2's number, each with: the book's id, title, author, the path it is at, the path it would have, and the reason as one of the keys of 3.4a's table. The build's plan already carries these for every book it refuses (`book_id`, `title`, `author`, `from_shown`, `to_shown`, `refused_key`); the list wants only the ones 3.2 counts.

*Third round, for the record: the quiet line (3.2)*
- One number: finished audiobooks with a series found that the app relies on and has not written. Books, each once. Not a book being written or moved now, not a doubtful result. The engine already counts the held series writes; this is that number, kept, with its meaning changed from "waits for him" to "not applied". **Fourth round: replaced by the number above.**
- Nothing else. No list, no reason per book.

*For the rows and items (3.3), once the automatic move is on*
- The series row's writing step, as now.
- A write that waits for a job: the book and a blocker object of the 0.30.0 shape, as now. With more than 5, the page groups them itself; it needs the whole number and the first one's book and blocker.
- A move that waits: confirm that an automatic move waits as a queued action of its own (the plan's note says "queued like a Choose folder move"). The page groups more than 5 of them itself. If they wait some other way, tell me how they show and I will word that instead.
- Tell me whether a queued automatic move has a Cancel on the book's row as a Choose folder move has, and what then stops the rules from queueing it again. I have added no control and no words for it. **Fourth round: decided for the page in 3.3 (no `Cancel` on the app's own move); the two engine facts it rests on are in the fourth-round list above.**

*For the record (3.4), once the automatic move is on*
- With the normal state: how many finished audiobooks the app has renamed or moved by its rules, and the time of the last one. That is what the summary prints while the record is closed.
- On opening it, the entries, newest first. Per entry: the book's id (for Show in list), its title, the author it is filed under now, when it happened, the path before and the path after (shown under Audiobooks Sorted, and whole), and each reason the rules had, with its value: series found (name, number, source name and address), author folder (the new folder's name), series name (the new name). Values as fields, never an engine sentence.
- One entry per book per time the rules were applied: the path before the app touched the book and the path it ended at. A series write and the move that follows it are two records in the engine and one entry here; the in-between name is not sent.
- Only changes that finished. Only the app's own: the engine must tell a rule-made move from a folder he chose himself, which is not listed.
- I read that the engine already keeps this: `book_moves` has the paths before and after, the times and the state of every move, and the series look-up's own record has the old and new path, the series, its number and its source. I did not run anything; if a piece is missing, tell me which.
- Whether the moves he approved by hand in 0.30.0 belong in the record is yours to say: they were rule-made. I would list them.

*For a doubtful result (3.5)*
- Nothing. It must arrive exactly as a book with no series found: settled in the look-up's count, absent from the quiet line's number, and with no field the page could show.
- **Amended 2026-11-22, fourth round (R21).** A series found on FantLab alone, with a counted number, arrives as any series a source gave: origin `source`, provider FantLab. The page needs no fact that the number was counted.

**Section 4**
- The new hold as its own reason on a row: the shared destination, how many others, and for each other book its id, whether it is a row or a queued book, and a name that tells it apart (its folder or file name, different from this row's).
- A code for Approve refused by a late clash.
- Its count under Name taken (or its own key the page adds to that chip).
- For R4: where a row's series and number came from (file tags, a named online source, entered by him), and for the details line, that the title came from the file's own title tag.
- Amended after build (G9): the split of 4.1 needs the row's own hold kind, apart from `destination.shared` (whose `kind` is `same_destination` on every row that has it). If the row does not carry it, add it; nothing else is missing. `shared` must keep coming with the `Goes to` preview, so a typed name that is free clears the label and the disabled press at once.
- **Amended 2026-11-22, after the final build.** Three small things, one batch:
  - Gap 5: an origin of its own for a series read from brackets (the album tag, the title tag or the folder's name: the record does not keep which). Today it is sent as `tags`.
  - Gap 2: nothing new. The show button uses the other book's id and name, which `destination.shared` already carries. A list filter by book ids is the fact a real "show both" would need; not asked for now.
  - Gap 1: nothing new. The page already has the latest answer's `shared`, `taken` and path.
- Amended, Sergei's answers (R15): a finer origin for the series than `tags`, so the Place line can say where it was really read: the series tags, the title tag's own text, or the file name (today all three arrive as `tags`; a series in brackets in the file name is not from a tag). And for the details line: that title, series and number all came from the title tag.
- Amended after build (G9), for your judgement, not a page matter: on class Q rows the page now disables the approve press whenever `shared` is set, because the engine refuses it. If a press on a real piece should go through when the only other books are its own set-mates, that is an engine rule; the page follows `shared`.

- **Amended 2026-11-22, fourth round (R22): a doubtful series on a book not converted yet (4.4).**
  - The engine stops sending the two asks (`number_unclear`, and `title_series` where nothing confirms the split) and stops listing a `Sources disagree` question whose sources differ only in the series or the number in it. Such a book carries no ask, no series on its Place line and no count under `Title or author`; a Missing files row carries no `also` for these causes.
  - Rows that are on the to-do list with one of these questions when the update is installed must be checked again by themselves, so they stop asking without a press.
  - A series he typed or approved is never doubtful and stays.
  - F9: under which title a book shaped "Series N. Title" is filed once its series is dropped: the whole text as the files have it, or the title part. The page shows whatever you file it under. Today's question proposes the title part; with the series "treated as not found" the whole text is the reading that guesses nothing. Yours to propose.
  - Read in the build, same kind, not named by R22: a book held with `Series and standalone evidence conflicts`, and the routing stop `Series membership has conflicting author credits. Confirm this book in Edit names.` Whether they follow R22 is Question 15. Until it is answered they stay as built. If you know of others, add them to that question.
- **Amended 2026-11-22, fourth round (R1, R3): English names on a row (4.5).**
  - Per row, where the title the book is filed under came from: the files, typed by him, or an online source with its name. The Title line shows only for the last.
  - Per row, when the series name shown is an English name taken from a source other than the origin already sent: that source's name. Otherwise nothing.
  - For the details panel's `English title` fact, one of: found (the title), nothing found, no answer after the limit (with the number of tries), typed by him. Today it has found, none and Russian original.
  - F11: what a translated book's series is named when no English name for the series is found. The page prints the name it is sent, with its origin.
  - For the author: nothing new. What the app does with a Latin name it cannot order is Question 13.

**Section 5** (amended 2026-11-22, fourth round: this version)
- Per waiting book: what it waits for. Only a wait for an online source gets the new status; a wait for the library drive or for the catalog keeps `Waiting for source` (today all of them are one state with a kind inside).
- Per book that waits for an online source: what is being asked (title, series, or both); the number of the next try and the number of tries in all, such that `Try 2 of 3` is literally true; the time of the next try; and whether the tries go on by themselves (automatic processing running) or wait for Start.
- F2: the limit. I read `SERIES_WAIT_LIMIT = 3` for the series wait of 0.30.0. Whether the title uses the same number, and how the next try's time is set, are yours; the page prints what it is sent.
- How the wait ended, per field: answered, nothing found, no answer after the limit (with the number of tries), doubtful (which arrives as nothing found and with no fact to show).
- The Waiting item: the number of books that wait for an online answer (not the other waits), the earliest next try, the limit; with one book, its id and title.
- F8: if he types the missing names in `Edit names` while a book waits, does the wait end at once?

**Section 5, third round, for the record**
- Per waiting book: tries made, the limit, the next try time, what is being asked (title, series).
- How the wait ended, per field: answered, nothing found, no answer after the limit.
- The Waiting item's count, next try and limit; with one book, its id and title.

**Strings**
- Every label, step, sentence and tooltip above is final copy. The engine sends keys; the page words them (the 0.30.0 rule).

## Assumptions

- A1. Read-only look at code and docs; nothing launched, no rects measured.
- A2. Amended, third round (R18, R19): there is no page control for a finished audiobook's name or place. R6's re-check of already-sorted books is a studio job and has no page surface. **Amended, fourth round (R20): that job is replaced by the automatic pass inside the app (Scope), which shows as 3.3, 3.3a and 3.4.**
- A3. Settled (R14): a drive that is not answering holds back `All done`. A book on hold does too, as before.
- A10. Withdrawn, third round: it was about what R12 holds out of the approval list.
- A11. Settled, third round (R19): a book that is not moved because a later version would move it again holds nothing back, `All done` included. The same goes for every book with a series found while the guard is at hold. **Superseded, fourth round (R20): no book waits for a later version and the guard is automatic. What holds nothing back now is a book the rules could not rename or move (3.2).**
- A12. Amended, third round: an automatic move waits as a queued action of its own (the plan's note; not run). The grouping in 3.3 rests on it.
- A13 (third round). The quiet line counts the series look-up's own result, which the engine already has, and not the author-folder corrections the rules would make. Counting those too means computing the whole plan at every poll; if Ender has that number cheaply, the line can read `61 finished audiobooks would get a new name or folder. They stay where they are.` instead. Not built unless he says it is cheap. **Superseded, fourth round: the line counts books the rules could not rename or move, whatever the kind of change (3.2).**
- A14 (third round). "The automatic move is on" is one switch for the page: the engine either applies a found series by itself or it does not. If Sergei approves the certainty rule for some kinds of change first and others later, nothing on the page changes: each element shows from its own fact. **Superseded, fourth round (R20): there is no switch on the page. The move is automatic in 0.31.0.**
- A15 (fourth round). The automatic pass applies to a finished audiobook every change the rules have for it: a series found, a series name in English, an English title, an author folder in its new order. I read this from R19 and R20 ("every finished book moves once") and from the Scope's facts (92 finished books with an English title never applied, 63 in Latin author folders). It is not in the build I read. If the pass applies fewer kinds, the rename row of 3.3 and the `English title` reason of 3.4 are simply never sent.
- A16 (fourth round). After a Quit the rules queue the remaining renames and moves again by themselves. Read: the engine cancels a queued move at start and finishes one that was cut (`book_move.py`). Not read: that anything queues the rest again, because the automatic pass is not built yet. 3.3a's last sentence rests on it.
- A17 (fourth round). `Waiting for source` is one engine state for several waits: an online source, the library drive, the catalog (read in `automatic_processing.py`). Section 5 rewords the first only.
- A18 (fourth round). The row of a book that asks nothing shows `Title clue:` until the book is approved and `Canonical title:` after, and the list's search matches the title clue and the file paths (read in `web/app.js`). 4.5 adds nothing to either.
- A4. A paused queue with nothing pending still reads `Paused`.
- A5. Withdrawn, after the final build: the list's search does not match the proposed title, so a title search cannot be relied on to list both rows. The button lists the other book by its own folder or file name instead (4.2), which the search does match (Ender's report; not run by me).
- A6. The detail look-up records answers and renames no finished audiobook (`gap_fill.py` docstring; Scope: "92 finished books have a recorded English title never applied"). **Amended, fourth round: still true of the look-up itself. The renaming is the rules' own job (A15), so the tooltip says `This look-up changes no file.` and no longer `No audiobook is renamed.`**
- A7. Amended, third round: the guard holds every series write in 0.31.0 as it stands, and nothing waits for an approval any more (R18). The `Finding series…` tooltip has one sentence for each state (2.1). **Superseded, fourth round (R20): the guard is switched to automatic, and the tooltip has one sentence.**
- A9 (added after build). On a class Q row the engine refuses the approve press while `shared` is set, set-mates included (`_approve_once` checks every row; read in `merge_service.py`). The page's disabled press in 4.2a rests on that.
- A8. One theme (dark). A light theme, if added, uses the same tokens and needs its own ratios.

## Open questions (facts the docs and code did not settle)

- F1. Settled: a guard holds every series write into a finished file. Amended, third round: it is lifted by a switch, not by an approval, so the writing step shows only once the automatic move is on. **Closed, fourth round (R20): the guard is switched to automatic in 0.31.0. The writing step shows whenever a series is written.**
- F2. Settled (R9, R16): both look-ups, 3 tries per source, 6 hours apart; the copy prints the engine's numbers. Still open: how many tries before a waiting book converts (section 5, R2 says "a few"). **Fourth round: read in the build, a book waits for its series at most 3 times in a row (`SERIES_WAIT_LIMIT`). Still open, for Ender: whether the wait for an English title uses the same number, and how `Try N of M` is counted so that it is literally true. The page prints what it is sent.**
- F3. Does the Electron shell take its window title from the page? R13 makes the title part of 0.31.0, so this needs Ender's answer before 1.5 is built. (`desktop/main.js` gives the window the title `Books Arranger` and the page has the same `<title>`; I did not run it.)
- F5. Closed, third round: it was asked for the withdrawn dialog's body text. The record's help line says only `The audio is never changed.`, which holds either way.
- F6 (third round). What "found for certain" and "would move again in the next version" mean in the engine are Ender's to propose and Sergei's to approve (Scope, third round). The page needs neither rule, only their results: a book is being changed, is in the quiet line's number, or is neither. **Closed, fourth round: R21 and R22 say what is doubtful, and no book waits for a later version (R20).**
- F7 (third round). Can a queued automatic move be cancelled from the book's row, and what happens next? (Notes for Ender, Section 3.) **Fourth round: decided for the page (3.3: no `Cancel` on the app's own move; Question 16). Still Ender's to confirm: a cancelled rule-made move would be queued again, and a folder he chooses after the move is kept.**
- F4. Whether the series look-up of finished books keeps running after R6's job (Scope: not ruled). If it stops, section 2's series row and item simply never appear. **Fourth round: R6's job is replaced by the automatic pass inside the app; the question, as the Scope words it, is still not ruled.**
- F8 (fourth round). If he types the missing names in `Edit names` while a book waits for an online answer, does the wait end at once? (5.2)
- F9 (fourth round). Under which title a book shaped "Series N. Title" is filed once its doubtful series is dropped: the whole text, or the title part. (4.4)
- F10 (fourth round). How a rename of a finished audiobook for an English title, an author's name or a series name runs: as a job of its own, inside the series row's writing step, or inside the move. (3.3)
- F11 (fourth round). What a translated book's series is named when no English name for the series is found. R3 rules the title only. (4.5)
- F12 (fourth round). Once the reason a book could not be renamed or moved is gone, do the rules file it by themselves at the next pass? (3.2)
- F13 (fourth round). Does Pause audiobook jobs hold the app's own renames and moves? 3.3a is worded to be true either way (the notice stays, the Waiting items say what they wait for).

## Questions for Sergei: answered (2026-11-22)

Questions 1 to 12 are closed. The answers, as ruled in the Scope's second round, for 1, 2, 3, 10 and 11 its third, and for 12 its fourth:

1. The approval list: series only, or all? **All** (R10). **Then withdrawn by R18 in the third round: there is no approval list.**
2. `Leave as it is`: the book or the series? **The book** (R11). **Then withdrawn by R18: there is no refusal.**
3. Books written in Chinese or Japanese: hold or let them move now? **Hold** (R12). **Generalised by R19: any book the next version would move again is not moved now. Fourth round (R20): English names ship in 0.31.0, so none is held.**
4. A count and Try again for look-ups that gave up? **No.**
5. A `Convert now` button on a book waiting for the online answer? **No.** (Fourth round: the wait itself ships in 0.31.0; the answer stands.)
6. The state in the window title? **Yes** (R13).
7. Does a drive that is not answering hold back `All done`? **Yes** (R14).
8. The same limit for the titles-and-author-names look-up? **Yes: 3 tries per source** (R16).
9. May the blocked press say `Join them into one book, or change this title.`? **Yes, only on a blocked press** (R17).

10. Refuse the series alone on a book with two kinds of change? **Closed by R18 (third round): there is no refusal at all.**
11. Does a book held for English series names hold back `All done`? **Closed by R19 (third round): "Don't move now if the next version will move it." It is simply not moved, and it holds nothing back. Fourth round (R20): no book is held for them any more.**
12. Should a book that is not converted yet stop asking about a doubtful series, in three places (`Number unclear`; `Title unclear` for a title that looks like a series name and number; `Sources disagree — which is correct?` about a series)? **Yes, and in this version** (R22). Specced in 4.4.

## Questions for Sergei: open (one word each)

**Amended 2026-11-22, fourth round (R20–R22).** Four open points. Each says what is built until he answers.

13. **An author's name the app cannot put in order.** A Latin name of two words where the app cannot tell which is the surname. Say nothing and file it as the source wrote it, or ask on the row? I recommend **say nothing**: it is the rule he gave for a doubtful series, and a name filed the wrong way round is corrected once in `Edit names`. If he prefers the question, it is one more `Author unclear` cause with the sentence `The app can't tell which word is the surname.` (4.5). Until he answers: no question and no words; the row shows the author as the engine files it. nothing / ask
14. **The books the app could not rename or move.** The jobs panel says how many (`12 finished audiobooks could not be renamed or moved. They stay where they are.`). Should it also list them, read-only, each with its reason (`A file with that name is already there.`), under the record of what was moved? I recommend **yes**: a count he cannot open tells him there is something and not what. Nothing in the list asks him or acts on a file. Until he answers: the count line only (3.2); the list is specced and not built (3.4a). yes / no
15. **Other stops that are about a doubtful series.** R22 named three questions. Reading the build, two more stops are of the same kind: a book held with `Series and standalone evidence conflicts` (one source lists it in a series, another calls it a standalone book), and `Series membership has conflicting author credits. Confirm this book in Edit names.` Same rule for them: no series, the book goes on, nothing is said? I recommend **yes**: it is the same doubt, and each can hold a book back. Until he answers: they stay exactly as built. yes / no
16. **No Cancel on a move the app queued by its rules.** Today a queued move has `Cancel` on the book's row. For a move the app queued itself, `Cancel` would not last: the rules would queue the move again. So the spec shows no `Cancel` there, and `Choose folder…` works again once the book has moved; a folder he chooses then is kept. OK? I recommend **yes**. Until he answers: built as described (3.3). yes / no

**Offered, not built** (no answer needed; say the word if wanted):
- A `Put back` on an entry of the record (3.4), to undo one automatic rename or move. Today the way to correct one is `Choose folder…` on the book's row.
- Fourth round: the second read-only list that was offered here is Question 14 now.
