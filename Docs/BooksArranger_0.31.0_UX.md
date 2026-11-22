# Books Arranger 0.31.0: UX spec (honest status)

Judy, 2026-11-22. For Ender. Source: `BooksArranger_0.31.0_Scope.md` (`d134484`; second round `d28f9ff`; third round `4a6c3a8`): Sergei's report, rulings R1 to R7 and, since the amendments of the same day, R8 to R19, step 4 ("Honest status") and the part of step 1 that shows on the page. Sergei, 2026-11-22: "How do I know that the app finished its queue and have nothing to do anymore? ... But what is 'Updating Metadata'? Is it re-researching old books? Or is it still a first pass?"

**This is an EXTEND of `BooksArranger_0.30.0_UX.md`.** The jobs panel, the Waiting list, the freshness cue, the blocker sentence and every string not named here stay as built. Where this spec replaces a 0.30.0 line it says so.

Basis: read-only look at `web/app.js` (`jobsFirstPart`, `renderWaitingForYou`, `WORK_LABELS`, `workStep`, `waitingLines`, `renderAutomatic`, `holdSentence`, `HOLD_APPROVE`, `destPlan`, `placeText`, `scopeBasisText`), `web/index.html`, `web/style.css`, `background_work.py`, `series_backfill.py`, `gap_fill.py`, `sorting_moves.py`, `merge_service.py` (`sorting_moves`, `sorting_moves_apply`), `web_server.py` (`needs_you_only`, the two sorting routes). Nothing was launched and no rect was measured (Sergei's copy was converting). The app has one theme, dark (`color-scheme: dark`, no light tokens), so contrast is checked against the dark tokens only.

## Amended 2026-11-22 after build

Ender built sections 1 and 2 (branch `ender/0.31.0`) and hit nine gaps. Each is ruled here and written into its section, marked **Amended 2026-11-22 after build**. Read for this round, read-only: his `web/app.js` (`statusParts`, `jobsFirstPart`, `notReadable`, `badgeState`, `renderWaitingForYou`, `waitingLines`), `destination_clash.py`, and `merge_service.py` (`ask_payload`, `approval_preview`, `series_origin`, the two `same_name` refusals). Nothing launched, no rect measured.

Engine facts settled since the first version: 3 tries per source, 6 hours apart (since approved, R9); the detail look-up has no tries limit (since given the same one, R16); a guard holds every series write into a finished file until he approves it; a book already waiting to convert keeps its name and only the newcomer row is held.

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
| 3 | Books written in Chinese or Japanese are held out of the list | R12 | **generalised by R19: such a book is simply not moved yet** (3.2) |
| 4 | No count or Try again for look-ups that gave up | as recommended | 2.3 |
| 5 | No `Convert now` button | as recommended | 5 |
| 6 | The window title shows the state | R13 | 1.5: a title for every state |
| 7 | A drive that is not answering holds back `All done` | R14 | 1.1, as already specced |
| 8 | The look-up for titles and author names gets the same limit | R16 | 2.2: one tooltip for both look-ups |
| 9 | The blocked press may say `Join them into one book, or change this title.` | R17 | 4.2a |
| also | Nothing is written into a finished book without approval | R8 | **its "without approval" half replaced by R18**; the guard stays at hold for now (3.2) |
| also | Tries: 3 per source, 6 hours apart, approved as built | R9 | 2.2 |
| also | A title tag shaped "Series NN - Title" is filed without asking | R15 | 4.3 |

Questions 10 and 11, opened by this round, were closed by the third round.

## Amended 2026-11-22, third round (R18, R19)

Sergei dropped the approval list. The rulings are R18 and R19 in `BooksArranger_0.31.0_Scope.md` ("Third round", `4a6c3a8`), which is the authority. Every change they cause is marked **Amended 2026-11-22, third round (R18, R19)**. Where this round and an earlier one disagree, this round wins.

- **R18.** Finished audiobooks are renamed and moved by the rules, with no approval step, when author and series are found. A result that could be wrong is treated as if nothing was found: no question, no move. Sergei: "Why would you ask me in such a case? If the author and series are found, then put it in the folder according to our rules."
- **R19.** A book is not moved now if the next version will move it again. Such books wait and move once.

**Two states, one page.** In 0.31.0 as it stands the write guard is at hold: no finished audiobook is written, renamed or moved by itself. The automatic move is switched on only after Sergei approves Ender's certainty rule and the "stable under the next version" rule, in 0.31.0 or in the next version. The page is the same in both states and never asks which one it is in: every element of section 3 shows from a fact the engine sends, and stays away when that fact is absent.

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
| Row questions that ask about a series today | **Not changed.** One open point for Sergei (Question 12) | end |

**What Ender changes on the page already built** (branch `ender/0.31.0`, read at `e1af686` plus his working changes):
1. Take out the status part `N series changes to approve` (`statusParts`).
2. Take out Waiting-for-you line 2 (`#jobs-you-moves`). The block shows for books that need attention only (1.4).
3. Engine: a series found and not applied is no longer a reason something waits for him (`moves` leaves the waits-for-you reasons and the state; the count stays, for the quiet line of 3.2).
4. Reword the series row's step tooltip: two sentences, by state, neither about approval (2.1).
5. Add the quiet line (3.2). New, small, and the only new thing 0.31.0 needs while the guard is at hold.
6. For when the automatic move is on: a series write counts as main work, not as a look-up (1.1); the two grouped Waiting items (2.2, 3.3); the record (3.4).

The series row keeps its one label in both steps, as built.

Nothing of the old section 3 was built, so nothing of it has to be removed.

## Amended 2026-11-22, after the final build

Ender finished the 0.31.0 page (`ender/0.31.0`, `89f1f2a`) and reported six gaps. Each is ruled here and written into its section, marked **Amended 2026-11-22, after the final build**. Read for this round, read-only: his `web/app.js` (`sameNameSentence`, `sharedOf`, `buildShowBoth`, `showSameName`, `buildAskActions`, `seriesOriginText`) and `merge_service.series_origin`, `local_identity.py` at the brackets rule. Nothing launched, no rect measured.

| Gap | Ruling | Code | Where |
|---|---|---|---|
| 1. A same-name row whose clash has ended | Not confirmed. The sentence follows the row's latest answer, not the recorded hold: `The name is free now. Approve files the book under it.`, or the Name taken sentence when a file is now on disk. | yes, small: one function | 4.1 |
| 2. `Show both books` and the list's search | Change what the button does, with what exists: it lists **the other book**, by the folder or file name the engine already sends. New face `Show the other book`. Showing both at once needs a list filter by book ids, which is more than a small change: next version. | yes, small: face, tooltip, search text | 4.2, 4.2a |
| 3. "Last button of the row" | Confirmed as built: after the row's ordinary buttons, before the break; `Delete book` and `Remove this copy` keep their own last line. | no | 4.2a |
| 4. The reason line on Missing files rows | Confirmed as built: it shows for `Convert what's there`, the press that is blocked. `Scan again` stays enabled. | no | 4.2a |
| 5. A series read from brackets | Not accepted: `from the file's tags` is untrue when the brackets were in the folder's name. Its own origin, with words true for all three places: ` · from the brackets in its name`. | yes, small: one origin in the engine, one string on the page | 4.3 |
| 6. `1 other book would get this file name.` | Keep. It is the right singular for a book the engine cannot name. | no | 4.1, 6.1 |

For the record, no objection to any of the three:
- The same-name presentation is tested with the engine's own fact, `ask.hold.kind`. That is the test 4.1 asked for; the interim test is withdrawn.
- The origins `title_tag` (` · from the title tag`) and `file_name` (` · from the file name`) are built, as 4.3 words them.
- A series found and not applied counts as done in the look-up's bar. That is 2.1's "settled": the look-up has finished with that book.

## Decisions in brief

- **Three finished states, one badge.** When no job runs, waits or is queued, the status line starts with a badge: `All done`, `Waiting for you` or `Background look-ups only`. The badge is there only when the queue is finished, so its presence alone answers Sergei's question; its words say which of the three.
- **The engine decides the state.** The page never works it out from rows (the 0.29.0 rule for `needs_you_only`, kept).
- **Bare `Nothing running` goes from the status line.** It read as "done" while work waited. With work waiting it says `Continues by itself`.
- **Two background look-ups get plain names** that say which books they are for and whether a file changes. Their bar counts the whole look-up, not one pass, so `691 of 903 books` answers "how much is left".
- **A look-up between tries is a Waiting item**, grouped, with the next try time.
- **Nothing about a finished book's name or place is asked of him** (amended, third round, R18 and R19: the approval dialog of the earlier rounds is withdrawn). The app renames and moves a finished audiobook by its rules when author and series are found for certain, and leaves it alone otherwise. He sees it happen as ordinary rows, reads afterwards what moved where in a record, and is told in one quiet line how many books have a series found that is not applied.
- **A book held only because another book has its name** reads `Same name as another book` and is offered a name change. A row with a question of its own keeps that question and its buttons (amended, G9).
- **Section 5 is the next version.** It is specced here so the words match; nothing in it is built in 0.31.0.

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
- **Amended 2026-11-22, third round (R18, R19): finished books and the states.**
  - A finished audiobook with a series found that the app has not applied (the guard is at hold, or R19 keeps the book for later) is not main work, is not a background look-up and does not wait for him. **It does not hold back `All done`** and is part of no state. It shows in one quiet line only (3.2). This is the answer he gave to the old Question 11's premise.
  - Once the automatic move is on, a book the app is about to change is work like any other: writing a series into a finished file and moving a finished book are **main work**, because they change his files. Only the asking online is a background look-up. So `Background look-ups only` never shows while a write or a move of a finished book runs or waits, and `All done` waits for them.
  - A doubtful result is the same as no result (3.5): it leaves nothing pending.

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

**Amended 2026-11-22, third round (R18, R19).** The status part for renames and moves to approve (`N series moves to approve`, then `N series changes…`, then `N renames and moves…`) is removed and has no replacement. There is one new part in this version, `212 background look-ups left`. Books with a series found that is not applied are not a status part (3.2).

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

## 2. Plain names for the background look-ups

Each row answers four things in a fixed place: what it is and whose books (the label), how much is left (the detail), what it does this second and whether a file changes (the step).

### 2.1 Running rows

Replaces the `series` and `gap_fill` lines of 0.30.0 table 1.5. Row anatomy is unchanged (label and subject, detail, bar, step, elapsed).

| Kind, step | Label: subject | Step line | Detail and bar |
|---|---|---|---|
| `series`, looking up | `Finding series for finished audiobooks: <book>` (was `Metadata: Updating series`) | `Asking online sources. No file is changed.` | `691 of 903 books`, determinate |
| `series`, writing (only when the automatic move is on; amended, third round) | the same label | `Writing the series into the file and renaming it. Audio unchanged.` | the same |
| `gap_fill` | `Finding original titles and author names: <book>` (was `Looking up book details`) | `For books you already approved. Recorded only, no file is changed.` | `40 of 71 books`, determinate |

- **The count is the whole look-up:** done = books settled (a series found, none found, or given up), total = every book that needed the look-up. It only grows and ends at the total. It is never the count of one pass, which starts again every ten minutes and reads as no progress.
- **No time estimate** on these two rows. Their pace is set by how often the sources may be asked; a guess would be wrong. The elapsed time stays.
- **Step tooltip** (the step line's `title`, as the chapter check uses it):
  - `series`: **amended 2026-11-22, third round (R18, R19).** The sentence about approval is withdrawn: he approves nothing. Two sentences now, chosen by one engine fact (does the app apply a found series by itself: no while the guard is at hold, yes once the automatic move is on):
    - guard at hold: `Finished audiobooks without a series are looked up online, one by one. A series that is found is recorded. No audiobook is renamed or moved.`
    - automatic move on: `Finished audiobooks without a series are looked up online, one by one. When author and series are found for certain, the book is filed under them. Otherwise it stays as it is.`
    - The writing step shows only in the second state.
  - `gap_fill`: `Books approved without an original title or a full author name are looked up online, one by one. The answers are recorded. No audiobook is renamed.`
- The step and the label are one line each with an ellipsis (the 0.30.0 row); at widths where the step is cut, its `title` holds the full sentence.
- These rows count in `tasks running` only beside main work. Alone, the badge leads the status line and the row shows below it. **Amended, third round:** this holds for the series row while it looks up. In its writing step the row is main work (1.1): the status line names it, `Finding series for finished audiobooks: Dune`, and no badge shows.
- **Amended 2026-11-22 after build (G7).** That rule is for the first parts that already say the app is not busy: a badge, `Continues by itself`, `Checking what is left`. It is not for `Paused`. A paused queue with a look-up still running reads as 0.30.0 reads any work Pause does not stop: `Paused · Finding series for finished audiobooks: Dune` (two or more: `Paused · 2 tasks running`). Without the name, a bar moves under a line that says only `Paused`, and nothing explains it.
- `Researching books` (books not converted yet), `Looking up metadata` (a Find metadata press) and `Re-checking finished audiobooks` (a file check, nothing online) keep their names. Read beside the two labels above, they no longer look like the same job.

### 2.2 Between tries: the Waiting list

A look-up that waits for its next try showed nowhere. It is a Waiting item, one per look-up, grouped (the cleanups precedent). Engine order: after `metadata_sources`, before `drive`.

| What waits | Line 1 | Line 2 | Button |
|---|---|---|---|
| series look-ups between tries | `Finding series for finished audiobooks: 212 books` | `Waiting for online sources. Next try 14:05. No file is changed.` | none |
| detail look-ups between tries | `Finding original titles and author names: 31 books` | `Waiting for online sources. Next try 14:05. No file is changed.` | none |
| a series the app is about to write, held by a job (automatic move on) | `Write series into audiobook: <book>` | the 0.30.0 blocker sentence: `It runs when Converting: Dune finishes.` (a cleanup or a scan the same way) | Show in list |
| more than 5 of those (amended, third round) | `Writing series into finished audiobooks: 290 books` | `Next: <book>.` then that book's blocker sentence, or `They run one at a time.` | Show in list, for that book |

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

### 3.1 Withdrawn: the approval control

Sergei, on being asked to approve moves: "Why would you ask me in such a case? If the author and series are found, then put it in the folder according to our rules." (R18). So nothing here asks him, lists books for his decision or lets him refuse one.

**Not built, in either state:**
- the dialog `Rename or move N finished audiobooks?`, its groups (`Series found`, `Author folder`, `Series name`), `Select all` and `Select these N`, its per-book lines with `Moves to` and `Renamed to`, and the button `Rename or move N books`;
- the list shortcut `Renames and moves · N` and the button `Review changes`;
- `Leave as it is`, `Offer again`, the list `Left as they are` and its reason sentences, the R12 sentence among them;
- the result lines, the changed-list warning and every loading and sending state of the dialog;
- the status part and the Waiting-for-you line about renames and moves to approve (1.3, 1.4).

Their singulars (6.1), control rows (7), layout states (8), acceptance checks (9) and engine notes are withdrawn with them. The full text is in git at `9a10b46` and is not to be used.

### 3.2 A series found and not applied

A finished audiobook for which the look-up found a series the app can rely on, and into which the app has not written it. Two causes, one presentation:

| State | Which books |
|---|---|
| guard at hold (0.31.0 as it stands) | every finished audiobook with a series found: nothing is written, renamed or moved by itself yet |
| automatic move on | only the books R19 keeps back: their name or folder would change again later, so they are not moved now |

Such a book waits for the app's rules, not for him and not for a job. So:

- **It holds nothing back.** No status part, no row, no Waiting item, no line under Waiting for you, no effect on the badge or the window title. `All done` shows with any number of them (1.1).
- **It is said once, quietly.** One line at the bottom of the Audiobook jobs panel, directly above the two help lines, in their look (`field-help`: 13 px, `--muted`). Not `aria-live`, no button, no tooltip.

  `Series found for 61 finished audiobooks. They are recorded and stay where they are.`

  One book: `Series found for 1 finished audiobook. It is recorded and stays where it is.` Hidden at zero, and when the engine sends no number.
- **Why it is shown at all.** In 0.31.0 the look-up runs through 903 books and changes none. Without this line its whole result is invisible, and a book he knows belongs to a series looks as if the look-up had failed on it.
- **Why these words.** They are true in both states and promise nothing: no "yet", no version, no reason he would have to trust. `recorded` says what the look-up produced; `stay where they are` answers why a book is not in its series folder.
- **Why no more.** Not a list of the books and not a control: a list invites a decision, and he has said he does not want one. Nothing is added to the books' own rows.
- The number is books. It leaves out a book the app is writing or moving at that moment (that is work, 3.3) and a book whose result was doubtful (3.5).
- Author-folder corrections the rules would make have no line. The number is the series look-up's own result, which the engine already counts.
- Until Ender's certainty rule exists, the number is every series the look-up found. Once it does, a doubtful one drops out of it (3.5), so the number may fall without anything having moved. That is correct and is not explained on the page.
- The line and the record of 3.4 are not part of the `All done` invariant of 1.1. Both may show under `All done`: neither is pending work.

### 3.3 While the app renames or moves a finished book

Only when the automatic move is on. Nothing asks and nothing announces it: it reads as ordinary work in the jobs panel, in the rows and items that already exist.

| Moment | Where | Words |
|---|---|---|
| the series is being written into the file | Running row | `Finding series for finished audiobooks: <book>`, step `Writing the series into the file and renaming it. Audio unchanged.` (2.1) |
| the book is moving to another folder | Running row, the 0.30.0 move | `Moving: <book>`, step `Copying to <folder>` |
| a write waits for a job | Waiting item | `Write series into audiobook: <book>` and the blocker sentence (2.2) |
| a move waits its turn | Waiting item, the 0.30.0 queued action | as 0.30.0 |
| more than 5 writes wait | one grouped Waiting item | `Writing series into finished audiobooks: 290 books` / `Next: Оно. It runs when Converting: Dune finishes.` |
| more than 5 moves wait | one grouped Waiting item | `Moving finished audiobooks: 338 books` / `Next: Оно. It runs when Converting: Dune finishes.` |

- **The groups.** The day the automatic move is switched on, every book held until then is released at once: hundreds. The 0.30.0 Waiting list draws one item per waiting write and per queued move, which would be a wall. So the cleanups' cap applies to both: with 5 or fewer, each is its own item as today; with more, one grouped item replaces them. Line 2 is `Next: <book>.` followed by that book's blocker sentence when something blocks it, else `Next: <book>. They run one at a time.` The button is Show in list, for that book. The status part `338 actions waiting` is unchanged.
- **State.** A write or a move of a finished book is main work (1.1): the first part names it or reads `Continues by itself`, the window title reads `working` or `continues by itself`, and `All done` comes only after the last one.
- **The book's own row** in the list reads as 0.30.0 reads any move: `Moves to`, `Moving to`, then `Now in`. Nothing is added.
- No toast, no sound, no focus change, no confirmation of any kind, before or after.
- Whether a queued automatic move can be cancelled from the book's row, and what then keeps the rules from queueing it again, is the engine's rule. The page adds no control for it.

### 3.4 Afterwards: what was renamed or moved

He no longer sees a move before it happens, so he must be able to read afterwards what moved where. A plain, read-only record, from what the engine already keeps for every move (from where, to where, when).

**Where.** A `<details>` at the bottom of the Audiobook jobs panel, after the Waiting-for-you block and above the quiet line of 3.2, built like `Author rules learned online` in the scan panel. Closed by default. Hidden while the app has never renamed or moved a finished audiobook by its rules, so it does not exist on screen while the guard is at hold.

**Summary.** `Renamed or moved by the app · 340 · last 22 Nov, 14:05`. One: `Renamed or moved by the app · 1 · 22 Nov, 14:05`. Tooltip: `Finished audiobooks the app renamed or moved by its rules, newest first.` Dates are in the form the page already prints dates.

**Inside,** top to bottom:
1. One help line (`field-help`): `The app files a finished audiobook under its author and series when both are found for certain. The audio is never changed.`
2. `Find book`, a search field (the look and behaviour of `Find author` in Author rules). Tooltip: `Show only entries whose title, author or path contains this text.`
3. The list, newest first, scrolling inside (`max-height: 40vh`), `role="group"`, `aria-label="Books renamed or moved by the app"`, `tabindex="0"`.

**An entry.** Three lines and one button.

```
Граф Ноль · Gibson William · 22 Nov, 14:05 · Series: Sprawl Trilogy · No. 2 · found on FantLab     [ Show in list ]
  Was in   Gibson William\Граф Ноль - Gibson William.m4b
  Now in   Gibson William\Sprawl Trilogy\2 - Граф Ноль - Gibson William.m4b
```

1. `Title · Author · date`, then one part per reason the rules had, ` · ` between: `Series: <name> · No. <n> · found on <source>` (the source names of 4.3), `Author folder: <the new folder's name>`, `Series name: <the new name>`. Title in weight 600. The author is the one it is filed under now.
2. `Was in` and the path before the app touched the book, under Audiobooks Sorted (the full path is the `title`).
3. `Now in` and the path after. The leading folders it shares with line 2 are `--muted`; what is new is `--text`. A book only renamed in its folder uses the same two labels; the file name shows the change.
- **Show in list** (quiet, 96 x 32 minimum): the existing button, tooltip `List this book: sets Status to All and searches for its title.`
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

- The summary's count and date come with the normal state, so they are right while the record is closed. The entries are fetched when it is opened, and again each time the count changes while it is open; the scroll position holds.
- **If a move was wrong:** the book's own row has `Choose folder…`, as for any finished audiobook. No undo is added here (offered at the end).

### 3.5 A doubtful result

R18: a result that could be wrong is treated as if nothing was found. On the page that means **the book says nothing, anywhere**:

- no status word, no hint, no chip, no count, no line on its row, in its details panel, in the jobs panel or in the record;
- it reads exactly as a finished audiobook for which no series was found, and the look-up counts it as settled (`691 of 903 books`);
- it is not in the quiet line's number (3.2), which counts only series the app can rely on.

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

- **Amended 2026-11-22 after build.** The suffix, by the origin the engine sends: `tags`: ` · from the file's tags`; `folders`: ` · from the folder names`; `entered`: ` · entered by you`; `source`: ` · found on Wikidata` (source names: `FantLab`, `Goodreads`, `Wikidata`, `Litres`, `the publisher's site`; a source with no name: ` · found online`; the same names are used in the record of 3.4); `unknown`: no suffix. `folders` and `unknown` had no words. `source` shows whenever the engine says so, not only from the next version.
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

## 5. Waiting for the online answer (next version, not built in 0.31.0)

R2: a book may wait a few tries for the online answer before it converts; then it converts as before. Specced now so the words match sections 1 and 2.

| Place | Words |
|---|---|
| Row status | `Waiting for an online answer` (replaces `Waiting for source`) |
| Row hint | `Asking online for its English title and series: try 2 of 3, next at 14:05. Nothing to do.` The asked part follows the book: `its English title`, `its series`, `its English title and series`. |
| Jobs panel, Waiting item, several books | `Waiting for an online answer: 3 books` / `Next try 14:05. After 3 tries a book converts with the names from its files.` No button. |
| Jobs panel, one book | `Waiting for an online answer: Тёмный лес` / the same line 2 / Show in list |
| Jobs panel, while it asks | the 0.30.0 row `Researching books: <book>`, unchanged |
| Automatic block detail (`Waiting for metadata sources; …`) | `Waiting for an online answer. Next try 14:05.` |
| Tries ran out, it converts anyway: row note under the status, while Queued or Processing | `No online answer after 3 tries. Named from its files.` |
| The same, details panel | `Original title: No online answer after 3 tries. Filed under the Russian title.` and `Series: No online answer after 3 tries.` |
| An answer came and found nothing (R3) | `No English title found online. Filed under the Russian title.` (the existing `Not found.` fact). No note for a missing series. |

- This is main work: while a book waits, the state is `Continues by itself`, never a badge.
- The Waiting item replaces 0.30.0's `Metadata sources` item (`3 books wait for a source to answer. Next try 14:05.`).
- "No answer" (the sources did not reply) and "nothing found" (they replied) are different sentences and are never merged.
- The numbers (`3`) are the engine's.
- No new control. No `Convert now` button on a waiting book (Sergei's answers, Question 5: as recommended).

## 6. Other places this touches

- **Automatic block**, `Automatic pass complete — 12 converted · 3 held` (`app.js` 2913 to 2916): it speaks of one pass and read as "all done". It gains a suffix from the state: main work left: ` Other jobs are still running or waiting.`; only look-ups left: ` Background look-ups continue.`; otherwise nothing.
- **Busy notice** (`Busy with: …`): uses the row labels, so it takes the two new names.
- **`needs_you_only`**: the page stops reading it; the finished state replaces it.
- **0.30.0 spec**: mark as superseded: table 1.5 rows `series` and `gap_fill`; section 4 "First part when only cleanups wait"; and, when section 5 ships, table 1.6 row `metadata_sources`.
- **Unchanged:** Pause and Resume, the freshness cue, the unread line, On hold, every other row and Waiting item, the review table's columns, the chips other than Name taken's tooltip, themes and colours.

### 6.1 Singular forms

**Amended 2026-11-22 after build (G3); amended 2026-11-22, third round (R18, R19): every row about the approval list is removed with the list, and the rows of section 3 as it now stands are added.** Every count this spec prints, one and many.

| Place | One | Many |
|---|---|---|
| status part | `1 background look-up left` | `212 background look-ups left` |
| Waiting-for-you | `1 book needs attention.` | `329 books need attention.` |
| look-up Waiting items, line 1 | `…: 1 book` | `…: 212 books` |
| look-up rows, detail | `1 of 1 book` | `691 of 903 books` |
| tries tooltip (2.2) | `Each source is asked once for a book.` | `…asked up to 3 times for a book` |
| tries tooltip, the gap | `, 1 hour apart` | `, 6 hours apart` |
| the quiet line (3.2) | `Series found for 1 finished audiobook. It is recorded and stays where it is.` | `Series found for 61 finished audiobooks. They are recorded and stay where they are.` |
| grouped writes waiting (3.3), line 1 | never one: it groups above 5 | `Writing series into finished audiobooks: 290 books` |
| grouped moves waiting (3.3), line 1 | never one: it groups above 5 | `Moving finished audiobooks: 338 books` |
| the record's summary (3.4) | `Renamed or moved by the app · 1 · 22 Nov, 14:05` | `Renamed or moved by the app · 340 · last 22 Nov, 14:05` |
| the record, more than 200 | never one | `Showing the newest 200 of 1,240. Find book searches all of them.` |
| same name, destination label | `Both go to` (this book and one other) | `All 3 go to` |
| same name, sentence | one other book: it is named (4.1). One the engine cannot name: `1 other book would get this file name.` (kept, after the final build, gap 6) | `2 other books would get this file name.` |
| same name, button (amended after the final build, gap 2) | one other book: `Show the other book` | several: `Show one of the others` |
| section 5 (next version) | `After 1 try a book converts…`, `No online answer after 1 try.` | `After 3 tries…`, `…after 3 tries.` |

Not in this spec's list of changes, noted only: the 0.30.0 status part `N need attention` prints `1 need attention` for one book. `1 needs attention` would be right.

## 7. Controls: tooltip, disabled state, keyboard

| Control | Tooltip | Disabled when, and what it says | Keyboard |
|---|---|---|---|
| the record's summary, `Renamed or moved by the app · N` (3.4) | `Finished audiobooks the app renamed or moved by its rules, newest first.` | never disabled; hidden while the record is empty | in the jobs panel's tab order after the Waiting-for-you block; Enter or Space opens and closes |
| `Find book` (3.4) | `Show only entries whose title, author or path contains this text.` | never | typing filters at once; Escape clears the field (and does nothing else) |
| the record's list (3.4) | none: a scrolling region, `aria-label="Books renamed or moved by the app"` | never | one tab stop; arrow keys and Page Up, Page Down scroll it |
| **Show in list**, on a record entry (3.4) | `List this book: sets Status to All and searches for its title.` | never | follows its entry in tab order; Enter or Space |
| **Show in list**, on a grouped Waiting item (3.3) | the same | never | as on any Waiting item |
| **Show the other book** / `Show one of the others` (was `Show both books`; amended after the final build) | 4.2: `List the other book: sets Status to All and searches for its folder or file name.` | never disabled; not shown when the name is free, when a file with it is on disk, or when the engine sends no name for the other book | class S: in the row's action order after Approve. Class Q (4.2a): last of the row's ordinary buttons, before `Delete book`'s own line |

- **Amended 2026-11-22, third round (R18, R19).** Every row of the withdrawn dialog is removed: the shortcut, `Review changes`, `Select all`, the groups, the books' checkboxes, `Left as they are`, `Leave as it is`, `Offer again`, `Cancel`, `Rename or move N books`. The record of 3.4 is the only new thing with controls, and none of them changes anything: it has no button that acts on a book's files.
- The quiet line of 3.2 is not a control and has no tooltip.
- Opening the record, typing in `Find book` and a refresh of its entries never move focus and never reset the scroll position.
- Hover-only texts on things that are not controls: the badge (1.2), the two step lines (2.1), line 2 of the grouped look-up items (2.2), the source name on a record entry (its address). None carries anything that is not also on screen in short form.
- Every `aria-disabled` button keeps its focus stop and says why in its tooltip (the app's existing pattern).

## 8. Layout, overlap and contrast

**Narrow layouts.** No string differs by width.
- Review table: every new row text is in the status cell or the destination cell, which the medium (600 to 799) and compact (under 600) bands never hide. Nothing new goes into columns 3 and 4, which they fold.
- Jobs panel under 560 px: rows stack as built; labels and steps keep their one-line ellipsis and full `title`. The status line wraps; the badge stays whole on the first line.
- The record (3.4) under 600 px: the label (`Was in`, `Now in`) sits above its path; paths wrap anywhere; an entry's Show in list drops to its own line under the paths, left-aligned.

**No element covers another.** By construction, not by measurement: everything new is in normal flow (no absolute, fixed or sticky positioning), so it can only wrap or push. **Amended, third round:** with the dialog withdrawn, this spec adds no overlay at all. States walked through on paper: each of the eight first parts of 1.1 (with `Checking what is left`, amended) with 0, 1, 2 and 5 rows; `Paused` beside a running look-up row; the badge with and without the as-of suffix; the Waiting-for-you block with its one line; the freshness cue and the unread line shown; the quiet line of 3.2 shown and hidden, alone and under an open record; the record closed, open with 1, 200 and 1,240 entries, loading, failed, with `Find book` matching nothing, with long Cyrillic paths, at each width; the Waiting list with 5 and with 338 queued moves and 290 waiting writes (3.3); the same-name row (class S) in the wide, medium and compact bands with Edit names open; a class Q row with its own buttons plus Show the other book, before `Delete book`'s line, in the same three bands; the Place line with a long series name and each origin suffix. Futaba measures the rects (check 12).

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

Nothing new relies on colour alone: each state, warning and disabled reason is also words.

## 9. Acceptance checks (Futaba)

1. **All done is true.** Force every other state in turn (a conversion, a queued action, a timed cleanup retry, automatic processing between tries, a series look-up between tries, a detail look-up running, one book needing attention, a drive not answering (R14), and, with the automatic move on, one series write waiting and one move of a finished book queued): the badge never reads `All done`. Positive control: with all of them cleared it does, within 3 s, and the four lists are empty. (Amended, third round: a rename or move waiting for his approval is no longer a state; check 26 covers the books that are not moved.)
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
12. **Layout, measured rects.** At 1280, 960, 760, 600 px and 200% zoom, long Cyrillic names: the toolbar rect is identical with and without the badge; no rect of the badge, the block line, the quiet line, the record's summary, its entries and their buttons, or row buttons intersects another; an open record with 200 entries scrolls inside itself and pushes the help lines down without covering them. (Amended, third round: the dialog's rects are gone with it.)
13. **Keyboard.** The record (3.4) can be opened, searched, scrolled and left without the mouse, and Show in list on an entry works from the keyboard. (Amended, third round: was the dialog.)
14. **R4 row.** A volume with its own title tag and a series in its tags shows its own title and `· from the file's tags`, and carries no question.

Added 2026-11-22 after build:

15. **Own question kept (class Q, G9).** Pieces of one book that all carry the set's name, each a `Part of a bigger book` row with `shared` set: every row still reads `Part of a bigger book` with its own sentence, still has `Approve as one book` (disabled, with R17's reason line `Another book would get this name. Join them into one book, or change this title.`) and `Keep as separate books` (enabled), its label reads `All N go to`, and it has the show button of 4.2 (`Show one of the others`; `Show the other book` when there is one). None reads `Same name as another book`. Typing a free title enables the approve press at once. Positive control for the split: a class S pair on the same list (check 11) reads `Same name as another book`, so both presentations are seen from the same `shared` fact.
16. **Withdrawn 2026-11-22, third round (R18).** Was G4's gate on line 2. Its replacement is check 27: the line and the status part are gone in every build.
17. **Still counting (G1, G2).** In the 2 minutes after the last book finishes, and in the 3 s before a badge comes up, the status line starts with `Checking what is left`: never with the counts, never with `…could be read`. With a source really unread for 3 s it reads `Nothing running that could be read`.
18. **Paused beside a look-up (G7).** Pause with only a series look-up running: the line starts `Paused · Finding series for finished audiobooks: <book>`.
19. **Tries tooltip (G8, R16).** Both look-up items' tooltips print the engine's tries per source and hours apart (3 and 6 today, each look-up its own numbers); change the engine's numbers and the tooltip follows. The no-limit sentence appears nowhere.

Added 2026-11-22, Sergei's answers:

20. **Withdrawn 2026-11-22, third round (R18).** Was every kind of change in one approval list.
21. **Withdrawn 2026-11-22, third round (R19).** Was the held books under Left as they are. Check 26 replaces it.
22. **Withdrawn 2026-11-22, third round (R18).** Was Leave as it is on a book with two kinds of change.
23. **Window title (R13).** Force each engine state: the main window's title is the one in table 1.5, and it changes with the status line, never ahead of the badge. No taskbar flash, no focus change.
24. **Withdrawn 2026-11-22, third round (R18).** Was the grouped item after an approval. Check 29 replaces it.
25. **Title tag (R15).** A file whose only clue is the title tag `Sprawl Trilogy 01 - Neuromancer`: no question on its row, title `Neuromancer`, Place line `Series: Sprawl Trilogy · No. 1` with the tag suffix of 4.3.

Added 2026-11-22, third round (R18, R19):

26. **A series found and not applied (guard at hold).** 61 finished audiobooks with a series found, nothing else pending: the badge reads `All done`, the window title `Books Arranger: all done`, the Waiting-for-you block is hidden, the status line has no part about them, and the bottom of the jobs panel reads `Series found for 61 finished audiobooks. They are recorded and stay where they are.` With one: the singular. With none: no line. Positive control that the line is not a state: add one book needing attention and the badge turns `Waiting for you` with the line unchanged.
27. **Nothing asks.** In both states, with books that have a series found: no status part about renames or moves to approve, no second line under Waiting for you, no shortcut, no dialog, no button that approves or refuses a move anywhere on the page.
28. **Tooltip follows the state.** Guard at hold: the series row's step tooltip ends `No audiobook is renamed or moved.` Automatic move on: it ends `Otherwise it stays as it is.` Neither mentions approval.
29. **Automatic move, many at once.** Switch the automatic move on with a backlog of more than 5 held books: the series row shows its writing step for the book being written; `Moving: <book>` shows for the one moving; the Waiting list has at most one grouped item for the writes and one for the moves, each with `Next: <book>.`; with 5 or fewer, one item each. The status line names the work, no badge shows, and `All done` comes only after the last book.
30. **The record.** After that run: `Renamed or moved by the app · N · last <date>` is at the bottom of the jobs panel; opened, its newest entry is the last book moved, with the right `Was in` and `Now in`, the series, number and source it was filed by, and one entry per book (a write followed by a move is one entry). A book only renamed in its folder has an entry. A move he made with `Choose folder…` has none. `Find book` narrows the list; Show in list finds the book's row. Before any automatic move, the record is not on the page.
31. **R19's books.** With the automatic move on, a finished audiobook the engine keeps back because its name would change again: it is not written, not moved, has no row, no Waiting item and no entry in the record, it is counted in the quiet line, and it does not hold back `All done`.
32. **A doubtful result is silent.** A finished audiobook whose series result the engine treats as not found: its row, its details panel, the jobs panel and the record say nothing about a series; it is not in the quiet line's number; the look-up counts it as settled.

Added 2026-11-22, after the final build:

33. **A clash that has ended (gap 1).** A class S row whose other book is renamed away while the row is still listed: its sentence reads `The name is free now. Approve files the book under it.`, never the other book's name; the label is `Goes to` and Approve is enabled. Convert the other book instead, so its file is in Audiobooks Sorted: the sentence is the Name taken one and the label `Already there`. Typing a free title on a clashing row gives the first sentence at once.
34. **The show button (gap 2).** On a class S row and on a class Q row with one other book: the face is `Show the other book`; a press lists that book (Status All, its own folder or file name in the search) and its row is on screen, whatever the two books' titles are. Positive control: two books whose proposed title is nowhere in their tags or paths.
35. **Brackets (gap 5).** A series read from brackets in the folder's name: the row's suffix is ` · from the brackets in its name` (or none), never `from the file's tags`.

## Notes for Ender

What the page needs from the engine, in plain words. How is yours.

**Section 1**
- One finished-state value per poll, decided by the engine from live facts: working, paused, continues by itself, waiting for you, background look-ups only, all done; and "not known" while a source is unread. The truth rules are table 1.1 and its bullets.
- For every row and Waiting item: whether it is a background look-up (so the page never guesses which work is "main").
- Counts: background look-ups left (series and detail, apart and together); drives not answering; books on hold (existing).
- The reasons something waits for him, as keys: attention, hold, drive.
- **Amended 2026-11-22, third round (R18, R19).** A rename or move of a finished audiobook is no longer a reason something waits for him. Today the engine sends `moves` among those reasons and lets it make the state `waiting for you`; that has to go, in both states. The number itself stays, for the quiet line (Section 3 below).
- **Amended, third round.** Which work is "main": writing a series into a finished file, and a write that waits for a job, are main work, not background look-ups (1.1). Today the series row and the waiting write are both marked as background whatever the step. Only the asking online is a look-up. This matters only once the automatic move is on.
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

**Section 3**
**Amended 2026-11-22, third round (R18, R19).** Everything the withdrawn dialog needed is withdrawn with it: the list for approval, the kinds of change per book for it, the digest sent back, leave-as-it-is and its undo, the approve answer per book, the reason keys of Left as they are. The page asks for none of it. What it needs instead:

*For the quiet line (3.2), in both states*
- One number: finished audiobooks with a series found that the app relies on and has not written. Books, each once. Not a book being written or moved now, not a doubtful result. The engine already counts the held series writes; this is that number, kept, with its meaning changed from "waits for him" to "not applied".
- Nothing else. No list, no reason per book.

*For the rows and items (3.3), once the automatic move is on*
- The series row's writing step, as now.
- A write that waits for a job: the book and a blocker object of the 0.30.0 shape, as now. With more than 5, the page groups them itself; it needs the whole number and the first one's book and blocker.
- A move that waits: confirm that an automatic move waits as a queued action of its own (the plan's note says "queued like a Choose folder move"). The page groups more than 5 of them itself. If they wait some other way, tell me how they show and I will word that instead.
- Tell me whether a queued automatic move has a Cancel on the book's row as a Choose folder move has, and what then stops the rules from queueing it again. I have added no control and no words for it.

*For the record (3.4), once the automatic move is on*
- With the normal state: how many finished audiobooks the app has renamed or moved by its rules, and the time of the last one. That is what the summary prints while the record is closed.
- On opening it, the entries, newest first. Per entry: the book's id (for Show in list), its title, the author it is filed under now, when it happened, the path before and the path after (shown under Audiobooks Sorted, and whole), and each reason the rules had, with its value: series found (name, number, source name and address), author folder (the new folder's name), series name (the new name). Values as fields, never an engine sentence.
- One entry per book per time the rules were applied: the path before the app touched the book and the path it ended at. A series write and the move that follows it are two records in the engine and one entry here; the in-between name is not sent.
- Only changes that finished. Only the app's own: the engine must tell a rule-made move from a folder he chose himself, which is not listed.
- I read that the engine already keeps this: `book_moves` has the paths before and after, the times and the state of every move, and the series look-up's own record has the old and new path, the series, its number and its source. I did not run anything; if a piece is missing, tell me which.
- Whether the moves he approved by hand in 0.30.0 belong in the record is yours to say: they were rule-made. I would list them.

*For a doubtful result (3.5)*
- Nothing. It must arrive exactly as a book with no series found: settled in the look-up's count, absent from the quiet line's number, and with no field the page could show.

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

**Section 5 (next version)**
- Per waiting book: tries made, the limit, the next try time, what is being asked (title, series).
- How the wait ended, per field: answered, nothing found, no answer after the limit.
- The Waiting item's count, next try and limit; with one book, its id and title.

**Strings**
- Every label, step, sentence and tooltip above is final copy. The engine sends keys; the page words them (the 0.30.0 rule).

## Assumptions

- A1. Read-only look at code and docs; nothing launched, no rects measured.
- A2. Amended, third round (R18, R19): there is no page control for a finished audiobook's name or place. R6's re-check of already-sorted books is a studio job and has no page surface.
- A3. Settled (R14): a drive that is not answering holds back `All done`. A book on hold does too, as before.
- A10. Withdrawn, third round: it was about what R12 holds out of the approval list.
- A11. Settled, third round (R19): a book that is not moved because a later version would move it again holds nothing back, `All done` included. The same goes for every book with a series found while the guard is at hold.
- A12. Amended, third round: an automatic move waits as a queued action of its own (the plan's note; not run). The grouping in 3.3 rests on it.
- A13 (third round). The quiet line counts the series look-up's own result, which the engine already has, and not the author-folder corrections the rules would make. Counting those too means computing the whole plan at every poll; if Ender has that number cheaply, the line can read `61 finished audiobooks would get a new name or folder. They stay where they are.` instead. Not built unless he says it is cheap.
- A14 (third round). "The automatic move is on" is one switch for the page: the engine either applies a found series by itself or it does not. If Sergei approves the certainty rule for some kinds of change first and others later, nothing on the page changes: each element shows from its own fact.
- A4. A paused queue with nothing pending still reads `Paused`.
- A5. Withdrawn, after the final build: the list's search does not match the proposed title, so a title search cannot be relied on to list both rows. The button lists the other book by its own folder or file name instead (4.2), which the search does match (Ender's report; not run by me).
- A6. The detail look-up records answers and renames no finished audiobook (`gap_fill.py` docstring; Scope: "92 finished books have a recorded English title never applied").
- A7. Amended, third round: the guard holds every series write in 0.31.0 as it stands, and nothing waits for an approval any more (R18). The `Finding series…` tooltip has one sentence for each state (2.1).
- A9 (added after build). On a class Q row the engine refuses the approve press while `shared` is set, set-mates included (`_approve_once` checks every row; read in `merge_service.py`). The page's disabled press in 4.2a rests on that.
- A8. One theme (dark). A light theme, if added, uses the same tokens and needs its own ratios.

## Open questions (facts the docs and code did not settle)

- F1. Settled: a guard holds every series write into a finished file. Amended, third round: it is lifted by a switch, not by an approval, so the writing step shows only once the automatic move is on.
- F2. Settled (R9, R16): both look-ups, 3 tries per source, 6 hours apart; the copy prints the engine's numbers. Still open: how many tries before a waiting book converts (section 5, R2 says "a few").
- F3. Does the Electron shell take its window title from the page? R13 makes the title part of 0.31.0, so this needs Ender's answer before 1.5 is built. (`desktop/main.js` gives the window the title `Books Arranger` and the page has the same `<title>`; I did not run it.)
- F5. Closed, third round: it was asked for the withdrawn dialog's body text. The record's help line says only `The audio is never changed.`, which holds either way.
- F6 (third round). What "found for certain" and "would move again in the next version" mean in the engine are Ender's to propose and Sergei's to approve (Scope, third round). The page needs neither rule, only their results: a book is being changed, is in the quiet line's number, or is neither.
- F7 (third round). Can a queued automatic move be cancelled from the book's row, and what happens next? (Notes for Ender, Section 3.)
- F4. Whether the series look-up of finished books keeps running after R6's job (Scope: not ruled). If it stops, section 2's series row and item simply never appear.

## Questions for Sergei: answered (2026-11-22)

Questions 1 to 11 are closed. The answers, as ruled in the Scope's second round, and for 1, 2, 3, 10 and 11 its third:

1. The approval list: series only, or all? **All** (R10). **Then withdrawn by R18 in the third round: there is no approval list.**
2. `Leave as it is`: the book or the series? **The book** (R11). **Then withdrawn by R18: there is no refusal.**
3. Books written in Chinese or Japanese: hold or let them move now? **Hold** (R12). **Generalised by R19: any book the next version would move again is not moved now.**
4. A count and Try again for look-ups that gave up? **No.**
5. A `Convert now` button on a book waiting for the online answer (next version)? **No.**
6. The state in the window title? **Yes** (R13).
7. Does a drive that is not answering hold back `All done`? **Yes** (R14).
8. The same limit for the titles-and-author-names look-up? **Yes: 3 tries per source** (R16).
9. May the blocked press say `Join them into one book, or change this title.`? **Yes, only on a blocked press** (R17).

10. Refuse the series alone on a book with two kinds of change? **Closed by R18 (third round): there is no refusal at all.**
11. Does a book held for English series names hold back `All done`? **Closed by R19 (third round): "Don't move now if the next version will move it." It is simply not moved, and it holds nothing back** (3.2).

## Questions for Sergei: open (one word each)

**Amended 2026-11-22, third round (R18, R19).** One open point. It is not changed in this spec.

12. R18 was said about finished books. A book that is **not converted yet** can still ask him about its series today, in three places:
    - the row status `Number unclear` (`The title says book 2, but FantLab says book 3.`);
    - the row status `Title unclear` when `The title starts with what looks like a series name and number.`;
    - the details panel's `Sources disagree — which is correct?` when the disagreement is about the series or the number in it.

    Should these follow R18 too: a doubtful series is treated as not found, the book is filed without a series, and nothing asks? I recommend **yes, in the next version**: it is the same reasoning, and each of the three can hold a book back until he answers. Until he says so they stay exactly as they are. yes / no

**Offered, not built** (no answer needed; say the word if wanted):
- A `Put back` on an entry of the record (3.4), to undo one automatic rename or move. Today the way to correct one is `Choose folder…` on the book's row.
- A second, read-only list in the record: finished audiobooks the rules would have moved and could not (a file with that name is already there, the file is not where the app left it), each with its reason. The engine already has the reasons.
