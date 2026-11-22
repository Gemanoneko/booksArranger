# Books Arranger 0.31.0: UX spec (honest status)

Judy, 2026-11-22. For Ender. Source: `BooksArranger_0.31.0_Scope.md` (`d134484`; second round `d28f9ff`): Sergei's report, rulings R1 to R7 and, since the amendment of the same day, R8 to R17, step 4 ("Honest status") and the part of step 1 that shows on the page. Sergei, 2026-11-22: "How do I know that the app finished its queue and have nothing to do anymore? ... But what is 'Updating Metadata'? Is it re-researching old books? Or is it still a first pass?"

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
| G4 | Keep the line, as written. In a build without the dialog it has no button and is not reworded. It is released only together with section 3. | 1.4, check 16 |
| G5 | One count, one list. The word changes from "series moves" to **series changes**; in the dialog each book says `Moves to` or `Renamed to`. `Move N books` is `Add series to N books`; `Keep here` is `Leave as it is`. **Superseded by Sergei's answers (next section): the list is `Renames and moves` and the button `Rename or move N books`. `Moves to`, `Renamed to` and `Leave as it is` stand.** | 1.3, 1.4, 3 |
| G6 | Tooltip given. That the detail look-up never gives up is a product question (Question 8). **Superseded by Sergei's answers: R16 gives it the limit, and its tooltip is the series one.** | 2.2 |
| G7 | Not intended. A paused queue names the look-up that still runs, as 0.30.0 names any work Pause does not stop. | 2.1 |
| G8 | The tooltip takes the engine's numbers (tries per source, hours apart). Example corrected to 3. | 2.2 |
| G9 | The presentation follows the row's own question, never the mere presence of `shared`. Only a row held for the clash itself reads `Same name as another book`; a row with its own question keeps it, `Approve as one book` included. No new engine fact is needed. | 4.1, 4.2, 4.2a |

Also closed while reading the build: the Place line had no words for the engine's `folders` and `unknown` origins (4.3).

## Amended 2026-11-22, Sergei's answers

Sergei answered every question of this spec. His rulings are R8 to R17 in `BooksArranger_0.31.0_Scope.md` ("Second round", `d28f9ff`), which is the authority. Each is written into its section, marked **Amended 2026-11-22, Sergei's answers**. Where this round and the "after build" round disagree, this round wins: the list of section 3 is no longer called "series changes".

**The names chosen for the list and its controls** (R10: it holds author-folder changes too, so "series changes" was no longer true; every change in it is a rename, a move or both):

| Thing | Name |
|---|---|
| the list, and its shortcut in the list toolbar | `Renames and moves · 55` |
| status part | `55 renames and moves to approve` (one: `1 rename or move to approve`) |
| Waiting-for-you line | `55 renames and moves wait for your approval.` |
| its button | `Review changes` |
| dialog title | `Rename or move 55 finished audiobooks?` |
| groups in the dialog | `Series found`, `Author folder`, `Series name` |
| per-book lines | `Now in`, then `Moves to` or `Renamed to` |
| approve button | `Rename or move 52 books` |
| refuse, per book | `Leave as it is`; undone with `Offer again` |
| second list | `Left as they are (3)` |

| Question | Answer | Ruling | Where it went |
|---|---|---|---|
| 1 | The list holds every kind of change the plan holds, author folders too | R10 | section 3 rewritten; 1.1, 1.3, 1.4, 6.1, 7, 9 |
| 2 | `Leave as it is` is about the book, for good, and can be taken back | R11 | 3.5 |
| 3 | Books written in Chinese or Japanese are held out of the list | R12 | 3.4 (shown under Left as they are, with the reason) |
| 4 | No count or Try again for look-ups that gave up | as recommended | 2.3 |
| 5 | No `Convert now` button | as recommended | 5 |
| 6 | The window title shows the state | R13 | 1.5: a title for every state |
| 7 | A drive that is not answering holds back `All done` | R14 | 1.1, as already specced |
| 8 | The look-up for titles and author names gets the same limit | R16 | 2.2: one tooltip for both look-ups |
| 9 | The blocked press may say `Join them into one book, or change this title.` | R17 | 4.2a |
| also | Nothing is written into a finished book without approval | R8 | 2.1, 3 |
| also | Tries: 3 per source, 6 hours apart, approved as built | R9 | 2.2 |
| also | A title tag shaped "Series NN - Title" is filed without asking | R15 | 4.3 |

Two questions opened by these answers are at the end (Questions 10 and 11), each with the default that is built until he answers.

## Decisions in brief

- **Three finished states, one badge.** When no job runs, waits or is queued, the status line starts with a badge: `All done`, `Waiting for you` or `Background look-ups only`. The badge is there only when the queue is finished, so its presence alone answers Sergei's question; its words say which of the three.
- **The engine decides the state.** The page never works it out from rows (the 0.29.0 rule for `needs_you_only`, kept).
- **Bare `Nothing running` goes from the status line.** It read as "done" while work waited. With work waiting it says `Continues by itself`.
- **Two background look-ups get plain names** that say which books they are for and whether a file changes. Their bar counts the whole look-up, not one pass, so `691 of 903 books` answers "how much is left".
- **A look-up between tries is a Waiting item**, grouped, with the next try time.
- **Renames and moves get a dialog** (the word was "series moves", then "series changes"; amended, Sergei's answers: R10 puts author-folder changes in the same list): the list he approves is the list he sees (the engine's existing gate). The books sit in groups by kind of change. Selected books are approved with one press, `Rename or move N books`; a wrong one is refused on its own line with `Leave as it is`. A refused book can be offered again from the same dialog, so no second confirm is needed.
- **A book held only because another book has its name** reads `Same name as another book` and is offered a name change. A row with a question of its own keeps that question and its buttons (amended, G9).
- **Section 5 is the next version.** It is specced here so the words match; nothing in it is built in 0.31.0.

## 1. "All done" and the other finished states

### 1.1 The states

"Main work" is everything the 0.30.0 Running and Waiting lists show (conversions, cleanups, checks, queued actions, moves, scans, research of books not converted yet, automatic processing running, stopping, start pending or between tries, timed retries, saved decisions). "Background look-ups" are the two jobs of section 2 only. "Waits for you" is: books that need attention, books on hold, renames and moves to approve (section 3), a drive that is not answering (R14, Sergei's answers: confirmed).

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

Status parts, in order (new parts marked): badge or first part, books waiting to convert, cleanup phrase, actions waiting, `N need attention`, **`55 renames and moves to approve`** (new, zero left out; amended, Sergei's answers, R10: was `series moves`, then `series changes`), `N converted out of M approved books`, `N waiting for retry checks`, **`212 background look-ups left`** (new, zero left out; series and detail look-ups together). Singulars: 6.1.

Examples:
- `[All done] · 0 need attention · 1,510 converted out of 1,510 approved books`
- `[Waiting for you] · 329 need attention · 55 renames and moves to approve · 1,181 converted out of 1,510 approved books · 212 background look-ups left`
- `[Background look-ups only] · 0 need attention · 1,510 converted out of 1,510 approved books · 212 background look-ups left`
- `Continues by itself · 3 books waiting to convert · 329 need attention · …`

`· N on hold` stays as a part after the badge (it was glued to `Nothing running`).

The idle line `#jobs-idle` (shown, as today, only when the Running list is empty):

| When | Line |
|---|---|
| `All done`, or `Waiting for you` with no look-up left | `Nothing is running, queued or waiting.` |
| a look-up waits for its next try, or `Continues by itself` | `Nothing is running right now.` |
| `Checking what is left` (amended, G1) | `Nothing is running right now.` |
| paused, unread | unchanged (0.30.0) |

**Supersedes:** 0.30.0 section 4 "otherwise `Nothing running` plus its counts"; the idle strings `Nothing running` and `Nothing running.`.

### 1.4 The Waiting-for-you block

Shown, as today, only in the `Waiting for you` state. It becomes a short list: heading `Waiting for you` (the look of `Waiting` and `On hold`), then one line per kind that has a count, each with its button at the right (96 x 32 minimum).

```
Waiting for you
 329 books need attention.                                        [ Review them ]
 55 renames and moves wait for your approval.                     [ Review changes ]
```

- Line 1 and **Review them** are the 0.29.0 line and button (tooltip `Show every book that needs you.`). The as-of suffix stays: `329 books need attention (as of 14:03:21).`
- Line 2 and **Review changes** are new (section 3). One book: `1 rename or move waits for your approval.` (amended, Sergei's answers, R10: the noun was `series moves`, then `series changes`; the button keeps its name). The number is books: a book with two kinds of change counts once.
- **Amended 2026-11-22 after build (G4).** Line 2 stays, with these words, in a build that does not have the dialog yet; it simply has no button there. It is not hidden: the changes do wait for him, and they are why the badge says `Waiting for you`. It is not reworded: an interim sentence would have to be taken out again. But a line that says something waits for him and gives no way to answer is a dead end, so line 2, the status part and the list shortcut are released only together with section 3 (check 16).
- The sentence `The app can't do more until you review them.` goes: the badge says it, and it was untrue while look-ups ran.
- A drive that is not answering and a book on hold keep their own homes (the Waiting item with its instruction, the On hold list). They make the badge `Waiting for you` but add no line here. If they are the only reason, the block is hidden and the badge sits above the item that explains it.
- Order is fixed: need attention, then renames and moves. A line with a zero count is left out.

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
| `series`, writing | the same label | `Writing the series into the file and renaming it. Audio unchanged.` | the same |
| `gap_fill` | `Finding original titles and author names: <book>` (was `Looking up book details`) | `For books you already approved. Recorded only, no file is changed.` | `40 of 71 books`, determinate |

- **The count is the whole look-up:** done = books settled (a series found, none found, or given up), total = every book that needed the look-up. It only grows and ends at the total. It is never the count of one pass, which starts again every ten minutes and reads as no progress.
- **No time estimate** on these two rows. Their pace is set by how often the sources may be asked; a guess would be wrong. The elapsed time stays.
- **Step tooltip** (the step line's `title`, as the chapter check uses it):
  - `series`: `Finished audiobooks without a series are looked up online, one by one. A series that is found changes a book only after you approve it.` (amended, G5: with the guard this is true of every write, not only of a move; the writing step therefore shows only after an approval)
  - `gap_fill`: `Books approved without an original title or a full author name are looked up online, one by one. The answers are recorded. No audiobook is renamed.`
- The step and the label are one line each with an ellipsis (the 0.30.0 row); at widths where the step is cut, its `title` holds the full sentence.
- These rows count in `tasks running` only beside main work. Alone, the badge leads the status line and the row shows below it.
- **Amended 2026-11-22 after build (G7).** That rule is for the first parts that already say the app is not busy: a badge, `Continues by itself`, `Checking what is left`. It is not for `Paused`. A paused queue with a look-up still running reads as 0.30.0 reads any work Pause does not stop: `Paused · Finding series for finished audiobooks: Dune` (two or more: `Paused · 2 tasks running`). Without the name, a bar moves under a line that says only `Paused`, and nothing explains it.
- `Researching books` (books not converted yet), `Looking up metadata` (a Find metadata press) and `Re-checking finished audiobooks` (a file check, nothing online) keep their names. Read beside the two labels above, they no longer look like the same job.

### 2.2 Between tries: the Waiting list

A look-up that waits for its next try showed nowhere. It is a Waiting item, one per look-up, grouped (the cleanups precedent). Engine order: after `metadata_sources`, before `drive`.

| What waits | Line 1 | Line 2 | Button |
|---|---|---|---|
| series look-ups between tries | `Finding series for finished audiobooks: 212 books` | `Waiting for online sources. Next try 14:05. No file is changed.` | none |
| detail look-ups between tries | `Finding original titles and author names: 31 books` | `Waiting for online sources. Next try 14:05. No file is changed.` | none |
| an approved series, its write held by a job | `Write series into audiobook: <book>` | the 0.30.0 blocker sentence: `It runs when Converting: Dune finishes.` (a cleanup or a scan the same way) | Show in list |

- The count is the books waiting for a later try. Books due in the running pass are in the row, not here, so no book is counted twice.
- `Next try 14:05.` is left out when the engine has no time.
- **Amended 2026-11-22 after build (G8, G6).** Line 2 tooltip, one per item. Every number is the engine's; none is written into the page.
  - Series look-ups (a limit exists): `Each source is asked up to 3 times for a book, 6 hours apart. With no answer after that, the book is left as it is and the app stops asking.` The page fills in the tries per source and the hours between tries. If the engine sends no hours, `, 6 hours apart` is left out. One try: `Each source is asked once for a book. With no answer, the book is left as it is and the app stops asking.`
  - Detail look-ups: **amended 2026-11-22, Sergei's answers (R16).** This look-up gets the same limit, so its item takes the same sentence as the series item, with its own numbers from the engine: `Each source is asked up to 3 times for a book, 6 hours apart. With no answer after that, the book is left as it is and the app stops asking.` The no-limit text of the "after build" round (`A book waits here until its sources answer…`) is withdrawn and is not built.
  - R9 approved the numbers as built (3 per source, 6 hours apart). They are still the engine's; the page prints what it is sent.
- A look-up that pauses inside one book for a source's pacing leaves the Running list and waits here. The row's `No progress for 5 min` text must never show on a look-up that is only being polite to a source.
- These items do not make the state "Working": with only them left, the badge is `Background look-ups only`.

### 2.3 After approval, and at the end

- An approved book with a series found runs as `Finding series for finished audiobooks: <book>` with the writing step; a book whose folder changes then gets the 0.30.0 `Moving: <book>` row (amended, G5: a book renamed in its own folder has no second row). An approved author-folder or series-name change has no series to write and runs as the `Moving: <book>` row alone.
- When every book is settled there is no row and no item. `All done` is the signal. No summary line, no count of books the look-up gave up on, no Try again (Sergei's answers, Question 4: as recommended).
- **Amended 2026-11-22, Sergei's answers (a consequence of R10).** One press can now approve hundreds of books, and the engine queues an approved move like a Choose folder move, so each waits its turn as a queued action (Notes for Ender: confirm). The 0.30.0 Waiting list draws one item per queued action, which would be a wall. So the cleanups' cap applies to them too: with 5 or fewer queued moves, each is its own item as today; with more, one grouped item replaces them: line 1 `Moving finished audiobooks: 338 books`, line 2 `Next: <book>.` followed by that book's blocker sentence when something blocks it (`Next: Оно. It runs when Converting: Dune finishes.`), else `Next: Оно. They run one at a time.`; button Show in list for that book. The status part `338 actions waiting` is unchanged. Each book's own row keeps its Cancel.

## 3. Renames and moves: the approval control

**Amended 2026-11-22, Sergei's answers (R8, R10, R11, R12).** This section is rewritten whole; build it from this text. It was "Series moves", then "Series changes". Three things changed it:

- **R10:** the list holds every kind of change the engine's plan holds for a finished audiobook, not the series ones only: a **series found** online for a book that had none, the **author folder** the app now files the author under, and the **series name** it now files the series under.
- **R8:** nothing is written into a finished audiobook without his approval, so a book whose series only needs writing and a new file name in the folder it is already in waits in this list too.
- **The name:** every change here ends as a rename, a move or both, whatever caused it, so the list is **Renames and moves**. "Series changes" was untrue for an author-folder move. A series being written into the file is said where it happens, in the dialog.

One book is one line of the count and one decision, however many kinds of change it has: the plan gives each book one new name and place.

The engine's gate stays: he approves the list he saw; if the list changed, nothing is changed.

### 3.1 Where it lives

| Entry | Place | Face | Shown |
|---|---|---|---|
| the list shortcut | list toolbar, right after `Needs attention · N` | `Renames and moves · 55` (quiet) | Audiobooks library, and either a book waits or he has left at least one book as it is (so Offer again is always reachable). With none waiting the face is `Renames and moves · 0`. |
| **Review changes** | the Waiting-for-you block (1.4) | `Review changes` (quiet, 96 x 32 minimum) | with its line |

Both open the same dialog. Tooltip, both: `List the finished audiobooks that wait for your approval to be renamed or moved.` At `· 0`: `Nothing waits for your approval. Lists the books you left as they are.`

The count is the books he can approve now. It leaves out the books under Left as they are (3.4): the ones he refused, the ones R12 holds, and the ones the app cannot change.

### 3.2 The dialog

A modal `<dialog>`, built like `join-dialog`: Cancel has `autofocus`, Escape cancels, no form (Enter in the list confirms nothing). Width `min(880px, 100vw - 24px)`: two paths per book do not fit 560. It opens at once with `Checking the list…` while the engine answers. The list can hold several hundred books (R8 alone covers 282), so it is grouped.

```
Rename or move 340 finished audiobooks?
Each book gets the name and folder shown. A series found online is also written into its file.
The audio is not changed. The app can't undo it.

[x] Select all

v Series found · 290
  [x] Select these 290
  [x] Граф Ноль · Gibson William · Series: Sprawl Trilogy · No. 2 · found on FantLab            [ Leave as it is ]
      Now in      Gibson William\Граф Ноль - Gibson William.m4b
      Moves to    Gibson William\Sprawl Trilogy\2 - Граф Ноль - Gibson William.m4b
  [x] Мона Лиза овердрайв · Gibson William · Series: Sprawl Trilogy · No. 3 · found on FantLab    [ Leave as it is ]
      Now in      Gibson William\Sprawl Trilogy\Мона Лиза овердрайв - Gibson William.m4b
      Renamed to  Gibson William\Sprawl Trilogy\3 - Мона Лиза овердрайв - Gibson William.m4b
  [x] Сияние · Stephen King · Series: The Shining · No. 1 · found on Goodreads · Author folder: King Stephen  [ Leave as it is ]
      Now in      Stephen King\Сияние - Stephen King.m4b
      Moves to    King Stephen\The Shining\1 - Сияние - King Stephen.m4b
  ...
v Author folder · 45
  [x] Select these 45
  [x] Оно · Stephen King · Author folder: King Stephen                                          [ Leave as it is ]
      Now in      Stephen King\Оно - Stephen King.m4b
      Moves to    King Stephen\Оно - King Stephen.m4b
  ...
v Series name · 5
  [x] Select these 5
  [x] Гарри Поттер и тайная комната · Rowling Joanne · Series name: Harry Potter                [ Leave as it is ]
      Now in      Rowling Joanne\Гарри Поттер\2 - Гарри Поттер и тайная комната - Rowling Joanne.m4b
      Moves to    Rowling Joanne\Harry Potter\2 - Гарри Поттер и тайная комната - Rowling Joanne.m4b
> Left as they are (12)

[ Cancel ]                                                            [ Rename or move 340 books ]
```

- Title: the number is the books that wait. One book: `Rename or move 1 finished audiobook?` While loading: `Renames and moves`.
- Body, one book: `This book gets the name and folder shown. A series found online is also written into its file. The audio is not changed. The app can't undo it.` The second sentence is left out of both bodies when no listed book has a series to write.
- The list is a `role="group"`, `aria-label="Books to rename or move"`, and scrolls inside the dialog (`max-height: 50vh`); the title, the body and the buttons stay in view. The button row is outside the scrolling list, in normal flow.
- Every book starts selected, each time the dialog opens. `Select all` is a checkbox (mixed when some are selected).

**Groups.** Three kinds of change, three groups, always in this order: `Series found`, `Author folder`, `Series name`. A group with no book is not drawn.

- A group is a native `<details open>`. Its summary is the group's name and count, weight 600: `Series found · 290`. Closing a group only folds it away; its books keep their selection and still count in the button. So that a folded group hides nothing he would approve unseen, the summary says when not all its books are selected: `Series found · 290 · 288 selected`, `Series found · 290 · none selected`.
- The first line inside a group is its own checkbox, `Select these 290` (mixed when some are selected). With one group only, this line is left out: `Select all` already does it.
- A book with two or three kinds of change is listed once, in the first of its groups in the order above, and its line 1 names every kind. So the group counts add up to the title's number.
- Inside a group the order is the engine's (by current path), so one author's books sit together.
- Series found comes first because it is the one worth reading book by book: an online match can be wrong, and it writes into the file. Author folder and Series name follow a rule and can usually be approved as a group.

### 3.3 Per book

Three lines. The checkbox's label is line 1, so the whole text of the line is its target; **Leave as it is** is a separate button at the line's right end (flex row, 12 px gap, the button never shrinks), not inside the label.

1. `Title · Author`, then one part per kind of change the book has, ` · ` between, in the groups' order. Title in weight 600. The author is the one the book is filed under now.

   | Kind | Part |
   |---|---|
   | series found | `Series: <name> · No. <n> · found on <source>` (the Place line's form). Source names: `FantLab`, `Goodreads`, `Wikidata`, `Litres`, `the publisher's site`; unknown: `found online`. The source's address is the `title` of that text. |
   | author folder | `Author folder: <the new folder's name>` |
   | series name | `Series name: <the new name>` |

2. `Now in` and the current path under Audiobooks Sorted (labels and path style of the row's destination block; the full path is the `title`).
3. The new path, under one of two labels: **`Moves to`** when its folder differs from line 2's, **`Renamed to`** when the folder is the same and only the file name changes. The page tells them apart by comparing the two folders. The leading folders the new path shares with line 2 are `--muted`; what is new (a folder, the file name) is `--text`, so the eye lands on what changes. Both pass 4.5:1; the labels carry the meaning without the colour.

A book that was approved and then could not be changed comes back to this list with a fourth line in `--warning`: `Approved, but not changed: its file changed. Check it and approve again.` or `Approved, but not changed: its new name or place changed. Check it and approve again.` It counts in `Renames and moves · N` again. An approved change never fails in silence.

### 3.4 Left as they are

A `<details>` under the groups, closed by default (open when no book waits), summary `Left as they are (12)`, tooltip `Finished audiobooks the app would rename or move but does not, and why.` Hidden when empty. Each entry: `Title · Author`, the `Now in` line, and one reason sentence. These books do not count in `Renames and moves · N` and are not selectable.

| Reason (the engine sends a key, never the sentence) | Sentence |
|---|---|
| refused by him (R11) | `Left as it is by you.` with **Offer again** |
| written in Chinese or Japanese (R12) | `Written in Chinese or Japanese: held until its series has an English name.` |
| a file with the new name exists | `A file with the new name is already in that folder.` |
| two listed books, one target | `Another book on this list would get the same name.` |
| he chose its folder | `You chose its folder.` |
| not in Audiobooks Sorted | `Not in Audiobooks Sorted.` |
| name is not the app's | `Its file name isn't the one the app gave it.` |
| file not where recorded | `The file isn't where the app left it.` |
| a newer version or a replacement | `It has a newer version.` |
| files kept at his choice | `You chose to keep its files as they are.` |
| data folder move unfinished | `Waits for the data folder move to finish.` |
| sources disagree | `Sources disagree about its series.` |
| no name can be built, or it could not be planned | `The app can't work out its new name or place.` |
| any other key | `The app leaves it as it is.` |

**Amended 2026-11-22, Sergei's answers (R12).** A book whose original is Chinese or Japanese is held out of the list. It is not simply absent: it is shown here, with its reason, so a book he knows has a series does not seem to have vanished. Nothing else shows it: no count in the status line, no line under Waiting for you, no shortcut of its own.
- The reason states the condition, not a version: it ends by itself when the app can give the series an English name.
- The whole book is held, whatever kinds of change it has (R12 names the books, not the series change), and it has no button: he cannot offer it himself.
- It does not wait for him. Whether it holds back `All done` is Question 11; until he answers, it does not.

### 3.5 Approve all, approve some, refuse

One pass down the list: a right book stays selected, a book to decide later is unselected, a wrong book gets **Leave as it is**. The dialog is the confirm: it is opened on purpose, shows the exact list, and the one bulk button says what it does and to how many.

| He wants | He does | Result |
|---|---|---|
| approve all | **Rename or move 340 books** | dialog closes |
| approve one kind | unselects the other groups with their `Select these N`, **Rename or move 45 books** | dialog closes; the rest stay waiting |
| approve some | unselects the ones to leave for later, **Rename or move 337 books** | dialog closes; the 3 stay waiting |
| refuse | **Leave as it is** on that book | it goes to Left as they are at once; the dialog stays open |

- **Rename or move N books** (default button, right end; the count is the selected books in every group, folded ones included; one: `Rename or move 1 book`). Tooltip: `Give each selected book the name and folder shown. A series found online is written into its file first. The audio is not changed. The app can't undo it.`
- **Leave as it is** (quiet, 96 x 32 minimum, one per book; `aria-label` `Leave as it is: <Title>`). Tooltip: `Leave this book as it is, for good: no rename, no move, no series written. Offer again brings it back.` While it is sent the face is `Leaving…`. Then focus goes to the next book's Leave as it is (the previous one for the last book; Cancel when the list is empty).
- **Offer again** (quiet, 96 x 32 minimum, on a book he refused). Tooltip: `Put this book back on the list of renames and moves.` The book returns to its group, selected.
- **Cancel** (quiet). Tooltip: `Close without changing any book.` A book already left as it is stays so; the tooltip is about the approval.
- Leave as it is needs no second confirm: it touches no file, and Offer again undoes it at any time. There is no bulk refuse, so no single press can empty the list.

**Amended 2026-11-22, Sergei's answers (R11): what Leave as it is means.**
- It is about **the book**, for good. The app stops asking about that book: it is never listed here again by itself, whatever it finds for it later (another series, a new author rule). It is not about the series: other books of the same series are still offered.
- **A book with two kinds of change** (say an author folder and a series found) gets one answer, and it covers both: neither is done. The plan gives a book one new name and place, built from all its changes together, so the page has no half to refuse. If the series is wrong and the author folder is right, the author folder is lost for that book too. Whether he should be able to refuse one kind and keep the other is Question 10; until he answers, it is the whole book.
- **It can be taken back.** Offer again puts the book back with whatever the plan holds for it at that moment, which may differ from what he refused. The shortcut stays visible while any book is left as it is by him (3.1), so the way back never disappears.
- The book keeps its place, its name and its file exactly as they are. It is still an ordinary finished audiobook everywhere else in the app.

**Result line**, one string, shown beside the control that opened the dialog (`role="status"`, in normal flow: under the Waiting-for-you block, or under the list toolbar like `#restart-summary`). It stays until the dialog is opened again. No toast.

| Outcome | Line |
|---|---|
| all accepted | `340 renames and moves approved. They run one at a time and show in Audiobook jobs.` |
| some refused | `338 renames and moves approved. 2 books were not accepted: open Renames and moves to see why.` (`--warning`) |
| none accepted | `No rename or move was accepted. Open Renames and moves to see why.` (`--warning`) |
| refused (inside the dialog, above the buttons, `role="status"`) | `«Граф Ноль» left as it is.` |
| offered again (the same line) | `«Граф Ноль» is back on the list.` |

After **Rename or move**, focus returns to the control that opened the dialog; if it is gone, to the Status select `#filter`.

### 3.6 Loading, a changed list, refusals

| Moment | The dialog shows | Buttons |
|---|---|---|
| loading | `Checking the list…` | Rename or move `aria-disabled`, tooltip `The list is still loading.` |
| nothing selected | the list | Rename or move `aria-disabled`, face `Rename or move`, tooltip `Select at least one book.` Leave as it is stays enabled (it does not use the selection). |
| sending an approval | the button's face `Approving…` | Rename or move, Cancel, every checkbox, every Leave as it is and Offer again `aria-disabled`, tooltip `Sending your answer.`; Escape does nothing until it returns |
| sending a Leave or an Offer | that button's face `Leaving…` / `Offering…` | Rename or move and the other Leave as it is and Offer again buttons `aria-disabled`, tooltip `Sending your answer.`; Cancel stays enabled |
| the list changed since it was shown | the new list in place, selections kept for books still listed, and above the buttons, in `--warning`, `role="status"`: `The list changed. Check it, then press Rename or move again. Nothing was changed.` | enabled |
| the app is closing | `Books Arranger is closing. Nothing was changed.` (`--warning`) | Rename or move, Leave as it is and Offer again `aria-disabled`, tooltip `Books Arranger is closing.` |
| the list could not be loaded | `The list couldn't be loaded. Close this and try again.` | Cancel only, face `Close` |
| nothing waits | `No books wait to be renamed or moved.` and Left as they are, open, if it has any | Cancel only, face `Close` |

## 4. Two books, one destination

### 4.1 The held rows

**Amended 2026-11-22 after build (G9, blocking).** The engine reports `destination.shared` on every to-do row whose planned name another book also has, whatever that row is asking: a row held for the clash itself, and equally a real piece of one book that is named after its set. This section, as first written, read as if every such row took the `Same name as another book` presentation and lost `Approve as one book`. It does not. **The presentation follows the row's own question, never the mere presence of `shared`.**

| Row | Test (facts the page has) | Presentation |
|---|---|---|
| **S.** The clash is its only question | group Name taken, **and** the row's own hold kind is `same_destination` | this section: `Same name as another book`, 4.1 and 4.2 |
| **D.** A file with the name is on disk | group Name taken with any other hold (`destination.taken` is true) | the 0.30.0 Name taken row (`Already there`), unchanged. `shared` adds nothing to it |
| **Q.** It has a question of its own | every other group: `part_of_book` (every cause: chapter, numbered part, siblings, part of a set, a set), `files_unclear` (the folder question included), `order_unclear`, `title_author`, `author_unclear`, `same_author`, `files_missing`, `other` | its own status, sentence, fields and buttons, unchanged. `Part of a bigger book`, `Approve as one book` and `Keep as separate books` all stay. `shared` adds only what 4.2a lists |

- **Do not test `destination.shared.kind`.** It reads `same_destination` on every row that carries `shared` (the object is the hold's shape). The test is the row's own hold: why the engine is holding this row.
- **No new engine fact is needed** to tell the three apart: the row's group and its own hold kind decide. If the row does not carry its own hold kind apart from `destination.shared`, that is the one fact to add; until then "group Name taken, `taken` false, `shared` set" is the same test.
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

### 4.2 What he is offered (class S)

| Control | State and words |
|---|---|
| **Approve** | `aria-disabled` while the names are the same. The line under the buttons: `Another book would get this name. Change the title, author, series or number.` Enabled as soon as this row's `Goes to` differs. |
| **Show both books** (new, quiet, 96 x 32 minimum; `Show all 3 books` for more) | Sets Status to All and searches for the shared title, so the rows sit together. Tooltip: `List the books that would get this name: sets Status to All and searches for this title.` |
| the other row actions a Name taken row has | unchanged |

- **Never on a class S row** (amended, G9: class S only, not every row with `shared`): the status `Part of a bigger book`, the face `Approve as one book`, `Keep as separate books`. A class S row never had them: the engine held it for the name alone. No Join hint either (Sergei's answer 10, 2026-11-18).
- When one row's name changes and the clash ends, the other row leaves by the 0.29.0 rule and strip line: `«Title» left this list: the name is free now. The book is checked again.`
- If the clash appears only at the press (the engine's `same_name` refusal, on a row of any class), Approve answers: `Another book would get this name. Change the title, author, series or number, then approve.` The row's `Goes to` line refreshes, as for Name taken.

### 4.2a A row with its own question whose name another book also has (class Q)

**Amended 2026-11-22 after build (G9).** The row keeps everything it has. While `shared` is set, three things are added. If `taken` is set too, the name on disk wins and the row shows as it does today.

| What | Words |
|---|---|
| Destination label | `Both go to` (`All 3 go to`), in the warning style, in place of `Goes to` or `As one book`. The path is unchanged. |
| The row's own approve press, whatever its face (`Approve`, `Approve as one book`, `Approve this order`, `Approve these files`, `Convert what's there`) | Face and tooltip unchanged. `aria-disabled`, with the reason on the line under the buttons: `Another book would get this name. Change the title, author, series or number.` (on a `part_of_book` row the line is R17's, below). The engine refuses that press while the clash stands (`same_name`), so the page prevents it instead of letting it be refused, exactly as it does for a name already on disk. The offer is not removed: it works again as soon as the name he types is free. |
| **Show both books** | Added as the last button of the row, after the row's own (4.2). A press that is blocked by another book must show him that book. |

- Untouched and enabled as before: the status, the sentence, the fields, `Keep as separate books`, `Scan again`, `Change order`, `Choose files`, `Remove from list` and every other button the row has.
- No `Also:` line and no second sentence. The label and the reason line carry the clash; the row's sentence stays its own question.
- When the name he types is free, the label and the approve press return to normal at once.
- **Amended 2026-11-22, Sergei's answers (R17: yes).** On a `part_of_book` row (every cause) whose approve press is blocked this way, the reason line names both ways out: **`Another book would get this name. Join them into one book, or change this title.`** For real pieces of one book joining is the answer and renaming is not. Build this line, not the plain one, on those rows.
  - Only there, and only while the press is blocked. Every other class Q row (the folder question included), every class S row and the late refusal of 4.2 keep the plain line. The line goes when the press is free again.
  - Nothing else about Join is added: no hint on a row that is not blocked, no Join button on the row. His "no Join hint on rows" of 2026-11-18 otherwise stands. "Join them" is the existing `Join into one book` in the bar above the list, for the rows he selects.

### 4.3 A volume named from its own tags (R4)

The book is filed without asking, so the row carries no question. It says where the series came from, on the Place line of the status cell:

`Series: Sprawl Trilogy · No. 2 · from the file's tags`

- **Amended 2026-11-22 after build.** The suffix, by the origin the engine sends: `tags`: ` · from the file's tags`; `folders`: ` · from the folder names`; `entered`: ` · entered by you`; `source`: ` · found on Wikidata` (the source names of 3.3; a source with no name: ` · found online`); `unknown`: no suffix. `folders` and `unknown` had no words. `source` shows whenever the engine says so, not only from the next version.
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

- The engine sends one origin, `tags`, for all three today (it folds the title tag's text and a series in brackets in the file name into it). Until it tells them apart, `tags` reads ` · from the file's tags`. That is true for the first two (a title tag is one of the file's tags), so R15's row is right in this build; it is not true for a series read from the file name. The finer origin is in Notes for Ender.

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

**Amended 2026-11-22 after build (G3); the rows about the list amended 2026-11-22, Sergei's answers (R10: its new name).** Every count this spec prints, one and many. A count of the list is always books: a book with two kinds of change is one.

| Place | One | Many |
|---|---|---|
| status part | `1 rename or move to approve` | `55 renames and moves to approve` |
| status part | `1 background look-up left` | `212 background look-ups left` |
| Waiting-for-you | `1 book needs attention.` | `329 books need attention.` |
| Waiting-for-you | `1 rename or move waits for your approval.` | `55 renames and moves wait for your approval.` |
| look-up Waiting items, line 1 | `…: 1 book` | `…: 212 books` |
| look-up rows, detail | `1 of 1 book` | `691 of 903 books` |
| grouped moves waiting (2.3), line 1 | never one: it groups above 5 | `Moving finished audiobooks: 338 books` |
| tries tooltip (2.2) | `Each source is asked once for a book.` | `…asked up to 3 times for a book` |
| tries tooltip, the gap | `, 1 hour apart` | `, 6 hours apart` |
| list shortcut | `Renames and moves · 1` | `Renames and moves · 55` (the noun names the list and stays plural; `· 0` as 3.1 says) |
| dialog title | `Rename or move 1 finished audiobook?` | `Rename or move 340 finished audiobooks?` |
| dialog body | `This book gets the name and folder shown. …` (3.2) | `Each book gets the name and folder shown. …` |
| group summary | `Series found · 1` | `Series found · 290` (the same for `Author folder`, `Series name`) |
| group checkbox | `Select this 1` | `Select these 290` |
| dialog button | `Rename or move 1 book` | `Rename or move 52 books` |
| dialog, second list | `Left as they are (1)` (a heading, stays plural) | `Left as they are (12)` |
| result line | `1 rename or move approved. It shows in Audiobook jobs when it runs.` | `340 renames and moves approved. They run one at a time and show in Audiobook jobs.` |
| result line, the refused part | `1 book was not accepted: open Renames and moves to see why.` | `2 books were not accepted: open Renames and moves to see why.` |
| same name, destination label | `Both go to` (this book and one other) | `All 3 go to` |
| same name, sentence | one other book: it is named (4.1) | `2 other books would get this file name.` |
| same name, button | `Show both books` | `Show all 3 books` |
| section 5 (next version) | `After 1 try a book converts…`, `No online answer after 1 try.` | `After 3 tries…`, `…after 3 tries.` |

Not in this spec's list of changes, noted only: the 0.30.0 status part `N need attention` prints `1 need attention` for one book. `1 needs attention` would be right.

## 7. Controls: tooltip, disabled state, keyboard

| Control | Tooltip | Disabled when, and what it says | Keyboard |
|---|---|---|---|
| `Renames and moves · N` | 3.1 (two tooltips: books waiting, and `· 0`) | never disabled; hidden outside Audiobooks, and when no book waits and he has left none as it is | in the toolbar's tab order after Needs attention; Enter or Space |
| **Review changes** | 3.1 | never disabled; shown with its line | tab order after Review them |
| Select all | `Select or unselect every book in this list.` | while loading or sending | Space |
| a group's summary (`Series found · 290`) | `Show or hide these books. Hidden books keep their selection.` | never | Enter or Space folds and unfolds |
| a group's checkbox (`Select these 290`) | `Select or unselect the books of this group.` | while loading or sending | Space |
| a book's checkbox | none of its own: its label is the book's line 1; `aria-label` is `Title, Author` | while sending | Space; focus scrolls it into view |
| Left as they are | 3.4 | never | Enter or Space opens and closes |
| **Leave as it is** (per book) | 3.5 | while anything is being sent, app closing (3.6) | Enter or Space; follows its book's checkbox in tab order |
| **Offer again** | 3.5 | the same | Enter or Space |
| **Cancel** / `Close` | `Close without changing any book.` | while an approval is being sent | Escape, Enter or Space |
| **Rename or move N books** | 3.5 | nothing selected, loading, sending, app closing (3.6) | Enter or Space; never Enter from the list |
| **Show both books** | 4.2 | never | class S: in the row's action order after Approve. Class Q (4.2a): the last button of the row |

- The names in this table follow section 3 as amended (Sergei's answers).
- Dialog tab order: Cancel (focused on open), Rename or move, then round to Select all, each group (its summary, its checkbox, then each book: its checkbox, its Leave as it is), Left as they are. Cancel and Rename or move are one or two presses from the start in either direction, whatever the list's length. A folded group takes its books out of the tab order, so folding is also the keyboard's way past 290 books.
- A reload of the list in place never moves focus off the dialog and never resets the scroll position.
- Hover-only texts on things that are not controls: the badge (1.2), the two step lines (2.1), line 2 of the grouped look-up items (2.2), the source name (3.3). None carries anything that is not also on screen in short form.
- Every `aria-disabled` button keeps its focus stop and says why in its tooltip (the app's existing pattern).

## 8. Layout, overlap and contrast

**Narrow layouts.** No string differs by width.
- Review table: every new row text is in the status cell or the destination cell, which the medium (600 to 799) and compact (under 600) bands never hide. Nothing new goes into columns 3 and 4, which they fold.
- Jobs panel under 560 px: rows stack as built; labels and steps keep their one-line ellipsis and full `title`. The status line wraps; the badge stays whole on the first line.
- Dialog under 600 px: the label (`Now in`, `Moves to`, `Renamed to`) sits above its path; paths wrap anywhere; a book's Leave as it is drops to its own line under the paths, left-aligned; Cancel and Rename or move keep one row.

**No element covers another.** By construction, not by measurement: everything new is in normal flow (no absolute, fixed or sticky positioning), so it can only wrap or push. The dialog is the one overlay, modal and dismissible, which is the allowed class. States walked through on paper: each of the eight first parts of 1.1 (with `Checking what is left`, amended) with 0, 1, 2 and 5 rows; `Paused` beside a running look-up row; the badge with and without the as-of suffix; the Waiting-for-you block with one and two lines, and line 2 with no button (G4's interim build); the freshness cue and the unread line shown; the list toolbar with the error, attention and `Renames and moves` shortcuts all shown at 600 px; the dialog loading, with 1, 55 and 400 books, with one, two and three groups, each open and folded, a book with three kinds of change on its first line, with `Moves to` and `Renamed to` books, with Left as they are open and closed, with the warning line, while sending; the Waiting list with 5 and with 338 queued moves (2.3); the same-name row (class S) in the wide, medium and compact bands with Edit names open; a class Q row with its own buttons plus Show both books, in the same three bands; the Place line with a long series name and each origin suffix. Futaba measures the rects (check 12).

**Contrast, dark tokens (the only theme).** Computed ratios, text against its background:

| Use | Pair | Ratio |
|---|---|---|
| `All done` badge text | `--notice-text` on `--notice` | 10.8:1 |
| `All done` badge edge against the panel | `--notice-border` on `--surface` | 5.0:1 (needs 3:1) |
| `Waiting for you` badge text and edge | `--warning` on `--surface` | 11.2:1 |
| `Background look-ups only` badge text | `--text` on `--raised` | 11.3:1 |
| its edge against the panel | `--border` on `--surface` | 4.1:1 (needs 3:1) |
| dialog text, titles, paths | `--text` on `--surface` | 13.9:1 |
| muted path folders, labels, result line | `--muted` on `--surface` | 8.9:1 |
| warning lines | `--warning` on `--surface` | 11.2:1 |
| quiet button text | `--accent` on `--surface` | 8.0:1 |
| default button text | `--on-accent` on `--accent` | 9.2:1 |
| disabled button text | `--disabled-text` on `--disabled` | 6.1:1 |
| focus ring | `--focus` on `--surface` | 11.2:1 |

Nothing new relies on colour alone: each state, warning and disabled reason is also words.

## 9. Acceptance checks (Futaba)

1. **All done is true.** Force every other state in turn (a conversion, a queued action, a timed cleanup retry, automatic processing between tries, a series look-up between tries, a detail look-up running, one book needing attention, one rename or move waiting for approval, a drive not answering (R14)): the badge never reads `All done`. Positive control: with all of them cleared it does, within 3 s, and the four lists are empty.
2. **Three badges.** Each of `All done`, `Waiting for you`, `Background look-ups only` shows for its state, and `Waiting for you` wins when both apply while the look-up item stays on screen.
3. **No bare `Nothing running`** in the status line in any state.
4. **No flicker.** A job under 1 s does not remove the badge.
5. **Counts behind.** At 45 s the badge is followed by `(as of …)`.
6. **Names.** A running series look-up reads `Finding series for finished audiobooks: <book>`, its step says no file is changed, and its count is the whole look-up (it does not start again at the next pass). Writing shows the writing step.
7. **Between tries.** With look-ups deferred and none running: a grouped Waiting item with a count and a next try time; the badge is `Background look-ups only`; no row carries `No progress for 5 min`.
8. **Dialog.** Opens from both entries. 55 books, all selected. Unselect 3, Rename or move: the engine receives exactly 52 and the digest shown. The result line shows beside the opener. A book whose folder stays the same reads `Renamed to`; one whose folder changes reads `Moves to`.
9. **Changed list.** Change the plan while the dialog is open, press Rename or move: nothing is changed, the warning line shows, the list is the new one.
10. **Leave as it is and Offer again (R11).** Leave as it is on 3 books: each goes under Left as they are with `Left as it is by you.`, the shortcut count drops by 3, the scroll position holds, and the app does not list them again by itself, for any kind of change. Offer again brings one back, selected. Leave the last waiting book as it is: the shortcut stays, reading `Renames and moves · 0`, and Offer again is still reachable.
11. **Same name (class S).** Two books the app would have filed by itself under one name: each row held for it reads `Same name as another book`, names the other's folder or file, has Approve disabled with its reason, and shows neither `Part of a bigger book` nor `Approve as one book`. Changing one title frees both.
12. **Layout, measured rects.** At 1280, 960, 760, 600 px and 200% zoom, long Cyrillic names: the toolbar rect is identical with and without the badge; no rect of the badge, block lines, shortcut buttons, dialog buttons or row buttons intersects another; the dialog's buttons stay in view with 200 books.
13. **Keyboard.** The dialog is fully usable without the mouse; focus returns as 3.5 says; Escape cancels except while sending.
14. **R4 row.** A volume with its own title tag and a series in its tags shows its own title and `· from the file's tags`, and carries no question.

Added 2026-11-22 after build:

15. **Own question kept (class Q, G9).** Pieces of one book that all carry the set's name, each a `Part of a bigger book` row with `shared` set: every row still reads `Part of a bigger book` with its own sentence, still has `Approve as one book` (disabled, with R17's reason line `Another book would get this name. Join them into one book, or change this title.`) and `Keep as separate books` (enabled), its label reads `All N go to`, and it has Show both books. None reads `Same name as another book`. Typing a free title enables the approve press at once. Positive control for the split: a class S pair on the same list (check 11) reads `Same name as another book`, so both presentations are seen from the same `shared` fact.
16. **Line and control together (G4).** In the build offered for release, the Waiting-for-you line 2, the status part `N renames and moves to approve` and the list shortcut never show without the dialog behind them.
17. **Still counting (G1, G2).** In the 2 minutes after the last book finishes, and in the 3 s before a badge comes up, the status line starts with `Checking what is left`: never with the counts, never with `…could be read`. With a source really unread for 3 s it reads `Nothing running that could be read`.
18. **Paused beside a look-up (G7).** Pause with only a series look-up running: the line starts `Paused · Finding series for finished audiobooks: <book>`.
19. **Tries tooltip (G8, R16).** Both look-up items' tooltips print the engine's tries per source and hours apart (3 and 6 today, each look-up its own numbers); change the engine's numbers and the tooltip follows. The no-limit sentence appears nowhere.

Added 2026-11-22, Sergei's answers:

20. **Every kind in one list (R10).** A plan with a series found, an author-folder change, a series-name change, a book with two kinds, and an in-place rename: the dialog shows the groups `Series found`, `Author folder`, `Series name` in that order; the two-kind book is listed once, in its first group, with both parts on line 1; the group counts add up to the title's number and to the shortcut's; the in-place book reads `Renamed to`. Unselect a group with its checkbox: the button's number drops by that group's count, and a folded group's summary says how many are selected.
21. **Held books (R12).** A finished audiobook written in Chinese or Japanese with a series found: it is not in any group and not in the count; it is under Left as they are with `Written in Chinese or Japanese: held until its series has an English name.`, with no button. With only such books left, the badge is not `Waiting for you` (Question 11's default).
22. **Whole book (R11).** Leave as it is on a book with an author-folder change and a series found: neither is done, the file and its place are untouched, and the book is not offered again for either.
23. **Window title (R13).** Force each engine state: the main window's title is the one in table 1.5, and it changes with the status line, never ahead of the badge. No taskbar flash, no focus change.
24. **Many approved at once.** Approve 340: the Waiting list shows one grouped item `Moving finished audiobooks: N books`, not 340 items; with 5 queued, five items.
25. **Title tag (R15).** A file whose only clue is the title tag `Sprawl Trilogy 01 - Neuromancer`: no question on its row, title `Neuromancer`, Place line `Series: Sprawl Trilogy · No. 1` with the tag suffix of 4.3.

## Notes for Ender

What the page needs from the engine, in plain words. How is yours.

**Section 1**
- One finished-state value per poll, decided by the engine from live facts: working, paused, continues by itself, waiting for you, background look-ups only, all done; and "not known" while a source is unread. The truth rules are table 1.1 and its bullets.
- For every row and Waiting item: whether it is a background look-up (so the page never guesses which work is "main").
- Counts: renames and moves waiting for approval; background look-ups left (series and detail, apart and together); drives not answering; books on hold (existing).
- Amended, Sergei's answers (R8, R10, R11, R12): that count is books, and it is every book the plan would change that he can approve now: every kind of change (series found, author folder, series name), moves and in-place writes alike, **less** the books he left as they are and the books R12 holds. It must equal the number of books the dialog lists in its groups.
- The reasons something waits for him, as keys (attention, renames and moves, hold, drive). A book R12 holds is not one of them (Question 11's default).
- Amended, Sergei's answers (R13): nothing new for the window title. It is made from the state the page already has. If the shell does not take its title from the page (F3), that is the one thing to wire.
- Amended after build (G1): when the state is "not known", whether a source is unread or the engine is still counting. The page reads this today from the unread list being empty; that is enough.

**Section 2**
- For the series and the detail look-up rows: done and total over the whole look-up (settled books, all books that needed it), and the step (looking up, writing).
- For each look-up between tries: how many books wait, the time of the next try, the tries limit. Amended after build (G8): the limit is tries per source, and the tooltip also prints the hours between tries, so the page needs that number too; without it that part of the sentence is left out.
- For a series write held by a job: the book, and a blocker object of the 0.30.0 shape.
- A look-up that waits on a source's pacing is not a running row.
- A real end: each book is settled after a limited number of tries (the limit is a product number, not mine). Amended, Sergei's answers: both look-ups have one now (R9: 3 per source, 6 hours apart; R16: the detail look-up the same). The detail look-up's Waiting item needs its own tries per source and hours apart, as the series item has; the page prints one sentence for both.
- Question 4 was answered no: nothing is needed for books a look-up gave up on.
- Amended, Sergei's answers (2.3): approved moves that wait as queued actions are grouped above 5. Confirm that an approved move does wait as a queued action of its own (the plan's note says "queued like a Choose folder move"). If approved moves wait some other way, tell me how they show and I will word that instead.

**Section 3**
Amended 2026-11-22, Sergei's answers. This list replaces the earlier one; it is everything the dialog of section 3 needs.

- The count of books waiting (Section 1 above says what is in it).
- The list of books he can approve. Per book: its id, title, the author it is filed under now, its current and new path (shown under Audiobooks Sorted, and whole), and **each kind of change it has, with that kind's own value**:
  - series found: the series name, the number, the source's name and address;
  - author folder: the new folder's name;
  - series name: the new name.
  The plan's own reason text (`why`) is an engine sentence and is never printed, so these values must come as fields.
- Whether a book was approved and then not changed, with a reason key (file changed; new name or place changed).
- The list's fingerprint (the existing digest), sent back with the approval and the selected books.
- The page groups the books by kind and tells `Moves to` from `Renamed to` by comparing the two folders; nothing more is needed for either.
- The books left as they are. Per book: a reason key (table 3.4), never a sentence. Two keys are new: **left as it is by him**, and **held because its original is Chinese or Japanese** (R12). For R12 the page needs nothing but the key.
- New: **leave a book as it is** (R11). It is recorded for the book, not for a series or a kind of change: the book leaves the plan and the count and is never offered again by itself, whatever the app finds for it later. And **take that back** (Offer again): the book is planned again from scratch.
- The approve answer per book: accepted, or refused with a reason key.
- An approved change that then fails comes back to the list or to Left as they are. Today such a book drops out of the plan (`series_backfill` holds it with a reason the plan does not read).
- R12's hold is the engine's: the page never decides from a language field which books are held.
- A fact I could not settle from the code: for an author-folder change and a series-name change, is anything written into the file, or is the book only renamed and moved? The dialog's body says a series found is written into the file and says nothing about the other two. If they write too, tell me and I will add the sentence.

**Section 4**
- The new hold as its own reason on a row: the shared destination, how many others, and for each other book its id, whether it is a row or a queued book, and a name that tells it apart (its folder or file name, different from this row's).
- A code for Approve refused by a late clash.
- Its count under Name taken (or its own key the page adds to that chip).
- For R4: where a row's series and number came from (file tags, a named online source, entered by him), and for the details line, that the title came from the file's own title tag.
- Amended after build (G9): the split of 4.1 needs the row's own hold kind, apart from `destination.shared` (whose `kind` is `same_destination` on every row that has it). If the row does not carry it, add it; nothing else is missing. `shared` must keep coming with the `Goes to` preview, so a typed name that is free clears the label and the disabled press at once.
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
- A2. Amended, Sergei's answers: the page control covers every change the engine's plan holds for a finished audiobook (R10), in-place series writes included (R8: 282 flat-named books), less R12's books. R6's re-check of already-sorted books is a studio job and has no page surface.
- A3. Settled (R14): a drive that is not answering holds back `All done`. A book on hold does too, as before.
- A10 (Sergei's answers). R12 holds the whole book, whatever kinds of change it has: the ruling names the books, not the series change. If only its series change should be held and an author-folder change may go ahead, the engine sends that book in the list with the kinds it may have, and the page needs no change.
- A11 (Sergei's answers). A book R12 holds does not wait for him and is not background work, so it does not hold back `All done` (Question 11 asks).
- A12 (Sergei's answers). An approved move waits as a queued action of its own (the plan's note; not run). The grouping in 2.3 rests on it.
- A4. A paused queue with nothing pending still reads `Paused`.
- A5. `showInList` with the shared title lists both same-name rows (it searches by title in the candidates view). If it cannot, the engine's ids of the other books are used.
- A6. The detail look-up records answers and renames no finished audiobook (`gap_fill.py` docstring; Scope: "92 finished books have a recorded English title never applied").
- A7. Settled by the build: the guard holds every series write until approval, so the `Finding series…` tooltip now says a found series changes a book only after he approves it (2.1).
- A9 (added after build). On a class Q row the engine refuses the approve press while `shared` is set, set-mates included (`_approve_once` checks every row; read in `merge_service.py`). The page's disabled press in 4.2a rests on that.
- A8. One theme (dark). A light theme, if added, uses the same tokens and needs its own ratios.

## Open questions (facts the docs and code did not settle)

- F1. Settled by the build: no. A guard holds every series write into a finished file until approval, so the writing step shows only after one.
- F2. Settled (R9, R16): both look-ups, 3 tries per source, 6 hours apart; the copy prints the engine's numbers. Still open: how many tries before a waiting book converts (section 5, R2 says "a few").
- F3. Does the Electron shell take its window title from the page? R13 makes the title part of 0.31.0, so this needs Ender's answer before 1.5 is built. (`desktop/main.js` gives the window the title `Books Arranger` and the page has the same `<title>`; I did not run it.)
- F5 (Sergei's answers). Does an author-folder change or a series-name change write anything into the file? (Notes for Ender, Section 3.)
- F4. Whether the series look-up of finished books keeps running after R6's job (Scope: not ruled). If it stops, section 2's series row and item simply never appear.

## Questions for Sergei: answered (2026-11-22)

Questions 1 to 9 are closed. The answers, as ruled in the Scope's second round:

1. The approval list: series only, or all? **All: every kind of change the plan holds, author folders too** (R10). I had recommended series only; section 3 is rewritten for all.
2. `Leave as it is`: the book or the series? **The book, for good; it can be taken back** (R11).
3. Books written in Chinese or Japanese: hold or let them move now? **Hold them out of the list until English series names ship** (R12).
4. A count and Try again for look-ups that gave up? **No.**
5. A `Convert now` button on a book waiting for the online answer (next version)? **No.**
6. The state in the window title? **Yes** (R13).
7. Does a drive that is not answering hold back `All done`? **Yes** (R14).
8. The same limit for the titles-and-author-names look-up? **Yes: 3 tries per source** (R16).
9. May the blocked press say `Join them into one book, or change this title.`? **Yes, only on a blocked press** (R17).

## Questions for Sergei: open (one word each)

Opened by the answers above. Each has a default, and the default is what is built until he answers.

10. A book with two kinds of change, say a new author folder and a series found: `Leave as it is` refuses both, because R11 is about the book. If the series is wrong and the author folder is right, that book keeps its old author folder. Should he be able to refuse the series alone and let the author folder go ahead? I recommend **no** for now: it is one book at a time, and Offer again brings it back. no / yes
11. A book R12 holds waits for the app to learn English series names, not for him and not for any job. Does it hold back `All done`? I recommend **no**: otherwise `All done` could not show until that ships. It stays listed under Left as they are with its reason. no / yes
